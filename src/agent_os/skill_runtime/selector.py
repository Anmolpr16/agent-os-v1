from dataclasses import dataclass

from .loader import Skill
from .registry import SkillRegistry


@dataclass(frozen=True)
class SkillSelection:
    skill: Skill
    score: float


class SkillSelector:
    """Deterministic V1 skill selector."""

    def __init__(self, registry: SkillRegistry):
        self.registry = registry

    def select(
        self,
        objective: str,
    ) -> SkillSelection | None:
        objective_terms = {
            term.lower()
            for term in objective.split()
            if term.strip()
        }

        best: SkillSelection | None = None

        for name in self.registry.list():
            skill = self.registry.get(name)

            searchable = " ".join(
                [
                    skill.name,
                    skill.objective,
                    *skill.inputs,
                    *skill.procedure,
                ]
            ).lower()

            matched = sum(
                1
                for term in objective_terms
                if term in searchable
            )

            score = (
                matched / len(objective_terms)
                if objective_terms
                else 0.0
            )

            if best is None or score > best.score:
                best = SkillSelection(
                    skill=skill,
                    score=score,
                )

        return best
