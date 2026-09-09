from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class LifecycleEvent:
    name: str
    task_id: str
    timestamp: str
    metadata: dict[str, Any]


class RuntimeLifecycle:
    def __init__(self) -> None:
        self._events: list[LifecycleEvent] = []

    def emit(
        self,
        name: str,
        task_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> LifecycleEvent:
        if not name.strip():
            raise ValueError("lifecycle_event_required")
        if not task_id.strip():
            raise ValueError("task_id_required")

        event = LifecycleEvent(
            name=name,
            task_id=task_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata=dict(metadata or {}),
        )
        self._events.append(event)
        return event

    def events(self) -> list[LifecycleEvent]:
        return list(self._events)

    def for_task(self, task_id: str) -> list[LifecycleEvent]:
        return [event for event in self._events if event.task_id == task_id]

    def latest(self, task_id: str) -> LifecycleEvent | None:
        events = self.for_task(task_id)
        return events[-1] if events else None


@dataclass(frozen=True)
class RuntimeHealth:
    status: str
    checks: dict[str, str]

    @property
    def healthy(self) -> bool:
        return self.status == "ok"


def check_runtime(runtime: Any) -> RuntimeHealth:
    checks: dict[str, str] = {}

    required = (
        ("state", getattr(runtime, "state", None)),
        ("messages", getattr(runtime, "messages", None)),
        ("audit", getattr(runtime, "audit", None)),
        ("metrics", getattr(runtime, "metrics", None)),
        ("replanner", getattr(runtime, "replanner", None)),
    )

    for name, value in required:
        checks[name] = "ok" if value is not None else "missing"

    status = "ok" if all(value == "ok" for value in checks.values()) else "degraded"
    return RuntimeHealth(status=status, checks=checks)
