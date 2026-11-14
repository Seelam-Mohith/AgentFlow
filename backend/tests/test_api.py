import asyncio
import httpx
import pytest
from backend.main import app
from backend.store import Store
from backend.models import TaskRecord


@pytest.fixture
async def client(monkeypatch, tmp_path):
    import backend.main as module
    monkeypatch.setattr(module, 'Store', lambda: Store(str(tmp_path / 'test.db')))
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as session:
            yield session


async def test_api_validation_and_unknown_task(client):
    assert (await client.get('/api/health')).json()['status'] == 'ok'
    assert (await client.post('/api/chat', json={'message': ''})).status_code == 422
    assert (await client.post('/api/tasks', json={'url':'https://example.com', 'max_pages':999})).status_code == 422
    assert (await client.get('/api/tasks/absent')).status_code == 404
    assert (await client.post('/api/tasks/absent/cancel')).status_code == 404


async def test_failed_task_history_and_sse(client):
    response = await client.post('/api/chat', json={'message':'Crawl http://127.0.0.1'})
    assert response.status_code == 202
    task_id = response.json()['task_id']
    for _ in range(20):
        await asyncio.sleep(.01)
        current = (await client.get('/api/tasks/' + task_id)).json()
        if current['status'] == 'failed': break
    TaskRecord.model_validate(current)
    assert current['status'] == 'failed'
    assert current['execution']['command'] == []
    assert (await client.get('/api/tasks')).json()[0]['task_id'] == task_id
    events = await client.get(f'/api/tasks/{task_id}/events', headers={'Last-Event-ID':'0'})
    assert 'event: progress' in events.text and 'event: done' in events.text
    assert (await client.post(f'/api/tasks/{task_id}/cancel')).json()['status'] == 'failed'


def test_restart_marks_interrupted_task_failed(tmp_path):
    from backend.manager import Manager
    # Use a saved minimal record, since persistence recovery does not run worker processes.
    path = str(tmp_path / 'recover.db')
    store = Store(path)
    store.save({'task_id':'interrupted','created_at':'2026-01-01','status':'running','execution':{'errors':[]}})
    store.db.close()
    reopened = Store(path)
    task = reopened.get('interrupted')
    assert task['status'] == 'failed'
    assert 'restarted' in task['execution']['errors'][0]
    reopened.db.close()
