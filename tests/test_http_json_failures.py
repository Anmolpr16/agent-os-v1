from agent_os.core.failures import FailureKind, classify_error
from agent_os.providers import HttpJsonProvider


def test_connection_error_is_recoverable():
    failure = classify_error(
        ConnectionError("provider_unreachable")
    )

    assert failure.kind == FailureKind.RECOVERABLE
    assert failure.recoverable is True
    assert failure.code == "connectionerror"


def test_invalid_provider_configuration_is_terminal():
    try:
        HttpJsonProvider(
            endpoint="http://127.0.0.1",
            api_key="",
            model="test-model",
        )
    except ValueError as exc:
        failure = classify_error(exc)
    else:
        raise AssertionError("expected ValueError")

    assert failure.kind == FailureKind.TERMINAL
    assert failure.recoverable is False
    assert failure.code == "valueerror"
