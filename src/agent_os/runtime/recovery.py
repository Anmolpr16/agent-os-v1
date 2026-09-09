
from dataclasses import dataclass
from typing import Callable, Any

@dataclass(frozen=True)
class RecoveryResult:
    success: bool
    attempts: int
    output: Any = None
    error: str | None = None

class RecoveryController:
    def __init__(self, max_attempts: int = 3):
        if max_attempts <= 0:
            raise ValueError("max_attempts must be positive")
        self.max_attempts = max_attempts

    def run(self, operation: Callable[[], Any]) -> RecoveryResult:
        last_error = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                return RecoveryResult(
                    success=True,
                    attempts=attempt,
                    output=operation(),
                )
            except (TimeoutError, ConnectionError) as exc:
                last_error = str(exc)
        return RecoveryResult(
            success=False,
            attempts=self.max_attempts,
            error=last_error or "recovery_failed",
        )
