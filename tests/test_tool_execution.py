from agent_os.tools import (
    PermissionPolicy,
    ToolAuditLog,
    ToolExecutor,
    ToolRegistry,
)


def test_successful_execution_is_structured():
    registry = ToolRegistry()

    registry.register(
        name="add",
        description="Add two numbers.",
        handler=lambda a, b: a + b,
    )

    executor = ToolExecutor(
        registry,
        PermissionPolicy(
            allowed_tools={"add"},
        ),
    )

    result = executor.execute(
        "add",
        a=2,
        b=3,
    )

    assert result.success
    assert result.output == 5
    assert result.error is None
    assert result.tool_name == "add"
    assert "a" in result.metadata["arguments"]
    assert "b" in result.metadata["arguments"]


def test_tool_failure_is_captured():
    registry = ToolRegistry()

    def failing_tool():
        raise RuntimeError("controlled failure")

    registry.register(
        name="fail",
        description="Controlled failure.",
        handler=failing_tool,
    )

    executor = ToolExecutor(
        registry,
        PermissionPolicy(
            allowed_tools={"fail"},
        ),
    )

    result = executor.execute("fail")

    assert not result.success
    assert result.output is None
    assert result.error == (
        "RuntimeError: controlled failure"
    )


def test_permission_failure_is_auditable():
    registry = ToolRegistry()

    registry.register(
        name="restricted",
        description="Restricted tool.",
        handler=lambda: "secret",
    )

    executor = ToolExecutor(
        registry,
        PermissionPolicy(),
    )

    result = executor.execute("restricted")

    assert not result.success
    assert result.error == (
        "PermissionError: "
        "tool_not_permitted:restricted"
    )


def test_audit_log():
    registry = ToolRegistry()

    registry.register(
        name="echo",
        description="Echo input.",
        handler=lambda value: value,
    )

    executor = ToolExecutor(
        registry,
        PermissionPolicy(
            allowed_tools={"echo"},
        ),
    )

    audit = ToolAuditLog()

    result = executor.execute(
        "echo",
        value="hello",
    )

    audit.record(result)

    assert len(audit.entries) == 1
    assert audit.last()["tool_name"] == "echo"
    assert audit.last()["success"] is True


def test_tool_executor_retries_recoverable_failure():
    from agent_os.core import RetryPolicy

    attempts = []

    def unstable():
        attempts.append(1)

        if len(attempts) == 1:
            raise TimeoutError("temporary")

        return "success"

    registry = ToolRegistry()
    registry.register(
        name="unstable",
        description="Transiently failing tool.",
        handler=unstable,
    )

    executor = ToolExecutor(
        registry,
        PermissionPolicy(
            allowed_tools={"unstable"}
        ),
        RetryPolicy(max_attempts=3),
    )

    result = executor.execute("unstable")

    assert result.success
    assert result.output == "success"
    assert len(attempts) == 2


def test_tool_executor_does_not_retry_terminal_failure():
    from agent_os.core import RetryPolicy

    attempts = []

    def restricted():
        attempts.append(1)
        raise ValueError("invalid input")

    registry = ToolRegistry()
    registry.register(
        name="invalid",
        description="Terminal failure.",
        handler=restricted,
    )

    executor = ToolExecutor(
        registry,
        PermissionPolicy(
            allowed_tools={"invalid"}
        ),
        RetryPolicy(max_attempts=3),
    )

    result = executor.execute("invalid")

    assert not result.success
    assert result.error == "ValueError: invalid input"
    assert len(attempts) == 1
