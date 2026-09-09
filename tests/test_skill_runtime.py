from agent_os.skill_runtime import (
    SkillRegistry,
    load_skill,
)


def test_markdown_skill_loader():
    skill = load_skill(
        "skills/research/SKILL.md"
    )

    assert skill.name == "research"
    assert skill.version == "1.0.0"
    assert "traceable answer" in (
        skill.objective
    )

    assert len(skill.inputs) == 3
    assert len(skill.procedure) == 9
    assert len(skill.failure_conditions) == 5
    assert len(skill.evaluation_rubric) == 4


def test_skill_registry():
    skill = load_skill(
        "skills/research/SKILL.md"
    )

    registry = SkillRegistry()
    registry.register(skill)

    assert registry.get("research") is skill
    assert registry.list() == ["research"]


def test_duplicate_skill_rejected():
    skill = load_skill(
        "skills/research/SKILL.md"
    )

    registry = SkillRegistry()
    registry.register(skill)

    try:
        registry.register(skill)
    except ValueError as exc:
        assert str(exc) == (
            "skill_already_registered:research"
        )
    else:
        raise AssertionError(
            "duplicate skill was accepted"
        )
