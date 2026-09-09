from agent_os.agents import Agent, AgentContext
from agent_os.core.harness import AgentHarness
from agent_os.providers import MockProvider


def test_harness_runs_agent_successfully():
    agent = Agent(
        MockProvider(
            response="completed",
            provider="test",
            model="test-v1",
        )
    )
    harness = AgentHarness(agent)

    result = harness.run(
        AgentContext(
            task_id="task-1",
            objective="complete task",
        )
    )

    assert result.success is True
    assert result.attempts == 1
    assert result.result is not None
    assert result.result.output == "completed"


def test_harness_rejects_invalid_attempt_limit():
    agent = Agent(MockProvider())

    try:
        AgentHarness(agent, max_attempts=0)
    except ValueError as exc:
        assert str(exc) == "max_attempts must be positive"
    else:
        raise AssertionError("expected ValueError")


class FailingAgent:
    def __init__(self):
        self.calls = 0

    def run(self, context):
        self.calls += 1
        raise TimeoutError("temporary failure")


def test_harness_retries_until_attempt_limit():
    agent = FailingAgent()
    harness = AgentHarness(agent, max_attempts=3)

    result = harness.run(
        AgentContext(
            task_id="task-2",
            objective="retry task",
        )
    )

    assert result.success is False
    assert result.attempts == 3
    assert result.error == "temporary failure"
    assert agent.calls == 3


class TerminalFailingAgent:
    def __init__(self):
        self.calls = 0

    def run(self, context):
        self.calls += 1
        raise ValueError("terminal failure")


def test_harness_does_not_retry_terminal_failure():
    agent = TerminalFailingAgent()
    harness = AgentHarness(agent, max_attempts=3)

    result = harness.run(
        AgentContext(
            task_id="task-3",
            objective="terminal task",
        )
    )

    assert result.success is False
    assert result.attempts == 1
    assert result.error == "terminal failure"
    assert agent.calls == 1
