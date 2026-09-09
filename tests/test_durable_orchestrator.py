from agent_os.core.orchestrator import (
    Orchestrator,
    State,
    Task,
)
from agent_os.memory import MemoryStore
from agent_os.observability import RunRepository


def test_orchestrator_persists_lifecycle_events():
    memory = MemoryStore(":memory:")
    repository = RunRepository(memory.conn)

    orchestrator = Orchestrator(
        memory=memory,
        run_repository=repository,
    )

    task = Task(
        id="durable-001",
        objective="Test durable execution",
    )

    run = orchestrator.run(task)

    persisted = repository.list_events(task.id)

    assert run.state == State.COMPLETE
    assert len(persisted) == len(orchestrator.ORDER)

    assert [
        event["state"]
        for event in persisted
    ] == [
        state.value
        for state in orchestrator.ORDER
    ]

    assert persisted[0]["task_id"] == task.id
    assert persisted[-1]["state"] == "complete"
