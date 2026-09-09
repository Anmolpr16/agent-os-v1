from dataclasses import dataclass, field

from .metrics import MetricResult


@dataclass(frozen=True)
class Examination:
    """Structured assessment of an agent result."""

    passed: bool
    score: float
    metrics: list[MetricResult] = field(default_factory=list)
    feedback: list[str] = field(default_factory=list)


class Examiner:
    """Evaluate an output and produce actionable examination feedback."""

    def examine(
        self,
        metrics: list[MetricResult],
    ) -> Examination:
        if not metrics:
            return Examination(
                passed=False,
                score=0.0,
                feedback=["no_metrics"],
            )

        score = sum(metric.score for metric in metrics) / len(metrics)
        feedback = [
            f"{metric.name}:below_threshold"
            for metric in metrics
            if not metric.passed
        ]

        return Examination(
            passed=all(metric.passed for metric in metrics),
            score=score,
            metrics=list(metrics),
            feedback=feedback,
        )
