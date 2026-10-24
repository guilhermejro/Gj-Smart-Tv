"""Fontes IPTV, favoritos, histórico e preferências (tudo local, em SQLite)."""
from typing import List, Optional

from app.config import HISTORY_LIMIT
from app.database import Database
from app.models.channel import Channel
from app.models.playlist import Source
import sqlite3

from app.utils.secrets import PREFIX, protect, unprotect
from app.utils.url import validate_url

SCHEMA_VERSION = 2


def _src(r) -> Source:
    return Source(r["id"], r["name"], unprotect(r["url"]), bool(r["active"]), bool(r["is_default"]))


def _chan(r) -> Channel:
    return Channel(name=r["name"], url=unprotect(r["url"]), group=r["group_title"] or "Sem categoria",
                   logo=r["logo"] or "")


class SettingsService:
    def __init__(self, db: Database):
        self.db = db
        self._migrate()

    def _migrate(self) -> None:
        """v2: URLs protegidas em repouso e chaves de canal sem URL em texto puro."""
        if self.db.query("PRAGMA user_version")[0][0] >= SCHEMA_VERSION:
            return
        for r in self.db.query("SELECT id, url FROM sources"):
            if not r["url"].startswith(PREFIX):
                self.db.execute("UPDATE sources SET url=? WHERE id=?", (protect(r["url"]), r["id"]))
        for table in ("favorites", "history"):
            for r in self.db.query(f"SELECT channel_key, name, url FROM {table}"):
                plain = unprotect(r["url"])
                new_key = Channel(r["name"], plain).key
                try:
                    self.db.execute(f"UPDATE {table} SET channel_key=?, url=? WHERE channel_key=?",
                                    (new_key, protect(plain), r["channel_key"]))
                except sqlite3.IntegrityError:
                    self.db.execute(f"DELETE FROM {table} WHERE channel_key=?", (r["channel_key"],))
        self.db.execute(f"PRAGMA user_version={SCHEMA_VERSION}")

    # ---- fontes ----
    def add_source(self, name: str, url: str) -> Source:
        url = validate_url(url)
        name = (name or "").strip() or "Minha IPTV"
        first = not self.db.query("SELECT 1 FROM sources LIMIT 1")
        cur = self.db.execute(
            "INSERT INTO sources(name,url,active,is_default) VALUES(?,?,1,?)", (name, protect(url), int(first))
        )
        return self.get_source(cur.lastrowid)

    def get_source(self, source_id: int) -> Optional[Source]:
        rows = self.db.query("SELECT * FROM sources WHERE id=?", (source_id,))
        return _src(rows[0]) if rows else None

    def list_sources(self) -> List[Source]:
        return [_src(r) for r in self.db.query("SELECT * FROM sources ORDER BY id")]

    def has_sources(self) -> bool:
        return bool(self.db.query("SELECT 1 FROM sources LIMIT 1"))

    def update_source(self, source_id: int, name: str, url: str) -> None:
        self.db.execute("UPDATE sources SET name=?, url=? WHERE id=?",
                        ((name or "").strip() or "Minha IPTV", protect(validate_url(url)), source_id))

    def set_active(self, source_id: int, active: bool) -> None:
        self.db.execute("UPDATE sources SET active=? WHERE id=?", (int(active), source_id))

    def set_default(self, source_id: int) -> None:
        self.db.execute("UPDATE sources SET is_default=0")
        self.db.execute("UPDATE sources SET is_default=1, active=1 WHERE id=?", (source_id,))

    def delete_source(self, source_id: int) -> None:
        was_default = (self.get_source(source_id) or Source(0, "", "")).is_default
        self.db.execute("DELETE FROM sources WHERE id=?", (source_id,))
        if was_default:
            rows = self.db.query("SELECT id FROM sources WHERE active=1 ORDER BY id LIMIT 1")
            if rows:
                self.set_default(rows[0]["id"])

    def default_source(self) -> Optional[Source]:
        rows = self.db.query("SELECT * FROM sources WHERE is_default=1 AND active=1 LIMIT 1") \
            or self.db.query("SELECT * FROM sources WHERE active=1 ORDER BY id LIMIT 1")
        return _src(rows[0]) if rows else None

    # ---- favoritos ----
    def is_favorite(self, ch: Channel) -> bool:
        return bool(self.db.query("SELECT 1 FROM favorites WHERE channel_key=?", (ch.key,)))

    def toggle_favorite(self, ch: Channel) -> bool:
        if self.is_favorite(ch):
            self.db.execute("DELETE FROM favorites WHERE channel_key=?", (ch.key,))
            return False
        self.db.execute("INSERT INTO favorites VALUES(?,?,?,?,?)", (ch.key, ch.name, protect(ch.url), ch.group, ch.logo))
        return True

    def favorites(self) -> List[Channel]:
        return [_chan(r) for r in self.db.query("SELECT * FROM favorites ORDER BY rowid")]

    # ---- histórico ----
    def add_history(self, ch: Channel) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO history(channel_key,name,url,group_title,logo,accessed_at) "
            "VALUES(?,?,?,?,?,datetime('now'))", (ch.key, ch.name, protect(ch.url), ch.group, ch.logo))
        self.db.execute(
            "DELETE FROM history WHERE channel_key NOT IN "
            "(SELECT channel_key FROM history ORDER BY accessed_at DESC, rowid DESC LIMIT ?)", (HISTORY_LIMIT,))

    def history(self, limit: int = 20) -> List[Channel]:
        return [_chan(r) for r in self.db.query(
            "SELECT * FROM history ORDER BY accessed_at DESC, rowid DESC LIMIT ?", (limit,))]

    def clear_history(self) -> None:
        self.db.execute("DELETE FROM history")

    # ---- preferências ----
    def get(self, key: str, default: str = "") -> str:
        rows = self.db.query("SELECT value FROM settings WHERE key=?", (key,))
        return rows[0]["value"] if rows else default

    def set(self, key: str, value) -> None:
        self.db.execute("INSERT OR REPLACE INTO settings VALUES(?,?)", (key, str(value)))
