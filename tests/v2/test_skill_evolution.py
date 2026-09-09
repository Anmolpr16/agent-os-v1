from agent_os.skill_evolution import SkillEvolutionEngine
from agent_os.skill_registry import SkillRegistry


def test_evolution_proposes_revision_from_existing_skill():
    registry = SkillRegistry()
    registry.register(
        "research",
        "Research the objective",
        examples=["verify evidence"],
        constraints=["cite sources"],
    )

    engine = SkillEvolutionEngine(registry)

    proposal = engine.propose(
        "research",
        "Improve evidence verification",
    )

    assert proposal.skill_id == "research"
    assert proposal.base_version == 1
    assert proposal.instructions == "Research the objective"
    assert proposal.reason == "Improve evidence verification"


def test_evolution_applies_new_version():
    registry = SkillRegistry()
    registry.register("coding", "Implement code")

    engine = SkillEvolutionEngine(registry)

    version = engine.revise(
        "coding",
        "Add mandatory test verification",
        instructions="Implement code and verify tests",
        constraints=["run pytest"],
    )

    assert version.version == 2
    assert version.instructions == "Implement code and verify tests"
    assert "run pytest" in version.constraints
    assert version.metadata["evolution"] is True
    assert version.metadata["base_version"] == 1


def test_evolution_detects_concurrent_version_change():
    registry = SkillRegistry()
    registry.register("research", "Initial instructions")

    engine = SkillEvolutionEngine(registry)

    proposal = engine.propose(
        "research",
        "Improve verification",
    )

    registry.register("research", "Concurrent revision")

    try:
        engine.apply(proposal)
    except ValueError as exc:
        assert str(exc) == "skill_version_conflict"
    else:
        raise AssertionError("expected skill_version_conflict")


def test_evolution_can_create_first_skill():
    registry = SkillRegistry()
    engine = SkillEvolutionEngine(registry)

    version = engine.revise(
        "planning",
        "Create a planning SOP",
        instructions="Plan the objective before execution",
    )

    assert version.version == 1
    assert version.metadata["evolution"] is True
    assert registry.latest("planning") == version
