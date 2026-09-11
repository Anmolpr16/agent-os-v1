from agent_os.integration.mcp import MCPIntegration


def test_response_id_must_match_request_id():
    def transport(request):
        return {
            "jsonrpc": "2.0",
            "id": request["id"] + 100,
            "result": {"ok": True},
        }

    integration = MCPIntegration(transport)

    response = integration.initialize(
        {"protocolVersion": "2025-06-18"}
    )

    assert response.success is False
    assert "response_id_mismatch" in response.error
    assert integration.initialized is False


def test_initialize_records_server_info_and_capabilities():
    def transport(request):
        assert request["method"] == "initialize"

        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {
                "protocolVersion": "2025-06-18",
                "serverInfo": {
                    "name": "test-server",
                    "version": "1.0",
                },
                "capabilities": {
                    "tools": {
                        "listChanged": True,
                    }
                },
            },
        }

    integration = MCPIntegration(transport)

    response = integration.initialize(
        {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {
                "name": "agent-os",
                "version": "0.1",
            },
        }
    )

    assert response.success is True
    assert integration.initialized is True
    assert integration.server_info["name"] == "test-server"
    assert integration.server_capabilities["tools"]["listChanged"] is True


def test_invalid_initialize_result_does_not_mark_initialized():
    def transport(request):
        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {
                "serverInfo": {},
                "capabilities": {},
            },
        }

    integration = MCPIntegration(transport)

    response = integration.initialize()

    assert response.success is False
    assert "initialize_protocol_version_missing" in response.error
    assert integration.initialized is False


def test_tools_require_initialization():
    calls = []

    def transport(request):
        calls.append(request)
        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {"tools": []},
        }

    integration = MCPIntegration(
        transport,
        require_initialization=True,
    )

    response = integration.list_tools()

    assert response.success is False
    assert "mcp_not_initialized" in response.error
    assert calls == []


def test_remote_error_preserves_error_code():
    def transport(request):
        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "error": {
                "code": -32601,
                "message": "Method not found",
            },
        }

    integration = MCPIntegration(transport)

    response = integration.initialize()

    assert response.success is False
    assert "remote_error:-32601:Method not found" in response.error
