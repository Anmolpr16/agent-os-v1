from dataclasses import dataclass

from .delegation import DelegatedResult, DelegatedTask
from .manager import AgentManager


@dataclass(frozen=True)
class CoordinationResult:
    results: list[DelegatedResult]

    @property
    def success(self) -> bool:
        return all(result.success for result in self.results)


class AgentCoordinator:
    """Deterministic coordinator for multiple delegated agent tasks."""

    def __init__(self, manager: AgentManager):
        self.manager = manager

    def run(
        self,
        agent_name: str,
        tasks: list[DelegatedTask],
        stop_on_failure: bool = False,
    ) -> CoordinationResult:
        results: list[DelegatedResult] = []

        for task in tasks:
            result = self.manager.delegate(agent_name, task)
            results.append(result)

            if stop_on_failure and not result.success:
                break

        return CoordinationResult(results=results)
