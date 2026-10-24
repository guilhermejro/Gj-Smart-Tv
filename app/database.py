"""Persistência SQLite (fontes, favoritos, histórico e preferências)."""
import sqlite3
import threading
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    is_default INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS favorites(
    channel_key TEXT PRIMARY KEY,
    name TEXT NOT NULL, url TEXT NOT NULL, group_title TEXT, logo TEXT
);
CREATE TABLE IF NOT EXISTS history(
    channel_key TEXT PRIMARY KEY,
    name TEXT NOT NULL, url TEXT NOT NULL, group_title TEXT, logo TEXT,
    accessed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


class Database:
    def __init__(self, path):
        self._lock = threading.RLock()
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        with self._lock:
            self.conn.execute("PRAGMA secure_delete=ON")  # apaga o conteúdo de verdade (ex.: histórico)
            self.conn.executescript(SCHEMA)
            self.conn.commit()
        if str(path) != ":memory:":
            from app.config import restrict_permissions
            restrict_permissions(Path(path))

    def execute(self, sql, params=()):
        with self._lock:
            cur = self.conn.execute(sql, params)
            self.conn.commit()
            return cur

    def query(self, sql, params=()):
        with self._lock:
            return self.conn.execute(sql, params).fetchall()

    def close(self):
        with self._lock:
            self.conn.close()
