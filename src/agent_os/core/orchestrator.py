from dataclasses import dataclass, field
from typing import Any

from agent_os.agents import Agent, AgentContext
from agent_os.evaluation import EvaluationRunner
from agent_os.memory import MemoryRetriever, MemoryStore
from agent_os.observability import RunRepository
from agent_os.providers import MockProvider
from agent_os.tools import (
    PermissionPolicy,
    ToolExecutor,
    ToolRegistry,
)

from .state import State, DEFAULT_ORDER
from ..cognition.planner import Plan, Planner
from ..cognition.predictor import Prediction, compare
from ..cognition.reflection import Reflection, reflect
from ..cognition.verifier import Verifier


@dataclass
class Task:
    id: str
    objective: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Run:
    task_id: str
    state: State
    events: list[dict[str, Any]] = field(default_factory=list)
    plan: Plan | None = None
    prediction_error: float | None = None
    reflection: Reflection | None = None
    output: str | None = None
    evaluation_score: float | None = None


class Orchestrator:
    """V1 integrated cognitive control loop."""

    ORDER = DEFAULT_ORDER

    def __init__(
        self,
        memory: MemoryStore | None = None,
        agent: Agent | None = None,
        evaluation: EvaluationRunner | None = None,
        tools: ToolExecutor | None = None,
        run_repository: RunRepository | None = None,
    ):
        self.memory = memory or MemoryStore(":memory:")

        self.retriever = MemoryRetriever(
            self.memory
        )

        self.planner = Planner()
        self.verifier = Verifier()
        self.evaluation = (
            evaluation or EvaluationRunner()
        )

        self.agent = agent or Agent(
            MockProvider(
                response="task completed",
            ),
            tools,
        )

        self.tools = tools
        self.run_repository = run_repository or RunRepository(
            self.memory.conn
        )

    def run(self, task: Task) -> Run:
        run = Run(
            task_id=task.id,
            state=State.INTAKE,
        )

        retrieved = []

        for state in self.ORDER:
            run.state = state

            event = {
                "state": state.value,
                "task_id": task.id,
            }

            if state == State.MEMORY_RETRIEVAL:
                retrieved = self.retriever.search(
                    task.objective,
                    limit=5,
                )

                event["memory"] = {
                    "matches": len(retrieved),
                    "ids": [
                        match.id
                        for match in retrieved
                    ],
                }

            elif state == State.PLANNING:
                run.plan = self.planner.create_plan(
                    task.objective
                )

                validation_errors = (
                    run.plan.validate()
                )

                event["plan"] = {
                    "objective": run.plan.objective,
                    "steps": len(run.plan.steps),
                    "valid": run.plan.is_valid,
                    "validation_errors": (
                        validation_errors
                    ),
                }

            elif state == State.EXECUTION:
                context = AgentContext(
                    task_id=task.id,
                    objective=task.objective,
                    metadata={
                        **task.metadata,
                        "memory_matches": len(
                            retrieved
                        ),
                    },
                )

                agent_result = self.agent.run(
                    context
                )

                run.output = agent_result.output

                prediction = Prediction(
                    action="execute_task",
                    expected="completed",
                    confidence=0.5,
                )

                observed = "completed"

                error = compare(
                    prediction,
                    observed,
                )

                run.prediction_error = (
                    error.magnitude
                )

                event["output"] = run.output
                event["provider"] = (
                    agent_result.provider
                )
                event["model"] = agent_result.model
                event["prediction"] = {
                    "action": prediction.action,
                    "expected": prediction.expected,
                    "confidence": prediction.confidence,
                }
                event["prediction_error"] = (
                    error.magnitude
                )

            elif state == State.VERIFICATION:
                result = self.verifier.verify(
                    run.output,
                    "task execution produced output",
                    lambda value: bool(value),
                )

                event["verification"] = {
                    "passed": result.passed,
                    "criterion": result.criterion,
                    "details": result.details,
                }

            elif state == State.FINALIZATION:
                evaluation = (
                    self.evaluation.evaluate(
                        case_id=task.id,
                        output=run.output or "",
                        required_keywords=[],
                    )
                )

                run.evaluation_score = (
                    evaluation.score
                )

                run.reflection = reflect(
                    outcome="task completed",
                    what_worked=[
                        "planning",
                        "agent execution",
                        "verification",
                    ],
                    lessons=[
                        "evaluate the produced output"
                    ],
                    confidence=0.9,
                )

                event["evaluation_score"] = (
                    run.evaluation_score
                )

                event["reflection"] = {
                    "outcome": (
                        run.reflection.outcome
                    ),
                    "confidence": (
                        run.reflection.confidence
                    ),
                    "has_failures": (
                        run.reflection.has_failures
                    ),
                    "has_lessons": (
                        run.reflection.has_lessons
                    ),
                }

            elif state == State.MEMORY_CONSOLIDATION:
                if run.output:
                    memory_id = (
                        self.memory.add_memory(
                            run.output,
                            kind="episodic",
                            metadata={
                                "task_id": task.id,
                                "evaluation_score": (
                                    run.evaluation_score
                                ),
                            },
                        )
                    )

                    event["memory_id"] = memory_id

            run.events.append(event)
            self.run_repository.record(
                task_id=task.id,
                state=state.value,
                event=event,
            )

        return run
