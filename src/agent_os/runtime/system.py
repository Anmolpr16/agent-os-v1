
from dataclasses import dataclass, field
from typing import Any, Callable

from .audit import AuditLog
from .closed_loop import ClosedLoopRunner, ClosedLoopResult
from .dag import TaskGraph, TaskNode
from .executor import GraphExecutionResult, GraphExecutor
from .limits import ExecutionLimits
from .policy import RuntimePolicy
from .lifecycle import RuntimeLifecycle, check_runtime
from ..memory_graph_store import PersistentMemoryGraph
from ..memory_context import MemoryContextBuilder
from ..skill_registry import SkillRegistry
from ..skill_context import SkillContextBuilder
from .memory_consolidation import MemoryConsolidator
from .observability import RuntimeMetrics
from .replanning import Replanner
from .shared_state import MessageBus, SharedState
from .skill_evolution import SkillEvolution
from ..skill_improvement_loop import SkillImprovementLoop

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
        human_judgment=None,
        memory_graph=None,
        skill_registry=None,
        skill_improvement=None,
        policy: RuntimePolicy | None = None,
    ):
        self.agent = agent
        self.memory = memory
        self.limits = limits or ExecutionLimits()
        self.policy = policy or RuntimePolicy()
        self.state = state or SharedState()
        self.messages = messages or MessageBus()
        self.audit = audit or AuditLog()
        self.metrics = metrics or RuntimeMetrics()
        self.replanner = replanner or Replanner()
        self.lifecycle = RuntimeLifecycle()
        self.memory_graph = memory_graph or PersistentMemoryGraph()
        self.memory_context = MemoryContextBuilder(self.memory_graph)
        self.skill_registry = skill_registry or SkillRegistry()
        self.skill_context = SkillContextBuilder(self.skill_registry)
        self.skill_improvement = skill_improvement
        if self.skill_improvement is not None and not isinstance(
            self.skill_improvement, SkillImprovementLoop
        ):
            raise TypeError(
                "skill_improvement_must_be_skill_improvement_loop"
            )
        if approval is not None:
            self.approval = approval
        elif human_judgment is not None:
            from agent_os.governance import HumanJudgmentApproval
            self.approval = HumanJudgmentApproval(
                human_judgment,
                audit=self.audit,
            )
        else:
            self.approval = None
        self.human_judgment = human_judgment
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
            policy=self.policy,
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
        runtime_metadata = {
            **self.memory_context.build(objective),
            **self.skill_context.build(objective),
        }

        result = loop.run(
            AgentContext(
                task_id=task_id,
                objective=objective,
                metadata=runtime_metadata,
            ),
            required_keywords,
        )

        # Skill improvement is opt-in. A genuine task execution failure
        # may trigger isolated skill learning. Approval outcomes do not.
        if (
            self.skill_improvement is not None
            and not result.success
            and result.approval is None
            and result.error is not None
        ):
            selected = runtime_metadata.get("skill_context", [])

            if selected:
                skill_id = selected[0].get("skill_id")

                if skill_id:
                    def execute_skill(skill_version):
                        metadata = dict(runtime_metadata)
                        metadata["skill_context"] = [{
                            "skill_id": skill_version.skill_id,
                            "version": skill_version.version,
                            "instructions": skill_version.instructions,
                            "examples": list(skill_version.examples),
                            "constraints": list(skill_version.constraints),
                            "metadata": dict(skill_version.metadata),
                            "match_score": selected[0].get("match_score", 0),
                        }]

                        return self.agent.run(
                            AgentContext(
                                task_id=task_id,
                                objective=objective,
                                metadata=metadata,
                            )
                        ).output

                    def evaluate_skill(output):
                        return self.evaluation.evaluate(
                            task_id,
                            output,
                            required_keywords,
                        )

                    try:
                        improvement = self.skill_improvement.improve(
                            skill_id=skill_id,
                            execute=execute_skill,
                            evaluate=evaluate_skill,
                            reason=result.error,
                        )

                        self.audit.record(
                            "skill_improvement_completed",
                            "runtime",
                            task_id,
                            {
                                "skill_id": skill_id,
                                "promoted": improvement.promoted,
                                "rejected": improvement.rejected,
                                "attempts": improvement.attempts,
                                "baseline_score": improvement.baseline_score,
                                "candidate_score": improvement.candidate_score,
                            },
                        )

                        self.lifecycle.emit(
                            "skill_improvement_completed",
                            task_id,
                            {
                                "skill_id": skill_id,
                                "promoted": improvement.promoted,
                                "attempts": improvement.attempts,
                            },
                        )

                    except Exception as exc:
                        # Learning failure must never replace the original
                        # task failure.
                        self.audit.record(
                            "skill_improvement_failed",
                            "runtime",
                            task_id,
                            {
                                "skill_id": skill_id,
                                "error": str(exc),
                            },
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
