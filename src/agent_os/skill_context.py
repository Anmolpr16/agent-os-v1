from __future__ import annotations

from typing import Any


class SkillContextBuilder:
    """Selects bounded, objective-relevant skill instructions for runtime use."""

    def __init__(self, registry, max_items: int = 4):
        self.registry = registry
        self.max_items = max(1, max_items)

    @staticmethod
    def _score(skill, objective: str) -> int:
        objective_terms = {
            term.strip(".,:;!?()[]{}").lower()
            for term in objective.split()
            if len(term.strip(".,:;!?()[]{}")) >= 3
        }

        if not objective_terms:
            return 0

        searchable = " ".join(
            [
                skill.skill_id,
                skill.instructions,
                *skill.examples,
                *skill.constraints,
            ]
        ).lower()

        return sum(1 for term in objective_terms if term in searchable)

    def build(self, objective: str) -> dict[str, Any]:
        if self.registry is None:
            return {}

        candidates = []
        for skill_id, history in self.registry._skills.items():
            if not history:
                continue

            skill = history[-1]
            score = self._score(skill, objective)

            if score > 0:
                candidates.append((score, skill))

        candidates.sort(key=lambda item: (-item[0], item[1].skill_id))

        selected = []
        for score, skill in candidates[: self.max_items]:
            selected.append(
                {
                    "skill_id": skill.skill_id,
                    "version": skill.version,
                    "instructions": skill.instructions,
                    "examples": list(skill.examples),
                    "constraints": list(skill.constraints),
                    "metadata": dict(skill.metadata),
                    "match_score": score,
                }
            )

        if not selected:
            return {}

        return {"skill_context": selected}
