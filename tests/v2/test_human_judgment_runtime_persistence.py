from agent_os.agents import Agent
from agent_os.evaluation import EvaluationRunner
from agent_os.governance import ApprovalStatus, GovernanceRepository, HumanJudgmentApproval
from agent_os.human_judgment import DecisionStatus, HumanJudgment
from agent_os.providers import MockProvider
from agent_os.runtime.pipeline import EndToEndPipeline
from agent_os.runtime.system import AgentOSRuntime
from agent_os.storage import Database


def make_runtime(db, judgment):
    repository = GovernanceRepository(database=db)
    approval = HumanJudgmentApproval(judgment, repository=repository)
    return AgentOSRuntime(
        agent=Agent(MockProvider(response="result completed")),
        evaluation=EvaluationRunner(),
        approval=approval,
        human_judgment=judgment,
    )


def test_human_judgment_survives_runtime_restart(tmp_path):
    db_path = tmp_path / "governance.db"

    with Database(str(db_path)) as db:
        first_judgment = HumanJudgment()
        first = make_runtime(db, first_judgment)

        pending = EndToEndPipeline(first).run(
            "restart-task",
            "produce result",
            ["result"],
        )

        assert pending.success is False
        assert pending.approval == ApprovalStatus.PENDING.value

        proposal = first_judgment.pending("restart-task")[0]

        decision = first_judgment.approve(
            proposal_id=proposal.proposal.proposal_id,
            decided_by="human",
            rationale="Approved after restart-persistence test.",
        )

        assert decision.status == DecisionStatus.APPROVED

        completed = EndToEndPipeline(first).run(
            "restart-task",
            "produce result",
            ["result"],
        )

        assert completed.success is True
        assert completed.approval == ApprovalStatus.APPROVED.value

    with Database(str(db_path)) as db:
        second_judgment = HumanJudgment()
        second = make_runtime(db, second_judgment)

        completed = EndToEndPipeline(second).run(
            "restart-task",
            "produce result",
            ["result"],
        )

        assert completed.success is True
        assert completed.approval == ApprovalStatus.APPROVED.value

        restored = second_judgment.get(proposal.proposal.proposal_id)
        assert restored is not None
        assert restored.status == DecisionStatus.APPROVED


def test_rejected_human_judgment_survives_restart(tmp_path):
    db_path = tmp_path / "rejected.db"

    with Database(str(db_path)) as db:
        judgment = HumanJudgment()
        runtime = make_runtime(db, judgment)

        pending = EndToEndPipeline(runtime).run(
            "restart-reject",
            "produce result",
            ["result"],
        )
        assert pending.approval == ApprovalStatus.PENDING.value

        proposal = judgment.pending("restart-reject")[0]
        decision = judgment.reject(
            proposal_id=proposal.proposal.proposal_id,
            decided_by="human",
            rationale="Rejected during restart test.",
        )
        assert decision.status == DecisionStatus.REJECTED

        blocked = EndToEndPipeline(runtime).run(
            "restart-reject",
            "produce result",
            ["result"],
        )
        assert blocked.success is False
        assert blocked.approval == ApprovalStatus.REJECTED.value

    with Database(str(db_path)) as db:
        restored_judgment = HumanJudgment()
        restored_runtime = make_runtime(db, restored_judgment)

        blocked = EndToEndPipeline(restored_runtime).run(
            "restart-reject",
            "produce result",
            ["result"],
        )

        assert blocked.success is False
        assert blocked.approval == ApprovalStatus.REJECTED.value


def test_revision_request_survives_restart(tmp_path):
    db_path = tmp_path / "revision.db"

    with Database(str(db_path)) as db:
        judgment = HumanJudgment()
        runtime = make_runtime(db, judgment)

        pending = EndToEndPipeline(runtime).run(
            "restart-revision",
            "produce result",
            ["result"],
        )
        assert pending.approval == ApprovalStatus.PENDING.value

        proposal = judgment.pending("restart-revision")[0]
        decision = judgment.request_revision(
            proposal_id=proposal.proposal.proposal_id,
            decided_by="human",
            rationale="More evidence is required.",
            conditions=["Add stronger verification."],
        )
        assert decision.status == DecisionStatus.REVISION_REQUESTED

        blocked = EndToEndPipeline(runtime).run(
            "restart-revision",
            "produce result",
            ["result"],
        )
        assert blocked.success is False
        assert blocked.approval == ApprovalStatus.PENDING.value

    with Database(str(db_path)) as db:
        restored_judgment = HumanJudgment()
        restored_runtime = make_runtime(db, restored_judgment)

        blocked = EndToEndPipeline(restored_runtime).run(
            "restart-revision",
            "produce result",
            ["result"],
        )

        assert blocked.success is False
        assert blocked.approval == ApprovalStatus.PENDING.value

        restored = restored_judgment.latest("restart-revision")
        assert restored is not None
        assert restored.status == DecisionStatus.REVISION_REQUESTED
        assert restored.decision is not None
        assert restored.decision.conditions == ("Add stronger verification.",)
