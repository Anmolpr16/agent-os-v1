from pathlib import Path

from agent_os.skill_evolution import SkillEvolutionEngine
from agent_os.skill_registry import SkillRegistry
from agent_os.skill_repository import SkillRepository
from agent_os.storage import Database


def test_skill_repository_persists_versions_across_restart(tmp_path: Path):
    path = tmp_path / "skills.db"

    with Database(str(path)) as database:
        repository = SkillRepository(database=database)
        registry = SkillRegistry(repository=repository)

        first = registry.register(
            "research",
            "Research evidence",
            examples=["verify sources"],
            constraints=["cite sources"],
            metadata={"domain": "research"},
        )

        second = registry.register(
            "research",
            "Research and verify evidence",
        )

        assert first.version == 1
        assert second.version == 2

    with Database(str(path)) as database:
        repository = SkillRepository(database=database)

        assert repository.latest("research").version == 2

        history = repository.history("research")

        assert [item.version for item in history] == [1, 2]
        assert history[0].examples == ("verify sources",)
        assert history[0].metadata["domain"] == "research"


def test_persistent_registry_restores_latest_skill(tmp_path: Path):
    path = tmp_path / "registry.db"

    with Database(str(path)) as database:
        repository = SkillRepository(database=database)
        registry = SkillRegistry(repository=repository)

        registry.register(
            "coding",
            "Implement and test code",
            constraints=["run pytest"],
        )

    with Database(str(path)) as database:
        repository = SkillRepository(database=database)
        restored = SkillRegistry(repository=repository)

        latest = restored.latest("coding")

        assert latest is not None
        assert latest.version == 1
        assert latest.instructions == "Implement and test code"
        assert latest.constraints == ("run pytest",)


def test_evolution_feedback_is_persisted(tmp_path: Path):
    path = tmp_path / "evolution.db"

    with Database(str(path)) as database:
        repository = SkillRepository(database=database)
        registry = SkillRegistry(repository=repository)

        registry.register("research", "Research the objective")

        engine = SkillEvolutionEngine(registry)

        proposal = engine.propose(
            "research",
            "Improve evidence verification",
            instructions="Research and verify the objective",
        )

        repository.record_evolution(
            proposal.skill_id,
            proposal.base_version,
            proposal.reason,
            resulting_version=2,
            event_type="promoted",
            payload={"source": "evaluation"},
        )

    with Database(str(path)) as database:
        repository = SkillRepository(database=database)

        events = repository.evolution_history("research")

        assert len(events) == 1
        assert events[0]["base_version"] == 1
        assert events[0]["resulting_version"] == 2
        assert events[0]["event_type"] == "promoted"
        assert events[0]["feedback"] == "Improve evidence verification"
        assert events[0]["payload"]["source"] == "evaluation"


def test_repository_rejects_two_connection_sources():
    database = Database()

    try:
        try:
            SkillRepository(
                connection=database.conn,
                database=database,
            )
        except ValueError as exc:
            assert str(exc) == (
                "provide either connection or database, not both"
            )
        else:
            raise AssertionError("expected ValueError")
    finally:
        database.close()


def test_existing_in_memory_registry_behavior_is_unchanged():
    registry = SkillRegistry()

    version = registry.register(
        "planning",
        "Plan before execution",
    )

    assert version.version == 1
    assert registry.latest("planning") == version
    assert registry.history("planning") == [version]
