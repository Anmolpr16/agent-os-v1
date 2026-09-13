import sqlite3

from agent_os.observability import (
    EventLogger,
    RunRepository,
    span,
)


def test_run_repository():
    connection = sqlite3.connect(":memory:")
    repository = RunRepository(connection)

    event_id = repository.record(
        task_id="run-001",
        state="execution",
        event={
            "output": "completed",
            "verified": True,
        },
    )

    assert event_id == 1

    events = repository.list_events(
        "run-001"
    )

    assert len(events) == 1
    assert events[0]["task_id"] == "run-001"
    assert events[0]["state"] == "execution"
    assert events[0]["event"]["verified"] is True
    connection.close()


def test_event_logger():
    logger = EventLogger()

    event = logger.log(
        "tool_execution",
        "run-002",
        tool="echo",
        success=True,
    )

    assert event["type"] == "tool_execution"
    assert event["task_id"] == "run-002"
    assert event["data"]["tool"] == "echo"
    assert event["data"]["success"] is True
    assert len(logger.entries) == 1


def test_trace_span():
    with span("operation") as result:
        value = 2 + 3

    assert value == 5
    assert "duration_ms" in result
    assert result["duration_ms"] >= 0.0
