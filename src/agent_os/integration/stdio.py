from __future__ import annotations

import json
import subprocess
import threading
from dataclasses import dataclass
from typing import Any


class MCPStdioError(RuntimeError):
    """Raised when the MCP stdio transport cannot complete an operation."""


@dataclass(frozen=True)
class MCPStdioConfig:
    """Configuration for a local MCP-style JSON-RPC server."""

    command: tuple[str, ...]
    timeout: float = 30.0
    cwd: str | None = None
    env: dict[str, str] | None = None

    def __post_init__(self) -> None:
        if not self.command or not self.command[0].strip():
            raise ValueError("stdio_command_missing")
        if self.timeout <= 0:
            raise ValueError("stdio_timeout_invalid")


class MCPStdioTransport:
    """
    Line-oriented JSON-RPC transport for a local MCP-style server.

    Commands are passed directly to subprocess.Popen(shell=False). The
    transport therefore does not interpret command strings as shell input.
    """

    def __init__(self, config: MCPStdioConfig):
        self.config = config
        self._process: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()

    @property
    def running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def start(self) -> None:
        with self._lock:
            if self.running:
                return

            try:
                self._process = subprocess.Popen(
                    list(self.config.command),
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    bufsize=1,
                    cwd=self.config.cwd,
                    env=self.config.env,
                    shell=False,
                )
            except OSError as exc:
                self._process = None
                raise MCPStdioError(
                    f"stdio_start_failed:{type(exc).__name__}:{exc}"
                ) from exc

    def _require_process(self) -> subprocess.Popen[str]:
        if not self.running:
            raise MCPStdioError("stdio_process_not_running")

        assert self._process is not None
        return self._process

    def send(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Send one JSON-RPC request and synchronously receive one response.

        The response read is performed in a worker thread so a server that
        stops responding cannot block the Agent OS indefinitely.
        """
        with self._lock:
            process = self._require_process()

            if process.stdin is None or process.stdout is None:
                raise MCPStdioError("stdio_pipes_unavailable")

            payload = json.dumps(
                request,
                separators=(",", ":"),
                ensure_ascii=False,
            )

            try:
                process.stdin.write(payload + "\n")
                process.stdin.flush()
            except (BrokenPipeError, OSError) as exc:
                raise MCPStdioError(
                    f"stdio_write_failed:{type(exc).__name__}:{exc}"
                ) from exc

            response_holder: list[str] = []
            error_holder: list[BaseException] = []

            def read_response() -> None:
                try:
                    line = process.stdout.readline()
                    if not line:
                        raise MCPStdioError("stdio_server_closed")
                    response_holder.append(line.rstrip("\r\n"))
                except BaseException as exc:
                    error_holder.append(exc)

            reader = threading.Thread(
                target=read_response,
                name="agent-os-mcp-stdio-reader",
                daemon=True,
            )
            reader.start()
            reader.join(self.config.timeout)

            if reader.is_alive():
                raise MCPStdioError("stdio_response_timeout")

            if error_holder:
                exc = error_holder[0]
                if isinstance(exc, MCPStdioError):
                    raise exc
                raise MCPStdioError(
                    f"stdio_read_failed:{type(exc).__name__}:{exc}"
                ) from exc

            raw = response_holder[0]

            try:
                response = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise MCPStdioError("stdio_invalid_json_response") from exc

            if not isinstance(response, dict):
                raise MCPStdioError("stdio_response_not_object")

            return response

    def __call__(self, request: dict[str, Any]) -> dict[str, Any]:
        if not self.running:
            self.start()
        return self.send(request)

    def close(self) -> None:
        with self._lock:
            process = self._process
            self._process = None

            if process is None:
                return

            if process.stdin is not None:
                try:
                    process.stdin.close()
                except OSError:
                    pass

            try:
                process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

            for stream in (process.stdout, process.stderr):
                if stream is not None:
                    try:
                        stream.close()
                    except OSError:
                        pass

    def __enter__(self) -> "MCPStdioTransport":
        self.start()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()
