from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .permissions import PermissionPolicy
from .registry import ToolRegistry


@dataclass(frozen=True)
class ToolExecutionResult:
    """Auditable result of a tool execution attempt."""

    tool_name: str
    success: bool
    output: Any = None
    error: str | None = None
    started_at: str = ""
    finished_at: str = ""
    metadata: dict[str, Any] = field(
        default_factory=dict
    )


class ToolExecutor:
    """Execute registered tools through an explicit permission boundary."""

    def __init__(
        self,
        registry: ToolRegistry,
        permissions: PermissionPolicy,
    ):
        self.registry = registry
        self.permissions = permissions

    def execute(
        self,
        tool_name: str,
        **kwargs: Any,
    ) -> ToolExecutionResult:
        """Execute a tool and return an auditable result."""

        started_at = datetime.now(
            timezone.utc
        ).isoformat()

        try:
            self.permissions.require(tool_name)
            tool = self.registry.get(tool_name)

            output = tool.handler(**kwargs)

            return ToolExecutionResult(
                tool_name=tool_name,
                success=True,
                output=output,
                started_at=started_at,
                finished_at=datetime.now(
                    timezone.utc
                ).isoformat(),
                metadata={
                    "arguments": sorted(kwargs),
                },
            )

        except Exception as exc:
            return ToolExecutionResult(
                tool_name=tool_name,
                success=False,
                error=f"{type(exc).__name__}: {exc}",
                started_at=started_at,
                finished_at=datetime.now(
                    timezone.utc
                ).isoformat(),
                metadata={
                    "arguments": sorted(kwargs),
                },
            )
