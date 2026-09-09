from dataclasses import dataclass
from enum import Enum


class FailureKind(str, Enum):
    RECOVERABLE = "recoverable"
    TERMINAL = "terminal"


@dataclass(frozen=True)
class RuntimeFailure:
    kind: FailureKind
    code: str
    message: str

    @property
    def recoverable(self) -> bool:
        return self.kind == FailureKind.RECOVERABLE


def classify_error(error: Exception) -> RuntimeFailure:
    """Classify runtime errors before recovery is attempted."""

    if isinstance(error, (TimeoutError, ConnectionError)):
        return RuntimeFailure(
            kind=FailureKind.RECOVERABLE,
            code=type(error).__name__.lower(),
            message=str(error),
        )

    if isinstance(error, (PermissionError, KeyError, ValueError)):
        return RuntimeFailure(
            kind=FailureKind.TERMINAL,
            code=type(error).__name__.lower(),
            message=str(error),
        )

    return RuntimeFailure(
        kind=FailureKind.TERMINAL,
        code=type(error).__name__.lower(),
        message=str(error),
    )
