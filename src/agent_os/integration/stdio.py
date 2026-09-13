from __future__ import annotations

import json
import os
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
    max_response_bytes: int = 1024 * 1024

    def __post_init__(self) -> None:
        if not self.command or not self.command[0].strip():
            raise ValueError("stdio_command_missing")
        if any(not isinstance(part, str) or not part for part in self.command):
            raise ValueError("stdio_command_invalid")
        if self.timeout <= 0:
            raise ValueError("stdio_timeout_invalid")
        if self.max_response_bytes <= 0:
            raise ValueError("stdio_max_response_bytes_invalid")
        if self.cwd is not None and not os.path.isdir(self.cwd):
            raise ValueError("stdio_cwd_invalid")
        if self.env is not None:
            for key, value in self.env.items():
                if not isinstance(key, str) or not key:
                    raise ValueError("stdio_env_key_invalid")
                if not isinstance(value, str):
                    raise ValueError("stdio_env_value_invalid")


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
        self._stderr_thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    def _merged_env(self) -> dict[str, str] | None:
        if self.config.env is None:
            return None
        merged = dict(os.environ)
        merged.update(self.config.env)
        return merged

    def _drain_stderr(self, process: subprocess.Popen[str]) -> None:
        stream = process.stderr
        if stream is None:
            return
        try:
            for _line in stream:
                pass
        except (OSError, ValueError):
            pass

    def start(self) -> None:
        with self._lock:
            if self.running:
                return

            try:
                process = subprocess.Popen(
                    list(self.config.command),
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    bufsize=1,
                    cwd=self.config.cwd,
                    env=self._merged_env(),
                    shell=False,
                )
            except (OSError, ValueError) as exc:
                self._process = None
                raise MCPStdioError(
                    f"stdio_start_failed:{type(exc).__name__}:{exc}"
                ) from exc

            self._process = process

            self._stderr_thread = threading.Thread(
                target=self._drain_stderr,
                args=(process,),
                name="agent-os-mcp-stdio-stderr",
                daemon=True,
            )
            self._stderr_thread.start()

    def _require_process(self) -> subprocess.Popen[str]:
        if not self.running:
            raise MCPStdioError("stdio_process_not_running")
        assert self._process is not None
        return self._process

    def _terminate_locked(self, process: subprocess.Popen[str]) -> None:
        if process.poll() is not None:
            return

        try:
            process.terminate()
            process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            try:
                process.kill()
                process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                pass

    def _invalidate_process_locked(
        self,
        process: subprocess.Popen[str],
    ) -> None:
        if self._process is process:
            self._process = None
        self._terminate_locked(process)

    def send(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Send one JSON-RPC request and synchronously receive one response.

        The response read is performed in a worker thread so a server that
        stops responding cannot block the Agent OS indefinitely. A timeout
        invalidates and terminates the affected child process so a stale
        reader cannot corrupt a future request/response pair.
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
            except (BrokenPipeError, OSError, ValueError) as exc:
                self._invalidate_process_locked(process)
                raise MCPStdioError(
                    f"stdio_write_failed:{type(exc).__name__}:{exc}"
                ) from exc

            response_holder: list[str] = []
            error_holder: list[BaseException] = []

            def read_response() -> None:
                try:
                    chunks: list[str] = []
                    total_bytes = 0
                    while True:
                        chunk = process.stdout.readline(1)
                        if not chunk:
                            if not chunks:
                                raise MCPStdioError("stdio_server_closed")
                            break

                        chunk_bytes = len(chunk.encode("utf-8"))
                        total_bytes += chunk_bytes
                        if total_bytes > self.config.max_response_bytes:
                            raise MCPStdioError("stdio_response_too_large")

                        chunks.append(chunk)
                        if chunk.endswith("\n"):
                            break

                    response_holder.append("".join(chunks).rstrip("\r\n"))
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
                self._invalidate_process_locked(process)
                raise MCPStdioError("stdio_response_timeout")

            if error_holder:
                exc = error_holder[0]
                self._invalidate_process_locked(process)
                if isinstance(exc, MCPStdioError):
                    raise exc
                raise MCPStdioError(
                    f"stdio_read_failed:{type(exc).__name__}:{exc}"
                ) from exc

            raw = response_holder[0]

            try:
                response = json.loads(raw)
            except json.JSONDecodeError as exc:
                self._invalidate_process_locked(process)
                raise MCPStdioError("stdio_invalid_json_response") from exc

            if not isinstance(response, dict):
                self._invalidate_process_locked(process)
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

            self._terminate_locked(process)

            for stream in (process.stdout, process.stderr):
                if stream is not None:
                    try:
                        stream.close()
                    except OSError:
                        pass

            stderr_thread = self._stderr_thread
            self._stderr_thread = None

            if stderr_thread is not None and stderr_thread is not threading.current_thread():
                stderr_thread.join(timeout=1.0)

    def __enter__(self) -> "MCPStdioTransport":
        self.start()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()
