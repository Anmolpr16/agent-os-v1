from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from .dag import TaskGraph, TaskNode
from .limits import ExecutionLimits
from .shared_state import MessageBus, SharedState
from .audit import AuditLog
from .observability import RuntimeMetrics

@dataclass(frozen=True)
class GraphExecutionResult:
    completed: list[str]
    failed: list[str]
    outputs: dict[str, str]
    errors: dict[str, str]

class GraphExecutor:
    def __init__(
        self,
        worker,
        limits: ExecutionLimits | None = None,
        state: SharedState | None = None,
        messages: MessageBus | None = None,
        audit: AuditLog | None = None,
        metrics: RuntimeMetrics | None = None,
    ):
        self.worker = worker
        self.limits = limits or ExecutionLimits()
        self.state = state or SharedState()
        self.messages = messages or MessageBus()
        self.audit = audit or AuditLog()
        self.metrics = metrics or RuntimeMetrics()

    def run(self, graph: TaskGraph) -> GraphExecutionResult:
        tasks = graph.topological_order()
        if len(tasks) > self.limits.max_tasks:
            raise ValueError("max_tasks_exceeded")

        completed: set[str] = set()
        failed: list[str] = []
        outputs: dict[str, str] = {}
        errors: dict[str, str] = {}

        while len(completed) + len(failed) < len(tasks):
            ready = graph.ready(completed)
            ready = [task for task in ready
                     if task.task_id not in failed]
            if not ready:
                unresolved = [
                    task.task_id for task in tasks
                    if task.task_id not in completed
                    and task.task_id not in failed
                ]
                for task_id in unresolved:
                    failed.append(task_id)
                    errors[task_id] = "dependency_blocked"
                break

            batch = ready[:self.limits.max_workers]

            def execute(task: TaskNode):
                self.audit.record("task_started", "graph_executor", task.task_id)
                self.metrics.emit("task_started", task.task_id)
                try:
                    result = self.worker(task)
                    output = getattr(result, "output", result)
                    if not isinstance(output, str):
                        output = str(output)
                    self.state.set(task.task_id, output)
                    self.audit.record("task_completed", "graph_executor",
                                      task.task_id)
                    self.metrics.emit("task_completed", task.task_id)
                    return task.task_id, True, output, None
                except Exception as exc:
                    self.audit.record(
                        "task_failed", "graph_executor", task.task_id,
                        {"error": str(exc)},
                    )
                    self.metrics.emit("task_failed", task.task_id)
                    return task.task_id, False, None, str(exc)

            with ThreadPoolExecutor(
                max_workers=min(self.limits.max_workers, len(batch))
            ) as executor:
                results = list(executor.map(execute, batch))

            for task_id, success, output, error in results:
                if success:
                    completed.add(task_id)
                    outputs[task_id] = output
                else:
                    failed.append(task_id)
                    errors[task_id] = error or "execution_failed"

        return GraphExecutionResult(
            completed=sorted(completed),
            failed=failed,
            outputs=outputs,
            errors=errors,
        )
