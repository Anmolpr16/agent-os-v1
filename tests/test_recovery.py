import pytest

from agent_os.core import RetryPolicy
from agent_os.core.state import State


def test_retry_policy_is_bounded():
    policy = RetryPolicy(max_attempts=3)

    assert policy.allows(1)
    assert policy.allows(2)
    assert policy.allows(3)
    assert not policy.allows(4)
    assert not policy.allows(0)


def test_retry_policy_rejects_invalid_limit():
    with pytest.raises(
        ValueError,
        match="max_attempts_must_be_positive",
    ):
        RetryPolicy(max_attempts=0)


def test_failed_state_exists():
    assert State.FAILED.value == "failed"


def test_retry_recovers_after_transient_failures():
    from agent_os.core.recovery import retry

    attempts = []

    def operation():
        attempts.append(len(attempts) + 1)

        if len(attempts) < 3:
            raise RuntimeError("transient")

        return "success"

    result = retry(
        operation,
        RetryPolicy(max_attempts=3),
    )

    assert result == "success"
    assert attempts == [1, 2, 3]


def test_retry_raises_after_budget_exhaustion():
    from agent_os.core.recovery import retry

    attempts = []

    def operation():
        attempts.append(len(attempts) + 1)
        raise RuntimeError("persistent")

    try:
        retry(
            operation,
            RetryPolicy(max_attempts=3),
        )
    except RuntimeError as exc:
        assert str(exc) == "persistent"
    else:
        raise AssertionError(
            "retry should have exhausted its budget"
        )

    assert attempts == [1, 2, 3]


def test_timeout_is_recoverable():
    from agent_os.core.failures import (
        FailureKind,
        classify_error,
    )

    failure = classify_error(
        TimeoutError("temporary timeout")
    )

    assert failure.kind == FailureKind.RECOVERABLE
    assert failure.recoverable
    assert failure.code == "timeouterror"


def test_permission_error_is_terminal():
    from agent_os.core.failures import (
        FailureKind,
        classify_error,
    )

    failure = classify_error(
        PermissionError("access denied")
    )

    assert failure.kind == FailureKind.TERMINAL
    assert not failure.recoverable


def test_unknown_error_is_terminal():
    from agent_os.core.failures import (
        FailureKind,
        classify_error,
    )

    failure = classify_error(
        RuntimeError("unexpected")
    )

    assert failure.kind == FailureKind.TERMINAL
    assert not failure.recoverable
