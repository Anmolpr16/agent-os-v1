from agent_os.core.orchestrator import (
    Orchestrator,
    Task,
)
from agent_os.memory import MemoryStore
from agent_os.providers import MockProvider
from agent_os.agents import Agent


def test_end_to_end_agent_os_runtime():
    memory = MemoryStore(":memory:")

    agent = Agent(
        MockProvider(
            response="verified task result",
        )
    )

    orchestrator = Orchestrator(
        memory=memory,
        agent=agent,
    )

    run = orchestrator.run(
        Task(
            id="e2e-001",
            objective="Build a verified workflow",
        )
    )

    assert run.state.value == "complete"

    assert run.output == "verified task result"

    assert run.prediction_error == 0.0

    assert run.evaluation_score == 1.0

    assert run.reflection is not None

    assert len(run.events) == 8

    memory_results = memory.search(
        "verified task result"
    )

    assert len(memory_results) == 1
    assert memory_results[0]["kind"] == "episodic"

    memory.close()


def test_memory_retrieval_is_used():
    memory = MemoryStore(":memory:")

    memory.add_memory(
        "previous research workflow",
        kind="episodic",
    )

    orchestrator = Orchestrator(
        memory=memory,
    )

    run = orchestrator.run(
        Task(
            id="memory-001",
            objective="previous research workflow",
        )
    )

    retrieval_event = next(
        event
        for event in run.events
        if event["state"] == "memory_retrieval"
    )

    assert retrieval_event["memory"]["matches"] >= 1

    memory.close()
