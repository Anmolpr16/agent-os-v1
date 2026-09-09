from agent_os.providers import (
    MockProvider,
    ProviderRequest,
)
from agent_os.tools import (
    PermissionPolicy,
    ToolExecutor,
    ToolRegistry,
)


def test_provider_boundary():
    provider = MockProvider(
        response="deterministic answer",
    )

    result = provider.generate(
        ProviderRequest(
            prompt="test prompt",
        )
    )

    assert result.text == "deterministic answer"
    assert result.provider == "mock"
    assert result.model == "mock-v1"
    assert result.metadata["prompt_length"] == 11


def test_tool_registry_and_executor():
    registry = ToolRegistry()

    registry.register(
        name="add",
        description="Add two numbers.",
        handler=lambda a, b: a + b,
    )

    permissions = PermissionPolicy(
        allowed_tools={"add"},
    )

    executor = ToolExecutor(
        registry,
        permissions,
    )

    result = executor.execute(
        "add",
        a=2,
        b=3,
    )

    assert result.success
    assert result.output == 5


def test_unpermitted_tool_is_blocked():
    registry = ToolRegistry()

    registry.register(
        name="secret",
        description="Restricted operation.",
        handler=lambda: "executed",
    )

    executor = ToolExecutor(
        registry,
        PermissionPolicy(),
    )

    result = executor.execute("secret")

    assert not result.success
    assert result.error == (
        "PermissionError: "
        "tool_not_permitted:secret"
    )


def test_unknown_tool_is_blocked():
    registry = ToolRegistry()

    executor = ToolExecutor(
        registry,
        PermissionPolicy(
            allowed_tools={"missing"},
        ),
    )

    result = executor.execute("missing")

    assert not result.success
    assert result.error == (
        "KeyError: "
        "'tool_not_registered:missing'"
    )
