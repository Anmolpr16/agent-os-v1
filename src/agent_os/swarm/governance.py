"""Bridge swarm council results into the existing human-judgment layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from agent_os.human_judgment import (
    Alternative,
    DecisionProposal,
    Evidence,
    ExpectedOutcome,
    HumanJudgment,
    Risk,
    RiskLevel,
)

from .council import CouncilResult, CouncilVerdict


@dataclass(frozen=True)
class CouncilProposal:
    """A council result paired with the human-judgment proposal it created."""

    council: CouncilResult
    proposal: DecisionProposal


class CouncilGovernanceBridge:
    """Translate council recommendations into existing HumanJudgment proposals.

    This bridge does not approve or execute anything. It creates a structured
    DecisionProposal that must continue through the existing
    HumanJudgmentApproval boundary.
    """

    def __init__(
        self,
        judgment: HumanJudgment,
        *,
        requested_by: str = "swarm_council",
    ) -> None:
        if judgment is None:
            raise ValueError("human_judgment_required")
        if not requested_by.strip():
            raise ValueError("requested_by_required")

        self.judgment = judgment
        self.requested_by = requested_by

    def propose(
        self,
        council: CouncilResult,
        *,
        action: str | None = None,
        rationale: str | None = None,
        alternatives: tuple[Alternative, ...] = (),
        expected_outcomes: tuple[ExpectedOutcome, ...] = (),
        reversibility: str = "unknown",
        metadata: Mapping[str, Any] | None = None,
    ) -> CouncilProposal:
        if not council.task_id.strip():
            raise ValueError("council_task_id_required")

        resolved_action = action or self._default_action(council)
        resolved_rationale = rationale or self._default_rationale(council)

        evidence = tuple(
            Evidence(
                source=f"agent:{agent_id}",
                claim=str(council.answer),
                relevance=1.0,
                confidence=council.confidence,
                metadata={"task_id": council.task_id},
            )
            for agent_id in council.supporting_agents
        )

        risks = self._build_risks(council)

        proposal_metadata = dict(metadata or {})
        proposal_metadata.update(
            {
                "source": "swarm_council",
                "council_verdict": council.verdict.value,
                "supporting_agents": list(council.supporting_agents),
                "dissenting_agents": list(council.dissenting_agents),
                "failed_agents": list(council.failed_agents),
                "council_confidence": council.confidence,
            }
        )

        proposal = self.judgment.propose(
            task_id=council.task_id,
            action=resolved_action,
            rationale=resolved_rationale,
            evidence=evidence,
            risks=risks,
            alternatives=alternatives,
            expected_outcomes=expected_outcomes,
            confidence=council.confidence,
            reversibility=reversibility,
            requested_by=self.requested_by,
            metadata=proposal_metadata,
        )

        return CouncilProposal(council=council, proposal=proposal)

    @staticmethod
    def _default_action(council: CouncilResult) -> str:
        return f"Proceed with council recommendation: {council.answer}"

    @staticmethod
    def _default_rationale(council: CouncilResult) -> str:
        verdict = council.verdict.value
        return (
            f"Swarm council evaluated the task with verdict '{verdict}' "
            f"and confidence {council.confidence:.2f}. "
            f"Supporting agents: {len(council.supporting_agents)}; "
            f"dissenting agents: {len(council.dissenting_agents)}; "
            f"failed agents: {len(council.failed_agents)}."
        )

    @staticmethod
    def _build_risks(council: CouncilResult) -> tuple[Risk, ...]:
        risks: list[Risk] = []

        if council.verdict == CouncilVerdict.DISAGREEMENT:
            risks.append(
                Risk(
                    description="Council members disagree on the recommended answer.",
                    level=RiskLevel.HIGH,
                    likelihood=max(0.5, 1.0 - council.confidence),
                    impact=0.8,
                    mitigation="Require human review of the competing agent conclusions.",
                )
            )

        if council.verdict == CouncilVerdict.INSUFFICIENT_EVIDENCE:
            risks.append(
                Risk(
                    description="The council lacks sufficient successful-agent evidence.",
                    level=RiskLevel.CRITICAL,
                    likelihood=1.0,
                    impact=0.9,
                    mitigation="Obtain additional evidence or agents before execution.",
                )
            )

        if council.failed_agents:
            risks.append(
                Risk(
                    description="One or more delegated agents failed.",
                    level=RiskLevel.MEDIUM,
                    likelihood=min(1.0, len(council.failed_agents) / max(1, len(
                        council.supporting_agents
                        + council.dissenting_agents
                        + council.failed_agents
                    ))),
                    impact=0.5,
                    mitigation="Review failed-agent errors before approving execution.",
                )
            )

        return tuple(risks)
