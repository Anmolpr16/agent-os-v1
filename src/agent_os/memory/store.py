import json
from datetime import datetime, timezone

from agent_os.storage import Database


class MemoryStore:
    """Persistent memory backed by a shared Database."""

    def __init__(
        self,
        path: str = "agent_os.db",
        database: Database | None = None,
    ):
        self.database = database or Database(path)
        self.conn = self.database.conn
        self._owns_database = database is None

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
        if self._owns_database:
            self.database.close()

    def upsert_entity(
        self,
        name: str,
        entity_type: str | None = None,
        metadata: dict | None = None,
    ) -> int:
        if not name.strip():
            raise ValueError("entity name must not be empty")

        existing = self.conn.execute(
            """
            SELECT id
            FROM entities
            WHERE name = ?
            """,
            (name,),
        ).fetchone()

        if existing is not None:
            self.conn.execute(
                """
                UPDATE entities
                SET type = ?,
                    metadata_json = ?
                WHERE id = ?
                """,
                (
                    entity_type,
                    json.dumps(metadata or {}),
                    existing["id"],
                ),
            )
            self.conn.commit()
            return int(existing["id"])

        cur = self.conn.execute(
            """
            INSERT INTO entities
            (
                name,
                type,
                metadata_json
            )
            VALUES (?, ?, ?)
            """,
            (
                name,
                entity_type,
                json.dumps(metadata or {}),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def add_relationship(
        self,
        source_entity_id: int,
        relation: str,
        target_entity_id: int,
        metadata: dict | None = None,
    ) -> int:
        if not relation.strip():
            raise ValueError("relation must not be empty")

        cur = self.conn.execute(
            """
            INSERT INTO relationships
            (
                source_entity_id,
                relation,
                target_entity_id,
                metadata_json
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT (
                source_entity_id,
                relation,
                target_entity_id
            )
            DO UPDATE SET metadata_json = excluded.metadata_json
            """,
            (
                source_entity_id,
                relation,
                target_entity_id,
                json.dumps(metadata or {}),
            ),
        )
        self.conn.commit()

        row = self.conn.execute(
            """
            SELECT id
            FROM relationships
            WHERE source_entity_id = ?
              AND relation = ?
              AND target_entity_id = ?
            """,
            (
                source_entity_id,
                relation,
                target_entity_id,
            ),
        ).fetchone()

        return int(row["id"])

    def get_entity(self, entity_id: int):
        return self.conn.execute(
            """
            SELECT
                id,
                name,
                type,
                metadata_json
            FROM entities
            WHERE id = ?
            """,
            (entity_id,),
        ).fetchone()

    def get_neighbors(
        self,
        entity_id: int,
        limit: int = 50,
    ) -> list[dict]:
        if limit <= 0:
            return []

        rows = self.conn.execute(
            """
            SELECT
                r.id AS relationship_id,
                r.relation,
                r.metadata_json AS relationship_metadata,
                e.id AS entity_id,
                e.name,
                e.type,
                e.metadata_json
            FROM relationships AS r
            JOIN entities AS e
              ON e.id = r.target_entity_id
            WHERE r.source_entity_id = ?

            UNION ALL

            SELECT
                r.id AS relationship_id,
                r.relation,
                r.metadata_json AS relationship_metadata,
                e.id AS entity_id,
                e.name,
                e.type,
                e.metadata_json
            FROM relationships AS r
            JOIN entities AS e
              ON e.id = r.source_entity_id
            WHERE r.target_entity_id = ?

            ORDER BY relationship_id ASC
            LIMIT ?
            """,
            (entity_id, entity_id, limit),
        ).fetchall()

        return [
            {
                "relationship_id": row["relationship_id"],
                "relation": row["relation"],
                "relationship_metadata": json.loads(
                    row["relationship_metadata"]
                ),
                "entity_id": row["entity_id"],
                "name": row["name"],
                "type": row["type"],
                "metadata": json.loads(
                    row["metadata_json"]
                ),
            }
            for row in rows
        ]
