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


def test_orchestrator_fails_on_tool_failure():
    from agent_os.agents import Agent
    from agent_os.providers import MockProvider
    from agent_os.tools import (
        PermissionPolicy,
        ToolExecutor,
        ToolRegistry,
    )

    memory = MemoryStore(":memory:")
    repository = RunRepository(memory.conn)

    registry = ToolRegistry()
    registry.register(
        name="restricted",
        description="Restricted operation.",
        handler=lambda: "should not run",
    )

    executor = ToolExecutor(
        registry,
        PermissionPolicy(allowed_tools=set()),
    )

    agent = Agent(
        MockProvider(response="done"),
        executor,
    )

    orchestrator = Orchestrator(
        memory=memory,
        agent=agent,
        run_repository=repository,
    )

    task = Task(
        id="failure-001",
        objective="Use restricted tool",
        metadata={
            "tool_calls": [
                {
                    "name": "restricted",
                    "arguments": {},
                }
            ]
        },
    )

    run = orchestrator.run(task)

    assert run.state == State.FAILED
    assert run.error == (
        "tool_execution_failed:restricted"
    )

    assert "finalization" not in [
        event["state"]
        for event in run.events
    ]

    persisted = repository.list_events(task.id)

    assert persisted[-1]["state"] == "failed"
    assert persisted[-1]["event"]["error"] == run.error


def test_orchestrator_persists_selected_skill():
    from agent_os.agents import Agent
    from agent_os.core.orchestrator import Orchestrator, Task
    from agent_os.observability import RunRepository
    from agent_os.providers import MockProvider
    from agent_os.skill_runtime import Skill, SkillRegistry

    memory = MemoryStore(":memory:")
    repository = RunRepository(memory.conn)

    registry = SkillRegistry()
    registry.register(
        Skill(
            name="research",
            version="1.0.0",
            objective="research evidence verification",
            inputs=["research question"],
            procedure=["Gather evidence.", "Verify evidence."],
        )
    )

    orchestrator = Orchestrator(
        memory=memory,
        agent=Agent(
            MockProvider(response="task completed")
        ),
        run_repository=repository,
        skill_registry=registry,
    )

    task_id = "durable-skill-001"

    orchestrator.run(
        Task(
            id=task_id,
            objective="research evidence verification",
        )
    )

    events = repository.list_events(task_id)

    planning_event = next(
        event
        for event in events
        if event["state"] == "planning"
    )

    assert planning_event["event"]["plan"]["skill"] == "research"
    assert planning_event["event"]["plan"]["skill_score"] > 0.0

    memory.close()
