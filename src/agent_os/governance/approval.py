from dataclasses import dataclass
from enum import Enum
from typing import Callable


class ApprovalStatus(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING = "pending"


@dataclass(frozen=True)
class ApprovalRequest:
    task_id: str
    objective: str
    output: str


@dataclass(frozen=True)
class ApprovalDecision:
    status: ApprovalStatus
    reason: str


class ApprovalGate:
    """Explicit governance boundary for accepting agent output."""

    def __init__(
        self,
        decider: Callable[[ApprovalRequest], ApprovalDecision] | None = None,
    ):
        self.decider = decider

    def request(
        self,
        request: ApprovalRequest,
    ) -> ApprovalDecision:
        if not request.task_id.strip():
            return ApprovalDecision(
                status=ApprovalStatus.REJECTED,
                reason="task_id_required",
            )

        if not request.objective.strip():
            return ApprovalDecision(
                status=ApprovalStatus.REJECTED,
                reason="objective_required",
            )

        if not request.output.strip():
            return ApprovalDecision(
                status=ApprovalStatus.REJECTED,
                reason="output_required",
            )

        if self.decider is None:
            return ApprovalDecision(
                status=ApprovalStatus.PENDING,
                reason="human_approval_required",
            )

        decision = self.decider(request)

        if not isinstance(decision, ApprovalDecision):
            raise TypeError("decider_must_return_approval_decision")

        return decision


class AutomaticApproval:
    """Deterministic approval policy for trusted test/runtime paths."""

    def __init__(self, reason: str = "automatically_approved"):
        if not reason.strip():
            raise ValueError("approval_reason_required")
        self.reason = reason

    def __call__(
        self,
        request: ApprovalRequest,
    ) -> ApprovalDecision:
        return ApprovalDecision(
            status=ApprovalStatus.APPROVED,
            reason=self.reason,
        )

from agent_os.human_judgment import DecisionStatus, Evidence, HumanJudgment


class HumanJudgmentApproval:
    """Approval adapter backed by structured HumanJudgment."""

    def __init__(
        self,
        judgment: HumanJudgment,
        *,
        requested_by: str = "agent",
    ):
        self.judgment = judgment
        self.requested_by = requested_by
        self._proposals: dict[str, str] = {}

    def proposal_id(self, task_id: str) -> str | None:
        return self._proposals.get(task_id)

    def request(
        self,
        request: ApprovalRequest,
    ) -> ApprovalDecision:
        proposal_id = self._proposals.get(request.task_id)

        if proposal_id is not None:
            record = self.judgment.get(proposal_id)

            # A revision request resolves the old proposal. If a new
            # proposal has subsequently been submitted for the same task,
            # bind the runtime approval request to that latest pending one.
            if (
                record is not None
                and record.status == DecisionStatus.REVISION_REQUESTED
            ):
                latest = self.judgment.latest(request.task_id)
                if latest is not None:
                    proposal_id = latest.proposal.proposal_id
                    self._proposals[request.task_id] = proposal_id
                else:
                    proposal_id = None

        if proposal_id is None:
            proposal = self.judgment.propose(
                task_id=request.task_id,
                action=request.objective,
                rationale="Agent produced an evaluated output requiring human judgment.",
                evidence=[
                    Evidence(
                        source="runtime",
                        claim=request.output,
                        relevance=1.0,
                        confidence=1.0,
                        metadata={"approval_request": True},
                    )
                ],
                confidence=1.0,
                requested_by=self.requested_by,
                metadata={
                    "objective": request.objective,
                    "output": request.output,
                },
            )
            proposal_id = proposal.proposal_id
            self._proposals[request.task_id] = proposal_id

        record = self.judgment.get(proposal_id)

        if record is None:
            return ApprovalDecision(
                status=ApprovalStatus.REJECTED,
                reason="human_judgment_proposal_missing",
            )

        if record.status == DecisionStatus.APPROVED:
            return ApprovalDecision(
                status=ApprovalStatus.APPROVED,
                reason=(
                    record.decision.rationale
                    if record.decision is not None
                    else "human_approved"
                ),
            )

        if record.status == DecisionStatus.REJECTED:
            return ApprovalDecision(
                status=ApprovalStatus.REJECTED,
                reason=(
                    record.decision.rationale
                    if record.decision is not None
                    else "human_rejected"
                ),
            )

        return ApprovalDecision(
            status=ApprovalStatus.PENDING,
            reason="human_approval_required",
        )

    def __call__(
        self,
        request: ApprovalRequest,
    ) -> ApprovalDecision:
        return self.request(request)
