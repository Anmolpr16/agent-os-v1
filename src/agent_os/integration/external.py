from __future__ import annotations

from typing import Any

from .contracts import Integration, IntegrationRequest
from agent_os.tools.registry import Tool


class IntegrationToolAdapter:
    """Expose one Integration operation through the normal Tool boundary.

    External systems therefore remain behind the existing registry,
    permission, retry, and audit mechanisms.
    """

    def __init__(
        self,
        integration: Integration,
        *,
        operation: str,
        tool_name: str | None = None,
        description: str = "",
    ):
        if not operation.strip():
            raise ValueError("integration_operation_missing")

        self.integration = integration
        self.operation = operation
        self.tool_name = tool_name or f"integration:{operation}"
        self.description = description or f"External integration operation: {operation}"

    def as_tool(self) -> Tool:
        def handler(**payload: Any) -> Any:
            response = self.integration.execute(
                IntegrationRequest(
                    operation=self.operation,
                    payload=payload,
                )
            )

            if not response.success:
                detail = response.error or "unknown"
                raise RuntimeError(
                    f"integration_operation_failed:{detail}"
                )

            return response.output

        return Tool(
            name=self.tool_name,
            description=self.description,
            handler=handler,
        )
