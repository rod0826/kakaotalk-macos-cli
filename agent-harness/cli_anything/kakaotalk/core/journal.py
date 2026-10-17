"""Only request IDs, hashes, timestamps and outcomes are persisted."""
import sqlite3
from pathlib import Path
from .errors import ToolError


class Journal:
    def __init__(self, path):
        self.path = Path(path)

    def connect(self):
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=5)
        self.path.chmod(0o600)
        connection.execute('CREATE TABLE IF NOT EXISTS requests '
            '(id TEXT PRIMARY KEY, digest TEXT NOT NULL, state TEXT NOT NULL, '
            'created TEXT DEFAULT CURRENT_TIMESTAMP)')
        return connection

    def claim(self, request_id, digest):
        with self.connect() as connection:
            try:
                connection.execute('INSERT INTO requests(id,digest,state) VALUES(?,?,?)',
                                   (request_id, digest, 'pending'))
            except sqlite3.IntegrityError:
                previous = connection.execute('SELECT digest FROM requests WHERE id=?', (request_id,)).fetchone()
                if previous[0] != digest:
                    raise ToolError('REQUEST_ID_CONFLICT', 'Request ID was used for different content.')
                raise ToolError('REQUEST_ALREADY_USED', 'Request already claimed; inspect KakaoTalk before any new request.')

    def finish(self, request_id, state):
        with self.connect() as connection:
            connection.execute('UPDATE requests SET state=? WHERE id=?', (state, request_id))

    def status(self):
        if not self.path.exists():
            return []
        with self.connect() as connection:
            connection.row_factory = sqlite3.Row
            return [dict(row) for row in connection.execute('SELECT id,state,created FROM requests ORDER BY created DESC LIMIT 100')]
