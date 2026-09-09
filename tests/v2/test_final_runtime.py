
from agent_os.runtime import (
    AuditLog,
    ExecutionLimits,
    GraphExecutor,
    Replanner,
    SharedState,
    TaskGraph,
    TaskNode,
)
from agent_os.api.health import health
from agent_os.governance import ApprovalGate, ApprovalRequest, ApprovalStatus
from agent_os.governance.pipeline import GovernancePipeline
from agent_os.security import PermissionPolicy

def test_graph_orders_dependencies():
    graph = TaskGraph([
        TaskNode("b", "B", ("a",)),
        TaskNode("a", "A"),
    ])
    assert [x.task_id for x in graph.topological_order()] == ["a", "b"]

def test_graph_detects_cycles():
    import pytest
    with pytest.raises(ValueError):
        TaskGraph([
            TaskNode("a", "A", ("b",)),
            TaskNode("b", "B", ("a",)),
        ])

def test_graph_executor_runs_dependencies():
    state = SharedState()
    graph = TaskGraph([
        TaskNode("a", "A"),
        TaskNode("b", "B", ("a",)),
        TaskNode("c", "C", ("a",)),
    ])
    result = GraphExecutor(
        lambda task: f"done:{task.task_id}",
        ExecutionLimits(max_tasks=10, max_workers=2),
        state=state,
    ).run(graph)
    assert result.failed == []
    assert set(result.completed) == {"a", "b", "c"}
    assert state.get("a") == "done:a"

def test_audit_and_metrics_are_recorded():
    from agent_os.runtime import RuntimeMetrics
    audit = AuditLog()
    metrics = RuntimeMetrics()
    audit.record("started", "test", "t1")
    metrics.emit("started", "t1")
    assert len(audit.for_task("t1")) == 1
    assert metrics.summary()["events"] == 1

def test_replanner():
    replanner = Replanner(lambda output, error: "fix:" + error)
    decision = replanner.decide("bad", "failed")
    assert decision.required is True
    assert decision.objective == "fix:failed"

def test_governance_pipeline():
    pipeline = GovernancePipeline(
        PermissionPolicy({"execute"}),
        ApprovalGate(lambda request: __import__(
            "agent_os.governance", fromlist=["ApprovalDecision"]
        ).ApprovalDecision(ApprovalStatus.APPROVED, "approved")),
    )
    request = ApprovalRequest("t1", "run", "output")
    result = pipeline.authorize("agent", "execute", "task:t1", request)
    assert result.allowed is True
    assert result.approval == ApprovalStatus.APPROVED

def test_health():
    result = health()
    assert result.status == "ok"
    assert result.version == "2.0.0"
