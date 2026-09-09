from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SkillFeedback:
    skill_id: str
    score: float
    passed: bool
    feedback: str
    metadata: dict[str, Any]


class SkillFeedbackBuilder:
    """Normalizes evaluation/examiner output into skill optimization feedback."""

    def __init__(self, threshold: float = 0.8):
        self.threshold = float(threshold)

    @staticmethod
    def _extract_score(result) -> float:
        if result is None:
            return 0.0

        for name in ("score", "overall_score", "value"):
            value = getattr(result, name, None)
            if isinstance(value, (int, float)):
                return float(value)

        metrics = getattr(result, "metrics", None)

        if isinstance(metrics, dict) and metrics:
            values = [
                float(value)
                for value in metrics.values()
                if isinstance(value, (int, float))
            ]
            if values:
                return sum(values) / len(values)

        return 0.0

    @staticmethod
    def _extract_feedback(result) -> str:
        if result is None:
            return "No evaluation result was produced."

        for name in ("feedback", "reason", "summary", "message"):
            value = getattr(result, name, None)
            if isinstance(value, str) and value.strip():
                return value

        examiner = getattr(result, "examiner", None)
        if isinstance(examiner, str) and examiner.strip():
            return examiner

        return "Evaluation completed without explicit feedback."

    def build(self, skill_id: str, result) -> SkillFeedback:
        if not skill_id.strip():
            raise ValueError("skill_id_required")

        score = self._extract_score(result)

        return SkillFeedback(
            skill_id=skill_id,
            score=score,
            passed=score >= self.threshold,
            feedback=self._extract_feedback(result),
            metadata={
                "threshold": self.threshold,
                "score": score,
            },
        )
