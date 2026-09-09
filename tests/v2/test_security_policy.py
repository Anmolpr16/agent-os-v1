from agent_os.security.policy import (
    PermissionPolicy,
    PermissionRequest,
)


def test_policy_allows_explicit_action():
    policy = PermissionPolicy({"read"})

    decision = policy.decide(
        PermissionRequest(
            principal="agent",
            action="read",
            resource="memory",
        )
    )

    assert decision.allowed is True
    assert decision.reason == "allowed"


def test_policy_denies_unknown_action():
    policy = PermissionPolicy({"read"})

    decision = policy.decide(
        PermissionRequest(
            principal="agent",
            action="write",
            resource="memory",
        )
    )

    assert decision.allowed is False
    assert decision.reason == "action_not_allowed"


def test_policy_rejects_missing_principal():
    policy = PermissionPolicy({"read"})

    decision = policy.decide(
        PermissionRequest(
            principal="",
            action="read",
            resource="memory",
        )
    )

    assert decision.allowed is False
    assert decision.reason == "principal_required"


def test_policy_rejects_missing_action():
    policy = PermissionPolicy({"read"})

    decision = policy.decide(
        PermissionRequest(
            principal="agent",
            action="",
            resource="memory",
        )
    )

    assert decision.allowed is False
    assert decision.reason == "action_required"


def test_policy_rejects_missing_resource():
    policy = PermissionPolicy({"read"})

    decision = policy.decide(
        PermissionRequest(
            principal="agent",
            action="read",
            resource="",
        )
    )

    assert decision.allowed is False
    assert decision.reason == "resource_required"
