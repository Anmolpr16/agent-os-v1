from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from typing import Any

from agent_os.human_judgment import (
    Alternative,
    DecisionProposal,
    DecisionRecord,
    DecisionStatus,
    Evidence,
    ExpectedOutcome,
    HumanDecision,
    HumanJudgment,
    Risk,
    RiskLevel,
)
from agent_os.storage import Database


def _proposal_to_dict(proposal: DecisionProposal) -> dict[str, Any]:
    return {
        "proposal_id": proposal.proposal_id,
        "task_id": proposal.task_id,
        "action": proposal.action,
        "rationale": proposal.rationale,
        "evidence": [asdict(item) for item in proposal.evidence],
        "risks": [
            {
                **asdict(item),
                "level": item.level.value,
            }
            for item in proposal.risks
        ],
        "alternatives": [asdict(item) for item in proposal.alternatives],
        "expected_outcomes": [asdict(item) for item in proposal.expected_outcomes],
        "confidence": proposal.confidence,
        "reversibility": proposal.reversibility,
        "requested_by": proposal.requested_by,
        "metadata": proposal.metadata,
        "created_at": proposal.created_at,
    }


def _decision_to_dict(decision: HumanDecision) -> dict[str, Any]:
    return {
        "decision_id": decision.decision_id,
        "proposal_id": decision.proposal_id,
        "status": decision.status.value,
        "decided_by": decision.decided_by,
        "rationale": decision.rationale,
        "conditions": list(decision.conditions),
        "timestamp": decision.timestamp,
        "metadata": decision.metadata,
    }


def _proposal_from_dict(data: dict[str, Any]) -> DecisionProposal:
    return DecisionProposal(
        proposal_id=data["proposal_id"],
        task_id=data["task_id"],
        action=data["action"],
        rationale=data["rationale"],
        evidence=tuple(
            Evidence(**item) for item in data.get("evidence", [])
        ),
        risks=tuple(
            Risk(
                description=item["description"],
                level=RiskLevel(item["level"]),
                likelihood=item.get("likelihood", 0.5),
                impact=item.get("impact", 0.5),
                mitigation=item.get("mitigation", ""),
            )
            for item in data.get("risks", [])
        ),
        alternatives=tuple(
            Alternative(**item)
            for item in data.get("alternatives", [])
        ),
        expected_outcomes=tuple(
            ExpectedOutcome(**item)
            for item in data.get("expected_outcomes", [])
        ),
        confidence=data.get("confidence", 0.5),
        reversibility=data.get("reversibility", "unknown"),
        requested_by=data.get("requested_by", "agent"),
        metadata=data.get("metadata", {}),
        created_at=data["created_at"],
    )


def _decision_from_dict(data: dict[str, Any]) -> HumanDecision:
    return HumanDecision(
        decision_id=data["decision_id"],
        proposal_id=data["proposal_id"],
        status=DecisionStatus(data["status"]),
        decided_by=data["decided_by"],
        rationale=data["rationale"],
        conditions=tuple(data.get("conditions", [])),
        timestamp=data["timestamp"],
        metadata=data.get("metadata", {}),
    )


class GovernanceRepository:
    """Persist and restore HumanJudgment state in SQLite."""

    def __init__(
        self,
        connection: sqlite3.Connection | None = None,
        database: Database | None = None,
    ):
        if connection is None and database is None:
            raise ValueError("connection or database required")
        if connection is not None and database is not None:
            raise ValueError(
                "provide either connection or database, not both"
            )

        self.database = database
        self.conn = database.conn if database is not None else connection

        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS governance_proposals (
                proposal_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                status TEXT NOT NULL,
                proposal_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS governance_decisions (
                decision_id TEXT PRIMARY KEY,
                proposal_id TEXT NOT NULL,
                status TEXT NOT NULL,
                decision_json TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (proposal_id)
                    REFERENCES governance_proposals(proposal_id)
            )
            """
        )
        self.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_governance_proposals_task
            ON governance_proposals(task_id)
            """
        )
        self.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_governance_proposals_status
            ON governance_proposals(status)
            """
        )
        self.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_governance_decisions_proposal
            ON governance_decisions(proposal_id)
            """
        )
        self.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_governance_decisions_timestamp
            ON governance_decisions(timestamp)
            """
        )
        self.conn.commit()

    def save_proposal(self, proposal: DecisionProposal) -> None:
        payload = _proposal_to_dict(proposal)
        self.conn.execute(
            """
            INSERT OR REPLACE INTO governance_proposals
                (proposal_id, task_id, status, proposal_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                proposal.proposal_id,
                proposal.task_id,
                DecisionStatus.PENDING.value,
                json.dumps(payload, sort_keys=True, default=str),
                proposal.created_at,
            ),
        )
        self.conn.commit()

    def save_decision(self, decision: HumanDecision) -> None:
        payload = _decision_to_dict(decision)
        self.conn.execute(
            """
            INSERT INTO governance_decisions
                (decision_id, proposal_id, status, decision_json, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                decision.decision_id,
                decision.proposal_id,
                decision.status.value,
                json.dumps(payload, sort_keys=True, default=str),
                decision.timestamp,
            ),
        )
        self.conn.execute(
            """
            UPDATE governance_proposals
            SET status = ?
            WHERE proposal_id = ?
            """,
            (decision.status.value, decision.proposal_id),
        )
        self.conn.commit()

    def get(self, proposal_id: str) -> DecisionRecord | None:
        row = self.conn.execute(
            """
            SELECT proposal_json
            FROM governance_proposals
            WHERE proposal_id = ?
            """,
            (proposal_id,),
        ).fetchone()

        if row is None:
            return None

        proposal = _proposal_from_dict(json.loads(row["proposal_json"]))

        decision_row = self.conn.execute(
            """
            SELECT decision_json
            FROM governance_decisions
            WHERE proposal_id = ?
            ORDER BY timestamp DESC, rowid DESC
            LIMIT 1
            """,
            (proposal_id,),
        ).fetchone()

        decision = (
            _decision_from_dict(json.loads(decision_row["decision_json"]))
            if decision_row is not None
            else None
        )

        return DecisionRecord(proposal=proposal, decision=decision)

    def list_task(self, task_id: str) -> list[DecisionRecord]:
        rows = self.conn.execute(
            """
            SELECT proposal_id
            FROM governance_proposals
            WHERE task_id = ?
            ORDER BY created_at ASC, rowid ASC
            """,
            (task_id,),
        ).fetchall()

        return [
            record
            for row in rows
            if (record := self.get(row["proposal_id"])) is not None
        ]

    def pending(self, task_id: str | None = None) -> list[DecisionRecord]:
        if task_id is None:
            rows = self.conn.execute(
                """
                SELECT proposal_id
                FROM governance_proposals
                WHERE status = ?
                ORDER BY created_at ASC, rowid ASC
                """,
                (DecisionStatus.PENDING.value,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                """
                SELECT proposal_id
                FROM governance_proposals
                WHERE status = ? AND task_id = ?
                ORDER BY created_at ASC, rowid ASC
                """,
                (DecisionStatus.PENDING.value, task_id),
            ).fetchall()

        return [
            record
            for row in rows
            if (record := self.get(row["proposal_id"])) is not None
        ]

    def load_into(self, judgment: HumanJudgment) -> None:
        rows = self.conn.execute(
            """
            SELECT proposal_json
            FROM governance_proposals
            ORDER BY created_at ASC, rowid ASC
            """
        ).fetchall()

        for row in rows:
            proposal = _proposal_from_dict(json.loads(row["proposal_json"]))
            decision_row = self.conn.execute(
                """
                SELECT decision_json
                FROM governance_decisions
                WHERE proposal_id = ?
                ORDER BY timestamp ASC, rowid ASC
                """,
                (proposal.proposal_id,),
            ).fetchall()

            judgment._records[proposal.proposal_id] = DecisionRecord(proposal)

            for item in decision_row:
                decision = _decision_from_dict(json.loads(item["decision_json"]))
                judgment._records[proposal.proposal_id] = DecisionRecord(
                    proposal=proposal,
                    decision=decision,
                )
                judgment._history.append(decision)

    def save_record(self, record: DecisionRecord) -> None:
        self.save_proposal(record.proposal)
        if record.decision is not None:
            self.save_decision(record.decision)
