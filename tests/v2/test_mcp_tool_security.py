from agent_os.integration.mcp import MCPIntegration
from agent_os.integration.mcp_tools import MCPToolRegistrar
from agent_os.tools import PermissionPolicy, ToolAuditLog, ToolExecutor, ToolRegistry


def make_integration(calls):
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
                            "description": "Search service",
                        }
                    ]
                },
            }

        if request["method"] == "tools/call":
            return {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {"answer": "ok"},
            }

        raise AssertionError("unexpected method")

    return MCPIntegration(transport)


def test_discovered_mcp_tool_requires_explicit_permission():
    calls = []
    integration = make_integration(calls)
    registry = ToolRegistry()
    MCPToolRegistrar(integration, registry).register()

    audit = ToolAuditLog()
    executor = ToolExecutor(
        registry,
        PermissionPolicy(allowed_tools=set()),
        audit=audit,
    )

    result = executor.execute("mcp:search", query="test")

    assert result.success is False
    assert "tool_not_permitted:mcp:search" in result.error
    assert len(calls) == 1
    assert calls[0]["method"] == "tools/list"
    assert len(audit.entries) == 1
    assert audit.last()["success"] is False


def test_permitted_mcp_tool_executes_through_executor():
    calls = []
    integration = make_integration(calls)
    registry = ToolRegistry()
    MCPToolRegistrar(integration, registry).register()

    audit = ToolAuditLog()
    executor = ToolExecutor(
        registry,
        PermissionPolicy(allowed_tools={"mcp:search"}),
        audit=audit,
    )

    result = executor.execute("mcp:search", query="agent os")

    assert result.success is True
    assert result.output == {"answer": "ok"}
    assert calls[1]["method"] == "tools/call"
    assert calls[1]["params"]["name"] == "search"
    assert calls[1]["params"]["arguments"] == {"query": "agent os"}
    assert audit.last()["success"] is True


def test_mcp_tool_failure_stays_inside_executor_boundary():
    calls = []

    def transport(request):
        calls.append(request)

        if request["method"] == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {
                    "tools": [{"name": "unstable"}]
                },
            }

        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "error": {
                "code": -32000,
                "message": "service unavailable",
            },
        }

    integration = MCPIntegration(transport)
    registry = ToolRegistry()
    MCPToolRegistrar(integration, registry).register()

    audit = ToolAuditLog()
    executor = ToolExecutor(
        registry,
        PermissionPolicy(allowed_tools={"mcp:unstable"}),
        audit=audit,
    )

    result = executor.execute("mcp:unstable")

    assert result.success is False
    assert "mcp_tool_execution_failed" in result.error
    assert "service unavailable" in result.error
    assert audit.last()["success"] is False
