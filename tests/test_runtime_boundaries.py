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

    assert executor.execute(
        "add",
        a=2,
        b=3,
    ) == 5


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

    try:
        executor.execute("secret")
    except PermissionError as exc:
        assert str(exc) == "tool_not_permitted:secret"
    else:
        raise AssertionError(
            "unpermitted tool executed"
        )


def test_unknown_tool_is_blocked():
    registry = ToolRegistry()

    executor = ToolExecutor(
        registry,
        PermissionPolicy(
            allowed_tools={"missing"},
        ),
    )

    try:
        executor.execute("missing")
    except KeyError as exc:
        assert str(exc) == (
            "'tool_not_registered:missing'"
        )
    else:
        raise AssertionError(
            "unknown tool executed"
        )
