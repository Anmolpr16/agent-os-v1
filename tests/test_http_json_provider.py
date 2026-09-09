import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from agent_os.providers import (
    HttpJsonProvider,
    ProviderRequest,
)


class Handler(BaseHTTPRequestHandler):
    response_body = {"text": "model response"}
    status = 200
    received_authorization = None

    def do_POST(self):
        type(self).received_authorization = self.headers.get(
            "Authorization"
        )

        length = int(self.headers["Content-Length"])
        body = json.loads(self.rfile.read(length))

        assert body["model"] == "test-model"
        assert body["prompt"] == "hello"

        payload = json.dumps(
            type(self).response_body
        ).encode("utf-8")

        self.send_response(type(self).status)
        self.send_header(
            "Content-Type",
            "application/json",
        )
        self.send_header(
            "Content-Length",
            str(len(payload)),
        )
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        pass


def server_url():
    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )
    thread.start()
    return server, f"http://127.0.0.1:{server.server_port}"


def test_http_json_provider_success():
    server, endpoint = server_url()

    try:
        provider = HttpJsonProvider(
            endpoint=endpoint,
            api_key="test-secret",
            model="test-model",
        )

        result = provider.generate(
            ProviderRequest(prompt="hello")
        )

        assert result.text == "model response"
        assert result.provider == "http-json"
        assert result.model == "test-model"
        assert result.metadata == {"status": "success"}
        assert Handler.received_authorization == (
            "Bearer test-secret"
        )
    finally:
        server.shutdown()
        server.server_close()


def test_http_json_provider_rejects_invalid_configuration():
    with pytest.raises(ValueError, match="endpoint"):
        HttpJsonProvider(
            endpoint="",
            api_key="key",
            model="model",
        )

    with pytest.raises(ValueError, match="api_key"):
        HttpJsonProvider(
            endpoint="http://127.0.0.1",
            api_key="",
            model="model",
        )

    with pytest.raises(ValueError, match="model"):
        HttpJsonProvider(
            endpoint="http://127.0.0.1",
            api_key="key",
            model="",
        )

    with pytest.raises(ValueError, match="timeout"):
        HttpJsonProvider(
            endpoint="http://127.0.0.1",
            api_key="key",
            model="model",
            timeout=0,
        )


def test_http_json_provider_rejects_invalid_json():
    class InvalidJsonHandler(Handler):
        response_body = None

        def do_POST(self):
            payload = b"not-json"

            self.send_response(200)
            self.send_header(
                "Content-Type",
                "application/json",
            )
            self.send_header(
                "Content-Length",
                str(len(payload)),
            )
            self.end_headers()
            self.wfile.write(payload)

    server = HTTPServer(
        ("127.0.0.1", 0),
        InvalidJsonHandler,
    )
    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )
    thread.start()

    try:
        provider = HttpJsonProvider(
            endpoint=(
                f"http://127.0.0.1:{server.server_port}"
            ),
            api_key="test-secret",
            model="test-model",
        )

        with pytest.raises(
            ValueError,
            match="provider_invalid_json",
        ):
            provider.generate(
                ProviderRequest(prompt="hello")
            )
    finally:
        server.shutdown()
        server.server_close()


def test_http_json_provider_rejects_missing_text():
    class MissingTextHandler(Handler):
        response_body = {"result": "wrong field"}

    server = HTTPServer(
        ("127.0.0.1", 0),
        MissingTextHandler,
    )
    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )
    thread.start()

    try:
        provider = HttpJsonProvider(
            endpoint=(
                f"http://127.0.0.1:{server.server_port}"
            ),
            api_key="test-secret",
            model="test-model",
        )

        with pytest.raises(
            ValueError,
            match="provider_missing_text",
        ):
            provider.generate(
                ProviderRequest(prompt="hello")
            )
    finally:
        server.shutdown()
        server.server_close()


def test_http_json_provider_maps_http_failure():
    class FailureHandler(Handler):
        status = 503
        response_body = {"error": "unavailable"}

    server = HTTPServer(
        ("127.0.0.1", 0),
        FailureHandler,
    )
    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )
    thread.start()

    try:
        provider = HttpJsonProvider(
            endpoint=(
                f"http://127.0.0.1:{server.server_port}"
            ),
            api_key="test-secret",
            model="test-model",
        )

        with pytest.raises(
            ConnectionError,
            match="http_status:503",
        ):
            provider.generate(
                ProviderRequest(prompt="hello")
            )
    finally:
        server.shutdown()
        server.server_close()
