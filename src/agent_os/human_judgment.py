"""Structured human-judgment and decision-governance layer for Agent OS V2."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable
from uuid import uuid4


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


class DecisionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class Evidence:
    source: str
    claim: str
    relevance: float = 1.0
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.source.strip():
            raise ValueError("evidence_source_required")
        if not self.claim.strip():
            raise ValueError("evidence_claim_required")
        if not 0.0 <= self.relevance <= 1.0:
            raise ValueError("evidence_relevance_invalid")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("evidence_confidence_invalid")


@dataclass(frozen=True)
class Risk:
    description: str
    level: RiskLevel
    likelihood: float = 0.5
    impact: float = 0.5
    mitigation: str = ""

    def __post_init__(self):
        if not self.description.strip():
            raise ValueError("risk_description_required")
        if not 0.0 <= self.likelihood <= 1.0:
            raise ValueError("risk_likelihood_invalid")
        if not 0.0 <= self.impact <= 1.0:
            raise ValueError("risk_impact_invalid")

    @property
    def exposure(self) -> float:
        return self.likelihood * self.impact


@dataclass(frozen=True)
class Alternative:
    name: str
    description: str
    expected_outcome: str = ""
    estimated_value: float | None = None

    def __post_init__(self):
        if not self.name.strip():
            raise ValueError("alternative_name_required")
        if not self.description.strip():
            raise ValueError("alternative_description_required")


@dataclass(frozen=True)
class ExpectedOutcome:
    outcome: str
    probability: float = 0.5
    value: float = 0.0

    def __post_init__(self):
        if not self.outcome.strip():
            raise ValueError("outcome_required")
        if not 0.0 <= self.probability <= 1.0:
            raise ValueError("outcome_probability_invalid")


@dataclass(frozen=True)
class DecisionProposal:
    proposal_id: str
    task_id: str
    action: str
    rationale: str
    evidence: tuple[Evidence, ...] = ()
    risks: tuple[Risk, ...] = ()
    alternatives: tuple[Alternative, ...] = ()
    expected_outcomes: tuple[ExpectedOutcome, ...] = ()
    confidence: float = 0.5
    reversibility: str = "unknown"
    requested_by: str = "agent"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_timestamp)

    def __post_init__(self):
        if not self.proposal_id.strip():
            raise ValueError("proposal_id_required")
        if not self.task_id.strip():
            raise ValueError("task_id_required")
        if not self.action.strip():
            raise ValueError("action_required")
        if not self.rationale.strip():
            raise ValueError("rationale_required")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence_invalid")
        if not self.reversibility.strip():
            raise ValueError("reversibility_required")


@dataclass(frozen=True)
class HumanDecision:
    decision_id: str
    proposal_id: str
    status: DecisionStatus
    decided_by: str
    rationale: str
    conditions: tuple[str, ...] = ()
    timestamp: str = field(default_factory=_timestamp)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.decision_id.strip():
            raise ValueError("decision_id_required")
        if not self.proposal_id.strip():
            raise ValueError("proposal_id_required")
        if not self.decided_by.strip():
            raise ValueError("decided_by_required")
        if not self.rationale.strip():
            raise ValueError("decision_rationale_required")
        if self.status == DecisionStatus.PENDING:
            raise ValueError("final_decision_cannot_be_pending")


@dataclass(frozen=True)
class DecisionRecord:
    proposal: DecisionProposal
    decision: HumanDecision | None = None

    @property
    def status(self) -> DecisionStatus:
        return (
            DecisionStatus.PENDING
            if self.decision is None
            else self.decision.status
        )

    @property
    def resolved(self) -> bool:
        return self.decision is not None


class HumanJudgment:
    """Append-only human decision manager."""

    def __init__(self):
        self._records: dict[str, DecisionRecord] = {}
        self._history: list[HumanDecision] = []

    def propose(
        self,
        *,
        task_id: str,
        action: str,
        rationale: str,
        evidence: Iterable[Evidence] = (),
        risks: Iterable[Risk] = (),
        alternatives: Iterable[Alternative] = (),
        expected_outcomes: Iterable[ExpectedOutcome] = (),
        confidence: float = 0.5,
        reversibility: str = "unknown",
        requested_by: str = "agent",
        metadata: dict[str, Any] | None = None,
    ) -> DecisionProposal:
        proposal = DecisionProposal(
            proposal_id=f"proposal-{uuid4().hex}",
            task_id=task_id,
            action=action,
            rationale=rationale,
            evidence=tuple(evidence),
            risks=tuple(risks),
            alternatives=tuple(alternatives),
            expected_outcomes=tuple(expected_outcomes),
            confidence=confidence,
            reversibility=reversibility,
            requested_by=requested_by,
            metadata=dict(metadata or {}),
        )
        self._records[proposal.proposal_id] = DecisionRecord(proposal)
        return proposal

    def get(self, proposal_id: str) -> DecisionRecord | None:
        return self._records.get(proposal_id)

    def pending(self, task_id: str | None = None) -> list[DecisionRecord]:
        records = [
            r for r in self._records.values()
            if r.decision is None
        ]
        if task_id is not None:
            records = [
                r for r in records
                if r.proposal.task_id == task_id
            ]
        return records

    def decide(
        self,
        *,
        proposal_id: str,
        status: DecisionStatus,
        decided_by: str,
        rationale: str,
        conditions: Iterable[str] = (),
        metadata: dict[str, Any] | None = None,
    ) -> HumanDecision:
        record = self._records.get(proposal_id)

        if record is None:
            raise ValueError("unknown_proposal")

        if record.decision is not None:
            raise ValueError("proposal_already_decided")

        if status == DecisionStatus.PENDING:
            raise ValueError("final_decision_cannot_be_pending")

        decision = HumanDecision(
            decision_id=f"decision-{uuid4().hex}",
            proposal_id=proposal_id,
            status=status,
            decided_by=decided_by,
            rationale=rationale,
            conditions=tuple(c for c in conditions if c.strip()),
            metadata=dict(metadata or {}),
        )

        self._records[proposal_id] = DecisionRecord(
            proposal=record.proposal,
            decision=decision,
        )
        self._history.append(decision)

        return decision

    def approve(
        self,
        *,
        proposal_id: str,
        decided_by: str,
        rationale: str,
        conditions: Iterable[str] = (),
        metadata: dict[str, Any] | None = None,
    ) -> HumanDecision:
        return self.decide(
            proposal_id=proposal_id,
            status=DecisionStatus.APPROVED,
            decided_by=decided_by,
            rationale=rationale,
            conditions=conditions,
            metadata=metadata,
        )

    def reject(
        self,
        *,
        proposal_id: str,
        decided_by: str,
        rationale: str,
        metadata: dict[str, Any] | None = None,
    ) -> HumanDecision:
        return self.decide(
            proposal_id=proposal_id,
            status=DecisionStatus.REJECTED,
            decided_by=decided_by,
            rationale=rationale,
            metadata=metadata,
        )

    def request_revision(
        self,
        *,
        proposal_id: str,
        decided_by: str,
        rationale: str,
        conditions: Iterable[str] = (),
        metadata: dict[str, Any] | None = None,
    ) -> HumanDecision:
        return self.decide(
            proposal_id=proposal_id,
            status=DecisionStatus.REVISION_REQUESTED,
            decided_by=decided_by,
            rationale=rationale,
            conditions=conditions,
            metadata=metadata,
        )

    def history(self, task_id: str | None = None) -> list[HumanDecision]:
        if task_id is None:
            return list(self._history)

        ids = {
            r.proposal.proposal_id
            for r in self._records.values()
            if r.proposal.task_id == task_id
        }

        return [
            d for d in self._history
            if d.proposal_id in ids
        ]

    def can_execute(self, proposal_id: str) -> bool:
        record = self._records.get(proposal_id)
        return bool(
            record
            and record.decision
            and record.decision.status == DecisionStatus.APPROVED
        )

    def require_approval(self, proposal_id: str) -> HumanDecision:
        record = self._records.get(proposal_id)

        if record is None:
            raise ValueError("unknown_proposal")

        if record.decision is None:
            raise PermissionError("human_approval_required")

        if record.decision.status != DecisionStatus.APPROVED:
            raise PermissionError(
                f"proposal_not_approved:{record.decision.status.value}"
            )

        return record.decision

    def risk_summary(self, proposal_id: str) -> dict[str, Any]:
        record = self._records.get(proposal_id)

        if record is None:
            raise ValueError("unknown_proposal")

        risks = record.proposal.risks
        levels = list(RiskLevel)

        max_level = (
            max(risks, key=lambda r: levels.index(r.level)).level.value
            if risks
            else RiskLevel.LOW.value
        )

        exposures = [r.exposure for r in risks]

        return {
            "count": len(risks),
            "max_level": max_level,
            "total_exposure": sum(exposures),
            "highest_exposure": max(exposures, default=0.0),
        }

    def summary(self, proposal_id: str) -> dict[str, Any]:
        record = self._records.get(proposal_id)

        if record is None:
            raise ValueError("unknown_proposal")

        proposal = record.proposal

        return {
            "proposal_id": proposal.proposal_id,
            "task_id": proposal.task_id,
            "action": proposal.action,
            "confidence": proposal.confidence,
            "reversibility": proposal.reversibility,
            "evidence_count": len(proposal.evidence),
            "risk_count": len(proposal.risks),
            "alternative_count": len(proposal.alternatives),
            "expected_outcome_count": len(proposal.expected_outcomes),
            "status": record.status.value,
            "approved": self.can_execute(proposal_id),
            "risk": self.risk_summary(proposal_id),
        }
