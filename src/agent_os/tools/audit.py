from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolAuditLog:
    """In-memory audit trail for tool execution attempts."""

    entries: list[dict[str, Any]] = field(
        default_factory=list
    )

    def record(
        self,
        result: Any,
    ) -> None:
        self.entries.append(
            {
                "tool_name": result.tool_name,
                "success": result.success,
                "error": result.error,
                "started_at": result.started_at,
                "finished_at": result.finished_at,
                "metadata": result.metadata,
            }
        )

    def last(self) -> dict[str, Any] | None:
        if not self.entries:
            return None

        return self.entries[-1]
