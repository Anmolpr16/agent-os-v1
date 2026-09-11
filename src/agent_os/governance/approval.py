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
from .repository import GovernanceRepository
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_os.runtime.audit import AuditLog


class HumanJudgmentApproval:
    """Approval adapter backed by structured HumanJudgment."""

    def __init__(
        self,
        judgment: HumanJudgment,
        *,
        requested_by: str = "agent",
        audit: "AuditLog | None" = None,
        repository: GovernanceRepository | None = None,
    ):
        self.judgment = judgment
        self.requested_by = requested_by
        self.audit = audit
        self.repository = repository
        self._proposals: dict[str, str] = {}
        self._audited_proposals: set[str] = set()
        self._audited_decisions: set[str] = set()

        if self.repository is not None:
            self.judgment.add_decision_listener(
                self.repository.save_decision
            )

        if self.repository is not None:
            self.repository.load_into(self.judgment)
            rows = self.repository.conn.execute(
                "SELECT DISTINCT task_id FROM governance_proposals ORDER BY task_id"
            ).fetchall()
            for row in rows:
                latest = self.judgment.latest(row[0])
                if latest is not None:
                    self._proposals[row[0]] = latest.proposal.proposal_id

    def proposal_id(self, task_id: str) -> str | None:
        return self._proposals.get(task_id)

    def _audit_proposal(self, task_id: str, record) -> None:
        proposal = record.proposal
        if self.audit is None or proposal.proposal_id in self._audited_proposals:
            return

        self.audit.record(
            "human_judgment_proposed",
            proposal.requested_by,
            task_id,
            {
                "proposal_id": proposal.proposal_id,
                "objective": proposal.action,
            },
        )
        self._audited_proposals.add(proposal.proposal_id)

    def _audit_decision(self, task_id: str, record) -> None:
        if self.audit is None or record.decision is None:
            return

        decision = record.decision
        if decision.decision_id in self._audited_decisions:
            return

        event_name = {
            DecisionStatus.APPROVED: "human_judgment_approved",
            DecisionStatus.REJECTED: "human_judgment_rejected",
            DecisionStatus.REVISION_REQUESTED: (
                "human_judgment_revision_requested"
            ),
        }.get(record.status)

        if event_name is None:
            return

        self.audit.record(
            event_name,
            decision.decided_by,
            task_id,
            {
                "proposal_id": record.proposal.proposal_id,
                "decision_id": decision.decision_id,
                "rationale": decision.rationale,
                "conditions": list(decision.conditions),
            },
        )
        self._audited_decisions.add(decision.decision_id)

    def request(self, request: ApprovalRequest) -> ApprovalDecision:
        proposal_id = self._proposals.get(request.task_id)

        if proposal_id is not None:
            record = self.judgment.get(proposal_id)

            if record is not None:
                self._audit_proposal(request.task_id, record)

                if record.status == DecisionStatus.REVISION_REQUESTED:
                    self._audit_decision(request.task_id, record)

                    latest = self.judgment.latest(request.task_id)
                    if latest is not None:
                        proposal_id = latest.proposal.proposal_id
                        self._proposals[request.task_id] = proposal_id
                        record = latest
                        self._audit_proposal(request.task_id, record)
                    else:
                        proposal_id = None

        if proposal_id is None:
            proposal = self.judgment.propose(
                task_id=request.task_id,
                action=request.objective,
                rationale=(
                    "Agent produced an evaluated output requiring "
                    "human judgment."
                ),
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
            if self.repository is not None:
                self.repository.save_proposal(proposal)

            record = self.judgment.get(proposal_id)
            if record is not None:
                self._audit_proposal(request.task_id, record)

        record = self.judgment.get(proposal_id)
        if record is None:
            return ApprovalDecision(
                status=ApprovalStatus.REJECTED,
                reason="human_judgment_proposal_missing",
            )

        self._audit_decision(request.task_id, record)

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

    def __call__(self, request: ApprovalRequest) -> ApprovalDecision:
        return self.request(request)
