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

        execute
          ↓
        evaluate
          ↓
        normalize feedback
          ↓
        propose skill revision
          ↓
        test candidate in an isolated registry
          ↓
        execute again
          ↓
        evaluate again
          ↓
        promote only if strictly better

    The production registry is never modified while a candidate is being
    evaluated. This gives the loop transactional candidate semantics without
    requiring destructive rollback.
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

        raise ValueError("evaluation result does not contain a numeric score")

    def improve(
        self,
        *,
        skill_id: str,
        execute: Callable[[SkillVersion], Any],
        evaluate: Callable[[Any], Any],
        reason: str = "evaluation_feedback",
    ) -> SkillImprovementResult:
        """
        Run one bounded improvement cycle.

        `execute(skill_version)` executes the task using the supplied skill.
        `evaluate(execution_result)` evaluates that execution and returns an
        evaluator result accepted by SkillFeedbackBuilder.

        The existing skill is evaluated first. A candidate revision is then
        created in an isolated registry. The candidate is only promoted to
        the real registry when its measured score is strictly higher.
        """

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

        best_version = current
        best_score = baseline_score
        last_feedback = baseline_feedback.feedback
        candidate_version: SkillVersion | None = None
        attempts = 0

        for attempt in range(1, self.max_attempts + 1):
            attempts = attempt

            candidate_registry = self._clone_registry(self.registry)
            candidate_evolution = SkillEvolutionEngine(candidate_registry)

            proposal = candidate_evolution.propose(
                skill_id,
                last_feedback,
                instructions=(
                    f"{current.instructions}\n\n"
                    f"Improvement reason: {reason}\n"
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

            if candidate_score > best_score:
                best_version = candidate_version
                best_score = candidate_score

                # Promote the exact candidate content to the production
                # registry. Registration creates the next immutable version.
                promoted = self.registry.register(
                    skill_id=best_version.skill_id,
                    instructions=best_version.instructions,
                    examples=best_version.examples,
                    constraints=best_version.constraints,
                    metadata={
                        **best_version.metadata,
                        "promoted_from_candidate": True,
                        "candidate_score": candidate_score,
                        "baseline_score": baseline_score,
                    },
                )

                return SkillImprovementResult(
                    skill_id=skill_id,
                    baseline_version=current.version,
                    candidate_version=promoted.version,
                    baseline_score=baseline_score,
                    candidate_score=candidate_score,
                    promoted=True,
                    rejected=False,
                    reason="candidate_outperformed_baseline",
                    feedback=candidate_feedback.feedback,
                    attempts=attempts,
                )

            # Candidate failed to improve. It remains isolated and is never
            # inserted into the production registry.
            break

        return SkillImprovementResult(
            skill_id=skill_id,
            baseline_version=current.version,
            candidate_version=(
                candidate_version.version if candidate_version is not None else None
            ),
            baseline_score=baseline_score,
            candidate_score=best_score,
            promoted=False,
            rejected=True,
            reason="candidate_did_not_improve",
            feedback=last_feedback,
            attempts=attempts,
        )
