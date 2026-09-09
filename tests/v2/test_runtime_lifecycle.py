from agent_os.runtime.lifecycle import RuntimeLifecycle, check_runtime
from agent_os.runtime.system import AgentOSRuntime


def test_lifecycle_records_events():
    lifecycle = RuntimeLifecycle()
    event = lifecycle.emit("started", "task-1", {"x": 1})

    assert event.name == "started"
    assert event.task_id == "task-1"
    assert event.metadata["x"] == 1
    assert lifecycle.latest("task-1") == event


def test_lifecycle_rejects_invalid_values():
    lifecycle = RuntimeLifecycle()

    try:
        lifecycle.emit("", "task-1")
        assert False
    except ValueError as exc:
        assert str(exc) == "lifecycle_event_required"

    try:
        lifecycle.emit("started", "")
        assert False
    except ValueError as exc:
        assert str(exc) == "task_id_required"


def test_runtime_health_is_healthy():
    runtime = AgentOSRuntime()
    health = check_runtime(runtime)

    assert health.healthy
    assert health.status == "ok"
    assert all(value == "ok" for value in health.checks.values())
    assert runtime.health().healthy


def test_runtime_lifecycle_is_shared_with_closed_loop():
    runtime = AgentOSRuntime()
    assert runtime.lifecycle.events() == []
