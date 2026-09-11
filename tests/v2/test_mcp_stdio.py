import sys

from agent_os.integration.contracts import IntegrationRequest
from agent_os.integration.mcp import MCPIntegration
from agent_os.integration.stdio import MCPStdioConfig, MCPStdioTransport


SERVER = r"""
import json
import sys

for line in sys.stdin:
    request = json.loads(line)
    response = {
        "jsonrpc": "2.0",
        "id": request["id"],
        "result": {
            "method": request["method"],
            "params": request["params"],
        },
    }
    print(json.dumps(response), flush=True)
"""


def make_transport(timeout=2.0):
    return MCPStdioTransport(
        MCPStdioConfig(
            command=(sys.executable, "-u", "-c", SERVER),
            timeout=timeout,
        )
    )


def test_stdio_transport_executes_json_rpc_request():
    transport = make_transport()
    integration = MCPIntegration(transport)

    try:
        response = integration.execute(
            IntegrationRequest(
                operation="tools/list",
                payload={"cursor": None},
            )
        )

        assert response.success
        assert response.output == {
            "method": "tools/list",
            "params": {"cursor": None},
        }
        assert transport.running
    finally:
        transport.close()

    assert not transport.running


def test_stdio_transport_reuses_server_process():
    transport = make_transport()
    integration = MCPIntegration(transport)

    try:
        first = integration.list_tools()
        second = integration.call_tool("echo", {"value": "ok"})

        assert first.success
        assert second.success
        assert first.output["method"] == "tools/list"
        assert second.output["method"] == "tools/call"
        assert second.output["params"]["name"] == "echo"
    finally:
        transport.close()


def test_stdio_transport_rejects_invalid_timeout():
    try:
        MCPStdioConfig(
            command=(sys.executable,),
            timeout=0,
        )
    except ValueError as exc:
        assert str(exc) == "stdio_timeout_invalid"
    else:
        raise AssertionError("expected ValueError")


def test_stdio_transport_rejects_empty_command():
    try:
        MCPStdioConfig(command=())
    except ValueError as exc:
        assert str(exc) == "stdio_command_missing"
    else:
        raise AssertionError("expected ValueError")


def test_stdio_transport_can_be_used_as_context_manager():
    transport = make_transport()

    with transport:
        assert transport.running

    assert not transport.running
