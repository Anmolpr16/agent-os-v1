from pathlib import Path

from agent_os.integration.external import IntegrationToolAdapter
from agent_os.integration.mock import MockIntegration
from agent_os.tools import PermissionPolicy, ToolAuditLog, ToolExecutor, ToolRegistry


def test_integration_adapter_uses_normal_tool_boundary():
    integration = MockIntegration(
        responses={"lookup": {"value": 42}}
    )

    adapter = IntegrationToolAdapter(
        integration,
        operation="lookup",
    )

    registry = ToolRegistry()
    tool = adapter.as_tool()
    registry.register(
        name=tool.name,
        description=tool.description,
        handler=tool.handler,
    )

    audit = ToolAuditLog()
    executor = ToolExecutor(
        registry,
        PermissionPolicy(allowed_tools={tool.name}),
        audit=audit,
    )

    result = executor.execute(tool.name, key="answer")

    assert result.success is True
    assert result.output == {"value": 42}
    assert len(integration.calls) == 1
    assert integration.calls[0].operation == "lookup"
    assert audit.last()["success"] is True


def test_integration_failure_is_captured_and_audited():
    integration = MockIntegration()
    adapter = IntegrationToolAdapter(
        integration,
        operation="missing",
    )

    registry = ToolRegistry()
    tool = adapter.as_tool()
    registry.register(tool.name, tool.description, tool.handler)

    audit = ToolAuditLog()
    executor = ToolExecutor(
        registry,
        PermissionPolicy(allowed_tools={tool.name}),
        audit=audit,
    )

    result = executor.execute(tool.name)

    assert result.success is False
    assert "integration_operation_failed" in result.error
    assert audit.last()["success"] is False


def test_tool_executor_can_own_audit_boundary():
    registry = ToolRegistry()
    registry.register(
        "echo",
        "Echo",
        lambda value: value,
    )

    audit = ToolAuditLog()
    executor = ToolExecutor(
        registry,
        PermissionPolicy(allowed_tools={"echo"}),
        audit=audit,
    )

    result = executor.execute("echo", value="ok")

    assert result.success is True
    assert len(audit.entries) == 1
    assert audit.last()["tool_name"] == "echo"
