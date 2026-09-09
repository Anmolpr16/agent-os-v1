from .contracts import IntegrationRequest, IntegrationResponse


class MockIntegration:
    """Deterministic integration for testing orchestration boundaries."""

    def __init__(self, responses: dict[str, object] | None = None):
        self.responses = dict(responses or {})
        self.calls: list[IntegrationRequest] = []

    def execute(
        self,
        request: IntegrationRequest,
    ) -> IntegrationResponse:
        self.calls.append(request)

        if request.operation not in self.responses:
            return IntegrationResponse(
                success=False,
                error="integration_operation_not_found",
            )

        return IntegrationResponse(
            success=True,
            output=self.responses[request.operation],
        )
