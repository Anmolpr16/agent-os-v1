from dataclasses import dataclass, field
from typing import Callable

from agent_os.evaluation import Examination, EvaluationRunner

from .base import Agent, AgentContext


@dataclass(frozen=True)
class CorrectionAttempt:
    attempt: int
    output: str | None
    examination: Examination
    error: str | None = None


@dataclass(frozen=True)
class CorrectionResult:
    success: bool
    output: str | None
    attempts: list[CorrectionAttempt] = field(
        default_factory=list
    )
    error: str | None = None


class CorrectionEngine:
    """Iteratively execute, examine, and correct agent output."""

    def __init__(
        self,
        agent: Agent,
        evaluation: EvaluationRunner | None = None,
        max_attempts: int = 3,
        corrector: Callable[[str, Examination], str] | None = None,
    ):
        if max_attempts <= 0:
            raise ValueError("max_attempts must be positive")

        self.agent = agent
        self.evaluation = evaluation or EvaluationRunner()
        self.max_attempts = max_attempts
        self.corrector = corrector

    def run(
        self,
        context: AgentContext,
        required_keywords: list[str],
    ) -> CorrectionResult:
        attempts: list[CorrectionAttempt] = []
        objective = context.objective

        for attempt_number in range(1, self.max_attempts + 1):
            attempt_context = AgentContext(
                task_id=context.task_id,
                objective=objective,
                metadata=dict(context.metadata),
            )

            try:
                result = self.agent.run(attempt_context)
                examination = self.evaluation.examine(
                    [
                        self.evaluation.evaluate(
                            context.task_id,
                            result.output,
                            required_keywords,
                        ).metrics[0]
                    ]
                )

                attempt = CorrectionAttempt(
                    attempt=attempt_number,
                    output=result.output,
                    examination=examination,
                )
                attempts.append(attempt)

                if examination.passed:
                    return CorrectionResult(
                        success=True,
                        output=result.output,
                        attempts=attempts,
                    )

                if self.corrector is None:
                    return CorrectionResult(
                        success=False,
                        output=result.output,
                        attempts=attempts,
                        error="correction_strategy_unavailable",
                    )

                objective = self.corrector(
                    result.output,
                    examination,
                )

                if not objective.strip():
                    return CorrectionResult(
                        success=False,
                        output=result.output,
                        attempts=attempts,
                        error="correction_objective_empty",
                    )

            except Exception as exc:
                attempts.append(
                    CorrectionAttempt(
                        attempt=attempt_number,
                        output=None,
                        examination=Examination(
                            passed=False,
                            score=0.0,
                            feedback=["execution_failed"],
                        ),
                        error=str(exc),
                    )
                )
                return CorrectionResult(
                    success=False,
                    output=None,
                    attempts=attempts,
                    error=str(exc),
                )

        return CorrectionResult(
            success=False,
            output=(
                attempts[-1].output
                if attempts
                else None
            ),
            attempts=attempts,
            error="max_correction_attempts_exceeded",
        )
