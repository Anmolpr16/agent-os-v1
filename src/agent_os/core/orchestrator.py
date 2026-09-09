from dataclasses import dataclass, field
from typing import Any

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


class Orchestrator:
    """V1 deterministic cognitive control loop."""

    ORDER = DEFAULT_ORDER

    def __init__(self):
        self.planner = Planner()
        self.verifier = Verifier()

    def run(self, task: Task) -> Run:
        run = Run(
            task_id=task.id,
            state=State.INTAKE,
        )

        for state in self.ORDER:
            run.state = state

            event = {
                "state": state.value,
                "task_id": task.id,
            }

            if state == State.PLANNING:
                run.plan = self.planner.create_plan(
                    task.objective
                )

                validation_errors = run.plan.validate()

                event["plan"] = {
                    "objective": run.plan.objective,
                    "steps": len(run.plan.steps),
                    "valid": run.plan.is_valid,
                    "validation_errors": validation_errors,
                }

            elif state == State.EXECUTION:
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

                run.prediction_error = error.magnitude

                event["prediction"] = {
                    "action": prediction.action,
                    "expected": prediction.expected,
                    "confidence": prediction.confidence,
                }

                event["prediction_error"] = error.magnitude

            elif state == State.VERIFICATION:
                result = self.verifier.verify(
                    "completed",
                    "task execution completed",
                    lambda value: value == "completed",
                )

                event["verification"] = {
                    "passed": result.passed,
                    "criterion": result.criterion,
                    "details": result.details,
                }

            elif state == State.FINALIZATION:
                run.reflection = reflect(
                    outcome="task completed",
                    what_worked=["deterministic execution"],
                    lessons=["verify the result before finalization"],
                    confidence=0.9,
                )

                event["reflection"] = {
                    "outcome": run.reflection.outcome,
                    "confidence": run.reflection.confidence,
                    "has_failures": run.reflection.has_failures,
                    "has_lessons": run.reflection.has_lessons,
                }

            run.events.append(event)

        return run
