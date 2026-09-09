from dataclasses import dataclass


@dataclass(frozen=True)
class PermissionRequest:
    principal: str
    action: str
    resource: str


@dataclass(frozen=True)
class PermissionDecision:
    allowed: bool
    reason: str


class PermissionPolicy:
    """Explicit allow-list policy for runtime security decisions."""

    def __init__(
        self,
        allowed_actions: set[str] | None = None,
    ):
        self.allowed_actions = set(allowed_actions or set())

    def decide(
        self,
        request: PermissionRequest,
    ) -> PermissionDecision:
        if not request.principal.strip():
            return PermissionDecision(
                allowed=False,
                reason="principal_required",
            )

        if not request.action.strip():
            return PermissionDecision(
                allowed=False,
                reason="action_required",
            )

        if not request.resource.strip():
            return PermissionDecision(
                allowed=False,
                reason="resource_required",
            )

        if request.action not in self.allowed_actions:
            return PermissionDecision(
                allowed=False,
                reason="action_not_allowed",
            )

        return PermissionDecision(
            allowed=True,
            reason="allowed",
        )
