
from agent_os.agents import Agent, AgentContext
from agent_os.governance import ApprovalDecision, ApprovalGate, ApprovalStatus
from agent_os.providers import MockProvider
from agent_os.runtime import (
    AgentOSRuntime,
    EndToEndPipeline,
    RuntimePolicy,
    RuntimeRequest,
    validate_request,
)

def test_runtime_request_validation():
    request = RuntimeRequest(
        task_id="t1",
        objective="produce result",
        required_keywords=("result",),
    )
    validate_request(request)

def test_e2e_pipeline_with_automatic_approval():
    agent = Agent(MockProvider(response="result completed"))
    runtime = AgentOSRuntime(
        agent=agent,
        approval=ApprovalGate(
            lambda request: ApprovalDecision(
                ApprovalStatus.APPROVED,
                "test_approved",
            )
        ),
    )
    result = EndToEndPipeline(
        runtime,
        policy=RuntimePolicy(max_output_length=1000),
    ).run(
        "t1",
        "produce result",
        ["result"],
    )
    assert result.success is True
    assert result.output == "result completed"
    assert result.approval == "approved"
    assert result.metadata["loop_attempts"] == 1

def test_e2e_pipeline_rejects_invalid_request():
    runtime = AgentOSRuntime()
    result = EndToEndPipeline(runtime).run("", "objective", [])
    assert result.success is False
    assert result.error == "task_id_required"

def test_e2e_pipeline_pending_approval_is_not_success():
    agent = Agent(MockProvider(response="result completed"))
    runtime = AgentOSRuntime(agent=agent)
    result = EndToEndPipeline(runtime).run(
        "t2",
        "produce result",
        ["result"],
    )
    assert result.success is False
    assert result.approval == "pending"
