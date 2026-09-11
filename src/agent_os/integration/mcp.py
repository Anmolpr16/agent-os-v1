from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

from .contracts import IntegrationRequest, IntegrationResponse


@dataclass(frozen=True)
class MCPMessage:
    """Minimal JSON-RPC message used at the external integration boundary."""

    method: str
    params: dict[str, Any]
    request_id: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": self.method,
            "params": self.params,
        }


class MCPProtocolError(RuntimeError):
    """Raised when an external JSON-RPC response is malformed or unsuccessful."""


class MCPIntegration:
    """
    Provider-neutral JSON-RPC integration boundary.

    The transport is injected so the Agent OS core remains independent of
    sockets, subprocesses, HTTP clients, or any particular MCP server.
    """

    def __init__(
        self,
        transport: Callable[[dict[str, Any]], dict[str, Any] | str],
        *,
        request_id_start: int = 1,
    ):
        if not callable(transport):
            raise TypeError("transport_must_be_callable")
        if request_id_start < 1:
            raise ValueError("request_id_start_invalid")

        self.transport = transport
        self._next_request_id = request_id_start

    def _request(self, method: str, params: dict[str, Any]) -> Any:
        if not method.strip():
            raise ValueError("method_missing")

        request = MCPMessage(
            method=method,
            params=params,
            request_id=self._next_request_id,
        )
        self._next_request_id += 1

        raw_response = self.transport(request.to_dict())

        if isinstance(raw_response, str):
            try:
                response = json.loads(raw_response)
            except json.JSONDecodeError as exc:
                raise MCPProtocolError("invalid_json_response") from exc
        elif isinstance(raw_response, dict):
            response = raw_response
        else:
            raise MCPProtocolError("invalid_response_type")

        if response.get("jsonrpc") != "2.0":
            raise MCPProtocolError("invalid_jsonrpc_version")

        if "error" in response:
            error = response["error"]
            if isinstance(error, dict):
                message = error.get("message", "unknown_error")
            else:
                message = str(error)
            raise MCPProtocolError(f"remote_error:{message}")

        if "result" not in response:
            raise MCPProtocolError("missing_result")

        return response["result"]

    def execute(self, request: IntegrationRequest) -> IntegrationResponse:
        """
        Execute an integration operation through the JSON-RPC boundary.

        The operation name is mapped directly to the JSON-RPC method. Payload
        remains structured and is never flattened into command-line text.
        """
        try:
            output = self._request(
                request.operation,
                request.payload,
            )
            return IntegrationResponse(
                success=True,
                output=output,
            )
        except Exception as exc:
            return IntegrationResponse(
                success=False,
                error=f"{type(exc).__name__}: {exc}",
            )

    def initialize(self, params: dict[str, Any] | None = None) -> IntegrationResponse:
        return self.execute(
            IntegrationRequest(
                operation="initialize",
                payload=dict(params or {}),
            )
        )

    def list_tools(self) -> IntegrationResponse:
        return self.execute(
            IntegrationRequest(
                operation="tools/list",
                payload={},
            )
        )

    def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> IntegrationResponse:
        if not name.strip():
            raise ValueError("tool_name_missing")

        return self.execute(
            IntegrationRequest(
                operation="tools/call",
                payload={
                    "name": name,
                    "arguments": dict(arguments or {}),
                },
            )
        )
