import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


class ApiHandler(BaseHTTPRequestHandler):
    """Minimal JSON API boundary for Agent OS."""

    orchestrator: Any = None
    orchestrator_factory: Any = None
    max_request_body_bytes: int = 1_048_576

    def _send_json(
        self,
        status: int,
        payload: dict[str, Any],
    ) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            raise ValueError("request_body_required")

        try:
            length = int(raw_length)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid_content_length") from exc

        if length <= 0:
            raise ValueError("request_body_required")

        if length > self.max_request_body_bytes:
            raise ValueError("request_body_too_large")

        raw = self.rfile.read(length)
        if len(raw) != length:
            raise ValueError("incomplete_request_body")

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("invalid_json") from exc

        if not isinstance(payload, dict):
            raise ValueError("request_object_required")

        return payload

    def do_GET(self) -> None:
        self._send_json(
            404,
            {"error": "not_found"},
        )

    def do_POST(self) -> None:
        if self.path != "/runs":
            self._send_json(
                404,
                {"error": "not_found"},
            )
            return

        try:
            payload = self._read_json()
        except ValueError as exc:
            self._send_json(
                400,
                {"error": str(exc)},
            )
            return

        objective = payload.get("objective")

        if not isinstance(objective, str) or not objective.strip():
            self._send_json(
                400,
                {"error": "objective_required"},
            )
            return

        if self.orchestrator is None and self.orchestrator_factory is None:
            self._send_json(
                503,
                {"error": "orchestrator_unavailable"},
            )
            return

        try:
            from agent_os.core.orchestrator import Task

            orchestrator = (
                self.orchestrator_factory()
                if self.orchestrator_factory is not None
                else self.orchestrator
            )

            task = Task(
                id=payload.get("task_id", ""),
                objective=objective,
                metadata=payload.get("metadata", {}),
            )

            if not task.id:
                self._send_json(
                    400,
                    {"error": "task_id_required"},
                )
                return

            if not isinstance(task.metadata, dict):
                self._send_json(
                    400,
                    {"error": "metadata_object_required"},
                )
                return

            result = orchestrator.run(task)
        except Exception:
            self._send_json(
                500,
                {"error": "run_failed"},
            )
            return

        self._send_json(
            200,
            {
                "task_id": result.task_id,
                "state": result.state.value,
                "output": result.output,
                "evaluation_score": result.evaluation_score,
                "error": result.error,
            },
        )

    def log_message(self, format: str, *args: Any) -> None:
        pass


def create_server(
    host: str = "127.0.0.1",
    port: int = 0,
    orchestrator_factory: Any = None,
    max_request_body_bytes: int = 1_048_576,
) -> ThreadingHTTPServer:
    if max_request_body_bytes <= 0:
        raise ValueError("max_request_body_bytes must be positive")

    ApiHandler.orchestrator_factory = orchestrator_factory
    ApiHandler.max_request_body_bytes = max_request_body_bytes

    return ThreadingHTTPServer(
        (host, port),
        ApiHandler,
    )
