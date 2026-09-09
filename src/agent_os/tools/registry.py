from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class Tool:
    """Explicitly registered callable capability."""

    name: str
    description: str
    handler: Callable[..., Any]


class ToolRegistry:
    """Registry of capabilities available to the agent runtime."""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(
        self,
        name: str,
        description: str,
        handler: Callable[..., Any],
    ) -> Tool:
        if not name.strip():
            raise ValueError("tool_name_missing")

        if name in self._tools:
            raise ValueError(
                f"tool_already_registered:{name}"
            )

        tool = Tool(
            name=name,
            description=description,
            handler=handler,
        )

        self._tools[name] = tool
        return tool

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError:
            raise KeyError(
                f"tool_not_registered:{name}"
            ) from None

    def list(self) -> list[Tool]:
        return list(self._tools.values())
