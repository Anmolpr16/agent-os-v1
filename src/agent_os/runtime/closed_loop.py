from dataclasses import dataclass, field
from typing import Any, Callable

from agent_os.agents import Agent, AgentContext
from agent_os.evaluation import EvaluationRunner
from agent_os.governance import ApprovalGate, ApprovalRequest, ApprovalStatus
from agent_os.runtime.replanning import Replanner
from agent_os.runtime.shared_state import SharedState
from agent_os.runtime.policy import RuntimePolicy

@dataclass(frozen=True)
class LoopAttempt:
    attempt: int
    output: str | None
    score: float
    passed: bool
    feedback: list[str] = field(default_factory=list)
    error: str | None = None

@dataclass(frozen=True)
class ClosedLoopResult:
    success: bool
    output: str | None
    attempts: list[LoopAttempt]
    approval: ApprovalStatus | None
    error: str | None = None

class ClosedLoopRunner:
    def __init__(
        self,
        agent: Agent,
        evaluation: EvaluationRunner | None = None,
        replanner: Replanner | None = None,
        approval: ApprovalGate | None = None,
        state: SharedState | None = None,
        max_attempts: int = 3,
        policy: RuntimePolicy | None = None,
    ):
        if max_attempts <= 0:
            raise ValueError("max_attempts must be positive")
        self.agent = agent
        self.evaluation = evaluation or EvaluationRunner()
        self.replanner = replanner or Replanner()
        self.approval = approval or ApprovalGate()
        self.state = state or SharedState()
        self.max_attempts = max_attempts
        self.policy = policy or RuntimePolicy()

    def run(
        self,
        context: AgentContext,
        required_keywords: list[str],
    ) -> ClosedLoopResult:
        objective = context.objective
        attempts: list[LoopAttempt] = []

        for number in range(1, self.max_attempts + 1):
            try:
                result = self.agent.run(
                    AgentContext(
                        task_id=context.task_id,
                        objective=objective,
                        metadata=dict(context.metadata),
                    )
                )

                if self.policy.require_evaluation:
                    evaluation = self.evaluation.evaluate(
                        context.task_id,
                        result.output,
                        required_keywords,
                    )
                    examination = self.evaluation.examine(evaluation.metrics)
                    score = examination.score
                    passed = examination.passed
                    feedback = list(examination.feedback)
                else:
                    score = 1.0
                    passed = True
                    feedback = []

                attempt = LoopAttempt(
                    attempt=number,
                    output=result.output,
                    score=score,
                    passed=passed,
                    feedback=feedback,
                )
                attempts.append(attempt)

                self.state.set(
                    f"{context.task_id}:attempt:{number}",
                    {
                        "output": result.output,
                        "score": score,
                        "passed": passed,
                    },
                )

                if passed:
                    if self.policy.require_approval:
                        decision = self.approval.request(
                            ApprovalRequest(
                                task_id=context.task_id,
                                objective=context.objective,
                                output=result.output,
                            )
                        )
                        if decision.status == ApprovalStatus.APPROVED:
                            self.state.set(
                                f"{context.task_id}:final",
                                result.output,
                            )
                            return ClosedLoopResult(
                                True,
                                result.output,
                                attempts,
                                decision.status,
                            )
                        return ClosedLoopResult(
                            False,
                            result.output,
                            attempts,
                            decision.status,
                            decision.reason,
                        )

                    self.state.set(
                        f"{context.task_id}:final",
                        result.output,
                    )
                    return ClosedLoopResult(
                        True,
                        result.output,
                        attempts,
                        ApprovalStatus.APPROVED,
                    )

                replan = self.replanner.decide(
                    result.output,
                    ";".join(feedback),
                )
                if not replan.required:
                    return ClosedLoopResult(
                        False,
                        result.output,
                        attempts,
                        None,
                        replan.reason,
                    )
                objective = replan.objective

            except Exception as exc:
                attempts.append(
                    LoopAttempt(
                        attempt=number,
                        output=None,
                        score=0.0,
                        passed=False,
                        feedback=["execution_failed"],
                        error=str(exc),
                    )
                )
                return ClosedLoopResult(
                    False,
                    None,
                    attempts,
                    None,
                    str(exc),
                )

        return ClosedLoopResult(
            False,
            attempts[-1].output if attempts else None,
            attempts,
            None,
            "max_loop_attempts_exceeded",
        )
