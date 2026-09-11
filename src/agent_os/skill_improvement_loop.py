from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .skill_evolution import SkillEvolutionEngine
from .skill_feedback import SkillFeedbackBuilder
from .skill_optimizer import SkillOptimizer
from .skill_registry import SkillRegistry, SkillVersion


@dataclass(frozen=True)
class SkillImprovementResult:
    skill_id: str
    baseline_version: int | None
    candidate_version: int | None
    baseline_score: float
    candidate_score: float
    promoted: bool
    rejected: bool
    reason: str
    feedback: str
    attempts: int


class SkillImprovementLoop:
    """
    Bounded closed-loop skill improvement controller.

    Flow:

        baseline
          ↓
        execute
          ↓
        evaluate
          ↓
        feedback
          ↓
        isolated candidate
          ↓
        execute candidate
          ↓
        evaluate candidate
          ↓
        compare against best score
          ├── improvement → promote → target reached? → stop
          └── no improvement → retain best → next candidate

    Candidate registries are isolated from the production registry.
    Production history is modified only after a candidate strictly
    outperforms the current best score.
    """

    def __init__(
        self,
        registry: SkillRegistry,
        *,
        feedback_builder: SkillFeedbackBuilder | None = None,
        optimizer: SkillOptimizer | None = None,
        evolution: SkillEvolutionEngine | None = None,
        max_attempts: int = 1,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")

        self.registry = registry
        self.feedback_builder = feedback_builder or SkillFeedbackBuilder()
        self.evolution = evolution or SkillEvolutionEngine(registry)
        self.optimizer = optimizer or SkillOptimizer(
            registry,
            self.evolution,
        )
        self.max_attempts = max_attempts

    @staticmethod
    def _clone_registry(registry: SkillRegistry) -> SkillRegistry:
        clone = SkillRegistry()

        for skill in registry.all():
            clone.register(
                skill.skill_id,
                skill.instructions,
                examples=skill.examples,
                constraints=skill.constraints,
                metadata=dict(skill.metadata),
            )

        return clone

    @staticmethod
    def _score(result: Any) -> float:
        if isinstance(result, (int, float)):
            return float(result)

        if isinstance(result, dict):
            for key in ("score", "overall_score", "value"):
                value = result.get(key)
                if isinstance(value, (int, float)):
                    return float(value)

            metrics = result.get("metrics")
            if isinstance(metrics, dict):
                values = [
                    float(value)
                    for value in metrics.values()
                    if isinstance(value, (int, float))
                ]
                if values:
                    return sum(values) / len(values)

        for key in ("score", "overall_score", "value"):
            value = getattr(result, key, None)
            if isinstance(value, (int, float)):
                return float(value)

        raise ValueError(
            "evaluation result does not contain a numeric score"
        )

    def improve(
        self,
        *,
        skill_id: str,
        execute: Callable[[SkillVersion], Any],
        evaluate: Callable[[Any], Any],
        reason: str = "evaluation_feedback",
        target_score: float | None = None,
    ) -> SkillImprovementResult:
        """
        Run bounded iterative skill improvement.

        A candidate is promoted only when its score is strictly greater
        than the best score seen so far. Rejected candidates never modify
        the production registry.

        `target_score`, when supplied, terminates the loop immediately
        after a promoted candidate reaches that score.
        """
        if target_score is not None and target_score <= 0:
            raise ValueError("target_score must be positive")

        current = self.registry.latest(skill_id)
        if current is None:
            raise ValueError(f"unknown skill: {skill_id}")

        baseline_execution = execute(current)
        baseline_evaluation = evaluate(baseline_execution)

        baseline_feedback = self.feedback_builder.build(
            skill_id=skill_id,
            result=baseline_evaluation,
        )

        baseline_score = self._score(baseline_evaluation)
        best_score = baseline_score
        last_feedback = baseline_feedback.feedback
        candidate_version: SkillVersion | None = None
        attempts = 0

        if target_score is not None and best_score >= target_score:
            return SkillImprovementResult(
                skill_id=skill_id,
                baseline_version=current.version,
                candidate_version=current.version,
                baseline_score=baseline_score,
                candidate_score=best_score,
                promoted=False,
                rejected=False,
                reason="target_score_already_reached",
                feedback=last_feedback,
                attempts=0,
            )

        for attempt in range(1, self.max_attempts + 1):
            attempts = attempt

            # Build and test every candidate in a completely isolated
            # registry. The production registry remains unchanged until
            # strict improvement has been demonstrated.
            candidate_registry = self._clone_registry(self.registry)
            candidate_evolution = SkillEvolutionEngine(candidate_registry)

            proposal = candidate_evolution.propose(
                skill_id,
                last_feedback,
                instructions=(
                    f"{current.instructions}\n\n"
                    f"Improvement reason: {reason}\n"
                    f"Improvement attempt: {attempt}\n"
                    f"Improvement feedback:\n{last_feedback}"
                ),
                examples=current.examples,
                constraints=current.constraints,
                metadata={
                    **current.metadata,
                    "improvement_attempt": attempt,
                    "base_score": best_score,
                    "improvement_reason": reason,
                },
            )

            candidate_version = candidate_evolution.apply(proposal)

            candidate_execution = execute(candidate_version)
            candidate_evaluation = evaluate(candidate_execution)

            candidate_feedback = self.feedback_builder.build(
                skill_id=skill_id,
                result=candidate_evaluation,
            )

            candidate_score = self._score(candidate_evaluation)
            last_feedback = candidate_feedback.feedback

            if candidate_score <= best_score:
                # Do not modify production state. The next attempt gets
                # another isolated candidate based on the current best.
                continue

            # Strict improvement: promote this exact candidate into the
            # production registry as the next immutable version.
            promoted = self.registry.register(
                skill_id=candidate_version.skill_id,
                instructions=candidate_version.instructions,
                examples=candidate_version.examples,
                constraints=candidate_version.constraints,
                metadata={
                    **candidate_version.metadata,
                    "promoted_from_candidate": True,
                    "candidate_score": candidate_score,
                    "baseline_score": baseline_score,
                    "previous_best_score": best_score,
                },
            )

            best_score = candidate_score
            candidate_version = promoted

            if target_score is not None and best_score >= target_score:
                return SkillImprovementResult(
                    skill_id=skill_id,
                    baseline_version=current.version,
                    candidate_version=promoted.version,
                    baseline_score=baseline_score,
                    candidate_score=best_score,
                    promoted=True,
                    rejected=False,
                    reason="target_score_reached",
                    feedback=last_feedback,
                    attempts=attempts,
                )

            return SkillImprovementResult(
                skill_id=skill_id,
                baseline_version=current.version,
                candidate_version=promoted.version,
                baseline_score=baseline_score,
                candidate_score=best_score,
                promoted=True,
                rejected=False,
                reason="candidate_outperformed_baseline",
                feedback=last_feedback,
                attempts=attempts,
            )

        return SkillImprovementResult(
            skill_id=skill_id,
            baseline_version=current.version,
            candidate_version=(
                candidate_version.version
                if candidate_version is not None
                else None
            ),
            baseline_score=baseline_score,
            candidate_score=best_score,
            promoted=False,
            rejected=True,
            reason="candidate_did_not_improve",
            feedback=last_feedback,
            attempts=attempts,
        )
