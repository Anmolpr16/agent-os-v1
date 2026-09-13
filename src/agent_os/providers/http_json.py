import json
from dataclasses import dataclass
from urllib import error, request

from .base import Provider, ProviderRequest, ProviderResponse


@dataclass(frozen=True)
class HttpJsonProvider(Provider):
    """Vendor-neutral provider for simple JSON HTTP model APIs."""

    endpoint: str
    api_key: str
    model: str
    provider: str = "http-json"
    timeout: float = 30.0

    def __post_init__(self) -> None:
        if not self.endpoint.strip():
            raise ValueError("endpoint must not be empty")
        if not self.api_key.strip():
            raise ValueError("api_key must not be empty")
        if not self.model.strip():
            raise ValueError("model must not be empty")
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")

    def generate(
        self,
        request_data: ProviderRequest,
    ) -> ProviderResponse:
        payload = json.dumps(
            {
                "model": self.model,
                "prompt": request_data.prompt,
            }
        ).encode("utf-8")

        http_request = request.Request(
            self.endpoint,
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )

        try:
            with request.urlopen(
                http_request,
                timeout=self.timeout,
            ) as response:
                raw = response.read()
        except error.HTTPError as exc:
            try:
                exc.close()
            finally:
                raise ConnectionError(
                    f"http_status:{exc.code}"
                ) from exc
        except error.URLError as exc:
            raise ConnectionError(
                f"provider_unreachable:{exc.reason}"
            ) from exc
        except TimeoutError:
            raise

        try:
            body = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("provider_invalid_json") from exc

        text = body.get("text")

        if not isinstance(text, str) or not text:
            raise ValueError("provider_missing_text")

        return ProviderResponse(
            text=text,
            provider=self.provider,
            model=self.model,
            metadata={
                "status": "success",
            },
        )
