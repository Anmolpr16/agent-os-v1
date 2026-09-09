from agent_os.governance import (
    ApprovalDecision,
    ApprovalGate,
    ApprovalRequest,
    ApprovalStatus,
    AutomaticApproval,
)


def request():
    return ApprovalRequest(
        task_id="task-1",
        objective="complete the task",
        output="completed result",
    )


def test_gate_requires_human_approval_by_default():
    decision = ApprovalGate().request(request())

    assert decision.status is ApprovalStatus.PENDING
    assert decision.reason == "human_approval_required"


def test_gate_accepts_explicit_decision():
    gate = ApprovalGate(
        decider=lambda item: ApprovalDecision(
            status=ApprovalStatus.APPROVED,
            reason="reviewed",
        )
    )

    decision = gate.request(request())

    assert decision.status is ApprovalStatus.APPROVED
    assert decision.reason == "reviewed"


def test_gate_supports_rejection():
    gate = ApprovalGate(
        decider=lambda item: ApprovalDecision(
            status=ApprovalStatus.REJECTED,
            reason="needs_revision",
        )
    )

    decision = gate.request(request())

    assert decision.status is ApprovalStatus.REJECTED
    assert decision.reason == "needs_revision"


def test_gate_rejects_missing_task_id():
    decision = ApprovalGate().request(
        ApprovalRequest(
            task_id="",
            objective="objective",
            output="output",
        )
    )

    assert decision.status is ApprovalStatus.REJECTED
    assert decision.reason == "task_id_required"


def test_gate_rejects_missing_objective():
    decision = ApprovalGate().request(
        ApprovalRequest(
            task_id="task-1",
            objective="",
            output="output",
        )
    )

    assert decision.status is ApprovalStatus.REJECTED
    assert decision.reason == "objective_required"


def test_gate_rejects_missing_output():
    decision = ApprovalGate().request(
        ApprovalRequest(
            task_id="task-1",
            objective="objective",
            output="",
        )
    )

    assert decision.status is ApprovalStatus.REJECTED
    assert decision.reason == "output_required"


def test_gate_rejects_invalid_decider_result():
    gate = ApprovalGate(
        decider=lambda item: "approved",
    )

    try:
        gate.request(request())
    except TypeError as exc:
        assert str(exc) == "decider_must_return_approval_decision"
    else:
        raise AssertionError("expected TypeError")


def test_automatic_approval_is_deterministic():
    decision = ApprovalGate(
        decider=AutomaticApproval(),
    ).request(request())

    assert decision.status is ApprovalStatus.APPROVED
    assert decision.reason == "automatically_approved"


def test_automatic_approval_requires_reason():
    try:
        AutomaticApproval("")
    except ValueError as exc:
        assert str(exc) == "approval_reason_required"
    else:
        raise AssertionError("expected ValueError")
