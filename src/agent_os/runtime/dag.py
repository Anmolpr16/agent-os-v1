from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class TaskNode:
    task_id: str
    objective: str
    depends_on: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

class DependencyError(ValueError):
    pass

class TaskGraph:
    def __init__(self, tasks: list[TaskNode] | None = None):
        self._tasks: dict[str, TaskNode] = {}
        for task in tasks or []:
            self._add_unchecked(task)
        self.topological_order()

    def _add_unchecked(self, task: TaskNode) -> None:
        if not task.task_id.strip():
            raise DependencyError("task_id_required")
        if not task.objective.strip():
            raise DependencyError("objective_required")
        if task.task_id in self._tasks:
            raise DependencyError(f"duplicate_task:{task.task_id}")
        self._tasks[task.task_id] = task

    def add(self, task: TaskNode) -> None:
        self._add_unchecked(task)
        try:
            self.topological_order()
        except Exception:
            self._tasks.pop(task.task_id, None)
            raise

    def get(self, task_id: str) -> TaskNode:
        try:
            return self._tasks[task_id]
        except KeyError:
            raise DependencyError(f"task_not_found:{task_id}") from None

    def tasks(self) -> list[TaskNode]:
        return list(self._tasks.values())

    def ready(self, completed: set[str]) -> list[TaskNode]:
        return [
            task for task in self._tasks.values()
            if task.task_id not in completed
            and all(dep in completed for dep in task.depends_on)
        ]

    def topological_order(self) -> list[TaskNode]:
        indegree = {key: 0 for key in self._tasks}
        children = {key: [] for key in self._tasks}
        for task in self._tasks.values():
            for dep in task.depends_on:
                if dep not in self._tasks:
                    raise DependencyError(f"dependency_not_found:{dep}")
                indegree[task.task_id] += 1
                children[dep].append(task.task_id)
        queue = [key for key, value in indegree.items() if value == 0]
        order = []
        while queue:
            current = queue.pop(0)
            order.append(self._tasks[current])
            for child in children[current]:
                indegree[child] -= 1
                if indegree[child] == 0:
                    queue.append(child)
        if len(order) != len(self._tasks):
            raise DependencyError("dependency_cycle_detected")
        return order
