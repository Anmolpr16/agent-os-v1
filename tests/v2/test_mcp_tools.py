from agent_os.tools.registry import Tool
import pytest
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


def test_registered_mcp_tool_enforces_input_schema():
    from agent_os.integration.mcp import MCPIntegration
    from agent_os.integration.mcp_tools import MCPToolRegistrar
    from agent_os.tools.registry import ToolRegistry

    calls = []

    def transport(request):
        calls.append(request)
        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {
                "tools": [
                    {
                        "name": "lookup",
                        "description": "Lookup a value",
                        "inputSchema": {
                            "type": "object",
                            "required": ["query"],
                            "properties": {
                                "query": {"type": "string"},
                            },
                            "additionalProperties": False,
                        },
                    }
                ]
            },
        }

    integration = MCPIntegration(transport)
    registry = ToolRegistry()

    tools = MCPToolRegistrar(
        integration,
        registry,
    ).register()

    assert len(tools) == 1

    result = tools[0].handler(query="hello")

    assert result == {"tools": [
        {
            "name": "lookup",
            "description": "Lookup a value",
            "inputSchema": {
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {"type": "string"},
                },
                "additionalProperties": False,
            },
        }
    ]}
    assert len(calls) == 2
    assert calls[1]["method"] == "tools/call"
    assert calls[1]["params"]["name"] == "lookup"
    assert calls[1]["params"]["arguments"] == {"query": "hello"}


def test_registered_mcp_tool_rejects_invalid_arguments_before_remote_call():
    from agent_os.integration.mcp import MCPIntegration
    from agent_os.integration.mcp_tools import MCPToolRegistrar
    from agent_os.tools.registry import ToolRegistry

    calls = []

    def transport(request):
        calls.append(request)
        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {
                "tools": [
                    {
                        "name": "lookup",
                        "inputSchema": {
                            "type": "object",
                            "required": ["query"],
                            "properties": {
                                "query": {"type": "string"},
                            },
                            "additionalProperties": False,
                        },
                    }
                ]
            },
        }

    integration = MCPIntegration(transport)
    registry = ToolRegistry()

    tool = MCPToolRegistrar(
        integration,
        registry,
    ).register()[0]

    import pytest

    with pytest.raises(ValueError, match="mcp_tool_arguments_invalid"):
        tool.handler(query=123)

    assert len(calls) == 1
    assert calls[0]["method"] == "tools/list"


def test_registered_mcp_tool_exposes_input_schema():
    schema = {
        "type": "object",
        "required": ["query"],
        "properties": {
            "query": {"type": "string"},
        },
        "additionalProperties": False,
    }

    def transport(request):
        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {
                "tools": [
                    {
                        "name": "lookup",
                        "description": "Lookup a value",
                        "inputSchema": schema,
                    }
                ]
            },
        }

    integration = MCPIntegration(transport)
    registry = ToolRegistry()

    MCPToolRegistrar(integration, registry).register()

    tool = registry.get("mcp:lookup")

    assert tool.input_schema == schema
    assert tool.input_schema is not schema


def test_legacy_tool_registration_has_no_input_schema():
    registry = ToolRegistry()

    tool = registry.register(
        name="legacy",
        description="Legacy tool",
        handler=lambda **kwargs: kwargs,
    )

    assert tool.input_schema is None


def test_tool_rejects_non_dict_input_schema():
    with pytest.raises(TypeError, match="tool_input_schema_invalid"):
        Tool(
            name="invalid",
            description="Invalid schema",
            handler=lambda **kwargs: kwargs,
            input_schema="not-a-schema",
        )
