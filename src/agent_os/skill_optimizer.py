from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .skill_scoring import extract_score


@dataclass(frozen=True)
class SkillOptimizationResult:
    skill_id: str
    previous_version: int
    new_version: int
    score_before: float
    score_after: float
    improved: bool
    feedback: str
    metadata: dict[str, Any]


class SkillOptimizer:
    """Controls evaluation-driven skill revision and accepts only improvements."""

    def __init__(self, registry, evolution_engine, evaluator=None):
        self.registry = registry
        self.evolution_engine = evolution_engine
        self.evaluator = evaluator

    @staticmethod
    def _score(result) -> float:
        return extract_score(result)

    def optimize(
        self,
        skill_id: str,
        feedback: str,
        *,
        score_before: float,
        score_after: float | None = None,
        instructions: str | None = None,
        examples: list[str] | None = None,
        constraints: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SkillOptimizationResult:
        if not skill_id.strip():
            raise ValueError("skill_id_required")
        if not feedback.strip():
            raise ValueError("feedback_required")

        current = self.registry.latest(skill_id)
        previous_version = current.version if current else 0

        if score_after is None:
            score_after = score_before

        if score_after <= score_before:
            return SkillOptimizationResult(
                skill_id=skill_id,
                previous_version=previous_version,
                new_version=previous_version,
                score_before=float(score_before),
                score_after=float(score_after),
                improved=False,
                feedback=feedback,
                metadata={"accepted": False, "reason": "no_improvement"},
            )

        version = self.evolution_engine.revise(
            skill_id,
            feedback,
            instructions=instructions,
            examples=examples,
            constraints=constraints,
            metadata={
                **dict(metadata or {}),
                "optimization": True,
                "score_before": float(score_before),
                "score_after": float(score_after),
            },
        )

        return SkillOptimizationResult(
            skill_id=skill_id,
            previous_version=previous_version,
            new_version=version.version,
            score_before=float(score_before),
            score_after=float(score_after),
            improved=True,
            feedback=feedback,
            metadata={"accepted": True, "reason": "improvement"},
        )
