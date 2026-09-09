from agent_os.evaluation.examiner import Examiner
from agent_os.evaluation.metrics import MetricResult


def test_examiner_passes_when_all_metrics_pass():
    examination = Examiner().examine(
        [
            MetricResult("accuracy", 1.0),
            MetricResult("coverage", 1.0),
        ]
    )

    assert examination.passed is True
    assert examination.score == 1.0
    assert examination.feedback == []


def test_examiner_reports_failed_metrics():
    examination = Examiner().examine(
        [
            MetricResult("accuracy", 1.0),
            MetricResult("coverage", 0.5),
        ]
    )

    assert examination.passed is False
    assert examination.score == 0.75
    assert examination.feedback == ["coverage:below_threshold"]


def test_examiner_rejects_empty_metric_set():
    examination = Examiner().examine([])

    assert examination.passed is False
    assert examination.score == 0.0
    assert examination.feedback == ["no_metrics"]


def test_evaluation_runner_exposes_examination():
    from agent_os.evaluation import EvaluationRunner

    runner = EvaluationRunner()

    examination = runner.examine(
        [MetricResult("quality", 1.0)]
    )

    assert examination.passed is True
    assert examination.score == 1.0
