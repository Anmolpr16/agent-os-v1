from agent_os.agents import Agent
from agent_os.evaluation import EvaluationRunner
from agent_os.governance import ApprovalStatus
from agent_os.human_judgment import DecisionStatus, HumanJudgment
from agent_os.providers import MockProvider
from agent_os.runtime.pipeline import EndToEndPipeline
from agent_os.runtime.system import AgentOSRuntime


def make_pipeline(judgment: HumanJudgment):
    runtime = AgentOSRuntime(
        agent=Agent(MockProvider(response="result completed")),
        evaluation=EvaluationRunner(),
        human_judgment=judgment,
    )
    return EndToEndPipeline(runtime)


def test_rejected_human_judgment_blocks_execution():
    judgment = HumanJudgment()
    pipeline = make_pipeline(judgment)

    pending = pipeline.run(
        "human-reject-1",
        "produce result",
        ["result"],
    )

    assert pending.success is False
    assert pending.approval == ApprovalStatus.PENDING.value

    proposal = judgment.pending("human-reject-1")[0]

    decision = judgment.reject(
        proposal_id=proposal.proposal.proposal_id,
        decided_by="human",
        rationale="The proposed action is not acceptable.",
    )

    assert decision.status == DecisionStatus.REJECTED

    rejected = pipeline.run(
        "human-reject-1",
        "produce result",
        ["result"],
    )

    assert rejected.success is False
    assert rejected.approval == ApprovalStatus.REJECTED.value
    assert rejected.error == "The proposed action is not acceptable."
    assert judgment.pending("human-reject-1") == []


def test_revision_request_blocks_execution_and_preserves_decision():
    judgment = HumanJudgment()
    pipeline = make_pipeline(judgment)

    pending = pipeline.run(
        "human-revision-1",
        "produce result",
        ["result"],
    )

    assert pending.success is False
    proposal = judgment.pending("human-revision-1")[0]

    decision = judgment.request_revision(
        proposal_id=proposal.proposal.proposal_id,
        decided_by="human",
        rationale="Provide stronger evidence before execution.",
        conditions=["Add supporting evidence."],
    )

    assert decision.status == DecisionStatus.REVISION_REQUESTED
    assert decision.rationale == "Provide stronger evidence before execution."
    assert decision.conditions == ("Add supporting evidence.",)

    blocked = pipeline.run(
        "human-revision-1",
        "produce result",
        ["result"],
    )

    assert blocked.success is False
    assert blocked.approval == ApprovalStatus.PENDING.value
    assert blocked.error == "human_approval_required"

    record = judgment.get(proposal.proposal.proposal_id)
    assert record is not None
    assert record.status == DecisionStatus.REVISION_REQUESTED
    assert record.decision is not None
    assert record.decision.decided_by == "human"


def test_approval_after_revision_request_requires_new_proposal():
    judgment = HumanJudgment()
    pipeline = make_pipeline(judgment)

    first = pipeline.run(
        "human-revision-2",
        "produce result",
        ["result"],
    )

    assert first.success is False

    original = judgment.pending("human-revision-2")[0]

    revision = judgment.request_revision(
        proposal_id=original.proposal.proposal_id,
        decided_by="human",
        rationale="Revise the proposal.",
    )

    assert revision.status == DecisionStatus.REVISION_REQUESTED
    assert judgment.pending("human-revision-2") == []

    revised = judgment.propose(
        task_id="human-revision-2",
        action="produce result with stronger evidence",
        rationale="Updated proposal after human feedback.",
        requested_by="agent",
    )

    assert revised.proposal_id != original.proposal.proposal_id
    assert revised.task_id == "human-revision-2"

    decision = judgment.approve(
        proposal_id=revised.proposal_id,
        decided_by="human",
        rationale="The revised proposal is acceptable.",
    )

    assert decision.status == DecisionStatus.APPROVED

    completed = pipeline.run(
        "human-revision-2",
        "produce result",
        ["result"],
    )

    assert completed.success is True
    assert completed.approval == ApprovalStatus.APPROVED.value
    assert completed.output == "result completed"

    history = judgment.history("human-revision-2")
    assert len(history) == 2
    assert history[0].status == DecisionStatus.REVISION_REQUESTED
    assert history[1].status == DecisionStatus.APPROVED
