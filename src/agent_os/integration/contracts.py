from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class IntegrationRequest:
    operation: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class IntegrationResponse:
    success: bool
    output: Any = None
    error: str | None = None


class Integration(Protocol):
    """Boundary for external service integrations."""

    def execute(
        self,
        request: IntegrationRequest,
    ) -> IntegrationResponse:
        ...
