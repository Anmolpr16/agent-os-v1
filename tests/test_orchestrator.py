from agent_os.core.orchestrator import Orchestrator, Task, State


def test_lifecycle():
    run = Orchestrator().run(
        Task(
            id="test-001",
            objective="Test lifecycle",
        )
    )

    assert run.state == State.COMPLETE

    assert [event["state"] for event in run.events] == [
        state.value for state in Orchestrator.ORDER
    ]
