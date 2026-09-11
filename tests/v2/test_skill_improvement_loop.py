from agent_os.skill_feedback import SkillFeedbackBuilder
from agent_os.skill_improvement_loop import SkillImprovementLoop
from agent_os.skill_registry import SkillRegistry


def make_registry():
    registry = SkillRegistry()
    registry.register(
        "planner",
        "Plan the task carefully.",
        examples=("Produce a structured plan.",),
        constraints=("Do not invent facts.",),
    )
    return registry


def test_improvement_loop_promotes_better_candidate():
    registry = make_registry()
    loop = SkillImprovementLoop(
        registry,
        feedback_builder=SkillFeedbackBuilder(threshold=0.8),
    )

    calls = []

    def execute(skill):
        calls.append(skill.version)
        return {"version": skill.version}

    def evaluate(result):
        # Baseline is version 1; isolated candidate is version 2.
        return {"score": 0.5 if result["version"] == 1 else 0.9, "feedback": "Improve"}

    result = loop.improve(
        skill_id="planner",
        execute=execute,
        evaluate=evaluate,
        reason="better planning",
    )

    assert result.promoted is True
    assert result.rejected is False
    assert result.baseline_version == 1
    assert result.candidate_version == 2
    assert result.baseline_score == 0.5
    assert result.candidate_score == 0.9
    assert registry.latest("planner").version == 2
    assert len(registry.history("planner")) == 2
    assert calls == [1, 2]


def test_improvement_loop_rejects_non_improving_candidate():
    registry = make_registry()
    loop = SkillImprovementLoop(registry)

    def execute(skill):
        return {"version": skill.version}

    def evaluate(result):
        return {"score": 0.7, "feedback": "No measurable improvement"}

    result = loop.improve(
        skill_id="planner",
        execute=execute,
        evaluate=evaluate,
    )

    assert result.promoted is False
    assert result.rejected is True
    assert result.reason == "candidate_did_not_improve"
    assert result.baseline_score == 0.7
    assert result.candidate_score == 0.7
    assert result.candidate_version == 2
    assert registry.latest("planner").version == 1
    assert len(registry.history("planner")) == 1


def test_candidate_isolation_prevents_failed_candidate_from_polluting_registry():
    registry = make_registry()
    loop = SkillImprovementLoop(registry)

    observed_versions = []

    def execute(skill):
        observed_versions.append(
            (skill.version, skill.instructions)
        )
        return {"score": 0.4, "feedback": "candidate failed"}

    def evaluate(result):
        return result

    result = loop.improve(
        skill_id="planner",
        execute=execute,
        evaluate=evaluate,
    )

    assert result.rejected is True
    assert registry.latest("planner").version == 1
    assert len(registry.history("planner")) == 1
    assert observed_versions[0][0] == 1
    assert observed_versions[1][0] == 2
    assert "Improvement feedback" in observed_versions[1][1]


def test_unknown_skill_fails_cleanly():
    registry = make_registry()
    loop = SkillImprovementLoop(registry)

    def execute(skill):
        return {}

    def evaluate(result):
        return {"score": 1.0}

    try:
        loop.improve(
            skill_id="missing",
            execute=execute,
            evaluate=evaluate,
        )
    except ValueError as exc:
        assert "unknown skill" in str(exc)
    else:
        raise AssertionError("expected unknown skill failure")


def test_invalid_attempt_limit_is_rejected():
    registry = make_registry()

    try:
        SkillImprovementLoop(registry, max_attempts=0)
    except ValueError:
        pass
    else:
        raise AssertionError("expected max_attempts validation failure")
