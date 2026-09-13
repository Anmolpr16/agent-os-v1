import sys
import time

import pytest

from agent_os.integration.stdio import MCPStdioConfig, MCPStdioError, MCPStdioTransport


def server_command(body: str):
    return (
        sys.executable,
        "-u",
        "-c",
        body,
    )


def test_transport_starts_lazily_and_reuses_process():
    body = r'''
import json
import sys

for line in sys.stdin:
    request = json.loads(line)
    print(json.dumps({
        "jsonrpc": "2.0",
        "id": request["id"],
        "result": {"ok": True},
    }), flush=True)
'''

    transport = MCPStdioTransport(
        MCPStdioConfig(command=server_command(body))
    )

    assert transport.running is False

    first = transport({"jsonrpc": "2.0", "id": 1, "method": "test", "params": {}})
    assert first["result"]["ok"] is True
    assert transport.running is True

    process = transport._process
    second = transport({"jsonrpc": "2.0", "id": 2, "method": "test", "params": {}})

    assert second["result"]["ok"] is True
    assert transport._process is process

    transport.close()
    assert transport.running is False


def test_close_is_idempotent():
    body = r'''
import json
import sys

for line in sys.stdin:
    request = json.loads(line)
    print(json.dumps({
        "jsonrpc": "2.0",
        "id": request["id"],
        "result": {},
    }), flush=True)
'''

    transport = MCPStdioTransport(
        MCPStdioConfig(command=server_command(body))
    )

    transport.start()
    assert transport.running is True

    transport.close()
    transport.close()

    assert transport.running is False
    assert transport._process is None


def test_server_crash_is_reported_and_process_reference_is_not_reused():
    body = r'''
import sys
sys.exit(7)
'''

    transport = MCPStdioTransport(
        MCPStdioConfig(
            command=server_command(body),
            timeout=1.0,
        )
    )

    transport.start()

    deadline = time.time() + 2.0
    while transport.running and time.time() < deadline:
        time.sleep(0.01)

    assert transport.running is False

    with pytest.raises(MCPStdioError, match="stdio_process_not_running"):
        transport.send({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "test",
            "params": {},
        })

    transport.close()


def test_missing_executable_is_explicit_start_failure():
    transport = MCPStdioTransport(
        MCPStdioConfig(
            command=("agent-os-command-that-does-not-exist",),
        )
    )

    with pytest.raises(MCPStdioError, match="stdio_start_failed"):
        transport.start()

    assert transport.running is False
    assert transport._process is None


def test_context_manager_closes_process():
    body = r'''
import json
import sys

for line in sys.stdin:
    request = json.loads(line)
    print(json.dumps({
        "jsonrpc": "2.0",
        "id": request["id"],
        "result": {"context": True},
    }), flush=True)
'''

    with MCPStdioTransport(
        MCPStdioConfig(command=server_command(body))
    ) as transport:
        response = transport({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "test",
            "params": {},
        })

        assert response["result"]["context"] is True
        assert transport.running is True

    assert transport.running is False
    assert transport._process is None

def test_response_timeout_invalidates_and_terminates_server():
    body = r'''
import sys
import time

for line in sys.stdin:
    time.sleep(5)
'''
    transport = MCPStdioTransport(
        MCPStdioConfig(
            command=server_command(body),
            timeout=0.1,
        )
    )

    with pytest.raises(MCPStdioError, match="stdio_response_timeout"):
        transport({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "test",
            "params": {},
        })

    assert transport.running is False
    assert transport._process is None
    transport.close()


def test_invalid_json_response_invalidates_server():
    body = r'''
import sys

for line in sys.stdin:
    print("not-json", flush=True)
'''
    transport = MCPStdioTransport(
        MCPStdioConfig(
            command=server_command(body),
            timeout=1.0,
        )
    )

    with pytest.raises(MCPStdioError, match="stdio_invalid_json_response"):
        transport({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "test",
            "params": {},
        })

    assert transport.running is False
    assert transport._process is None
    transport.close()


def test_non_object_json_response_invalidates_server():
    body = r'''
import sys
import json

for line in sys.stdin:
    print(json.dumps(["not", "an", "object"]), flush=True)
'''
    transport = MCPStdioTransport(
        MCPStdioConfig(
            command=server_command(body),
            timeout=1.0,
        )
    )

    with pytest.raises(MCPStdioError, match="stdio_response_not_object"):
        transport({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "test",
            "params": {},
        })

    assert transport.running is False
    assert transport._process is None
    transport.close()

def test_response_size_limit_rejects_oversized_response():
    body = r'''
import sys

for line in sys.stdin:
    print("x" * 200, flush=True)
'''
    transport = MCPStdioTransport(
        MCPStdioConfig(
            command=server_command(body),
            timeout=1.0,
            max_response_bytes=100,
        )
    )

    with pytest.raises(MCPStdioError, match="stdio_response_too_large"):
        transport({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "test",
            "params": {},
        })

    assert transport.running is False
    assert transport._process is None
    transport.close()


def test_response_size_limit_accepts_response_at_boundary():
    body = r'''
import sys

for line in sys.stdin:
    print('{}', flush=True)
'''
    transport = MCPStdioTransport(
        MCPStdioConfig(
            command=server_command(body),
            timeout=1.0,
            max_response_bytes=3,
        )
    )

    try:
        response = transport({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "test",
            "params": {},
        })
        assert response == {}
    finally:
        transport.close()


def test_response_size_limit_rejects_invalid_limit():
    with pytest.raises(ValueError, match="stdio_max_response_bytes_invalid"):
        MCPStdioConfig(
            command=server_command("import sys"),
            max_response_bytes=0,
        )
