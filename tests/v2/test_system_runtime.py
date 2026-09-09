
from agent_os.runtime import AgentOSRuntime, ExecutionLimits, TaskNode

def test_unified_runtime_executes_dependency_graph():
    runtime = AgentOSRuntime(
        limits=ExecutionLimits(max_tasks=10, max_workers=2)
    )
    result = runtime.execute_graph(
        [
            TaskNode("research", "research"),
            TaskNode("draft", "draft", ("research",)),
            TaskNode("verify", "verify", ("draft",)),
        ],
        lambda task: f"output:{task.task_id}",
    )
    assert result.failed == []
    assert result.completed == ["draft", "research", "verify"]
    assert runtime.state.get("verify") == "output:verify"

def test_unified_runtime_exposes_runtime_snapshot():
    runtime = AgentOSRuntime()
    runtime.state.set("x", 1)
    snapshot = runtime.snapshot()
    assert snapshot["state"]["x"] == 1
    assert snapshot["messages"] == 0
    assert snapshot["audit_events"] == 0
    assert "metrics" in snapshot

def test_unified_runtime_records_graph_observability():
    runtime = AgentOSRuntime()
    runtime.execute_graph(
        [TaskNode("a", "a")],
        lambda task: "ok",
    )
    assert runtime.metrics.summary()["events"] >= 2
    assert len(runtime.audit.for_task("a")) >= 2
