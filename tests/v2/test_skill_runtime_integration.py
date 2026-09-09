from agent_os.skill_registry import SkillRegistry
from agent_os.skill_context import SkillContextBuilder


def test_skill_context_selects_latest_relevant_skill():
    registry = SkillRegistry()

    registry.register(
        "research",
        "Research the objective and verify evidence",
        examples=["compare primary sources"],
        constraints=["cite evidence"],
    )

    registry.register(
        "coding",
        "Implement software changes and run tests",
        examples=["pytest"],
        constraints=["preserve compatibility"],
    )

    context = SkillContextBuilder(registry).build(
        "research evidence and primary sources"
    )

    assert "skill_context" in context
    assert context["skill_context"][0]["skill_id"] == "research"
    assert context["skill_context"][0]["version"] == 1


def test_skill_context_uses_latest_version():
    registry = SkillRegistry()

    registry.register(
        "coding",
        "Implement code",
        constraints=["run tests"],
    )

    registry.register(
        "coding",
        "Implement code and verify integration",
        constraints=["run tests", "preserve compatibility"],
    )

    context = SkillContextBuilder(registry).build(
        "coding integration compatibility"
    )

    selected = context["skill_context"][0]

    assert selected["skill_id"] == "coding"
    assert selected["version"] == 2
    assert "verify integration" in selected["instructions"]


def test_skill_context_is_empty_when_no_skill_matches():
    registry = SkillRegistry()

    registry.register(
        "coding",
        "Implement software and run tests",
    )

    assert SkillContextBuilder(registry).build(
        "astronomy telescope observation"
    ) == {}
