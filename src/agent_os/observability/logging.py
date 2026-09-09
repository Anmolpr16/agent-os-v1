from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class EventLogger:
    """Structured in-memory event logger."""

    entries: list[dict[str, Any]] = field(
        default_factory=list
    )

    def log(
        self,
        event_type: str,
        task_id: str,
        **data: Any,
    ) -> dict[str, Any]:
        event = {
            "type": event_type,
            "task_id": task_id,
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "data": data,
        }

        self.entries.append(event)

        return event
