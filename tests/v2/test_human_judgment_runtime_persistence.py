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


def test_human_judgment_survives_runtime_restart():
    with Database() as db:
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

        # Persist the decision through the repository just as the
        # integrated approval path will do.
        first.approval.repository.save_decision(decision)

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
