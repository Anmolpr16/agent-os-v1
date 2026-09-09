from agent_os.agents import Agent, AgentContext
from agent_os.evaluation import EvaluationRunner
from agent_os.providers import MockProvider
from agent_os.runtime.pipeline import EndToEndPipeline
from agent_os.runtime.system import AgentOSRuntime
from agent_os.governance import ApprovalGate, AutomaticApproval


def test_runtime_pipeline_records_complete_lifecycle():
    agent = Agent(MockProvider(response="result completed"))
    evaluation = EvaluationRunner()
    runtime = AgentOSRuntime(
        agent=agent,
        evaluation=evaluation,
        approval=ApprovalGate(
            decider=AutomaticApproval(),
        ),
    )

    result = EndToEndPipeline(runtime).run(
        "integration-1",
        "produce result",
        ["result"],
    )

    assert result.success
    events = runtime.lifecycle.for_task("integration-1")
    assert events
    names = [event.name for event in events]
    assert "pipeline_started" in names
    assert "closed_loop_started" in names
    assert "closed_loop_completed" in names
    assert "pipeline_completed" in names
    assert names.index("pipeline_started") < names.index("closed_loop_started")
    assert names.index("closed_loop_started") < names.index("closed_loop_completed")
    assert names.index("closed_loop_completed") < names.index("pipeline_completed")


def test_runtime_snapshot_contains_operational_state():
    runtime = AgentOSRuntime()
    snapshot = runtime.snapshot()

    assert set(snapshot) == {
        "state",
        "messages",
        "audit_events",
        "metrics",
    }
    assert snapshot["messages"] == 0
    assert snapshot["audit_events"] == 0
    assert isinstance(snapshot["metrics"], dict)


def test_runtime_health_survives_empty_optional_components():
    runtime = AgentOSRuntime()
    health = runtime.health()

    assert health.status == "ok"
    assert health.healthy


def test_agent_context_reaches_provider_boundary():
    agent = Agent(MockProvider(response="ok"))

    result = agent.run(
        AgentContext(
            task_id="boundary-1",
            objective="do work",
            metadata={"source": "integration"},
        )
    )

    assert result.output == "ok"
    assert result.provider == "mock"
    assert result.model == "mock-v1"
