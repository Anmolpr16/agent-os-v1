from typing import Any

from .permissions import PermissionPolicy
from .registry import ToolRegistry


class ToolExecutor:
    """Execute only explicitly registered and permitted tools."""

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
    ) -> Any:
        self.permissions.require(tool_name)

        tool = self.registry.get(tool_name)

        return tool.handler(**kwargs)
