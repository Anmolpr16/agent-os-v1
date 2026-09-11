from agent_os.integration.mcp import MCPIntegration, MCPProtocolError


def test_mcp_integration_builds_json_rpc_request():
    calls = []

    def transport(request):
        calls.append(request)
        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {"ok": True},
        }

    integration = MCPIntegration(transport)

    response = integration.execute(
        __import__("agent_os.integration.contracts", fromlist=["IntegrationRequest"])
        .IntegrationRequest(
            operation="tools/list",
            payload={"cursor": None},
        )
    )

    assert response.success
    assert response.output == {"ok": True}
    assert calls[0]["jsonrpc"] == "2.0"
    assert calls[0]["id"] == 1
    assert calls[0]["method"] == "tools/list"
    assert calls[0]["params"] == {"cursor": None}


def test_mcp_integration_accepts_json_string_response():
    integration = MCPIntegration(
        lambda request: '{"jsonrpc":"2.0","id":1,"result":{"value":42}}'
    )

    response = integration.list_tools()

    assert response.success
    assert response.output == {"value": 42}


def test_mcp_remote_error_becomes_failed_response():
    integration = MCPIntegration(
        lambda request: {
            "jsonrpc": "2.0",
            "id": request["id"],
            "error": {"code": -32601, "message": "method not found"},
        }
    )

    response = integration.execute(
        __import__("agent_os.integration.contracts", fromlist=["IntegrationRequest"])
        .IntegrationRequest(
            operation="missing",
            payload={},
        )
    )

    assert not response.success
    assert "remote_error:method not found" in response.error


def test_mcp_rejects_malformed_response():
    integration = MCPIntegration(lambda request: {"unexpected": True})

    response = integration.list_tools()

    assert not response.success
    assert "invalid_jsonrpc_version" in response.error


def test_mcp_call_tool_uses_structured_arguments():
    calls = []

    def transport(request):
        calls.append(request)
        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {"content": [{"type": "text", "text": "ok"}]},
        }

    integration = MCPIntegration(transport)

    response = integration.call_tool(
        "search",
        {"query": "agent os"},
    )

    assert response.success
    assert calls[0]["method"] == "tools/call"
    assert calls[0]["params"] == {
        "name": "search",
        "arguments": {"query": "agent os"},
    }


def test_mcp_request_ids_increment():
    calls = []

    def transport(request):
        calls.append(request["id"])
        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {},
        }

    integration = MCPIntegration(transport)

    integration.list_tools()
    integration.list_tools()

    assert calls == [1, 2]
