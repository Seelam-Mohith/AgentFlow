import asyncio
import json
import os
import sys
import pytest
from pydantic import ValidationError
from backend.ai import interpret, summarize
from backend.models import Intent, CrawlOutput
from backend.runner import command_for, run_cli
from backend.crawler import extract
from backend.manager import Manager
from backend.store import Store


@pytest.fixture(autouse=True)
def no_api_key(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)


async def test_intent():
    intent, mode = await interpret('Crawl https://example.com and summarize 2 pages as JSON.')
    assert intent.url == 'https://example.com/'
    assert intent.max_pages == 2
    assert mode == 'deterministic'


@pytest.mark.parametrize('message', ['crawl this site', 'run shell https://example.com', 'crawl http://127.0.0.1', 'crawl https://example.com 999 pages'])
async def test_invalid_intents(message):
    with pytest.raises(ValueError):
        await interpret(message)


def test_command_allowlist():
    argv = command_for(Intent(url='https://example.com'))
    assert argv[:3] == [sys.executable, '-m', 'backend.cli.site_crawler']
    assert '--url' in argv
    with pytest.raises(ValueError): command_for(Intent(url='https://example.com'), 'bash')
    with pytest.raises(ValueError): command_for(Intent(url='https://user:password@example.com'))


async def test_subprocess_capture_and_nonzero():
    execution = await run_cli(Intent(url='https://example.com'), lambda *a: None, lambda *a: None, command=[sys.executable, '-c', 'import sys; print("{\\\"ok\\\":true}"); print("diagnostic",file=sys.stderr); sys.exit(7)'])
    assert json.loads(execution.stdout) == {'ok': True}
    assert execution.stderr.strip() == 'diagnostic'
    assert execution.exit_code == 7


async def test_timeout_kills_process():
    processes = []
    output = await run_cli(Intent(url='https://example.com'), lambda p,a: processes.append(p), lambda line: None, timeout=.2, command=[sys.executable, '-c', 'import time; time.sleep(30)'])
    assert 'timed out' in output.error
    assert processes[0].returncode is not None


async def test_cancel_kills_process():
    processes = []
    started = asyncio.Event()
    def on_start(p, a): processes.append(p); started.set()
    job = asyncio.create_task(run_cli(Intent(url='https://example.com'), on_start, lambda line: None, command=[sys.executable, '-c', 'import time; time.sleep(30)']))
    await asyncio.wait_for(started.wait(), 5)
    job.cancel()
    with pytest.raises(asyncio.CancelledError): await job
    assert processes[0].returncode is not None


async def test_output_limit():
    result = await run_cli(Intent(url='https://example.com'), lambda *a: None, lambda *a: None, output_limit=100, command=[sys.executable, '-c', 'print("x"*5000)'])
    assert 'capture limit' in result.error
    assert len(result.stdout) <= 100


def test_invalid_output_schema():
    with pytest.raises(ValidationError): CrawlOutput.model_validate_json('{"pages":"bad"}')


async def test_extract_summary_grounded():
    page = extract('https://example.com/', '<title>Example</title><p>Only actual content.</p>')
    result, mode = await summarize(CrawlOutput(pages=[page], errors=[], status='completed'), '')
    assert result.summary == 'Only actual content.'
    assert result.key_findings[0].source_url == page.url
    assert mode == 'extractive'


async def test_manager_rejects_malformed_json(monkeypatch):
    import backend.manager as module
    from backend.runner import Execution
    async def resolve(*args): return ['93.184.216.34']
    async def broken(*args): return Execution('not json', '', 0)
    monkeypatch.setattr(module, 'resolve_public', resolve)
    monkeypatch.setattr(module, 'run_cli', broken)
    store = Store(':memory:')
    manager = Manager(store)
    task = manager.create('Crawl https://example.com')
    await manager.jobs[task['task_id']]
    saved = store.get(task['task_id'])
    assert saved['status'] == 'failed'
    assert 'malformed' in saved['execution']['errors'][0]
    store.db.close()


@pytest.mark.live
@pytest.mark.skipif(os.getenv('AGENTFLOW_LIVE_TEST') != '1', reason='Set AGENTFLOW_LIVE_TEST=1 for real public network execution')
async def test_live_api_to_real_cli():
    from backend.main import app
    import httpx
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            response = await client.post('/api/chat', json={'message': 'Crawl https://example.com, extract important information, give me a summary, and return JSON.'})
            assert response.status_code == 202
            task_id = response.json()['task_id']
            for _ in range(120):
                task = (await client.get(f'/api/tasks/{task_id}')).json()
                if task['status'] in ('completed','partial','failed','cancelled'): break
                await asyncio.sleep(.6)
            assert task['status'] == 'completed', task['execution']['errors']
            assert task['execution']['exit_code'] == 0
            assert task['result']['website_title'] == 'Example Domain'
            assert task['result']['total_pages_crawled'] >= 1
            assert 'backend.cli.site_crawler' in task['execution']['command']
            assert task['result']['summary']
            assert json.loads(task['execution']['stdout'])['pages']
