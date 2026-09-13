from agent_os.core.state import State
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


def test_orchestrator_passes_selected_skill_to_agent():
    from agent_os.agents import Agent, AgentContext
    from agent_os.providers import MockProvider
    from agent_os.skill_runtime import Skill, SkillRegistry
    from agent_os.core.orchestrator import Orchestrator, Task

    class CapturingProvider(MockProvider):
        def generate(self, request):
            self.metadata = request.metadata
            return super().generate(request)

    provider = CapturingProvider(response="task completed")

    registry = SkillRegistry()
    registry.register(
        Skill(
            name="research",
            version="1.0.0",
            objective="research evidence verification",
            inputs=["research question"],
            procedure=["Gather evidence.", "Verify evidence."],
            failure_conditions=["missing evidence"],
            evaluation_rubric=["evidence"],
        )
    )

    agent = Agent(provider)
    orchestrator = Orchestrator(
        agent=agent,
        skill_registry=registry,
    )

    run = orchestrator.run(
        Task(
            id="skill-agent-1",
            objective="research evidence verification",
        )
    )

    assert run.output == "task completed"
    assert provider.metadata["skill"]["name"] == "research"
    assert provider.metadata["skill"]["version"] == "1.0.0"
    assert provider.metadata["skill"]["procedure"] == [
        "Gather evidence.",
        "Verify evidence.",
    ]
    orchestrator.close()


def test_orchestrator_records_skill_procedure_runtime():
    from agent_os.core.orchestrator import Orchestrator, Task
    from agent_os.skill_runtime import Skill, SkillRegistry

    registry = SkillRegistry()
    registry.register(
        Skill(
            name="research",
            version="1.0.0",
            objective="research evidence verification",
            procedure=[
                "Gather evidence.",
                "Verify evidence.",
            ],
        )
    )

    orchestrator = Orchestrator(
        skill_registry=registry,
    )

    run = orchestrator.run(
        Task(
            id="skill-runtime-001",
            objective="research evidence verification",
        )
    )

    planning_event = next(
        event
        for event in run.events
        if event["state"] == "planning"
    )

    runtime = planning_event["skill_runtime"]

    assert runtime["name"] == "research"
    assert runtime["version"] == "1.0.0"
    assert runtime["status"] == "completed"
    assert [step["status"] for step in runtime["steps"]] == [
        "acknowledged",
        "acknowledged",
    ]
    orchestrator.close()


def test_orchestrator_uses_runtime_config_for_default_provider():
    from agent_os.config import RuntimeConfig
    from agent_os.core.orchestrator import Orchestrator

    orchestrator = Orchestrator(
        config=RuntimeConfig(
            provider_response="configured response",
            provider_name="configured-provider",
            provider_model="configured-model",
        )
    )

    from agent_os.core.orchestrator import Task

    task = Task(id="config-task", objective="configured task")
    result = orchestrator.run(task)

    assert result.output == "configured response"
    execution_event = next(
        event for event in result.events
        if event["state"] == "execution"
    )

    assert execution_event["provider"] == "configured-provider"
    assert execution_event["model"] == "configured-model"
    orchestrator.close()


def test_orchestrator_uses_configured_memory_path(tmp_path):
    from agent_os.config import RuntimeConfig
    from agent_os.core.orchestrator import Orchestrator

    db_path = tmp_path / "runtime.db"
    config = RuntimeConfig(memory_path=str(db_path))

    first = Orchestrator(config=config)
    first.memory.add_memory(
        content="configured persistent memory",
        kind="semantic",
    )
    first.close()

    second = Orchestrator(config=config)
    matches = second.retriever.search("configured persistent memory")

    assert matches
    assert matches[0].content == "configured persistent memory"
    second.close()


def test_orchestrator_converts_unexpected_agent_error_to_failed_run():
    class FailingAgent:
        def run(self, context):
            raise RuntimeError("unexpected agent failure")

    memory = MemoryStore(":memory:")
    orchestrator = Orchestrator(
        memory=memory,
        agent=FailingAgent(),
    )

    run = orchestrator.run(
        Task(
            id="failure-001",
            objective="trigger an unexpected agent failure",
        )
    )

    assert run.state == State.FAILED
    assert run.error == "runtimeerror:unexpected agent failure"

    failure_event = run.events[-1]
    assert failure_event["state"] == "failed"
    assert failure_event["error"] == run.error

    persisted = orchestrator.run_repository.list_events("failure-001")
    assert persisted[-1]["state"] == "failed"

    memory.close()
