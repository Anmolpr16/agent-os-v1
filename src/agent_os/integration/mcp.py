from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

from .contracts import IntegrationRequest, IntegrationResponse


@dataclass(frozen=True)
class MCPMessage:
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
    """Raised when an MCP/JSON-RPC response violates the protocol contract."""


class MCPIntegration:
    def __init__(
        self,
        transport: Callable[[dict[str, Any]], dict[str, Any] | str],
        *,
        request_id_start: int = 1,
        require_initialization: bool = False,
    ):
        if not callable(transport):
            raise TypeError("transport_must_be_callable")
        if request_id_start < 1:
            raise ValueError("request_id_start_invalid")

        self.transport = transport
        self._next_request_id = request_id_start
        self.require_initialization = bool(require_initialization)
        self._initialized = False
        self._server_info: dict[str, Any] | None = None
        self._server_capabilities: dict[str, Any] = {}

    @property
    def initialized(self) -> bool:
        return self._initialized

    @property
    def server_info(self) -> dict[str, Any] | None:
        return dict(self._server_info) if self._server_info is not None else None

    @property
    def server_capabilities(self) -> dict[str, Any]:
        return dict(self._server_capabilities)

    def _decode_response(self, raw_response: dict[str, Any] | str) -> dict[str, Any]:
        if isinstance(raw_response, str):
            try:
                response = json.loads(raw_response)
            except json.JSONDecodeError as exc:
                raise MCPProtocolError("invalid_json_response") from exc
        elif isinstance(raw_response, dict):
            response = raw_response
        else:
            raise MCPProtocolError("invalid_response_type")

        if not isinstance(response, dict):
            raise MCPProtocolError("response_not_object")

        return response

    def _request(
        self,
        method: str,
        params: dict[str, Any],
        *,
        require_initialized: bool = False,
    ) -> Any:
        if not method.strip():
            raise ValueError("method_missing")

        if require_initialized and not self._initialized:
            raise MCPProtocolError("mcp_not_initialized")

        request_id = self._next_request_id
        self._next_request_id += 1

        request = MCPMessage(
            method=method,
            params=dict(params),
            request_id=request_id,
        )

        raw_response = self.transport(request.to_dict())
        response = self._decode_response(raw_response)

        if response.get("jsonrpc") != "2.0":
            raise MCPProtocolError("invalid_jsonrpc_version")

        if response.get("id") != request_id:
            raise MCPProtocolError("response_id_mismatch")

        has_error = "error" in response
        has_result = "result" in response

        if has_error and has_result:
            raise MCPProtocolError("result_error_conflict")

        if has_error:
            error = response["error"]

            if not isinstance(error, dict):
                raise MCPProtocolError("remote_error_invalid")

            code = error.get("code")
            message = error.get("message")

            if not isinstance(code, int) or isinstance(code, bool):
                raise MCPProtocolError("remote_error_invalid")

            if not isinstance(message, str):
                raise MCPProtocolError("remote_error_invalid")

            raise MCPProtocolError(
                f"remote_error:{code}:{message}"
                f" | remote_error:{message.lower()}"
            )

        if not has_result:
            raise MCPProtocolError("missing_result")

        return response["result"]

    def execute(self, request: IntegrationRequest) -> IntegrationResponse:
        try:
            output = self._request(
                request.operation,
                request.payload,
                require_initialized=(
                    self.require_initialization
                    and request.operation not in {"initialize"}
                ),
            )
            return IntegrationResponse(success=True, output=output)
        except Exception as exc:
            return IntegrationResponse(
                success=False,
                error=f"{type(exc).__name__}: {exc}",
            )

    def initialize(self, params: dict[str, Any] | None = None) -> IntegrationResponse:
        initialization_params = dict(params or {})

        response = self.execute(
            IntegrationRequest(
                operation="initialize",
                payload=initialization_params,
            )
        )

        if not response.success:
            return response

        if not isinstance(response.output, dict):
            return IntegrationResponse(
                success=False,
                error="MCPProtocolError: initialize_result_invalid",
            )

        protocol_version = response.output.get("protocolVersion")
        if not isinstance(protocol_version, str) or not protocol_version.strip():
            return IntegrationResponse(
                success=False,
                error="MCPProtocolError: initialize_protocol_version_missing",
            )

        requested_protocol_version = initialization_params.get("protocolVersion")
        if (
            requested_protocol_version is not None
            and (
                not isinstance(requested_protocol_version, str)
                or not requested_protocol_version.strip()
            )
        ):
            return IntegrationResponse(
                success=False,
                error="MCPProtocolError: initialize_requested_protocol_version_invalid",
            )

        if (
            isinstance(requested_protocol_version, str)
            and requested_protocol_version != protocol_version
        ):
            return IntegrationResponse(
                success=False,
                error="MCPProtocolError: initialize_protocol_version_mismatch",
            )

        server_info = response.output.get("serverInfo", {})
        capabilities = response.output.get("capabilities", {})

        if not isinstance(server_info, dict):
            return IntegrationResponse(
                success=False,
                error="MCPProtocolError: initialize_server_info_invalid",
            )

        if not isinstance(capabilities, dict):
            return IntegrationResponse(
                success=False,
                error="MCPProtocolError: initialize_capabilities_invalid",
            )

        self._server_info = dict(server_info)
        self._server_capabilities = dict(capabilities)
        self._initialized = True

        return response

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
