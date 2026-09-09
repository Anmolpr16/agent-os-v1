from .base import Provider, ProviderRequest, ProviderResponse


class MockProvider(Provider):
    """Deterministic provider used for tests and local development."""

    def __init__(
        self,
        response: str = "mock response",
        model: str = "mock-v1",
    ):
        self.response = response
        self.model = model

    def generate(
        self,
        request: ProviderRequest,
    ) -> ProviderResponse:
        return ProviderResponse(
            text=self.response,
            provider="mock",
            model=self.model,
            metadata={
                "prompt_length": len(request.prompt),
            },
        )
