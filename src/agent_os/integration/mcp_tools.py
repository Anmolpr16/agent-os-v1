from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .mcp import MCPIntegration
from .contracts import IntegrationRequest
from agent_os.tools.registry import Tool, ToolRegistry


@dataclass(frozen=True)
class MCPToolDefinition:
    """Validated description of one tool advertised by an MCP server."""

    name: str
    description: str = ""
    input_schema: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("mcp_tool_name_missing")

        if self.input_schema is not None and not isinstance(
            self.input_schema, dict
        ):
            raise TypeError("mcp_tool_input_schema_invalid")


class MCPToolRegistrar:
    """Discover MCP tools and expose them through the Agent OS ToolRegistry."""

    def __init__(
        self,
        integration: MCPIntegration,
        registry: ToolRegistry,
    ):
        self.integration = integration
        self.registry = registry

    @staticmethod
    def _definitions(output: Any) -> list[MCPToolDefinition]:
        if not isinstance(output, dict):
            raise ValueError("mcp_tools_list_invalid")

        raw_tools = output.get("tools", [])
        if not isinstance(raw_tools, list):
            raise ValueError("mcp_tools_list_invalid")

        definitions: list[MCPToolDefinition] = []

        for raw in raw_tools:
            if not isinstance(raw, dict):
                raise ValueError("mcp_tool_definition_invalid")

            name = raw.get("name")
            description = raw.get("description", "")
            schema = raw.get("inputSchema")

            if not isinstance(name, str):
                raise ValueError("mcp_tool_name_invalid")

            if not isinstance(description, str):
                raise ValueError("mcp_tool_description_invalid")

            definitions.append(
                MCPToolDefinition(
                    name=name,
                    description=description,
                    input_schema=schema,
                )
            )

        return definitions

    def discover(self) -> list[MCPToolDefinition]:
        response = self.integration.list_tools()

        if not response.success:
            raise RuntimeError(
                f"mcp_tool_discovery_failed:{response.error or 'unknown'}"
            )

        return self._definitions(response.output)

    def register(self) -> list[Tool]:
        definitions = self.discover()
        registered: list[Tool] = []

        for definition in definitions:
            tool_name = f"mcp:{definition.name}"

            if tool_name in {tool.name for tool in self.registry.list()}:
                raise ValueError(
                    f"mcp_tool_already_registered:{definition.name}"
                )

            def handler(
                _tool_name: str = definition.name,
                **arguments: Any,
            ) -> Any:
                response = self.integration.call_tool(
                    _tool_name,
                    arguments,
                )

                if not response.success:
                    raise RuntimeError(
                        "mcp_tool_execution_failed:"
                        f"{response.error or 'unknown'}"
                    )

                return response.output

            tool = self.registry.register(
                name=tool_name,
                description=definition.description
                or f"MCP tool: {definition.name}",
                handler=handler,
            )
            registered.append(tool)

        return registered
