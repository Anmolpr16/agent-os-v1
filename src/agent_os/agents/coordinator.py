from concurrent.futures import ThreadPoolExecutor
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
        parallel: bool = False,
        max_workers: int | None = None,
    ) -> CoordinationResult:
        if parallel and stop_on_failure:
            raise ValueError(
                "stop_on_failure_not_supported_in_parallel_mode"
            )

        if not parallel:
            results: list[DelegatedResult] = []

            for task in tasks:
                result = self.manager.delegate(agent_name, task)
                results.append(result)

                if stop_on_failure and not result.success:
                    break

            return CoordinationResult(results=results)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(
                executor.map(
                    lambda task: self.manager.delegate(
                        agent_name,
                        task,
                    ),
                    tasks,
                )
            )

        return CoordinationResult(results=results)

    def run_routed(
        self,
        tasks: list[tuple[str, DelegatedTask]],
        parallel: bool = False,
        max_workers: int | None = None,
    ) -> CoordinationResult:
        """Execute tasks using an explicit agent for each task."""

        if not parallel:
            return CoordinationResult(
                results=[
                    self.manager.delegate(agent_name, task)
                    for agent_name, task in tasks
                ]
            )

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(
                executor.map(
                    lambda item: self.manager.delegate(
                        item[0],
                        item[1],
                    ),
                    tasks,
                )
            )

        return CoordinationResult(results=results)
