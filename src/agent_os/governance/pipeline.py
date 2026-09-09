from dataclasses import dataclass
from agent_os.governance import (
    ApprovalGate,
    ApprovalRequest,
    ApprovalStatus,
)
from agent_os.security import PermissionPolicy, PermissionRequest

@dataclass(frozen=True)
class GovernanceResult:
    allowed: bool
    approval: ApprovalStatus
    reason: str

class GovernancePipeline:
    def __init__(self, permissions: PermissionPolicy,
                 approval: ApprovalGate):
        self.permissions = permissions
        self.approval = approval

    def authorize(self, principal: str, action: str, resource: str,
                  request: ApprovalRequest) -> GovernanceResult:
        decision = self.permissions.decide(
            PermissionRequest(principal, action, resource)
        )
        if not decision.allowed:
            return GovernanceResult(False, ApprovalStatus.REJECTED,
                                    decision.reason)
        approval = self.approval.request(request)
        return GovernanceResult(
            approval.status == ApprovalStatus.APPROVED,
            approval.status,
            approval.reason,
        )
