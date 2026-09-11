from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class SkillVersion:
    skill_id: str
    version: int
    instructions: str
    examples: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""


class SkillRegistry:
    def __init__(self, repository=None):
        self._skills: dict[str, list[SkillVersion]] = {}
        self.repository = repository

        if repository is not None:
            repository.load_registry(self)

    def register(
        self,
        skill_id: str,
        instructions: str,
        examples: list[str] | None = None,
        constraints: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SkillVersion:
        if not skill_id.strip():
            raise ValueError("skill_id_required")
        if not instructions.strip():
            raise ValueError("skill_instructions_required")

        history = self._skills.setdefault(skill_id, [])
        version = SkillVersion(
            skill_id=skill_id,
            version=len(history) + 1,
            instructions=instructions,
            examples=tuple(examples or []),
            constraints=tuple(constraints or []),
            metadata=dict(metadata or {}),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        history.append(version)

        if self.repository is not None:
            self.repository.save_version(version)

        return version

    def latest(self, skill_id: str) -> SkillVersion | None:
        history = self._skills.get(skill_id, [])
        return history[-1] if history else None

    def history(self, skill_id: str) -> list[SkillVersion]:
        return list(self._skills.get(skill_id, []))

    def all(self) -> list[SkillVersion]:
        return [
            version
            for history in self._skills.values()
            for version in history
        ]
