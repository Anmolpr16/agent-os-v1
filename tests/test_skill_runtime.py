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


def test_skill_selector_prefers_matching_skill():
    from agent_os.skill_runtime import (
        Skill,
        SkillRegistry,
        SkillSelector,
    )

    registry = SkillRegistry()

    registry.register(
        Skill(
            name="research",
            version="1.0.0",
            objective="Produce a traceable answer supported by evidence.",
            inputs=["research question", "constraints"],
            procedure=["Gather relevant evidence."],
        )
    )

    registry.register(
        Skill(
            name="coding",
            version="1.0.0",
            objective="Implement and verify software.",
            inputs=["source code"],
            procedure=["Write code.", "Run tests."],
        )
    )

    selector = SkillSelector(registry)

    selection = selector.select(
        "research evidence and verification"
    )

    assert selection is not None
    assert selection.skill.name == "research"
    assert selection.score > 0.0


def test_skill_selector_handles_empty_objective():
    from agent_os.skill_runtime import (
        Skill,
        SkillRegistry,
        SkillSelector,
    )

    registry = SkillRegistry()
    registry.register(
        Skill(
            name="research",
            version="1.0.0",
            objective="Research.",
        )
    )

    selection = SkillSelector(registry).select("")

    assert selection is not None
    assert selection.score == 0.0


def test_skill_runner_tracks_procedure_steps():
    from agent_os.skill_runtime import (
        Skill,
        SkillRunner,
    )

    skill = Skill(
        name="research",
        version="1.0.0",
        objective="Produce an evidence-backed answer.",
        procedure=[
            "Gather evidence.",
            "Check contradictions.",
            "Verify the final answer.",
        ],
    )

    result = SkillRunner().run(skill)

    assert result.skill_name == "research"
    assert result.skill_version == "1.0.0"
    assert result.status == "completed"
    assert result.passed
    assert [step.index for step in result.steps] == [1, 2, 3]
    assert all(
        step.status == "acknowledged"
        for step in result.steps
    )


def test_skill_runner_rejects_empty_procedure_step():
    from agent_os.skill_runtime import (
        Skill,
        SkillRunner,
    )

    skill = Skill(
        name="research",
        version="1.0.0",
        objective="Research.",
        procedure=[
            "Gather evidence.",
            "",
            "Verify.",
        ],
    )

    result = SkillRunner().run(skill)

    assert result.status == "failed"
    assert not result.passed
    assert result.steps[-1].error == "empty_procedure_step"
    assert result.steps[-1].status == "failed"
    assert len(result.steps) == 2
