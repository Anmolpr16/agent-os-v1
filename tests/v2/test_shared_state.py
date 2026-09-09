from agent_os.runtime import AgentMessage, MessageBus, SharedState


def test_shared_state_round_trip():
    state = SharedState()

    state.set("answer", 42)

    assert state.get("answer") == 42
    assert state.snapshot() == {"answer": 42}


def test_shared_state_update_is_atomic_at_api_boundary():
    state = SharedState()

    state.update(
        {
            "status": "running",
            "count": 2,
        }
    )

    assert state.snapshot() == {
        "status": "running",
        "count": 2,
    }


def test_shared_state_rejects_empty_key():
    state = SharedState()

    try:
        state.set("", "value")
    except ValueError as exc:
        assert str(exc) == "state_key_required"
    else:
        raise AssertionError("expected ValueError")


def test_message_bus_sends_and_receives():
    bus = MessageBus()

    message = AgentMessage(
        sender="researcher",
        recipient="writer",
        task_id="task-1",
        content="research complete",
    )

    bus.send(message)

    assert bus.receive("writer") == [message]
    assert bus.receive("writer", "task-1") == [message]
    assert bus.receive("other") == []


def test_message_bus_preserves_message_order():
    bus = MessageBus()

    first = AgentMessage(
        sender="a",
        recipient="b",
        task_id="task-1",
        content="first",
    )
    second = AgentMessage(
        sender="a",
        recipient="b",
        task_id="task-1",
        content="second",
    )

    bus.send(first)
    bus.send(second)

    assert bus.receive("b") == [first, second]


def test_message_bus_rejects_invalid_message():
    bus = MessageBus()

    try:
        bus.send(
            AgentMessage(
                sender="",
                recipient="b",
                task_id="task-1",
                content="message",
            )
        )
    except ValueError as exc:
        assert str(exc) == "sender_required"
    else:
        raise AssertionError("expected ValueError")


def test_execution_limits_validate_configuration():
    from agent_os.runtime import ExecutionLimits

    limits = ExecutionLimits(
        max_tasks=10,
        max_workers=4,
    )

    assert limits.max_tasks == 10
    assert limits.max_workers == 4


def test_execution_limits_reject_invalid_values():
    from agent_os.runtime import ExecutionLimits

    for kwargs in (
        {"max_tasks": 0},
        {"max_workers": 0},
        {"max_tasks": 2, "max_workers": 3},
    ):
        try:
            ExecutionLimits(**kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError")
