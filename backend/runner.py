import asyncio
import os
import re
import signal
import subprocess
import sys
from dataclasses import dataclass
from backend.config import ROOT, TIMEOUT
from backend.models import Intent
from backend.security import validate_url

TOOLS = {'site_crawler': 'backend.cli.site_crawler'}


def command_for(intent: Intent, tool='site_crawler') -> list[str]:
    intent = Intent.model_validate(intent.model_dump())
    if tool not in TOOLS:
        raise ValueError('Tool is not approved.')
    return [sys.executable, '-m', TOOLS[tool], '--url', validate_url(intent.url), '--max-pages', str(intent.max_pages), '--output', 'json']


def sanitize(value: str) -> str:
    value = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', value)
    value = ''.join(c for c in value if c in '\n\t' or ord(c) >= 32)
    for key, secret in os.environ.items():
        if any(word in key.upper() for word in ('KEY', 'TOKEN', 'SECRET', 'PASSWORD')) and len(secret) >= 8:
            value = value.replace(secret, '[REDACTED]')
    return value


async def terminate(process):
    if process.returncode is not None:
        return
    try:
        if os.name == 'nt':
            killer = await asyncio.create_subprocess_exec('taskkill', '/PID', str(process.pid), '/T', '/F', stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
            await killer.wait()
            if process.returncode is None:
                process.kill()
        else:
            os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    await process.wait()


@dataclass
class Execution:
    stdout: str
    stderr: str
    exit_code: int
    error: str | None = None


async def run_cli(intent: Intent, on_start, on_log, timeout=TIMEOUT, command=None, output_limit=1_500_000) -> Execution:
    # command override is internal test injection; no API accepts a command.
    argv = command if command is not None else command_for(intent)
    env = {key: value for key, value in os.environ.items() if key.upper() in {'PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'SSL_CERT_FILE', 'SSL_CERT_DIR', 'MAX_CRAWL_PAGES'}}
    env.update(PYTHONIOENCODING='utf-8', PYTHONUNBUFFERED='1')
    options = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session': True}
    process = await asyncio.create_subprocess_exec(*argv, cwd=ROOT, env=env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, **options)
    stdout, stderr = bytearray(), bytearray()
    readers = []

    async def read(stream, target, diagnostics=False):
        pending = ''
        while chunk := await stream.read(4096):
            target.extend(chunk)
            if len(stdout) + len(stderr) > output_limit:
                raise ValueError('CLI output exceeded the capture limit.')
            if diagnostics:
                pending += chunk.decode('utf-8', errors='replace')
                while '\n' in pending:
                    line, pending = pending.split('\n', 1)
                    on_log(sanitize(line)[:1000])
        if diagnostics and pending:
            on_log(sanitize(pending)[:1000])

    error = None
    try:
        on_start(process, argv)
        readers = [asyncio.create_task(read(process.stdout, stdout)), asyncio.create_task(read(process.stderr, stderr, True))]
        await asyncio.wait_for(asyncio.gather(*readers, process.wait()), timeout)
    except asyncio.CancelledError:
        await terminate(process)
        raise
    except Exception as exc:
        error = 'CLI execution timed out.' if isinstance(exc, asyncio.TimeoutError) else str(exc)
        await terminate(process)
    finally:
        for reader in readers:
            if not reader.done():
                reader.cancel()
        await asyncio.gather(*readers, return_exceptions=True)
    return Execution(stdout[:output_limit].decode('utf-8', errors='replace'), sanitize(stderr[:output_limit].decode('utf-8', errors='replace')), process.returncode, error)

