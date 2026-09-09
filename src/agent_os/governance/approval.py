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
