from dataclasses import dataclass
from typing import Callable, TypeVar


T = TypeVar("T")


@dataclass(frozen=True)
class RetryPolicy:
    """Bounded retry policy for recoverable operations."""

    max_attempts: int = 3

    def __post_init__(self):
        if self.max_attempts < 1:
            raise ValueError(
                "max_attempts_must_be_positive"
            )

    def allows(self, attempt: int) -> bool:
        return 1 <= attempt <= self.max_attempts


def retry(
    operation: Callable[[], T],
    policy: RetryPolicy,
    retryable_errors: tuple[type[Exception], ...] = (
        Exception,
    ),
) -> T:
    """Retry only exceptions explicitly classified as retryable."""

    attempt = 1

    while policy.allows(attempt):
        try:
            return operation()
        except retryable_errors:
            if not policy.allows(attempt + 1):
                raise
            attempt += 1

    raise RuntimeError("retry_operation_failed")
