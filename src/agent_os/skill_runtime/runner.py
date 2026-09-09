from dataclasses import dataclass, field

from .loader import Skill


@dataclass(frozen=True)
class SkillStepResult:
    index: int
    description: str
    status: str
    error: str | None = None


@dataclass
class SkillRunResult:
    skill_name: str
    skill_version: str
    status: str
    steps: list[SkillStepResult] = field(
        default_factory=list
    )

    @property
    def passed(self) -> bool:
        return self.status == "completed"


class SkillRunner:
    """Deterministic V1 runner for declarative skill procedures."""

    def run(self, skill: Skill) -> SkillRunResult:
        steps = []

        for index, description in enumerate(
            skill.procedure,
            start=1,
        ):
            if not description.strip():
                steps.append(
                    SkillStepResult(
                        index=index,
                        description=description,
                        status="failed",
                        error="empty_procedure_step",
                    )
                )

                return SkillRunResult(
                    skill_name=skill.name,
                    skill_version=skill.version,
                    status="failed",
                    steps=steps,
                )

            steps.append(
                SkillStepResult(
                    index=index,
                    description=description,
                    status="acknowledged",
                )
            )

        return SkillRunResult(
            skill_name=skill.name,
            skill_version=skill.version,
            status="completed",
            steps=steps,
        )
