from agent_os.human_judgment import (
    Alternative,
    DecisionStatus,
    Evidence,
    ExpectedOutcome,
    HumanJudgment,
    Risk,
    RiskLevel,
)


def proposal(j):
    return j.propose(
        task_id="task-1",
        action="deploy_candidate",
        rationale="Candidate performed better.",
        evidence=[
            Evidence(
                source="evaluation",
                claim="Candidate scored 0.92.",
                confidence=0.95,
            )
        ],
        risks=[
            Risk(
                description="Possible regression.",
                level=RiskLevel.MEDIUM,
                likelihood=0.3,
                impact=0.8,
                mitigation="Run verification.",
            )
        ],
        alternatives=[
            Alternative(
                name="retain_current",
                description="Keep current version.",
            )
        ],
        expected_outcomes=[
            ExpectedOutcome(
                outcome="Improved performance.",
                probability=0.85,
                value=0.8,
            )
        ],
        confidence=0.87,
        reversibility="rollback",
    )


def test_structured_proposal():
    j = HumanJudgment()
    p = proposal(j)

    assert p.task_id == "task-1"
    assert len(p.evidence) == 1
    assert len(p.risks) == 1
    assert len(p.alternatives) == 1
    assert len(p.expected_outcomes) == 1
    assert p.confidence == 0.87
    assert j.get(p.proposal_id).status == DecisionStatus.PENDING


def test_pending_requires_human_approval():
    j = HumanJudgment()
    p = proposal(j)

    assert not j.can_execute(p.proposal_id)

    try:
        j.require_approval(p.proposal_id)
        assert False
    except PermissionError as exc:
        assert str(exc) == "human_approval_required"


def test_approval_unlocks_execution():
    j = HumanJudgment()
    p = proposal(j)

    d = j.approve(
        proposal_id=p.proposal_id,
        decided_by="human",
        rationale="Evidence sufficient.",
        conditions=["Run post-deployment verification."],
    )

    assert d.status == DecisionStatus.APPROVED
    assert j.can_execute(p.proposal_id)
    assert j.require_approval(p.proposal_id) == d


def test_rejection_blocks_execution():
    j = HumanJudgment()
    p = proposal(j)

    d = j.reject(
        proposal_id=p.proposal_id,
        decided_by="human",
        rationale="Risk too high.",
    )

    assert d.status == DecisionStatus.REJECTED
    assert not j.can_execute(p.proposal_id)

    try:
        j.require_approval(p.proposal_id)
        assert False
    except PermissionError as exc:
        assert str(exc) == "proposal_not_approved:rejected"


def test_revision_request_blocks_execution():
    j = HumanJudgment()
    p = proposal(j)

    d = j.request_revision(
        proposal_id=p.proposal_id,
        decided_by="human",
        rationale="Need more evidence.",
        conditions=["Add independent verification."],
    )

    assert d.status == DecisionStatus.REVISION_REQUESTED
    assert not j.can_execute(p.proposal_id)


def test_double_decision_rejected():
    j = HumanJudgment()
    p = proposal(j)

    j.approve(
        proposal_id=p.proposal_id,
        decided_by="human",
        rationale="Approved.",
    )

    try:
        j.reject(
            proposal_id=p.proposal_id,
            decided_by="human",
            rationale="Changed.",
        )
        assert False
    except ValueError as exc:
        assert str(exc) == "proposal_already_decided"


def test_history():
    j = HumanJudgment()
    p1 = proposal(j)

    j.approve(
        proposal_id=p1.proposal_id,
        decided_by="human",
        rationale="Approved.",
    )

    p2 = j.propose(
        task_id="task-2",
        action="archive",
        rationale="Obsolete.",
    )

    j.reject(
        proposal_id=p2.proposal_id,
        decided_by="human",
        rationale="Not yet.",
    )

    assert len(j.history()) == 2
    assert len(j.history("task-1")) == 1
    assert len(j.history("task-2")) == 1


def test_risk_summary():
    j = HumanJudgment()
    p = proposal(j)

    summary = j.risk_summary(p.proposal_id)

    assert summary["count"] == 1
    assert summary["max_level"] == "medium"
    assert summary["total_exposure"] == 0.24
    assert summary["highest_exposure"] == 0.24


def test_summary():
    j = HumanJudgment()
    p = proposal(j)

    summary = j.summary(p.proposal_id)

    assert summary["status"] == "pending"
    assert summary["approved"] is False
    assert summary["evidence_count"] == 1
    assert summary["risk_count"] == 1


def test_validation():
    try:
        Evidence(source="", claim="x")
        assert False
    except ValueError as exc:
        assert str(exc) == "evidence_source_required"

    try:
        Risk(
            description="bad",
            level=RiskLevel.HIGH,
            likelihood=2.0,
        )
        assert False
    except ValueError as exc:
        assert str(exc) == "risk_likelihood_invalid"

    try:
        j = HumanJudgment()
        j.propose(
            task_id="t",
            action="a",
            rationale="r",
            confidence=1.5,
        )
        assert False
    except ValueError as exc:
        assert str(exc) == "confidence_invalid"


def test_unknown_proposal():
    j = HumanJudgment()

    try:
        j.require_approval("missing")
        assert False
    except ValueError as exc:
        assert str(exc) == "unknown_proposal"
