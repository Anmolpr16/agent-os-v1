"""Deterministic primitives for controlled multi-agent coordination."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping

from agent_os.runtime.audit import AuditLog
from uuid import uuid4


class AgentStatus(str, Enum):
    """Lifecycle status for a delegated agent task."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True)
class AgentSpec:
    """Identity and specialization of an agent."""

    agent_id: str
    role: str
    capabilities: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.agent_id.strip():
            raise ValueError("agent_id must not be empty")
        if not self.role.strip():
            raise ValueError("role must not be empty")

        normalized = tuple(
            capability.strip()
            for capability in self.capabilities
            if capability.strip()
        )
        object.__setattr__(self, "capabilities", normalized)


@dataclass(frozen=True)
class AgentTask:
    """A unit of work delegated to one specialized agent."""

    task_id: str
    objective: str
    assigned_agent: str
    constraints: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.task_id.strip():
            raise ValueError("task_id must not be empty")
        if not self.objective.strip():
            raise ValueError("objective must not be empty")
        if not self.assigned_agent.strip():
            raise ValueError("assigned_agent must not be empty")


@dataclass(frozen=True)
class AgentResult:
    """Immutable result envelope returned by an agent."""

    task_id: str
    agent_id: str
    status: AgentStatus
    output: Any = None
    evidence: tuple[str, ...] = ()
    error: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.task_id.strip():
            raise ValueError("task_id must not be empty")
        if not self.agent_id.strip():
            raise ValueError("agent_id must not be empty")

        if self.status == AgentStatus.FAILED and not self.error:
            raise ValueError("failed results require an error")

        if self.status != AgentStatus.FAILED and self.error is not None:
            raise ValueError("only failed results may contain an error")


AgentHandler = Callable[[AgentTask], AgentResult | Any]


class AgentCoordinator:
    """Controlled registry and execution coordinator for specialized agents."""

    def __init__(self, audit: AuditLog | None = None) -> None:
        self.audit = audit
        self._agents: dict[str, AgentSpec] = {}
        self._handlers: dict[str, AgentHandler] = {}
        self._tasks: dict[str, AgentTask] = {}
        self._results: dict[str, AgentResult] = {}

    def register(
        self,
        agent: AgentSpec,
        handler: AgentHandler,
    ) -> None:
        if not callable(handler):
            raise TypeError("handler must be callable")
        if agent.agent_id in self._agents:
            raise ValueError(f"agent already registered: {agent.agent_id}")

        self._agents[agent.agent_id] = agent
        self._handlers[agent.agent_id] = handler

    def get_agent(self, agent_id: str) -> AgentSpec | None:
        return self._agents.get(agent_id)

    def agents(self) -> tuple[AgentSpec, ...]:
        return tuple(self._agents.values())

    def delegate(
        self,
        objective: str,
        agent_id: str,
        *,
        constraints: tuple[str, ...] = (),
        metadata: Mapping[str, Any] | None = None,
    ) -> AgentTask:
        if not objective.strip():
            raise ValueError("objective must not be empty")

        if agent_id not in self._agents:
            raise KeyError(f"unknown agent: {agent_id}")

        task = AgentTask(
            task_id=str(uuid4()),
            objective=objective,
            assigned_agent=agent_id,
            constraints=constraints,
            metadata=dict(metadata or {}),
        )
        self._tasks[task.task_id] = task

        if self.audit is not None:
            self.audit.record(
                event="swarm_task_delegated",
                actor="agent_coordinator",
                task_id=task.task_id,
                metadata={
                    "assigned_agent": task.assigned_agent,
                    "objective": task.objective,
                },
            )

        return task

    def execute(self, task: AgentTask) -> AgentResult:
        if task.task_id not in self._tasks:
            self._tasks[task.task_id] = task

        if task.assigned_agent not in self._handlers:
            raise KeyError(f"unknown agent: {task.assigned_agent}")

        handler = self._handlers[task.assigned_agent]

        try:
            result = handler(task)

            if isinstance(result, AgentResult):
                if result.task_id != task.task_id:
                    raise ValueError("handler returned result for a different task")
                if result.agent_id != task.assigned_agent:
                    raise ValueError("handler returned result for a different agent")
            else:
                result = AgentResult(
                    task_id=task.task_id,
                    agent_id=task.assigned_agent,
                    status=AgentStatus.SUCCEEDED,
                    output=result,
                )

        except Exception as exc:
            result = AgentResult(
                task_id=task.task_id,
                agent_id=task.assigned_agent,
                status=AgentStatus.FAILED,
                error=f"{type(exc).__name__}: {exc}",
            )

        self._results[task.task_id] = result

        if self.audit is not None:
            self.audit.record(
                event="swarm_task_completed"
                if result.status == AgentStatus.SUCCEEDED
                else "swarm_task_failed",
                actor=result.agent_id,
                task_id=task.task_id,
                metadata={
                    "status": result.status.value,
                    "error": result.error,
                },
            )

        return result

    def execute_many(
        self,
        tasks: tuple[AgentTask, ...] | list[AgentTask],
        *,
        max_workers: int | None = None,
    ) -> tuple[AgentResult, ...]:
        """Execute independent delegated tasks concurrently.

        Each task is isolated: an agent exception becomes a FAILED result
        without cancelling sibling tasks.
        """
        task_list = tuple(tasks)

        if not task_list:
            return ()

        seen: set[str] = set()
        for task in task_list:
            if task.task_id in seen:
                raise ValueError(f"duplicate task: {task.task_id}")
            seen.add(task.task_id)

            if task.assigned_agent not in self._handlers:
                raise KeyError(f"unknown agent: {task.assigned_agent}")

            if task.task_id not in self._tasks:
                self._tasks[task.task_id] = task

        results: dict[str, AgentResult] = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.execute, task): task
                for task in task_list
            }

            for future in as_completed(futures):
                task = futures[future]
                try:
                    results[task.task_id] = future.result()
                except Exception as exc:
                    # execute() normally isolates handler failures. This
                    # protects the batch even if coordinator infrastructure
                    # itself raises unexpectedly.
                    result = AgentResult(
                        task_id=task.task_id,
                        agent_id=task.assigned_agent,
                        status=AgentStatus.FAILED,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                    self._results[task.task_id] = result
                    results[task.task_id] = result

        # Preserve caller order rather than completion order.
        return tuple(results[task.task_id] for task in task_list)

    def result(self, task_id: str) -> AgentResult | None:
        return self._results.get(task_id)

    def pending(self) -> tuple[AgentTask, ...]:
        return tuple(
            task
            for task in self._tasks.values()
            if task.task_id not in self._results
        )

    def results(self) -> tuple[AgentResult, ...]:
        return tuple(self._results.values())
