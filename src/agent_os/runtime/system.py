
from dataclasses import dataclass, field
from typing import Any, Callable

from .audit import AuditLog
from .closed_loop import ClosedLoopRunner, ClosedLoopResult
from .dag import TaskGraph, TaskNode
from .executor import GraphExecutionResult, GraphExecutor
from .limits import ExecutionLimits
from .lifecycle import RuntimeLifecycle, check_runtime
from .memory_consolidation import MemoryConsolidator
from .observability import RuntimeMetrics
from .replanning import Replanner
from .shared_state import MessageBus, SharedState
from .skill_evolution import SkillEvolution

@dataclass(frozen=True)
class SystemResult:
    success: bool
    task_id: str
    output: str | None
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

class AgentOSRuntime:
    def __init__(
        self,
        agent=None,
        memory=None,
        limits: ExecutionLimits | None = None,
        state: SharedState | None = None,
        messages: MessageBus | None = None,
        audit: AuditLog | None = None,
        metrics: RuntimeMetrics | None = None,
        replanner: Replanner | None = None,
        approval=None,
        evaluation=None,
    ):
        self.agent = agent
        self.memory = memory
        self.limits = limits or ExecutionLimits()
        self.state = state or SharedState()
        self.messages = messages or MessageBus()
        self.audit = audit or AuditLog()
        self.metrics = metrics or RuntimeMetrics()
        self.replanner = replanner or Replanner()
        self.lifecycle = RuntimeLifecycle()
        self.approval = approval
        self.evaluation = evaluation

    def execute_graph(
        self,
        tasks: list[TaskNode],
        worker: Callable[[TaskNode], Any],
    ) -> GraphExecutionResult:
        graph = TaskGraph(tasks)
        executor = GraphExecutor(
            worker=worker,
            limits=self.limits,
            state=self.state,
            messages=self.messages,
            audit=self.audit,
            metrics=self.metrics,
        )
        return executor.run(graph)

    def execute_closed_loop(
        self,
        task_id: str,
        objective: str,
        required_keywords: list[str],
    ) -> ClosedLoopResult:
        if self.agent is None:
            raise RuntimeError("agent_required")

        from agent_os.agents import AgentContext

        loop = ClosedLoopRunner(
            agent=self.agent,
            evaluation=self.evaluation,
            replanner=self.replanner,
            approval=self.approval,
            state=self.state,
            max_attempts=self.limits.max_tasks
            if self.limits.max_tasks < 100
            else 3,
        )
        self.audit.record("closed_loop_started", "runtime", task_id)
        self.lifecycle.emit("closed_loop_started", task_id)
        result = loop.run(
            AgentContext(task_id=task_id, objective=objective),
            required_keywords,
        )
        self.audit.record(
            "closed_loop_completed" if result.success else "closed_loop_failed",
            "runtime",
            task_id,
            {"attempts": len(result.attempts)},
        )
        event_name = (
            "closed_loop_completed"
            if result.success
            else "closed_loop_failed"
        )
        self.metrics.emit(
            event_name,
            task_id,
            {"attempts": len(result.attempts)},
        )
        self.lifecycle.emit(
            event_name,
            task_id,
            {
                "attempts": len(result.attempts),
                "error": result.error,
            },
        )
        return result

    def consolidate(
        self,
        task_id: str,
        output: str,
        metadata: dict[str, Any] | None = None,
    ):
        if self.memory is None:
            raise RuntimeError("memory_store_required")
        return MemoryConsolidator(self.memory).consolidate(
            task_id,
            output,
            metadata,
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "state": self.state.snapshot(),
            "messages": len(self.messages.all()),
            "audit_events": len(self.audit.all()),
            "metrics": self.metrics.summary(),
        }

    def health(self):
        return check_runtime(self)
