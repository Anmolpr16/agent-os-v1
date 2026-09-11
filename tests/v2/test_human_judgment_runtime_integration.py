from agent_os.agents import Agent
from agent_os.evaluation import EvaluationRunner
from agent_os.governance import ApprovalStatus
from agent_os.human_judgment import DecisionStatus, HumanJudgment
from agent_os.providers import MockProvider
from agent_os.runtime.pipeline import EndToEndPipeline
from agent_os.runtime.system import AgentOSRuntime


def test_runtime_creates_pending_human_judgment_proposal():
    judgment = HumanJudgment()
    runtime = AgentOSRuntime(
        agent=Agent(MockProvider(response="result completed")),
        evaluation=EvaluationRunner(),
        human_judgment=judgment,
    )

    result = EndToEndPipeline(runtime).run(
        "human-review-1",
        "produce result",
        ["result"],
    )

    assert result.success is False
    assert result.approval == ApprovalStatus.PENDING.value
    assert result.error == "human_approval_required"

    pending = judgment.pending("human-review-1")
    assert len(pending) == 1
    assert pending[0].status == DecisionStatus.PENDING
    assert pending[0].proposal.task_id == "human-review-1"
    assert pending[0].proposal.action == "produce result"
    assert len(pending[0].proposal.evidence) == 1


def test_human_approval_unlocks_runtime_execution():
    judgment = HumanJudgment()
    runtime = AgentOSRuntime(
        agent=Agent(MockProvider(response="result completed")),
        evaluation=EvaluationRunner(),
        human_judgment=judgment,
    )
    pipeline = EndToEndPipeline(runtime)

    pending = pipeline.run(
        "human-review-2",
        "produce result",
        ["result"],
    )

    assert pending.success is False
    assert pending.approval == ApprovalStatus.PENDING.value

    proposal = judgment.pending("human-review-2")[0]

    decision = judgment.approve(
        proposal_id=proposal.proposal.proposal_id,
        decided_by="human",
        rationale="Evidence and risk are acceptable.",
        conditions=["Perform post-execution verification."],
    )

    assert decision.status == DecisionStatus.APPROVED

    completed = pipeline.run(
        "human-review-2",
        "produce result",
        ["result"],
    )

    assert completed.success is True
    assert completed.approval == ApprovalStatus.APPROVED.value
    assert completed.output == "result completed"
    assert judgment.pending("human-review-2") == []
    assert judgment.get(proposal.proposal.proposal_id).status == DecisionStatus.APPROVED
