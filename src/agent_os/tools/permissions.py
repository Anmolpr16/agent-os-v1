from dataclasses import dataclass, field


@dataclass
class PermissionPolicy:
    """Allowlist controlling which registered tools may execute."""

    allowed_tools: set[str] = field(default_factory=set)

    def allows(self, tool_name: str) -> bool:
        return tool_name in self.allowed_tools

    def require(self, tool_name: str) -> None:
        if not self.allows(tool_name):
            raise PermissionError(
                f"tool_not_permitted:{tool_name}"
            )
