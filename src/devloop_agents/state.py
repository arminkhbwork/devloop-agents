from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Iterator


class LeaseBusy(RuntimeError):
    pass


class StateStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS leases (
                resource TEXT PRIMARY KEY,
                owner TEXT NOT NULL,
                expires_at TEXT NOT NULL
                )"""
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    @contextmanager
    def lease(self, resource: str, owner: str, ttl_seconds: int = 3600) -> Iterator[None]:
        now = datetime.now(UTC)
        expires = (now + timedelta(seconds=ttl_seconds)).isoformat()
        with self._connect() as connection:
            connection.execute("DELETE FROM leases WHERE expires_at < ?", (now.isoformat(),))
            try:
                connection.execute(
                    "INSERT INTO leases(resource, owner, expires_at) VALUES (?, ?, ?)",
                    (resource, owner, expires),
                )
                connection.commit()
            except sqlite3.IntegrityError as error:
                raise LeaseBusy(f"Resource is already leased: {resource}") from error
        try:
            yield
        finally:
            with self._connect() as connection:
                connection.execute(
                    "DELETE FROM leases WHERE resource = ? AND owner = ?", (resource, owner)
                )
                connection.commit()

