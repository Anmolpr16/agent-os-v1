from dataclasses import dataclass, field
from typing import Callable

@dataclass(frozen=True)
class SkillRevision:
    version: int
    content: str
    score: float
    passed: bool
    feedback: tuple[str, ...] = ()

@dataclass
class SkillEvolutionResult:
    active_version: int
    revisions: list[SkillRevision] = field(default_factory=list)

class SkillEvolution:
    def __init__(
        self,
        initial_skill: str,
        proposer: Callable[[str, list[str]], str] | None = None,
        threshold: float = 1.0,
    ):
        if not initial_skill.strip():
            raise ValueError("initial_skill_required")
        if threshold <= 0:
            raise ValueError("threshold_must_be_positive")
        self._active = initial_skill
        self._version = 1
        self.proposer = proposer
        self.threshold = threshold
        self.revisions = [
            SkillRevision(1, initial_skill, threshold, True, ())
        ]

    @property
    def active(self) -> str:
        return self._active

    @property
    def version(self) -> int:
        return self._version

    def propose(self, feedback: list[str]) -> str:
        if self.proposer is None:
            raise RuntimeError("skill_revision_strategy_unavailable")
        proposal = self.proposer(self._active, feedback)
        if not isinstance(proposal, str) or not proposal.strip():
            raise ValueError("skill_revision_empty")
        return proposal

    def evaluate_revision(
        self,
        content: str,
        score: float,
        feedback: list[str] | None = None,
    ) -> SkillRevision:
        if not content.strip():
            raise ValueError("skill_revision_empty")
        revision = SkillRevision(
            self._version + 1,
            content,
            score,
            score >= self.threshold,
            tuple(feedback or ()),
        )
        self.revisions.append(revision)
        if revision.passed:
            self._version = revision.version
            self._active = revision.content
        return revision
