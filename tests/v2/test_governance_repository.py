from pathlib import Path

from agent_os.governance import GovernanceRepository
from agent_os.human_judgment import (
    Alternative,
    DecisionStatus,
    Evidence,
    ExpectedOutcome,
    HumanJudgment,
    Risk,
    RiskLevel,
)
from agent_os.storage import Database


def make_proposal(judgment: HumanJudgment):
    return judgment.propose(
        task_id="persistent-task",
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
        requested_by="agent",
        metadata={"source": "test"},
    )


def test_governance_repository_persists_proposal(tmp_path: Path):
    path = tmp_path / "governance.db"

    with Database(str(path)) as database:
        judgment = HumanJudgment()
        proposal = make_proposal(judgment)
        repository = GovernanceRepository(database=database)
        repository.save_record(judgment.get(proposal.proposal_id))

    with Database(str(path)) as database:
        repository = GovernanceRepository(database=database)
        record = repository.get(proposal.proposal_id)

        assert record is not None
        assert record.status == DecisionStatus.PENDING
        assert record.proposal.task_id == "persistent-task"
        assert len(record.proposal.evidence) == 1
        assert len(record.proposal.risks) == 1
        assert record.proposal.risks[0].level == RiskLevel.MEDIUM
        assert record.proposal.metadata["source"] == "test"


def test_governance_repository_persists_decision_and_reloads(tmp_path: Path):
    path = tmp_path / "governance.db"

    with Database(str(path)) as database:
        judgment = HumanJudgment()
        proposal = make_proposal(judgment)
        repository = GovernanceRepository(database=database)

        decision = judgment.approve(
            proposal_id=proposal.proposal_id,
            decided_by="human",
            rationale="Evidence sufficient.",
            conditions=["Run verification."],
        )
        repository.save_record(judgment.get(proposal.proposal_id))

        assert repository.get(proposal.proposal_id).decision == decision

    with Database(str(path)) as database:
        repository = GovernanceRepository(database=database)
        restored = HumanJudgment()
        repository.load_into(restored)

        record = restored.get(proposal.proposal_id)

        assert record is not None
        assert record.status == DecisionStatus.APPROVED
        assert record.decision is not None
        assert record.decision.decided_by == "human"
        assert record.decision.conditions == ("Run verification.",)
        assert restored.can_execute(proposal.proposal_id)


def test_governance_repository_pending_survives_restart(tmp_path: Path):
    path = tmp_path / "governance.db"

    with Database(str(path)) as database:
        judgment = HumanJudgment()
        proposal = make_proposal(judgment)
        repository = GovernanceRepository(database=database)
        repository.save_record(judgment.get(proposal.proposal_id))

    with Database(str(path)) as database:
        repository = GovernanceRepository(database=database)
        pending = repository.pending("persistent-task")

        assert len(pending) == 1
        assert pending[0].proposal.proposal_id == proposal.proposal_id
        assert pending[0].status == DecisionStatus.PENDING


def test_governance_repository_listener_persists_decision(tmp_path: Path):
    path = tmp_path / "governance-listener.db"

    with Database(str(path)) as database:
        judgment = HumanJudgment()
        repository = GovernanceRepository(database=database)
        judgment.add_decision_listener(repository.save_decision)

        proposal = make_proposal(judgment)
        repository.save_proposal(proposal)

        decision = judgment.approve(
            proposal_id=proposal.proposal_id,
            decided_by="human",
            rationale="Listener persisted the decision.",
        )

        restored = repository.get(proposal.proposal_id)

        assert restored is not None
        assert restored.decision == decision

        # Persistence must be idempotent for the same immutable decision.
        repository.save_decision(decision)

        count = database.conn.execute(
            "SELECT COUNT(*) FROM governance_decisions WHERE decision_id = ?",
            (decision.decision_id,),
        ).fetchone()[0]

        assert count == 1
