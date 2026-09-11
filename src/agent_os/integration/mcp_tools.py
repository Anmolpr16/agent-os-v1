from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .mcp import MCPIntegration
from .mcp_schema import validate_mcp_arguments, MCPSchemaValidationError
from agent_os.tools.registry import Tool, ToolRegistry


@dataclass(frozen=True)
class MCPToolDefinition:
    name: str
    description: str = ""
    input_schema: dict[str, Any] | None = None

    def __post_init__(self):
        if not self.name.strip():
            raise ValueError("mcp_tool_name_missing")

        if not isinstance(self.description, str):
            raise TypeError("mcp_tool_description_invalid")

        if self.input_schema is not None and not isinstance(self.input_schema, dict):
            raise TypeError("mcp_tool_input_schema_invalid")

    @property
    def tool_name(self) -> str:
        return f"mcp:{self.name}"


class MCPToolRegistrar:
    """Discover MCP tools and expose them through the normal Tool boundary."""

    def __init__(
        self,
        integration: MCPIntegration,
        registry: ToolRegistry,
        *,
        require_capability: bool = False,
    ):
        self.integration = integration
        self.registry = registry
        self.require_capability = bool(require_capability)

    def _require_tools_capability(self) -> None:
        if not self.require_capability:
            return

        if not self.integration.initialized:
            raise RuntimeError("mcp_not_initialized")

        capabilities = self.integration.server_capabilities

        if not isinstance(capabilities, dict):
            raise RuntimeError("mcp_capabilities_invalid")

        tools_capability = capabilities.get("tools")

        if tools_capability is None:
            raise RuntimeError("mcp_tools_capability_missing")

        if not isinstance(tools_capability, dict):
            raise RuntimeError("mcp_tools_capability_invalid")

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

            if not isinstance(name, str) or not name.strip():
                raise ValueError("mcp_tool_name_invalid")

            if not isinstance(description, str):
                raise ValueError("mcp_tool_description_invalid")

            if schema is not None and not isinstance(schema, dict):
                raise ValueError("mcp_tool_input_schema_invalid")

            definitions.append(
                MCPToolDefinition(
                    name=name,
                    description=description,
                    input_schema=dict(schema) if schema is not None else None,
                )
            )

        return definitions

    def discover(self) -> list[MCPToolDefinition]:
        self._require_tools_capability()

        response = self.integration.list_tools()

        if not response.success:
            raise RuntimeError(
                f"mcp_tool_discovery_failed:{response.error or 'unknown'}"
            )

        return self._definitions(response.output)

    def register(self) -> list[Tool]:
        definitions = self.discover()
        existing = {tool.name for tool in self.registry.list()}
        registered: list[Tool] = []

        for definition in definitions:
            tool_name = definition.tool_name

            if tool_name in existing:
                raise ValueError(
                    f"mcp_tool_already_registered:{definition.name}"
                )

            def handler(
                _tool_name: str = definition.name,
                _input_schema: dict[str, Any] | None = definition.input_schema,
                **arguments: Any,
            ) -> Any:
                try:
                    validate_mcp_arguments(arguments, _input_schema)
                except MCPSchemaValidationError as exc:
                    raise ValueError(
                        f"mcp_tool_arguments_invalid:{exc}"
                    ) from exc

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

            description = (
                definition.description
                or f"MCP tool: {definition.name}"
            )

            tool = self.registry.register(
                name=tool_name,
                description=description,
                handler=handler,
                input_schema=(
                    dict(definition.input_schema)
                    if definition.input_schema is not None
                    else None
                ),
            )

            existing.add(tool_name)
            registered.append(tool)

        return registered

    def initialize_and_register(
        self,
        params: dict[str, Any] | None = None,
    ) -> list[Tool]:
        """Initialize the MCP session, enforce the tools capability, then register."""
        response = self.integration.initialize(params)

        if not response.success:
            raise RuntimeError(
                f"mcp_initialization_failed:{response.error or 'unknown'}"
            )

        self.require_capability = True
        return self.register()
