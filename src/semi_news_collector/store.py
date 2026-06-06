from __future__ import annotations

import sqlite3
from pathlib import Path
from types import TracebackType


class SeenStore:
    def __init__(self, path: str):
        self.path = Path(path)
        self.connection: sqlite3.Connection | None = None

    def __enter__(self) -> "SeenStore":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_items (
                item_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                link TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.connection.commit()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self.connection:
            self.connection.close()

    def has_seen(self, item_id: str) -> bool:
        assert self.connection is not None, "SeenStore must be used as a context manager"
        cursor = self.connection.execute("SELECT 1 FROM seen_items WHERE item_id = ?", (item_id,))
        return cursor.fetchone() is not None

    def mark_seen(self, item_id: str, title: str, link: str) -> None:
        assert self.connection is not None, "SeenStore must be used as a context manager"
        self.connection.execute(
            "INSERT OR IGNORE INTO seen_items (item_id, title, link) VALUES (?, ?, ?)",
            (item_id, title, link),
        )
        self.connection.commit()
