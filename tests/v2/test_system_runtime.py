
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

def test_runtime_can_trigger_opt_in_skill_improvement():
    from agent_os.agents import AgentContext
    from agent_os.evaluation import EvaluationRunner
    from agent_os.runtime.system import AgentOSRuntime
    from agent_os.skill_improvement_loop import SkillImprovementLoop
    from agent_os.skill_registry import SkillRegistry

    class FakeAgent:
        def __init__(self):
            self.calls = []

        def run(self, context):
            self.calls.append(context.metadata)
            skill = context.metadata["skill_context"][0]
            version = skill["version"]
            if version == 1:
                return type("Result", (), {"output": "weak"})()
            return type("Result", (), {"output": "answer target"})()

    registry = SkillRegistry()
    registry.register("research", "Produce a researched answer.")

    agent = FakeAgent()
    runtime = AgentOSRuntime(
        agent=agent,
        evaluation=EvaluationRunner(),
        skill_registry=registry,
        skill_improvement=SkillImprovementLoop(
            registry,
            max_attempts=1,
        ),
    )

    result = runtime.execute_closed_loop(
        "skill-learning-1",
        "research answer",
        ["target"],
    )

    assert not result.success
    assert registry.latest("research").version == 2
    assert any(
        event.event == "skill_improvement_completed"
        for event in runtime.audit.all()
    )


def test_runtime_skill_improvement_failure_does_not_replace_task_failure():
    from agent_os.evaluation import EvaluationRunner
    from agent_os.runtime.system import AgentOSRuntime
    from agent_os.skill_improvement_loop import SkillImprovementLoop
    from agent_os.skill_registry import SkillRegistry

    class FailingAgent:
        def run(self, context):
            raise RuntimeError("agent_failure")

    registry = SkillRegistry()
    registry.register("research", "Produce a researched answer.")

    runtime = AgentOSRuntime(
        agent=FailingAgent(),
        evaluation=EvaluationRunner(),
        skill_registry=registry,
        skill_improvement=SkillImprovementLoop(
            registry,
            max_attempts=1,
        ),
    )

    result = runtime.execute_closed_loop(
        "skill-learning-2",
        "research answer",
        ["target"],
    )

    assert not result.success
    assert result.error == "agent_failure"
    assert registry.latest("research").version == 1


def test_runtime_without_skill_learning_preserves_existing_behavior():
    from agent_os.runtime.system import AgentOSRuntime

    assert AgentOSRuntime().skill_improvement is None


if __name__ == "__main__":
    raise SystemExit("pytest-only module")
