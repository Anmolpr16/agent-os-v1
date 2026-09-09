import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


SCHEMA = (
    Path(__file__).resolve().parents[2]
    / "memory"
    / "schema.sql"
)


class MemoryStore:
    """V1 persistent memory backed by SQLite."""

    def __init__(self, path: str = "agent_os.db"):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row

        schema = SCHEMA.read_text(encoding="utf-8")
        self.conn.executescript(schema)

    def add_memory(
        self,
        content: str,
        kind: str = "semantic",
        source_id: int | None = None,
        metadata: dict | None = None,
    ) -> int:

        cur = self.conn.execute(
            """
            INSERT INTO memory_items
            (
                kind,
                content,
                source_id,
                metadata_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                kind,
                content,
                source_id,
                json.dumps(metadata or {}),
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        self.conn.commit()

        return int(cur.lastrowid)

    def search(
        self,
        query: str,
        limit: int = 10,
    ):
        pattern = f"%{query}%"

        return self.conn.execute(
            """
            SELECT *
            FROM memory_items
            WHERE content LIKE ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (pattern, limit),
        ).fetchall()

    def close(self) -> None:
        self.conn.close()
