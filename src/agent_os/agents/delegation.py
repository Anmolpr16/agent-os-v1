from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DelegatedTask:
    task_id: str
    objective: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DelegatedResult:
    task_id: str
    success: bool
    output: str | None = None
    error: str | None = None


class AgentWorker:
    """Minimal worker contract for delegated agent tasks."""

    def execute(self, task: DelegatedTask) -> DelegatedResult:
        raise NotImplementedError
