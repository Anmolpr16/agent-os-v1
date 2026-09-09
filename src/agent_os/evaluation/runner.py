from dataclasses import dataclass, field

from .metrics import MetricResult


@dataclass
class EvaluationResult:
    case_id: str
    metrics: list[MetricResult] = field(
        default_factory=list
    )

    @property
    def score(self) -> float:
        if not self.metrics:
            return 0.0

        return sum(
            metric.score
            for metric in self.metrics
        ) / len(self.metrics)

    @property
    def passed(self) -> bool:
        return all(
            metric.passed
            for metric in self.metrics
        )


class EvaluationRunner:
    """Run deterministic evaluation cases."""

    def evaluate(
        self,
        case_id: str,
        output: str,
        required_keywords: list[str],
    ) -> EvaluationResult:
        metric = (
            __import__(
                "agent_os.evaluation.metrics",
                fromlist=["keyword_coverage"],
            ).keyword_coverage(
                output,
                required_keywords,
            )
        )

        return EvaluationResult(
            case_id=case_id,
            metrics=[metric],
        )
