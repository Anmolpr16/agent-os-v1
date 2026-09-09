from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Any


class State(str, Enum):
    INTAKE = "intake"
    MEMORY_RETRIEVAL = "memory_retrieval"
    PLANNING = "planning"
    EXECUTION = "execution"
    VERIFICATION = "verification"
    FINALIZATION = "finalization"
    MEMORY_CONSOLIDATION = "memory_consolidation"
    COMPLETE = "complete"


@dataclass
class Task:
    id: str
    objective: str
    constraints: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Run:
    task: Task
    state: State = State.INTAKE
    events: list[dict[str, Any]] = field(default_factory=list)
    result: Any = None

    def transition(self, state: State, **data: Any) -> None:
        self.state = state
        self.events.append({
            "state": state.value,
            **data,
        })


class Orchestrator:
    """
    V1 deterministic control plane.

    The orchestrator owns the lifecycle. Intelligence providers,
    memory retrieval, tools, and specialized agents can be attached
    through handlers without changing the state machine.
    """

    ORDER = [
        State.INTAKE,
        State.MEMORY_RETRIEVAL,
        State.PLANNING,
        State.EXECUTION,
        State.VERIFICATION,
        State.FINALIZATION,
        State.MEMORY_CONSOLIDATION,
        State.COMPLETE,
    ]

    def __init__(
        self,
        handlers: dict[State, Callable[[Run], Any]] | None = None,
    ):
        self.handlers = handlers or {}

    def run(self, task: Task) -> Run:
        run = Run(task=task)

        for state in self.ORDER:
            run.transition(state)

            handler = self.handlers.get(state)

            if handler is not None:
                output = handler(run)

                if output is not None:
                    run.result = output

        return run
