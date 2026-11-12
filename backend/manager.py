import asyncio
import time
import uuid
from datetime import datetime, timezone
from backend.ai import interpret, summarize
from backend.models import Intent, CrawlOutput, TaskResult
from backend.runner import run_cli, sanitize
from backend.security import validate_url, resolve_public
from urllib.parse import urlsplit

TERMINAL = {'completed', 'partial', 'failed', 'cancelled'}
STAGES = ['Understanding request', 'Validating input', 'Preparing CLI command', 'Running crawler', 'Extracting information', 'Generating summary', 'Validating output', 'Completed']


class Manager:
    def __init__(self, store):
        self.store, self.jobs, self.processes = store, {}, {}

    def event(self, task, stage, message):
        if len(task['events']) < 500:
            task['events'].append({'id': len(task['events']) + 1, 'stage': stage, 'message': sanitize(message), 'time': datetime.now(timezone.utc).isoformat()})
        task['stage'] = stage
        self.store.save(task)

    def create(self, message: str, intent: Intent | None = None):
        if sum(not job.done() for job in self.jobs.values()) >= 4:
            raise ValueError('Four tasks are already running. Wait or cancel a task.')
        self.jobs = {key: value for key, value in self.jobs.items() if not value.done()}
        task = {'task_id': 'task_' + uuid.uuid4().hex[:12], 'task_type': 'website_crawl', 'message': message, 'status': 'queued', 'created_at': datetime.now(timezone.utc).isoformat(), 'stage': 0, 'input': None, 'result': None, 'events': [], 'execution': {'tool': 'site_crawler', 'command': [], 'started_at': None, 'exit_code': None, 'duration_seconds': 0, 'stdout': '', 'stderr': '', 'errors': [], 'intent_mode': None, 'summary_mode': None}}
        self.store.save(task)
        self.jobs[task['task_id']] = asyncio.create_task(self.execute(task, intent))
        return task

    async def execute(self, task, intent):
        started = time.monotonic()
        execution = task['execution']
        try:
            task['status'] = 'running'
            execution['started_at'] = datetime.now(timezone.utc).isoformat()
            self.event(task, 0, 'Request received. Interpreting website task.')
            if intent is None:
                intent, execution['intent_mode'] = await interpret(task['message'])
            else:
                execution['intent_mode'] = 'validated API task'
            task['input'] = intent.model_dump()
            self.event(task, 1, 'Intent identified. Validating URL and public DNS addresses.')
            intent.url = validate_url(intent.url)
            parts = urlsplit(intent.url)
            await resolve_public(parts.hostname, parts.port or (443 if parts.scheme == 'https' else 80))
            self.event(task, 2, 'URL validated. Selected approved site_crawler workflow.')

            def on_start(process, argv):
                self.processes[task['task_id']] = process
                execution['command'] = ['python', *argv[1:]]
                self.event(task, 3, f'CLI process started (PID {process.pid}).')

            def on_log(line):
                self.event(task, 4 if 'Page extracted:' in line else 3, line)

            captured = await run_cli(intent, on_start, on_log)
            execution.update(stdout=sanitize(captured.stdout), stderr=captured.stderr, exit_code=captured.exit_code)
            if captured.error:
                raise ValueError(captured.error)
            self.event(task, 4, f'CLI exited with code {captured.exit_code}. Parsing machine-readable output.')
            try:
                output = CrawlOutput.model_validate_json(captured.stdout)
            except Exception:
                raise ValueError('CLI returned malformed output; JSON schema validation failed.') from None
            execution['errors'].extend(output.errors)
            if len(output.pages) > intent.max_pages:
                raise ValueError('Worker exceeded the validated page limit.')
            if output.status == 'completed' and output.errors:
                raise ValueError('Worker status contradicts reported errors.')
            if any(urlsplit(validate_url(page.url)).hostname != parts.hostname for page in output.pages):
                raise ValueError('Worker returned an unexpected source domain.')
            if captured.exit_code != 0 or output.status == 'failed' or not output.pages:
                raise ValueError('Crawler failed. ' + ('; '.join(output.errors) or 'No useful pages returned.'))
            self.event(task, 5, f'{len(output.pages)} real pages extracted. Generating source-grounded summary.')
            summary, execution['summary_mode'] = await summarize(output, intent.instructions)
            self.event(task, 6, 'Validating result and source citations.')
            # Summary and pages are validated Pydantic objects; unavailable metadata remains null.
            task['result'] = {'website_url': intent.url, 'website_title': output.pages[0].title, 'description': output.pages[0].description, **summary.model_dump(), 'pages': [p.model_dump() for p in output.pages], 'total_pages_crawled': len(output.pages), 'source_urls': [p.url for p in output.pages]}
            task['result'] = TaskResult.model_validate(task['result']).model_dump()
            task['status'] = output.status
            self.event(task, 7, 'Final response ready.' if output.status == 'completed' else 'Partial results ready. Review crawl errors.')
        except asyncio.CancelledError:
            task['status'] = 'cancelled'
            execution['errors'].append('Cancelled by user. Running subprocess terminated.')
            self.event(task, task['stage'], 'Task cancelled.')
        except Exception as exc:
            task['status'] = 'failed'
            execution['errors'].append(sanitize(str(exc))[:2000])
            self.event(task, task['stage'], 'Task failed: ' + str(exc)[:1000])
        finally:
            process = self.processes.pop(task['task_id'], None)
            if process and execution['exit_code'] is None:
                execution['exit_code'] = process.returncode
            execution['duration_seconds'] = round(time.monotonic() - started, 3)
            self.store.save(task)

    async def cancel(self, task_id):
        job = self.jobs.get(task_id)
        if job and not job.done():
            # Let a newly scheduled coroutine enter its cancellation handler.
            await asyncio.sleep(0)
            job.cancel()
            await asyncio.gather(job, return_exceptions=True)
        return self.store.get(task_id)

    async def close(self):
        for task_id in list(self.jobs):
            await self.cancel(task_id)

