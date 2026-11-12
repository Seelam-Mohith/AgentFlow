import asyncio
import json
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from backend.manager import Manager, TERMINAL
from backend.models import ChatRequest, Intent, TaskRecord
from backend.store import Store


@asynccontextmanager
async def lifespan(app):
    store = Store()
    app.state.manager = Manager(store)
    yield
    await app.state.manager.close()
    store.db.close()


app = FastAPI(title='AgentFlow', version='1.0.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[os.getenv('FRONTEND_ORIGIN', 'http://localhost:3000')], allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])


def manager(request: Request):
    return request.app.state.manager


def get_task(request, task_id):
    task = manager(request).store.get(task_id)
    if task is None:
        raise HTTPException(404, 'Task not found.')
    return task


@app.get('/api/health')
async def health():
    return {'status': 'ok', 'ai_configured': bool(os.getenv('OPENAI_API_KEY')), 'tool': 'site_crawler'}


@app.post('/api/chat', status_code=202, response_model=TaskRecord)
async def chat(payload: ChatRequest, request: Request):
    try:
        return manager(request).create(payload.message)
    except ValueError as exc:
        raise HTTPException(429, str(exc)) from None


@app.post('/api/tasks', status_code=202, response_model=TaskRecord)
async def create_task(payload: Intent, request: Request):
    try:
        return manager(request).create(f'Crawl {payload.url}', payload)
    except ValueError as exc:
        raise HTTPException(429, str(exc)) from None


@app.get('/api/tasks', response_model=list[TaskRecord])
async def tasks(request: Request):
    return manager(request).store.list()


@app.get('/api/tasks/{task_id}', response_model=TaskRecord)
async def task(task_id: str, request: Request):
    return get_task(request, task_id)


@app.post('/api/tasks/{task_id}/cancel', response_model=TaskRecord)
async def cancel(task_id: str, request: Request):
    get_task(request, task_id)
    return await manager(request).cancel(task_id)


@app.get('/api/tasks/{task_id}/events')
async def events(task_id: str, request: Request):
    get_task(request, task_id)
    try:
        cursor = max(0, int(request.headers.get('last-event-id', '0')))
    except ValueError:
        cursor = 0

    async def stream():
        nonlocal cursor
        while not await request.is_disconnected():
            current = get_task(request, task_id)
            for event in current['events'][cursor:]:
                yield f'id: {event["id"]}\nevent: progress\ndata: {json.dumps(event)}\n\n'
                cursor = event['id']
            if current['status'] in TERMINAL:
                yield f'event: done\ndata: {json.dumps(current)}\n\n'
                break
            yield ': heartbeat\n\n'
            await asyncio.sleep(.4)
    return StreamingResponse(stream(), media_type='text/event-stream', headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

