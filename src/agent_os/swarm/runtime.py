"""Runtime integration for swarm council recommendations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from agent_os.governance.approval import (
    ApprovalDecision,
    ApprovalRequest,
    ApprovalStatus,
    HumanJudgmentApproval,
)
from agent_os.human_judgment import (
    DecisionStatus,
    HumanJudgment,
)

from .council import CouncilResult
from .governance import CouncilGovernanceBridge, CouncilProposal


@dataclass(frozen=True)
class SwarmGovernanceResult:
    """Result of routing a council recommendation through human judgment."""

    council: CouncilResult
    proposal: CouncilProposal
    approval: ApprovalDecision

    @property
    def allowed(self) -> bool:
        return self.approval.status == ApprovalStatus.APPROVED


class SwarmGovernanceRuntime:
    """Connect council recommendations to the existing approval boundary.

    The swarm may recommend an action, but this class never bypasses
    HumanJudgmentApproval.
    """

    def __init__(
        self,
        judgment: HumanJudgment,
        approval: HumanJudgmentApproval,
        *,
        requested_by: str = "swarm_council",
    ) -> None:
        if judgment is None:
            raise ValueError("human_judgment_required")
        if approval is None:
            raise ValueError("human_judgment_approval_required")

        self.judgment = judgment
        self.approval = approval
        self.bridge = CouncilGovernanceBridge(
            judgment,
            requested_by=requested_by,
        )

    def request(
        self,
        council: CouncilResult,
        *,
        action: str | None = None,
        rationale: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> SwarmGovernanceResult:
        council_proposal = self.bridge.propose(
            council,
            action=action,
            rationale=rationale,
            metadata=metadata,
        )

        proposal = council_proposal.proposal
        record = self.judgment.get(proposal.proposal_id)

        if record is None:
            raise RuntimeError("council_proposal_not_registered")

        # Hand the exact council-created proposal to the existing approval
        # adapter. This prevents HumanJudgmentApproval from creating a
        # duplicate proposal for the same task.
        self.approval._proposals[council.task_id] = proposal.proposal_id

        approval_request = ApprovalRequest(
            task_id=council.task_id,
            objective=proposal.action,
            output=str(council.answer),
        )

        approval = self.approval.request(approval_request)

        return SwarmGovernanceResult(
            council=council,
            proposal=council_proposal,
            approval=approval,
        )

    def decide(
        self,
        proposal_id: str,
        *,
        status: DecisionStatus,
        decided_by: str,
        rationale: str,
        conditions: tuple[str, ...] = (),
    ) -> SwarmGovernanceResult:
        record = self.judgment.get(proposal_id)
        if record is None:
            raise ValueError("unknown_proposal")

        decision = self.judgment.decide(
            proposal_id=proposal_id,
            status=status,
            decided_by=decided_by,
            rationale=rationale,
            conditions=conditions,
        )

        council_verdict = record.proposal.metadata.get(
            "council_verdict",
            "unknown",
        )

        # Reconstruct a minimal council representation from the persisted
        # proposal metadata so callers receive one stable result shape.
        from .council import CouncilVerdict

        try:
            verdict = CouncilVerdict(council_verdict)
        except ValueError:
            verdict = CouncilVerdict.INSUFFICIENT_EVIDENCE

        council = CouncilResult(
            task_id=record.proposal.task_id,
            verdict=verdict,
            answer=record.proposal.action,
            supporting_agents=tuple(
                record.proposal.metadata.get("supporting_agents", ())
            ),
            dissenting_agents=tuple(
                record.proposal.metadata.get("dissenting_agents", ())
            ),
            failed_agents=tuple(
                record.proposal.metadata.get("failed_agents", ())
            ),
            confidence=float(
                record.proposal.metadata.get("council_confidence", 0.0)
            ),
        )

        status_map = {
            DecisionStatus.APPROVED: ApprovalStatus.APPROVED,
            DecisionStatus.REJECTED: ApprovalStatus.REJECTED,
            DecisionStatus.REVISION_REQUESTED: ApprovalStatus.PENDING,
        }

        approval_status = status_map[decision.status]

        return SwarmGovernanceResult(
            council=council,
            proposal=CouncilProposal(council=council, proposal=record.proposal),
            approval=ApprovalDecision(
                status=approval_status,
                reason=decision.rationale,
            ),
        )
