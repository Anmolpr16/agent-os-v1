from agent_os.agents import (
    Agent,
    AgentContext,
    AgentManager,
)
from agent_os.evaluation import EvaluationRunner
from agent_os.providers import MockProvider


def test_agent_runtime():
    agent = Agent(
        MockProvider(
            response="verified agent output",
        )
    )

    result = agent.run(
        AgentContext(
            task_id="agent-001",
            objective="Perform a test task",
        )
    )

    assert result.output == "verified agent output"
    assert result.provider == "mock"
    assert result.model == "mock-v1"


def test_agent_manager():
    manager = AgentManager()

    agent = Agent(MockProvider())

    manager.register("default", agent)

    assert manager.get("default") is agent
    assert manager.list() == ["default"]


def test_evaluation_runner():
    runner = EvaluationRunner()

    result = runner.evaluate(
        case_id="eval-001",
        output=(
            "Evidence was gathered and "
            "verification was completed."
        ),
        required_keywords=[
            "evidence",
            "verification",
        ],
    )

    assert result.passed
    assert result.score == 1.0


def test_evaluation_failure():
    runner = EvaluationRunner()

    result = runner.evaluate(
        case_id="eval-002",
        output="Incomplete answer.",
        required_keywords=[
            "evidence",
            "verification",
        ],
    )

    assert not result.passed
    assert result.score == 0.0
