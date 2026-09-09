from dataclasses import dataclass, field
from threading import RLock
from time import monotonic
from typing import Any

@dataclass(frozen=True)
class RuntimeEvent:
    name: str
    task_id: str
    metadata: dict[str, Any] = field(default_factory=dict)

class RuntimeMetrics:
    def __init__(self):
        self._events: list[RuntimeEvent] = []
        self._durations: list[float] = []
        self._lock = RLock()

    def emit(self, name: str, task_id: str,
              metadata: dict[str, Any] | None = None) -> None:
        if not name.strip():
            raise ValueError("event_name_required")
        if not task_id.strip():
            raise ValueError("event_task_id_required")
        with self._lock:
            self._events.append(
                RuntimeEvent(name, task_id, dict(metadata or {}))
            )

    def timed(self):
        return _Timer(self)

    def events(self) -> list[RuntimeEvent]:
        with self._lock:
            return list(self._events)

    def summary(self) -> dict[str, Any]:
        with self._lock:
            counts: dict[str, int] = {}
            for event in self._events:
                counts[event.name] = counts.get(event.name, 0) + 1
            return {
                "events": len(self._events),
                "counts": counts,
                "timed_operations": len(self._durations),
                "total_duration": sum(self._durations),
            }

class _Timer:
    def __init__(self, metrics: RuntimeMetrics):
        self.metrics = metrics
        self.started = 0.0

    def __enter__(self):
        self.started = monotonic()
        return self

    def __exit__(self, exc_type, exc, traceback):
        with self.metrics._lock:
            self.metrics._durations.append(monotonic() - self.started)
