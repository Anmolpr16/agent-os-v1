import json
import threading
from http.client import HTTPConnection

from agent_os.api import ApiHandler, create_server
from agent_os.core.orchestrator import Orchestrator


def start_server():
    ApiHandler.orchestrator = None
    server = create_server(
        orchestrator_factory=Orchestrator,
    )
    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )
    thread.start()
    return server


def request(server, method, path, payload=None):
    connection = HTTPConnection(
        "127.0.0.1",
        server.server_port,
        timeout=5,
    )

    body = (
        json.dumps(payload).encode("utf-8")
        if payload is not None
        else None
    )

    headers = (
        {"Content-Type": "application/json"}
        if body is not None
        else {}
    )

    connection.request(
        method,
        path,
        body=body,
        headers=headers,
    )

    response = connection.getresponse()
    raw = response.read()
    connection.close()

    return response.status, json.loads(raw.decode("utf-8"))


def test_post_run_success():
    server = start_server()

    try:
        status, body = request(
            server,
            "POST",
            "/runs",
            {
                "task_id": "api-001",
                "objective": "complete an API test",
            },
        )

        assert status == 200
        assert body["task_id"] == "api-001"
        assert body["state"] == "complete"
        assert body["output"] == "task completed"
        assert body["error"] is None
    finally:
        server.shutdown()
        server.server_close()


def test_post_run_requires_task_id():
    server = start_server()

    try:
        status, body = request(
            server,
            "POST",
            "/runs",
            {"objective": "missing identifier"},
        )

        assert status == 400
        assert body == {"error": "task_id_required"}
    finally:
        server.shutdown()
        server.server_close()


def test_post_run_requires_objective():
    server = start_server()

    try:
        status, body = request(
            server,
            "POST",
            "/runs",
            {"task_id": "api-002"},
        )

        assert status == 400
        assert body == {"error": "objective_required"}
    finally:
        server.shutdown()
        server.server_close()


def test_post_run_rejects_invalid_json():
    server = start_server()

    try:
        connection = HTTPConnection(
            "127.0.0.1",
            server.server_port,
            timeout=5,
        )

        connection.request(
            "POST",
            "/runs",
            body=b"{invalid",
            headers={"Content-Type": "application/json"},
        )

        response = connection.getresponse()
        body = json.loads(
            response.read().decode("utf-8")
        )
        connection.close()

        assert response.status == 400
        assert body == {"error": "invalid_json"}
    finally:
        server.shutdown()
        server.server_close()


def test_unknown_route_returns_not_found():
    server = start_server()

    try:
        status, body = request(
            server,
            "GET",
            "/unknown",
        )

        assert status == 404
        assert body == {"error": "not_found"}
    finally:
        server.shutdown()
        server.server_close()


def test_metadata_must_be_object():
    server = start_server()

    try:
        status, body = request(
            server,
            "POST",
            "/runs",
            {
                "task_id": "api-003",
                "objective": "metadata validation",
                "metadata": [],
            },
        )

        assert status == 400
        assert body == {
            "error": "metadata_object_required"
        }
    finally:
        server.shutdown()
        server.server_close()
