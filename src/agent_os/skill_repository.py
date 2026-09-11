from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from agent_os.skill_registry import SkillVersion
from agent_os.storage import Database


class SkillRepository:
    """Persist versioned skills and their evolution events in SQLite."""

    def __init__(
        self,
        connection: sqlite3.Connection | None = None,
        database: Database | None = None,
    ):
        if connection is None and database is None:
            raise ValueError("connection or database required")
        if connection is not None and database is not None:
            raise ValueError(
                "provide either connection or database, not both"
            )

        self.database = database
        self.conn = database.conn if database is not None else connection

        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS skill_versions (
                skill_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                instructions TEXT NOT NULL,
                examples_json TEXT NOT NULL DEFAULT '[]',
                constraints_json TEXT NOT NULL DEFAULT '[]',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                PRIMARY KEY (skill_id, version)
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS skill_evolution_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_id TEXT NOT NULL,
                base_version INTEGER NOT NULL,
                resulting_version INTEGER,
                event_type TEXT NOT NULL,
                feedback TEXT NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            )
            """
        )
        self.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_skill_versions_skill
            ON skill_versions(skill_id, version)
            """
        )
        self.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_skill_evolution_skill
            ON skill_evolution_events(skill_id, created_at)
            """
        )
        self.conn.commit()

    @staticmethod
    def _from_row(row: sqlite3.Row) -> SkillVersion:
        return SkillVersion(
            skill_id=row["skill_id"],
            version=row["version"],
            instructions=row["instructions"],
            examples=tuple(json.loads(row["examples_json"])),
            constraints=tuple(json.loads(row["constraints_json"])),
            metadata=dict(json.loads(row["metadata_json"])),
            created_at=row["created_at"],
        )

    def save_version(self, version: SkillVersion) -> None:
        self.conn.execute(
            """
            INSERT INTO skill_versions
                (
                    skill_id,
                    version,
                    instructions,
                    examples_json,
                    constraints_json,
                    metadata_json,
                    created_at
                )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(skill_id, version) DO UPDATE SET
                instructions = excluded.instructions,
                examples_json = excluded.examples_json,
                constraints_json = excluded.constraints_json,
                metadata_json = excluded.metadata_json,
                created_at = excluded.created_at
            """,
            (
                version.skill_id,
                version.version,
                version.instructions,
                json.dumps(list(version.examples), sort_keys=True),
                json.dumps(list(version.constraints), sort_keys=True),
                json.dumps(version.metadata, sort_keys=True, default=str),
                version.created_at,
            ),
        )
        self.conn.commit()

    def get(self, skill_id: str, version: int) -> SkillVersion | None:
        row = self.conn.execute(
            """
            SELECT *
            FROM skill_versions
            WHERE skill_id = ? AND version = ?
            """,
            (skill_id, version),
        ).fetchone()

        return None if row is None else self._from_row(row)

    def latest(self, skill_id: str) -> SkillVersion | None:
        row = self.conn.execute(
            """
            SELECT *
            FROM skill_versions
            WHERE skill_id = ?
            ORDER BY version DESC
            LIMIT 1
            """,
            (skill_id,),
        ).fetchone()

        return None if row is None else self._from_row(row)

    def history(self, skill_id: str) -> list[SkillVersion]:
        rows = self.conn.execute(
            """
            SELECT *
            FROM skill_versions
            WHERE skill_id = ?
            ORDER BY version ASC
            """,
            (skill_id,),
        ).fetchall()

        return [self._from_row(row) for row in rows]

    def all(self) -> list[SkillVersion]:
        rows = self.conn.execute(
            """
            SELECT *
            FROM skill_versions
            ORDER BY skill_id ASC, version ASC
            """
        ).fetchall()

        return [self._from_row(row) for row in rows]

    def record_evolution(
        self,
        skill_id: str,
        base_version: int,
        feedback: str,
        *,
        resulting_version: int | None = None,
        event_type: str = "revision",
        payload: dict[str, Any] | None = None,
    ) -> None:
        created_at = datetime.now(timezone.utc).isoformat()

        self.conn.execute(
            """
            INSERT INTO skill_evolution_events
                (
                    skill_id,
                    base_version,
                    resulting_version,
                    event_type,
                    feedback,
                    payload_json,
                    created_at
                )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                skill_id,
                base_version,
                resulting_version,
                event_type,
                feedback,
                json.dumps(payload or {}, sort_keys=True, default=str),
                created_at,
            ),
        )
        self.conn.commit()

    def evolution_history(self, skill_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT
                event_id,
                skill_id,
                base_version,
                resulting_version,
                event_type,
                feedback,
                payload_json,
                created_at
            FROM skill_evolution_events
            WHERE skill_id = ?
            ORDER BY event_id ASC
            """,
            (skill_id,),
        ).fetchall()

        return [
            {
                "event_id": row["event_id"],
                "skill_id": row["skill_id"],
                "base_version": row["base_version"],
                "resulting_version": row["resulting_version"],
                "event_type": row["event_type"],
                "feedback": row["feedback"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def load_registry(self, registry) -> None:
        for version in self.all():
            registry._skills.setdefault(version.skill_id, []).append(version)


class PersistentSkillRegistry:
    """SkillRegistry-compatible facade backed by SkillRepository."""

    def __init__(self, database: Database):
        from agent_os.skill_registry import SkillRegistry

        self.repository = SkillRepository(database=database)
        self._registry = SkillRegistry()
        self.repository.load_registry(self._registry)

    @property
    def _skills(self):
        return self._registry._skills

    def register(
        self,
        skill_id: str,
        instructions: str,
        examples: list[str] | None = None,
        constraints: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SkillVersion:
        version = self._registry.register(
            skill_id,
            instructions,
            examples=examples,
            constraints=constraints,
            metadata=metadata,
        )
        self.repository.save_version(version)
        return version

    def latest(self, skill_id: str) -> SkillVersion | None:
        return self._registry.latest(skill_id)

    def history(self, skill_id: str) -> list[SkillVersion]:
        return self._registry.history(skill_id)

    def all(self) -> list[SkillVersion]:
        return self._registry.all()
