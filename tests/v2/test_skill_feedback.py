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
