from dataclasses import dataclass, field


@dataclass
class PlanStep:
    """One executable step in a task plan."""

    id: str
    description: str
    dependencies: list[str] = field(default_factory=list)


@dataclass
class Plan:
    """Structured representation of an agent plan."""

    objective: str
    steps: list[PlanStep] = field(default_factory=list)

    def add_step(
        self,
        step_id: str,
        description: str,
        dependencies: list[str] | None = None,
    ) -> PlanStep:
        step = PlanStep(
            id=step_id,
            description=description,
            dependencies=dependencies or [],
        )

        self.steps.append(step)
        return step

    def validate(self) -> list[str]:
        """Return structural validation errors."""

        errors = []
        ids = {step.id for step in self.steps}

        for step in self.steps:
            if not step.id:
                errors.append("step_id_missing")

            if not step.description.strip():
                errors.append(f"{step.id}:description_missing")

            for dependency in step.dependencies:
                if dependency not in ids:
                    errors.append(
                        f"{step.id}:unknown_dependency:{dependency}"
                    )

        return errors

    @property
    def is_valid(self) -> bool:
        return not self.validate()


class Planner:
    """Deterministic V1 task decomposition engine."""

    def create_plan(self, objective: str) -> Plan:
        """Create a minimal structured plan from an objective."""

        objective = objective.strip()

        plan = Plan(objective=objective)

        plan.add_step(
            "understand",
            f"Understand the objective: {objective}",
        )

        plan.add_step(
            "execute",
            f"Execute the objective: {objective}",
            dependencies=["understand"],
        )

        plan.add_step(
            "verify",
            "Verify that the objective was completed.",
            dependencies=["execute"],
        )

        return plan
