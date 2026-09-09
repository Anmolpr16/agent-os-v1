from .loader import Skill


class SkillRegistry:
    """Explicit registry of available skills."""

    def __init__(self):
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        if not skill.name.strip():
            raise ValueError(
                "skill_name_missing"
            )

        if skill.name in self._skills:
            raise ValueError(
                f"skill_already_registered:{skill.name}"
            )

        self._skills[skill.name] = skill

    def get(self, name: str) -> Skill:
        try:
            return self._skills[name]
        except KeyError:
            raise KeyError(
                f"skill_not_registered:{name}"
            ) from None

    def list(self) -> list[str]:
        return sorted(self._skills)
