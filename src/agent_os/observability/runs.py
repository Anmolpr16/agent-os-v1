import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from agent_os.storage import Database


class RunRepository:
    """Persist complete agent run records in SQLite."""

    def __init__(
        self,
        connection: sqlite3.Connection | None = None,
        database: Database | None = None,
    ):
        if connection is None and database is None:
            raise ValueError("connection or database required")
        if connection is not None and database is not None:
            raise ValueError("provide either connection or database, not both")

        self.database = database
        self.conn = (
            database.conn
            if database is not None
            else connection
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS run_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                state TEXT NOT NULL,
                event_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_run_events_task
            ON run_events(task_id)
            """
        )
        self.conn.commit()

    def record(
        self,
        task_id: str,
        state: str,
        event: dict[str, Any],
    ) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO run_events
            (
                task_id,
                state,
                event_json,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                task_id,
                state,
                json.dumps(
                    event,
                    sort_keys=True,
                    default=str,
                ),
                datetime.now(
                    timezone.utc
                ).isoformat(),
            ),
        )

        self.conn.commit()

        return int(cur.lastrowid)

    def list_events(
        self,
        task_id: str,
    ) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT
                id,
                task_id,
                state,
                event_json,
                created_at
            FROM run_events
            WHERE task_id = ?
            ORDER BY id ASC
            """,
            (task_id,),
        ).fetchall()

        return [
            {
                "id": row[0],
                "task_id": row[1],
                "state": row[2],
                "event": json.loads(row[3]),
                "created_at": row[4],
            }
            for row in rows
        ]
