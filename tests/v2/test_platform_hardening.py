
import pytest

from agent_os.runtime import RecoveryController, RuntimePolicy

def test_recovery_retries_transient_failure():
    calls = {"count": 0}

    def operation():
        calls["count"] += 1
        if calls["count"] < 3:
            raise ConnectionError("temporary")
        return "ok"

    result = RecoveryController(3).run(operation)
    assert result.success is True
    assert result.attempts == 3
    assert result.output == "ok"

def test_recovery_stops_after_limit():
    result = RecoveryController(2).run(
        lambda: (_ for _ in ()).throw(ConnectionError("down"))
    )
    assert result.success is False
    assert result.attempts == 2

def test_runtime_policy():
    policy = RuntimePolicy(max_output_length=10)
    policy.validate_output("hello")
    with pytest.raises(ValueError):
        policy.validate_output("this is too long")

def test_runtime_policy_rejects_invalid_limit():
    with pytest.raises(ValueError):
        RuntimePolicy(max_output_length=0)
