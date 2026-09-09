from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock
from typing import Any

@dataclass(frozen=True)
class AuditEvent:
    event: str
    actor: str
    task_id: str
    metadata: dict[str, Any]
    timestamp: str

class AuditLog:
    def __init__(self):
        self._events: list[AuditEvent] = []
        self._lock = RLock()

    def record(self, event: str, actor: str, task_id: str,
               metadata: dict[str, Any] | None = None) -> AuditEvent:
        if not event.strip():
            raise ValueError("audit_event_required")
        if not actor.strip():
            raise ValueError("audit_actor_required")
        if not task_id.strip():
            raise ValueError("audit_task_id_required")
        item = AuditEvent(
            event=event,
            actor=actor,
            task_id=task_id,
            metadata=dict(metadata or {}),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        with self._lock:
            self._events.append(item)
        return item

    def all(self) -> list[AuditEvent]:
        with self._lock:
            return list(self._events)

    def for_task(self, task_id: str) -> list[AuditEvent]:
        with self._lock:
            return [event for event in self._events if event.task_id == task_id]
