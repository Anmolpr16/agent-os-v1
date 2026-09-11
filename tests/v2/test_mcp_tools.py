from agent_os.integration.mcp import MCPIntegration
from agent_os.integration.mcp_tools import MCPToolRegistrar
from agent_os.tools import ToolRegistry


def test_mcp_tool_discovery_validates_and_registers_tools():
    calls = []

    def transport(request):
        calls.append(request)

        if request["method"] == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {
                    "tools": [
                        {
                            "name": "search",
                            "description": "Search information",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string"},
                                },
                            },
                        }
                    ]
                },
            }

        raise AssertionError("unexpected method")

    integration = MCPIntegration(transport)
    registry = ToolRegistry()
    registrar = MCPToolRegistrar(integration, registry)

    tools = registrar.register()

    assert len(tools) == 1
    assert tools[0].name == "mcp:search"
    assert tools[0].description == "Search information"
    assert registry.get("mcp:search") is tools[0]
    assert calls[0]["method"] == "tools/list"


def test_mcp_registered_tool_routes_to_tools_call():
    calls = []

    def transport(request):
        calls.append(request)

        if request["method"] == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {
                    "tools": [
                        {
                            "name": "echo",
                            "description": "Echo values",
                        }
                    ]
                },
            }

        if request["method"] == "tools/call":
            return {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {
                    "content": [
                        {"type": "text", "text": request["params"]["arguments"]["value"]}
                    ]
                },
            }

        raise AssertionError("unexpected method")

    integration = MCPIntegration(transport)
    registry = ToolRegistry()
    registrar = MCPToolRegistrar(integration, registry)

    registrar.register()

    result = registry.get("mcp:echo").handler(value="hello")

    assert result["content"][0]["text"] == "hello"
    assert calls[1]["method"] == "tools/call"
    assert calls[1]["params"]["name"] == "echo"
    assert calls[1]["params"]["arguments"] == {"value": "hello"}


def test_mcp_discovery_failure_is_explicit():
    integration = MCPIntegration(
        lambda request: {
            "jsonrpc": "2.0",
            "id": request["id"],
            "error": {
                "code": -32601,
                "message": "method not found",
            },
        }
    )

    registrar = MCPToolRegistrar(integration, ToolRegistry())

    try:
        registrar.discover()
    except RuntimeError as exc:
        assert "mcp_tool_discovery_failed" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")


def test_mcp_malformed_tool_definition_is_rejected():
    integration = MCPIntegration(
        lambda request: {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {
                "tools": [
                    {
                        "description": "missing name",
                    }
                ]
            },
        }
    )

    registrar = MCPToolRegistrar(integration, ToolRegistry())

    try:
        registrar.discover()
    except ValueError as exc:
        assert str(exc) == "mcp_tool_name_invalid"
    else:
        raise AssertionError("expected ValueError")


def test_mcp_duplicate_registration_is_rejected():
    def transport(request):
        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {
                "tools": [
                    {
                        "name": "echo",
                        "description": "Echo",
                    }
                ]
            },
        }

    integration = MCPIntegration(transport)
    registry = ToolRegistry()
    registrar = MCPToolRegistrar(integration, registry)

    registrar.register()

    try:
        registrar.register()
    except ValueError as exc:
        assert str(exc) == "mcp_tool_already_registered:echo"
    else:
        raise AssertionError("expected ValueError")
