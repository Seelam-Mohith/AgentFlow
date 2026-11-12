import json
import sqlite3
from backend.config import DATABASE


class Store:
    def __init__(self, path=DATABASE):
        self.db = sqlite3.connect(path)
        self.db.execute('CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, created TEXT NOT NULL, payload TEXT NOT NULL)')
        self.db.commit()
        # A restarted server cannot recover process ownership; never leave stale running jobs.
        for task in self.list(10000):
            if task['status'] in ('queued', 'running'):
                task['status'] = 'failed'
                task['execution']['errors'].append('Server restarted during execution. Rerun this task.')
                self.save(task)

    def save(self, task):
        self.db.execute('INSERT OR REPLACE INTO tasks VALUES (?, ?, ?)', (task['task_id'], task['created_at'], json.dumps(task)))
        self.db.commit()

    def get(self, task_id):
        row = self.db.execute('SELECT payload FROM tasks WHERE id=?', (task_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def list(self, limit=100):
        return [json.loads(row[0]) for row in self.db.execute('SELECT payload FROM tasks ORDER BY created DESC LIMIT ?', (limit,))]

