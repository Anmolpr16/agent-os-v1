from agent_os.integration.mcp import MCPIntegration
from agent_os.integration.mcp_tools import MCPToolRegistrar
from agent_os.tools.registry import ToolRegistry


def make_transport(capabilities):
    def transport(request):
        if request["method"] == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {
                    "protocolVersion": "2025-06-18",
                    "serverInfo": {
                        "name": "capability-server",
                        "version": "1.0",
                    },
                    "capabilities": capabilities,
                },
            }

        if request["method"] == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {
                    "tools": [
                        {
                            "name": "search",
                            "description": "Search",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string"},
                                },
                                "required": ["query"],
                            },
                        }
                    ]
                },
            }

        raise AssertionError(f"unexpected method: {request['method']}")

    return transport


def test_strict_registrar_requires_initialized_session():
    integration = MCPIntegration(
        make_transport({"tools": {}}),
        require_initialization=False,
    )
    registrar = MCPToolRegistrar(
        integration,
        ToolRegistry(),
        require_capability=True,
    )

    try:
        registrar.discover()
    except RuntimeError as exc:
        assert str(exc) == "mcp_not_initialized"
    else:
        raise AssertionError("expected initialization requirement")


def test_strict_registrar_requires_tools_capability():
    integration = MCPIntegration(
        make_transport({}),
        require_initialization=False,
    )
    integration.initialize()

    registrar = MCPToolRegistrar(
        integration,
        ToolRegistry(),
        require_capability=True,
    )

    try:
        registrar.discover()
    except RuntimeError as exc:
        assert str(exc) == "mcp_tools_capability_missing"
    else:
        raise AssertionError("expected tools capability requirement")


def test_initialize_and_register_enforces_tools_capability():
    integration = MCPIntegration(
        make_transport({"tools": {}}),
    )
    registry = ToolRegistry()

    tools = MCPToolRegistrar(
        integration,
        registry,
    ).initialize_and_register()

    assert len(tools) == 1
    assert tools[0].name == "mcp:search"
    assert integration.initialized is True
    assert integration.server_capabilities == {"tools": {}}


def test_tool_schema_is_validated_during_discovery():
    def transport(request):
        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {
                "tools": [
                    {
                        "name": "bad",
                        "description": "Bad schema",
                        "inputSchema": "not-an-object",
                    }
                ]
            },
        }

    integration = MCPIntegration(transport)

    try:
        MCPToolRegistrar(
            integration,
            ToolRegistry(),
        ).discover()
    except ValueError as exc:
        assert str(exc) == "mcp_tool_input_schema_invalid"
    else:
        raise AssertionError("expected schema validation failure")


def test_initialize_failure_stops_registration():
    def transport(request):
        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "error": {
                "code": -32602,
                "message": "invalid parameters",
            },
        }

    integration = MCPIntegration(transport)
    registry = ToolRegistry()

    try:
        MCPToolRegistrar(
            integration,
            registry,
        ).initialize_and_register()
    except RuntimeError as exc:
        assert "mcp_initialization_failed" in str(exc)
    else:
        raise AssertionError("expected initialization failure")

    assert registry.list() == []
