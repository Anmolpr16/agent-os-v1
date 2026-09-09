from agent_os.integration.contracts import (
    IntegrationRequest,
    IntegrationResponse,
)


def test_integration_request_is_structured():
    request = IntegrationRequest(
        operation="lookup",
        payload={"key": "value"},
    )

    assert request.operation == "lookup"
    assert request.payload == {"key": "value"}


def test_integration_response_can_represent_success():
    response = IntegrationResponse(
        success=True,
        output={"result": "ok"},
    )

    assert response.success is True
    assert response.output == {"result": "ok"}
    assert response.error is None


def test_integration_response_can_represent_failure():
    response = IntegrationResponse(
        success=False,
        error="integration_unavailable",
    )

    assert response.success is False
    assert response.output is None
    assert response.error == "integration_unavailable"


def test_mock_integration_returns_configured_response():
    from agent_os.integration.mock import MockIntegration

    integration = MockIntegration(
        responses={"lookup": {"value": 42}}
    )

    response = integration.execute(
        IntegrationRequest(
            operation="lookup",
            payload={"key": "answer"},
        )
    )

    assert response.success is True
    assert response.output == {"value": 42}
    assert response.error is None
    assert len(integration.calls) == 1


def test_mock_integration_rejects_unknown_operation():
    from agent_os.integration.mock import MockIntegration

    integration = MockIntegration()

    response = integration.execute(
        IntegrationRequest(
            operation="missing",
            payload={},
        )
    )

    assert response.success is False
    assert response.error == "integration_operation_not_found"
