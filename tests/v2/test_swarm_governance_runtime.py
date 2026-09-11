from agent_os.governance.approval import ApprovalStatus, HumanJudgmentApproval
from agent_os.human_judgment import DecisionStatus, HumanJudgment
from agent_os.swarm.council import CouncilResult, CouncilVerdict
from agent_os.swarm.runtime import SwarmGovernanceRuntime


def council(task_id="swarm-runtime-task"):
    return CouncilResult(
        task_id=task_id,
        verdict=CouncilVerdict.CONSENSUS,
        answer="recommended result",
        supporting_agents=("researcher", "reviewer"),
        dissenting_agents=(),
        failed_agents=(),
        evidence=("evidence",),
        confidence=1.0,
    )


def test_council_routes_to_pending_human_judgment():
    judgment = HumanJudgment()
    approval = HumanJudgmentApproval(judgment)
    runtime = SwarmGovernanceRuntime(judgment, approval)

    result = runtime.request(council())

    assert result.approval.status == ApprovalStatus.PENDING
    assert result.allowed is False
    assert result.proposal.proposal.task_id == "swarm-runtime-task"

    pending = judgment.pending("swarm-runtime-task")
    assert len(pending) == 1
    assert pending[0].status == DecisionStatus.PENDING


def test_approval_allows_council_recommendation():
    judgment = HumanJudgment()
    approval = HumanJudgmentApproval(judgment)
    runtime = SwarmGovernanceRuntime(judgment, approval)

    result = runtime.request(council())

    proposal_id = result.proposal.proposal.proposal_id
    decision = judgment.approve(
        proposal_id=proposal_id,
        decided_by="human",
        rationale="Council evidence reviewed and approved.",
    )

    assert decision.status == DecisionStatus.APPROVED

    second = approval.request(
        __import__("agent_os.governance.approval", fromlist=["ApprovalRequest"])
        .ApprovalRequest(
            task_id="swarm-runtime-task",
            objective="recommended result",
            output="recommended result",
        )
    )

    assert second.status == ApprovalStatus.APPROVED


def test_rejection_blocks_execution():
    judgment = HumanJudgment()
    approval = HumanJudgmentApproval(judgment)
    runtime = SwarmGovernanceRuntime(judgment, approval)

    result = runtime.request(council())
    proposal_id = result.proposal.proposal.proposal_id

    decision = judgment.reject(
        proposal_id=proposal_id,
        decided_by="human",
        rationale="Rejected after human review.",
    )

    assert decision.status == DecisionStatus.REJECTED

    second = approval.request(
        __import__("agent_os.governance.approval", fromlist=["ApprovalRequest"])
        .ApprovalRequest(
            task_id="swarm-runtime-task",
            objective="recommended result",
            output="recommended result",
        )
    )

    assert second.status == ApprovalStatus.REJECTED


def test_revision_request_keeps_execution_blocked():
    judgment = HumanJudgment()
    approval = HumanJudgmentApproval(judgment)
    runtime = SwarmGovernanceRuntime(judgment, approval)

    result = runtime.request(council())
    proposal_id = result.proposal.proposal.proposal_id

    decision = judgment.request_revision(
        proposal_id=proposal_id,
        decided_by="human",
        rationale="Need stronger evidence.",
    )

    assert decision.status == DecisionStatus.REVISION_REQUESTED

    second = approval.request(
        __import__("agent_os.governance.approval", fromlist=["ApprovalRequest"])
        .ApprovalRequest(
            task_id="swarm-runtime-task",
            objective="recommended result",
            output="recommended result",
        )
    )

    assert second.status == ApprovalStatus.PENDING
