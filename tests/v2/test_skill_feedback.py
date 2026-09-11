from types import SimpleNamespace

from agent_os.skill_feedback import SkillFeedbackBuilder


def test_feedback_extracts_direct_score_and_message():
    result = SimpleNamespace(
        score=0.91,
        feedback="Strong result",
    )

    feedback = SkillFeedbackBuilder().build("research", result)

    assert feedback.skill_id == "research"
    assert feedback.score == 0.91
    assert feedback.passed is True
    assert feedback.feedback == "Strong result"


def test_feedback_extracts_average_metrics():
    result = SimpleNamespace(
        metrics={
            "accuracy": 0.8,
            "coverage": 0.6,
        }
    )

    feedback = SkillFeedbackBuilder().build("research", result)

    assert feedback.score == 0.7
    assert feedback.passed is False


def test_feedback_handles_missing_result():
    feedback = SkillFeedbackBuilder().build("research", None)

    assert feedback.score == 0.0
    assert feedback.passed is False
    assert "No evaluation" in feedback.feedback


def test_feedback_threshold_is_configurable():
    result = SimpleNamespace(score=0.75, feedback="Needs improvement")

    feedback = SkillFeedbackBuilder(threshold=0.7).build(
        "coding",
        result,
    )

    assert feedback.passed is True
    assert feedback.metadata["threshold"] == 0.7


def test_shared_score_normalizer_accepts_numeric_result():
    from agent_os.skill_scoring import extract_score

    assert extract_score(0.75) == 0.75


def test_shared_score_normalizer_accepts_dict_score_shapes():
    from agent_os.skill_scoring import extract_score

    assert extract_score({"score": 0.71}) == 0.71
    assert extract_score({"overall_score": 0.72}) == 0.72
    assert extract_score({"value": 0.73}) == 0.73


def test_shared_score_normalizer_accepts_dict_metrics():
    from agent_os.skill_scoring import extract_score

    assert extract_score({"metrics": {"accuracy": 0.8, "coverage": 0.6}}) == 0.7


def test_shared_score_normalizer_accepts_object_shapes():
    from agent_os.skill_scoring import extract_score

    assert extract_score(SimpleNamespace(overall_score=0.74)) == 0.74
    assert extract_score(SimpleNamespace(value=0.75)) == 0.75
    assert extract_score(
        SimpleNamespace(metrics={"accuracy": 0.9, "coverage": 0.7})
    ) == 0.8


def test_shared_score_normalizer_rejects_missing_score():
    from agent_os.skill_scoring import extract_score

    try:
        extract_score({"feedback": "no score"})
    except ValueError as exc:
        assert str(exc) == "evaluation result does not contain a numeric score"
    else:
        raise AssertionError("expected score extraction failure")
