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


def test_response_cannot_contain_result_and_error():
    def transport(request):
        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {},
            "error": {"code": -1, "message": "also failed"},
        }

    integration = MCPIntegration(transport)
    response = integration.list_tools()

    assert response.success is False
    assert "result_error_conflict" in response.error


def test_remote_error_requires_structured_code_and_message():
    def transport(request):
        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "error": {"message": "bad"},
        }

    integration = MCPIntegration(transport)
    response = integration.list_tools()

    assert response.success is False
    assert "remote_error_invalid" in response.error


def test_remote_error_rejects_non_string_message():
    def transport(request):
        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "error": {"code": -32600, "message": 123},
        }

    integration = MCPIntegration(transport)
    response = integration.list_tools()

    assert response.success is False
    assert "remote_error_invalid" in response.error


def test_remote_error_rejects_non_integer_code():
    def transport(request):
        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "error": {"code": "bad", "message": "invalid"},
        }

    integration = MCPIntegration(transport)
    response = integration.list_tools()

    assert response.success is False
    assert "remote_error_invalid" in response.error


def test_response_rejects_non_integer_request_id():
    integration = MCPIntegration(
        lambda request: {
            "jsonrpc": "2.0",
            "id": "wrong-type",
            "result": {},
        }
    )

    response = integration.list_tools()

    assert response.success is False
    assert "response_id_mismatch" in response.error


def test_response_rejects_null_result_when_result_field_missing():
    integration = MCPIntegration(
        lambda request: {
            "jsonrpc": "2.0",
            "id": request["id"],
        }
    )

    response = integration.list_tools()

    assert response.success is False
    assert "missing_result" in response.error


def test_initialize_rejects_non_string_protocol_version():
    def transport(request):
        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {
                "protocolVersion": 2025,
                "serverInfo": {},
                "capabilities": {},
            },
        }

    integration = MCPIntegration(transport)
    response = integration.initialize()

    assert response.success is False
    assert "initialize_protocol_version_missing" in response.error
    assert integration.initialized is False


def test_initialize_rejects_non_object_server_capabilities():
    def transport(request):
        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {
                "protocolVersion": "2025-06-18",
                "serverInfo": {},
                "capabilities": [],
            },
        }

    integration = MCPIntegration(transport)
    response = integration.initialize()

    assert response.success is False
    assert "initialize_capabilities_invalid" in response.error
    assert integration.initialized is False

def test_initialize_rejects_empty_protocol_version():
    def transport(request):
        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {
                "protocolVersion": "   ",
                "serverInfo": {},
                "capabilities": {},
            },
        }

    integration = MCPIntegration(transport)
    response = integration.initialize()
    assert response.success is False
    assert "initialize_protocol_version_missing" in response.error
    assert integration.initialized is False


def test_initialize_rejects_non_object_server_info():
    def transport(request):
        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {
                "protocolVersion": "2025-06-18",
                "serverInfo": "invalid",
                "capabilities": {},
            },
        }

    integration = MCPIntegration(transport)
    response = integration.initialize()
    assert response.success is False
    assert "initialize_server_info_invalid" in response.error
    assert integration.initialized is False


def test_failed_reinitialization_does_not_destroy_existing_session():
    responses = [
        {
            "jsonrpc": "2.0",
            "result": {
                "protocolVersion": "2025-06-18",
                "serverInfo": {"name": "server-a"},
                "capabilities": {"tools": {}},
            },
        },
        {
            "jsonrpc": "2.0",
            "result": {
                "protocolVersion": 2025,
                "serverInfo": {},
                "capabilities": {},
            },
        },
    ]

    def transport(request):
        response = responses.pop(0)
        response["id"] = request["id"]
        return response

    integration = MCPIntegration(transport)

    first = integration.initialize()
    assert first.success is True
    assert integration.initialized is True
    assert integration.server_info == {"name": "server-a"}

    second = integration.initialize()
    assert second.success is False
    assert integration.initialized is True
    assert integration.server_info == {"name": "server-a"}
    assert integration.server_capabilities == {"tools": {}}


def test_initialize_requires_result_object():
    integration = MCPIntegration(
        lambda request: {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": [],
        }
    )

    response = integration.initialize()
    assert response.success is False
    assert "initialize_result_invalid" in response.error
    assert integration.initialized is False

def test_initialize_rejects_protocol_version_mismatch():
    def transport(request):
        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {
                "protocolVersion": "2025-11-25",
                "serverInfo": {},
                "capabilities": {},
            },
        }

    integration = MCPIntegration(transport)
    response = integration.initialize({"protocolVersion": "2025-06-18"})

    assert response.success is False
    assert "initialize_protocol_version_mismatch" in response.error
    assert integration.initialized is False


def test_initialize_accepts_matching_protocol_version():
    def transport(request):
        assert request["params"]["protocolVersion"] == "2025-06-18"
        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {
                "protocolVersion": "2025-06-18",
                "serverInfo": {"name": "test-server"},
                "capabilities": {},
            },
        }

    integration = MCPIntegration(transport)
    response = integration.initialize({"protocolVersion": "2025-06-18"})

    assert response.success is True
    assert integration.initialized is True
    assert integration.server_info == {"name": "test-server"}

def test_transport_exception_is_returned_as_failed_response():
    def transport(request):
        raise ConnectionError("connection lost")

    integration = MCPIntegration(transport)
    response = integration.list_tools()

    assert response.success is False
    assert "ConnectionError: connection lost" in response.error


def test_transport_failure_does_not_consume_successful_session_state():
    calls = []

    def transport(request):
        calls.append(request)
        if len(calls) == 1:
            return {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {
                    "protocolVersion": "2025-06-18",
                    "serverInfo": {"name": "stable-server"},
                    "capabilities": {"tools": {}},
                },
            }
        raise ConnectionError("temporary failure")

    integration = MCPIntegration(transport)

    initialized = integration.initialize(
        {"protocolVersion": "2025-06-18"}
    )
    assert initialized.success is True
    assert integration.initialized is True

    failed = integration.list_tools()
    assert failed.success is False
    assert "ConnectionError: temporary failure" in failed.error

    assert integration.initialized is True
    assert integration.server_info == {"name": "stable-server"}
    assert integration.server_capabilities == {"tools": {}}


def test_transport_failure_advances_request_id_deterministically():
    calls = []

    def transport(request):
        calls.append(request)
        if len(calls) == 1:
            raise TimeoutError("timed out")
        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {"tools": []},
        }

    integration = MCPIntegration(transport)

    first = integration.list_tools()
    second = integration.list_tools()

    assert first.success is False
    assert second.success is True
    assert [request["id"] for request in calls] == [1, 2]

def test_malformed_response_does_not_destroy_initialized_session():
    calls = []

    def transport(request):
        calls.append(request)
        if len(calls) == 1:
            return {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {
                    "protocolVersion": "2025-06-18",
                    "serverInfo": {"name": "stable-server"},
                    "capabilities": {"tools": {}},
                },
            }
        if len(calls) == 2:
            return "{not-valid-json"
        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": {"tools": []},
        }

    integration = MCPIntegration(transport)

    assert integration.initialize(
        {"protocolVersion": "2025-06-18"}
    ).success is True

    failed = integration.list_tools()
    assert failed.success is False
    assert "invalid_json_response" in failed.error

    assert integration.initialized is True
    assert integration.server_info == {"name": "stable-server"}

    recovered = integration.list_tools()
    assert recovered.success is True
    assert recovered.output == {"tools": []}


def test_protocol_corruption_does_not_reuse_previous_response():
    responses = [
        {
            "jsonrpc": "2.0",
            "id": 999,
            "result": {"stale": True},
        },
        {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {"fresh": True},
        },
    ]

    def transport(request):
        return responses.pop(0)

    integration = MCPIntegration(transport)

    first = integration.list_tools()
    second = integration.list_tools()

    assert first.success is False
    assert "response_id_mismatch" in first.error

    assert second.success is True
    assert second.output == {"fresh": True}


def test_remote_protocol_error_does_not_mark_session_uninitialized():
    calls = []

    def transport(request):
        calls.append(request)
        if len(calls) == 1:
            return {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {
                    "protocolVersion": "2025-06-18",
                    "serverInfo": {"name": "stable-server"},
                    "capabilities": {"tools": {}},
                },
            }
        return {
            "jsonrpc": "2.0",
            "id": request["id"],
            "error": {
                "code": -32601,
                "message": "Method not found",
            },
        }

    integration = MCPIntegration(transport)

    assert integration.initialize(
        {"protocolVersion": "2025-06-18"}
    ).success is True

    failed = integration.list_tools()

    assert failed.success is False
    assert "remote_error:-32601:Method not found" in failed.error
    assert integration.initialized is True
