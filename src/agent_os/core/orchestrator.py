from dataclasses import dataclass, field
from typing import Any

from agent_os.agents import Agent, AgentContext
from agent_os.evaluation import EvaluationRunner
from agent_os.memory import MemoryRetriever, MemoryStore
from agent_os.observability import RunRepository
from agent_os.skill_runtime import SkillRegistry, SkillSelector
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
    error: str | None = None


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
        skill_registry: SkillRegistry | None = None,
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

        self.skill_registry = (
            skill_registry or SkillRegistry()
        )
        self.skill_selector = SkillSelector(
            self.skill_registry
        )

    def run(self, task: Task) -> Run:
        run = Run(
            task_id=task.id,
            state=State.INTAKE,
        )

        retrieved = []
        selected_skill = None

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

                selected_skill = self.skill_selector.select(
                    task.objective
                )

                event["plan"] = {
                    "objective": run.plan.objective,
                    "steps": len(run.plan.steps),
                    "valid": run.plan.is_valid,
                    "validation_errors": (
                        validation_errors
                    ),
                    "skill": (
                        selected_skill.skill.name
                        if selected_skill
                        else None
                    ),
                    "skill_score": (
                        selected_skill.score
                        if selected_skill
                        else 0.0
                    ),
                }

            elif state == State.EXECUTION:
                execution_metadata = {
                    **task.metadata,
                    "memory_matches": len(
                        retrieved
                    ),
                }

                if selected_skill is not None:
                    execution_metadata["skill"] = {
                        "name": selected_skill.skill.name,
                        "version": selected_skill.skill.version,
                        "objective": selected_skill.skill.objective,
                        "inputs": list(
                            selected_skill.skill.inputs
                        ),
                        "procedure": list(
                            selected_skill.skill.procedure
                        ),
                        "failure_conditions": list(
                            selected_skill.skill.failure_conditions
                        ),
                        "evaluation_rubric": list(
                            selected_skill.skill.evaluation_rubric
                        ),
                        "selection_score": selected_skill.score,
                    }

                context = AgentContext(
                    task_id=task.id,
                    objective=task.objective,
                    metadata=execution_metadata,
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

                tool_calls = agent_result.metadata.get(
                    "tool_calls",
                    [],
                )

                failed_tools = [
                    call
                    for call in tool_calls
                    if not call.get("success", False)
                ]

                if failed_tools:
                    run.error = (
                        "tool_execution_failed:"
                        + failed_tools[0]["tool_name"]
                    )

                    event["tool_failures"] = failed_tools
                    event["error"] = run.error

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

                if not result.passed:
                    run.error = (
                        "verification_failed:"
                        + result.criterion
                    )

                    event["error"] = run.error

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

            if run.error is not None:
                run.state = State.FAILED
                failure_event = {
                    "state": State.FAILED.value,
                    "task_id": task.id,
                    "error": run.error,
                }

                run.events.append(event)
                self.run_repository.record(
                    task_id=task.id,
                    state=state.value,
                    event=event,
                )

                run.events.append(failure_event)
                self.run_repository.record(
                    task_id=task.id,
                    state=State.FAILED.value,
                    event=failure_event,
                )
                break

            run.events.append(event)
            self.run_repository.record(
                task_id=task.id,
                state=state.value,
                event=event,
            )

        if run.state != State.FAILED and run.error is not None:
            run.state = State.FAILED

        return run
