"""Cross-verification and council consensus for agent swarms."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Mapping

from agent_os.runtime.audit import AuditLog

from .core import AgentResult, AgentStatus


class CouncilVerdict(str, Enum):
    """Aggregate outcome produced by cross-verification."""

    CONSENSUS = "consensus"
    DISAGREEMENT = "disagreement"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


@dataclass(frozen=True)
class CouncilResult:
    """Immutable aggregate of independent agent results."""

    task_id: str
    verdict: CouncilVerdict
    answer: Any
    supporting_agents: tuple[str, ...]
    dissenting_agents: tuple[str, ...]
    failed_agents: tuple[str, ...]
    evidence: tuple[str, ...] = ()
    confidence: float = 0.0
    metadata: Mapping[str, Any] = None

    def __post_init__(self) -> None:
        if not self.task_id.strip():
            raise ValueError("task_id must not be empty")

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

        if self.metadata is None:
            object.__setattr__(self, "metadata", {})


AnswerExtractor = Callable[[AgentResult], Any]


class CrossVerifier:
    """Compare independent agent results and produce a council verdict."""

    def __init__(
        self,
        *,
        quorum: int = 2,
        answer_extractor: AnswerExtractor | None = None,
        audit: AuditLog | None = None,
    ) -> None:
        if quorum < 1:
            raise ValueError("quorum must be at least 1")

        self.quorum = quorum
        self.audit = audit
        self.answer_extractor = answer_extractor or (
            lambda result: result.output
        )

    def evaluate(
        self,
        task_id: str,
        results: tuple[AgentResult, ...] | list[AgentResult],
    ) -> CouncilResult:
        """Evaluate independent results for a common parent task."""
        result_list = tuple(results)

        if not result_list:
            council = CouncilResult(
                task_id=task_id,
                verdict=CouncilVerdict.INSUFFICIENT_EVIDENCE,
                answer=None,
                supporting_agents=(),
                dissenting_agents=(),
                failed_agents=(),
            )
            self._audit(council)
            return council

        successful = tuple(
            result
            for result in result_list
            if result.status == AgentStatus.SUCCEEDED
        )
        failed = tuple(
            result
            for result in result_list
            if result.status == AgentStatus.FAILED
        )

        if len(successful) < self.quorum:
            council = CouncilResult(
                task_id=task_id,
                verdict=CouncilVerdict.INSUFFICIENT_EVIDENCE,
                answer=None,
                supporting_agents=tuple(
                    result.agent_id for result in successful
                ),
                dissenting_agents=(),
                failed_agents=tuple(
                    result.agent_id for result in failed
                ),
                evidence=tuple(
                    evidence
                    for result in successful
                    for evidence in result.evidence
                ),
            )
            self._audit(council)
            return council

        grouped: dict[str, list[AgentResult]] = {}

        for result in successful:
            answer = self.answer_extractor(result)
            key = repr(answer)
            grouped.setdefault(key, []).append(result)

        winning_group = max(
            grouped.values(),
            key=lambda group: len(group),
        )

        winning_answer = self.answer_extractor(winning_group[0])

        supporting = tuple(
            result.agent_id
            for result in winning_group
        )

        dissenting = tuple(
            result.agent_id
            for result in successful
            if result.agent_id not in supporting
        )

        verdict = (
            CouncilVerdict.CONSENSUS
            if not dissenting
            else CouncilVerdict.DISAGREEMENT
        )

        confidence = len(winning_group) / len(successful)

        council = CouncilResult(
            task_id=task_id,
            verdict=verdict,
            answer=winning_answer,
            supporting_agents=supporting,
            dissenting_agents=dissenting,
            failed_agents=tuple(
                result.agent_id for result in failed
            ),
            evidence=tuple(
                evidence
                for result in winning_group
                for evidence in result.evidence
            ),
            confidence=confidence,
            metadata={
                "successful_agents": len(successful),
                "failed_agents": len(failed),
                "quorum": self.quorum,
            },
        )
        self._audit(council)
        return council

    def _audit(self, council: CouncilResult) -> None:
        if self.audit is None:
            return

        self.audit.record(
            event="swarm_council_evaluated",
            actor="cross_verifier",
            task_id=council.task_id,
            metadata={
                "verdict": council.verdict.value,
                "confidence": council.confidence,
                "supporting_agents": council.supporting_agents,
                "dissenting_agents": council.dissenting_agents,
                "failed_agents": council.failed_agents,
            },
        )
