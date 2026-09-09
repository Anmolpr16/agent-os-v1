from .base import Agent, AgentContext
from .delegation import DelegatedResult, DelegatedTask


class AgentManager:
    """Registry and lifecycle manager for named agents."""

    def __init__(self):
        self._agents: dict[str, Agent] = {}

    def register(self, name: str, agent: Agent) -> None:
        if not name.strip():
            raise ValueError("agent_name_missing")

        if name in self._agents:
            raise ValueError(
                f"agent_already_registered:{name}"
            )

        self._agents[name] = agent

    def get(self, name: str) -> Agent:
        try:
            return self._agents[name]
        except KeyError:
            raise KeyError(
                f"agent_not_registered:{name}"
            ) from None

    def list(self) -> list[str]:
        return sorted(self._agents)

    def delegate(
        self,
        agent_name: str,
        task: DelegatedTask,
    ) -> DelegatedResult:
        if not agent_name.strip():
            return DelegatedResult(
                task_id=task.task_id,
                success=False,
                error="agent_name_missing",
            )

        if not task.task_id.strip():
            return DelegatedResult(
                task_id=task.task_id,
                success=False,
                error="task_id_missing",
            )

        if not task.objective.strip():
            return DelegatedResult(
                task_id=task.task_id,
                success=False,
                error="objective_missing",
            )

        try:
            agent = self.get(agent_name)
            result = agent.run(
                AgentContext(
                    task_id=task.task_id,
                    objective=task.objective,
                    metadata=task.metadata,
                )
            )
        except KeyError:
            return DelegatedResult(
                task_id=task.task_id,
                success=False,
                error=f"agent_not_registered:{agent_name}",
            )
        except Exception as exc:
            return DelegatedResult(
                task_id=task.task_id,
                success=False,
                error=str(exc),
            )

        return DelegatedResult(
            task_id=task.task_id,
            success=True,
            output=result.output,
        )
