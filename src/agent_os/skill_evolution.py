from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SkillRevisionProposal:
    skill_id: str
    base_version: int
    reason: str
    instructions: str
    examples: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    metadata: dict[str, Any] | None = None


class SkillEvolutionEngine:
    """Turns evaluation feedback into versioned skill revision proposals."""

    def __init__(self, registry):
        self.registry = registry

    def propose(
        self,
        skill_id: str,
        feedback: str,
        *,
        instructions: str | None = None,
        examples: list[str] | None = None,
        constraints: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SkillRevisionProposal:
        if not skill_id.strip():
            raise ValueError("skill_id_required")
        if not feedback.strip():
            raise ValueError("feedback_required")

        current = self.registry.latest(skill_id)

        if current is None:
            base_version = 0
            base_instructions = instructions or feedback
            base_examples = tuple(examples or [])
            base_constraints = tuple(constraints or [])
        else:
            base_version = current.version
            base_instructions = instructions or current.instructions
            base_examples = tuple(examples or current.examples)
            base_constraints = tuple(constraints or current.constraints)

        metadata_out = dict(metadata or {})
        metadata_out.update(
            {
                "evolution": True,
                "base_version": base_version,
                "feedback": feedback,
            }
        )

        return SkillRevisionProposal(
            skill_id=skill_id,
            base_version=base_version,
            reason=feedback,
            instructions=base_instructions,
            examples=base_examples,
            constraints=base_constraints,
            metadata=metadata_out,
        )

    def apply(self, proposal: SkillRevisionProposal):
        current = self.registry.latest(proposal.skill_id)

        if current is not None and current.version != proposal.base_version:
            raise ValueError("skill_version_conflict")

        return self.registry.register(
            proposal.skill_id,
            proposal.instructions,
            examples=list(proposal.examples),
            constraints=list(proposal.constraints),
            metadata=dict(proposal.metadata or {}),
        )

    def revise(
        self,
        skill_id: str,
        feedback: str,
        *,
        instructions: str | None = None,
        examples: list[str] | None = None,
        constraints: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        proposal = self.propose(
            skill_id,
            feedback,
            instructions=instructions,
            examples=examples,
            constraints=constraints,
            metadata=metadata,
        )
        return self.apply(proposal)
