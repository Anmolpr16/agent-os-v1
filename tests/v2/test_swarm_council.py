from agent_os.swarm import (
    AgentResult,
    AgentStatus,
    CouncilVerdict,
    CrossVerifier,
)


def result(agent_id, output, evidence=()):
    return AgentResult(
        task_id="parent-task",
        agent_id=agent_id,
        status=AgentStatus.SUCCEEDED,
        output=output,
        evidence=evidence,
    )


def failed(agent_id):
    return AgentResult(
        task_id="parent-task",
        agent_id=agent_id,
        status=AgentStatus.FAILED,
        error="agent unavailable",
    )


def test_unanimous_results_produce_consensus():
    verifier = CrossVerifier(quorum=2)

    council = verifier.evaluate(
        "parent-task",
        (
            result("researcher", "supported", ("source-a",)),
            result("verifier", "supported", ("source-b",)),
        ),
    )

    assert council.verdict == CouncilVerdict.CONSENSUS
    assert council.answer == "supported"
    assert council.supporting_agents == ("researcher", "verifier")
    assert council.dissenting_agents == ()
    assert council.confidence == 1.0
    assert council.evidence == ("source-a", "source-b")


def test_disagreement_is_explicit():
    verifier = CrossVerifier(quorum=2)

    council = verifier.evaluate(
        "parent-task",
        (
            result("researcher", "supported"),
            result("critic", "unsupported"),
        ),
    )

    assert council.verdict == CouncilVerdict.DISAGREEMENT
    assert council.answer == "supported"
    assert council.supporting_agents == ("researcher",)
    assert council.dissenting_agents == ("critic",)
    assert council.confidence == 0.5


def test_failed_agents_do_not_count_as_evidence():
    verifier = CrossVerifier(quorum=2)

    council = verifier.evaluate(
        "parent-task",
        (
            result("researcher", "supported"),
            result("verifier", "supported"),
            failed("critic"),
        ),
    )

    assert council.verdict == CouncilVerdict.CONSENSUS
    assert council.failed_agents == ("critic",)
    assert council.confidence == 1.0


def test_insufficient_successful_agents():
    verifier = CrossVerifier(quorum=2)

    council = verifier.evaluate(
        "parent-task",
        (
            result("researcher", "supported"),
            failed("verifier"),
        ),
    )

    assert council.verdict == CouncilVerdict.INSUFFICIENT_EVIDENCE
    assert council.answer is None
    assert council.supporting_agents == ("researcher",)
    assert council.failed_agents == ("verifier",)


def test_empty_results_are_insufficient():
    verifier = CrossVerifier(quorum=2)

    council = verifier.evaluate("parent-task", ())

    assert council.verdict == CouncilVerdict.INSUFFICIENT_EVIDENCE
    assert council.answer is None
    assert council.confidence == 0.0


def test_custom_answer_extractor_supports_structured_outputs():
    verifier = CrossVerifier(
        quorum=2,
        answer_extractor=lambda result: result.output["answer"],
    )

    council = verifier.evaluate(
        "parent-task",
        (
            result("agent-a", {"answer": "yes", "score": 0.9}),
            result("agent-b", {"answer": "yes", "score": 0.8}),
            result("agent-c", {"answer": "no", "score": 0.2}),
        ),
    )

    assert council.verdict == CouncilVerdict.DISAGREEMENT
    assert council.answer == "yes"
    assert council.supporting_agents == ("agent-a", "agent-b")
    assert council.dissenting_agents == ("agent-c",)
    assert council.confidence == 2 / 3


def test_quorum_must_be_positive():
    try:
        CrossVerifier(quorum=0)
    except ValueError as exc:
        assert str(exc) == "quorum must be at least 1"
    else:
        raise AssertionError("expected ValueError")


def test_confidence_must_be_bounded():
    try:
        from agent_os.swarm import CouncilResult

        CouncilResult(
            task_id="task",
            verdict=CouncilVerdict.CONSENSUS,
            answer="yes",
            supporting_agents=("a",),
            dissenting_agents=(),
            failed_agents=(),
            confidence=1.5,
        )
    except ValueError as exc:
        assert str(exc) == "confidence must be between 0 and 1"
    else:
        raise AssertionError("expected ValueError")


def test_council_consensus_is_audited():
    from agent_os.runtime.audit import AuditLog

    audit = AuditLog()
    verifier = CrossVerifier(quorum=2, audit=audit)

    council = verifier.evaluate(
        "parent-task",
        (
            result("researcher", "supported"),
            result("verifier", "supported"),
        ),
    )

    events = audit.for_task("parent-task")

    assert council.verdict == CouncilVerdict.CONSENSUS
    assert [event.event for event in events] == [
        "swarm_council_evaluated",
    ]
    assert events[0].metadata["verdict"] == "consensus"
    assert events[0].metadata["confidence"] == 1.0


def test_council_disagreement_is_audited():
    from agent_os.runtime.audit import AuditLog

    audit = AuditLog()
    verifier = CrossVerifier(quorum=2, audit=audit)

    council = verifier.evaluate(
        "parent-task",
        (
            result("researcher", "yes"),
            result("critic", "no"),
        ),
    )

    events = audit.for_task("parent-task")

    assert council.verdict == CouncilVerdict.DISAGREEMENT
    assert events[0].event == "swarm_council_evaluated"
    assert events[0].metadata["dissenting_agents"] == ("critic",)


def test_council_governance_bridge_creates_human_judgment_proposal():
    from agent_os.human_judgment import HumanJudgment
    from agent_os.swarm.council import CouncilResult, CouncilVerdict
    from agent_os.swarm.governance import CouncilGovernanceBridge

    judgment = HumanJudgment()
    bridge = CouncilGovernanceBridge(judgment)

    council = CouncilResult(
        task_id="task-governance",
        verdict=CouncilVerdict.CONSENSUS,
        answer="recommended action",
        supporting_agents=("researcher", "reviewer"),
        dissenting_agents=(),
        failed_agents=(),
        evidence=("evidence-a",),
        confidence=1.0,
    )

    result = bridge.propose(council)

    assert result.council == council
    assert result.proposal.task_id == "task-governance"
    assert result.proposal.requested_by == "swarm_council"
    assert result.proposal.confidence == 1.0
    assert result.proposal.metadata["source"] == "swarm_council"
    assert result.proposal.metadata["council_verdict"] == "consensus"
    assert len(result.proposal.evidence) == 2
    assert judgment.get(result.proposal.proposal_id) is not None


def test_council_disagreement_creates_high_risk():
    from agent_os.human_judgment import HumanJudgment, RiskLevel
    from agent_os.swarm.council import CouncilResult, CouncilVerdict
    from agent_os.swarm.governance import CouncilGovernanceBridge

    council = CouncilResult(
        task_id="task-disagreement",
        verdict=CouncilVerdict.DISAGREEMENT,
        answer="answer-a",
        supporting_agents=("agent-a",),
        dissenting_agents=("agent-b",),
        failed_agents=(),
        confidence=0.5,
    )

    proposal = CouncilGovernanceBridge(HumanJudgment()).propose(council).proposal

    assert any(r.level == RiskLevel.HIGH for r in proposal.risks)


def test_insufficient_evidence_creates_critical_risk():
    from agent_os.human_judgment import HumanJudgment, RiskLevel
    from agent_os.swarm.council import CouncilResult, CouncilVerdict
    from agent_os.swarm.governance import CouncilGovernanceBridge

    council = CouncilResult(
        task_id="task-insufficient",
        verdict=CouncilVerdict.INSUFFICIENT_EVIDENCE,
        answer=None,
        supporting_agents=("agent-a",),
        dissenting_agents=(),
        failed_agents=("agent-b",),
        confidence=0.5,
    )

    proposal = CouncilGovernanceBridge(HumanJudgment()).propose(council).proposal

    assert any(r.level == RiskLevel.CRITICAL for r in proposal.risks)


def test_council_governance_bridge_does_not_auto_approve():
    from agent_os.human_judgment import DecisionStatus, HumanJudgment
    from agent_os.swarm.council import CouncilResult, CouncilVerdict
    from agent_os.swarm.governance import CouncilGovernanceBridge

    council = CouncilResult(
        task_id="task-approval-boundary",
        verdict=CouncilVerdict.CONSENSUS,
        answer="safe recommendation",
        supporting_agents=("agent-a", "agent-b"),
        dissenting_agents=(),
        failed_agents=(),
        confidence=1.0,
    )

    judgment = HumanJudgment()
    proposal = CouncilGovernanceBridge(judgment).propose(council).proposal

    assert judgment.get(proposal.proposal_id).status == DecisionStatus.PENDING
