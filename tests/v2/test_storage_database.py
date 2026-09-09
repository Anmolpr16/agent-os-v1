import json
from pathlib import Path

import pytest

from agent_os.storage import Database


def test_database_initializes_schema():
    with Database() as database:
        tables = {
            row[0]
            for row in database.conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            ).fetchall()
        }

    assert {
        "sources",
        "memory_items",
        "entities",
        "relationships",
        "task_runs",
    } <= tables


def test_database_persists_across_instances(tmp_path: Path):
    path = str(tmp_path / "agent.db")

    with Database(path) as first:
        first.conn.execute(
            """
            INSERT INTO memory_items
            (kind, content, metadata_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                "semantic",
                "persistent test",
                "{}",
                "2026-01-01T00:00:00+00:00",
            ),
        )
        first.conn.commit()

    with Database(path) as second:
        row = second.conn.execute(
            """
            SELECT content
            FROM memory_items
            WHERE content = ?
            """,
            ("persistent test",),
        ).fetchone()

    assert row["content"] == "persistent test"


def test_database_rejects_empty_path():
    with pytest.raises(
        ValueError,
        match="path must not be empty",
    ):
        Database("")


def test_memory_store_can_use_shared_database():
    from agent_os.memory import MemoryStore

    with Database() as database:
        memory = MemoryStore(database=database)
        assert memory.conn is database.conn

        memory.add_memory(
            content="shared database test",
        )

        row = database.conn.execute(
            """
            SELECT content
            FROM memory_items
            WHERE content = ?
            """,
            ("shared database test",),
        ).fetchone()

        assert row["content"] == "shared database test"


def test_memory_store_does_not_close_injected_database():
    from agent_os.memory import MemoryStore

    database = Database()
    memory = MemoryStore(database=database)

    memory.close()

    row = database.conn.execute(
        "SELECT 1"
    ).fetchone()

    assert row[0] == 1

    database.close()


def test_memory_store_owns_standalone_database():
    from agent_os.memory import MemoryStore

    memory = MemoryStore(":memory:")
    connection = memory.conn

    memory.close()

    with pytest.raises(Exception):
        connection.execute("SELECT 1")


def test_run_repository_can_use_shared_database():
    from agent_os.observability import RunRepository

    with Database() as database:
        repository = RunRepository(database=database)

        repository.record(
            "storage-run-001",
            "complete",
            {"ok": True},
        )

        events = repository.list_events(
            "storage-run-001"
        )

        assert len(events) == 1
        assert events[0]["event"]["ok"] is True


def test_run_repository_rejects_two_connection_sources():
    from agent_os.observability import RunRepository

    database = Database()

    with pytest.raises(
        ValueError,
        match="either connection or database",
    ):
        RunRepository(
            connection=database.conn,
            database=database,
        )

    database.close()


def test_run_repository_can_use_shared_database():
    from agent_os.observability import RunRepository

    with Database() as database:
        repository = RunRepository(database=database)

        repository.record(
            "storage-run-001",
            "complete",
            {"ok": True},
        )

        events = repository.list_events(
            "storage-run-001"
        )

        assert len(events) == 1
        assert events[0]["event"]["ok"] is True


def test_run_repository_rejects_two_connection_sources():
    from agent_os.observability import RunRepository

    database = Database()

    with pytest.raises(
        ValueError,
        match="either connection or database",
    ):
        RunRepository(
            connection=database.conn,
            database=database,
        )

    database.close()


def test_orchestrator_can_use_shared_database():
    from agent_os.core.orchestrator import Orchestrator, State, Task

    with Database() as database:
        orchestrator = Orchestrator(
            database=database
        )

        run = orchestrator.run(
            Task(
                id="database-orchestrator-001",
                objective="test shared database",
            )
        )

        assert run.state == State.COMPLETE
        assert orchestrator.memory.conn is database.conn
        assert orchestrator.run_repository.conn is database.conn


def test_orchestrator_rejects_memory_and_database_together():
    from agent_os.core.orchestrator import Orchestrator
    from agent_os.memory import MemoryStore

    database = Database()
    memory = MemoryStore(database=database)

    with pytest.raises(
        ValueError,
        match="either memory or database",
    ):
        Orchestrator(
            memory=memory,
            database=database,
        )

    database.close()


def test_memory_store_entity_relationship_graph():
    from agent_os.memory import MemoryStore

    with Database() as database:
        memory = MemoryStore(database=database)

        agent_id = memory.upsert_entity(
            "Agent OS",
            entity_type="system",
        )
        memory_id = memory.upsert_entity(
            "Memory Graph",
            entity_type="component",
        )

        relationship_id = memory.add_relationship(
            agent_id,
            "contains",
            memory_id,
            metadata={"version": 2},
        )

        assert agent_id > 0
        assert memory_id > 0
        assert relationship_id > 0

        row = database.conn.execute(
            """
            SELECT
                e1.name AS source_name,
                r.relation,
                e2.name AS target_name,
                r.metadata_json
            FROM relationships AS r
            JOIN entities AS e1
              ON e1.id = r.source_entity_id
            JOIN entities AS e2
              ON e2.id = r.target_entity_id
            WHERE r.id = ?
            """,
            (relationship_id,),
        ).fetchone()

        assert row["source_name"] == "Agent OS"
        assert row["relation"] == "contains"
        assert row["target_name"] == "Memory Graph"
        assert json.loads(row["metadata_json"]) == {
            "version": 2
        }


def test_memory_store_upsert_entity_preserves_id():
    from agent_os.memory import MemoryStore

    with Database() as database:
        memory = MemoryStore(database=database)

        entity_id = memory.upsert_entity(
            "Research",
            entity_type="skill",
            metadata={"version": 1},
        )

        same_id = memory.upsert_entity(
            "Research",
            entity_type="skill",
            metadata={"version": 2},
        )

        assert same_id == entity_id

        row = database.conn.execute(
            """
            SELECT type, metadata_json
            FROM entities
            WHERE id = ?
            """,
            (entity_id,),
        ).fetchone()

        assert row["type"] == "skill"
        assert json.loads(row["metadata_json"]) == {
            "version": 2
        }


def test_memory_store_graph_neighbors_are_bidirectional():
    from agent_os.memory import MemoryStore

    with Database() as database:
        memory = MemoryStore(database=database)

        agent_id = memory.upsert_entity(
            "Agent",
            entity_type="system",
        )
        memory_id = memory.upsert_entity(
            "Memory",
            entity_type="component",
        )

        memory.add_relationship(
            agent_id,
            "uses",
            memory_id,
            metadata={"strength": 1},
        )

        forward = memory.get_neighbors(agent_id)
        reverse = memory.get_neighbors(memory_id)

        assert len(forward) == 1
        assert forward[0]["entity_id"] == memory_id
        assert forward[0]["relation"] == "uses"
        assert forward[0]["relationship_metadata"] == {
            "strength": 1
        }

        assert len(reverse) == 1
        assert reverse[0]["entity_id"] == agent_id
        assert reverse[0]["relation"] == "uses"


def test_memory_store_get_entity_and_neighbor_limit():
    from agent_os.memory import MemoryStore

    with Database() as database:
        memory = MemoryStore(database=database)

        entity_id = memory.upsert_entity(
            "Research",
            entity_type="skill",
            metadata={"version": 2},
        )

        assert memory.get_entity(entity_id)["name"] == "Research"
        assert memory.get_entity(999999) is None
        assert memory.get_neighbors(entity_id, limit=0) == []


def test_memory_retriever_entity_graph_traversal():
    from agent_os.memory import MemoryRetriever, MemoryStore

    with Database() as database:
        memory = MemoryStore(database=database)
        retriever = MemoryRetriever(memory)

        agent_id = memory.upsert_entity("Agent")
        memory_id = memory.upsert_entity("Memory")
        skill_id = memory.upsert_entity("Research Skill")

        memory.add_relationship(agent_id, "uses", memory_id)
        memory.add_relationship(memory_id, "supports", skill_id)

        results = retriever.search_entity_graph(
            agent_id,
            depth=2,
        )

        assert [item["name"] for item in results] == [
            "Memory",
            "Research Skill",
        ]
        assert [item["depth"] for item in results] == [1, 2]


def test_memory_store_relationship_upsert_preserves_id():
    from agent_os.memory import MemoryStore

    with Database() as database:
        memory = MemoryStore(database=database)

        source_id = memory.upsert_entity("Source")
        target_id = memory.upsert_entity("Target")

        first_id = memory.add_relationship(
            source_id,
            "links",
            target_id,
            metadata={"version": 1},
        )

        second_id = memory.add_relationship(
            source_id,
            "links",
            target_id,
            metadata={"version": 2},
        )

        assert second_id == first_id

        row = database.conn.execute(
            """
            SELECT metadata_json
            FROM relationships
            WHERE id = ?
            """,
            (first_id,),
        ).fetchone()

        assert json.loads(row["metadata_json"]) == {
            "version": 2
        }
