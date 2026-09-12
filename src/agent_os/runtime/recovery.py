from dataclasses import dataclass
from typing import Any, Callable

from agent_os.core.recovery import RetryPolicy, retry


@dataclass(frozen=True)
class RecoveryResult:
    """Structured result of a bounded runtime recovery attempt."""

    success: bool
    attempts: int
    output: Any = None
    error: str | None = None


class RecoveryController:
    """Runtime adapter over the canonical core retry primitive."""

    def __init__(self, max_attempts: int = 3):
        self.policy = RetryPolicy(max_attempts=max_attempts)

    @property
    def max_attempts(self) -> int:
        return self.policy.max_attempts

    def run(self, operation: Callable[[], Any]) -> RecoveryResult:
        attempts = 0

        def tracked_operation() -> Any:
            nonlocal attempts
            attempts += 1
            return operation()

        try:
            output = retry(
                tracked_operation,
                self.policy,
                retryable_errors=(TimeoutError, ConnectionError),
            )
            return RecoveryResult(
                success=True,
                attempts=attempts,
                output=output,
            )
        except (TimeoutError, ConnectionError) as exc:
            return RecoveryResult(
                success=False,
                attempts=attempts,
                error=str(exc) or "recovery_failed",
            )
