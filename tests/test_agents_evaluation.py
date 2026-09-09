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


def test_agent_executes_requested_tools():
    from agent_os.agents import Agent, AgentContext
    from agent_os.providers import MockProvider
    from agent_os.tools import (
        PermissionPolicy,
        ToolExecutor,
        ToolRegistry,
    )

    registry = ToolRegistry()
    registry.register(
        name="add",
        description="Add two numbers.",
        handler=lambda a, b: a + b,
    )

    executor = ToolExecutor(
        registry,
        PermissionPolicy(
            allowed_tools={"add"}
        ),
    )

    agent = Agent(
        MockProvider(response="done"),
        executor,
    )

    result = agent.run(
        AgentContext(
            task_id="tool-agent-001",
            objective="Use the calculator",
            metadata={
                "tool_calls": [
                    {
                        "name": "add",
                        "arguments": {
                            "a": 4,
                            "b": 6,
                        },
                    }
                ]
            },
        )
    )

    assert result.output == "done"
    assert result.metadata["tool_calls"][0][
        "tool_name"
    ] == "add"
    assert result.metadata["tool_calls"][0][
        "success"
    ] is True
    assert result.metadata["tool_calls"][0][
        "output"
    ] == 10


def test_agent_records_tool_permission_failure():
    from agent_os.agents import Agent, AgentContext
    from agent_os.providers import MockProvider
    from agent_os.tools import (
        PermissionPolicy,
        ToolExecutor,
        ToolRegistry,
    )

    registry = ToolRegistry()
    registry.register(
        name="secret",
        description="Restricted operation.",
        handler=lambda: "should not run",
    )

    executor = ToolExecutor(
        registry,
        PermissionPolicy(
            allowed_tools=set()
        ),
    )

    agent = Agent(
        MockProvider(response="done"),
        executor,
    )

    result = agent.run(
        AgentContext(
            task_id="tool-agent-002",
            objective="Use restricted tool",
            metadata={
                "tool_calls": [
                    {
                        "name": "secret",
                        "arguments": {},
                    }
                ]
            },
        )
    )

    tool_result = result.metadata["tool_calls"][0]

    assert tool_result["tool_name"] == "secret"
    assert tool_result["success"] is False
    assert tool_result["output"] is None
    assert tool_result["error"] == (
        "PermissionError: "
        "tool_not_permitted:secret"
    )


def test_agent_records_missing_tool_failure():
    from agent_os.agents import Agent, AgentContext
    from agent_os.providers import MockProvider
    from agent_os.tools import (
        PermissionPolicy,
        ToolExecutor,
        ToolRegistry,
    )

    executor = ToolExecutor(
        ToolRegistry(),
        PermissionPolicy(
            allowed_tools={"missing"}
        ),
    )

    agent = Agent(
        MockProvider(response="done"),
        executor,
    )

    result = agent.run(
        AgentContext(
            task_id="tool-agent-003",
            objective="Use missing tool",
            metadata={
                "tool_calls": [
                    {
                        "name": "missing",
                        "arguments": {},
                    }
                ]
            },
        )
    )

    tool_result = result.metadata["tool_calls"][0]

    assert tool_result["tool_name"] == "missing"
    assert tool_result["success"] is False
    assert tool_result["output"] is None
    assert tool_result["error"] == (
        "KeyError: "
        "'tool_not_registered:missing'"
    )
