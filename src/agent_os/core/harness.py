from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .failures import classify_error

if TYPE_CHECKING:
    from agent_os.agents import Agent, AgentContext, AgentResult


@dataclass(frozen=True)
class HarnessResult:
    success: bool
    result: AgentResult | None = None
    error: str | None = None
    attempts: int = 0


class AgentHarness:
    """Controlled execution boundary for agent runs."""

    def __init__(
        self,
        agent: Agent,
        max_attempts: int = 1,
    ):
        if max_attempts <= 0:
            raise ValueError("max_attempts must be positive")

        self.agent = agent
        self.max_attempts = max_attempts

    def run(self, context: AgentContext) -> HarnessResult:
        last_error: Exception | None = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                result = self.agent.run(context)
            except Exception as exc:
                last_error = exc
                failure = classify_error(exc)
                if not failure.recoverable:
                    break
                continue

            return HarnessResult(
                success=True,
                result=result,
                attempts=attempt,
            )

        return HarnessResult(
            success=False,
            error=str(last_error) if last_error is not None else "run_failed",
            attempts=attempt if last_error is not None else 0,
        )
