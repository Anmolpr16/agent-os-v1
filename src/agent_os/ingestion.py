from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .memory_graph import MemoryGraph


@dataclass(frozen=True)
class IngestionRecord:
    source_id: str
    source_type: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    ingested_at: str = ""


class KnowledgeIngestor:
    def __init__(self, graph: MemoryGraph):
        self.graph = graph

    def ingest(
        self,
        source_id: str,
        source_type: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> IngestionRecord:
        if not source_id.strip():
            raise ValueError("source_id_required")
        if not source_type.strip():
            raise ValueError("source_type_required")
        if not content.strip():
            raise ValueError("content_required")

        record = IngestionRecord(
            source_id=source_id,
            source_type=source_type,
            content=content,
            metadata=dict(metadata or {}),
            ingested_at=datetime.now(timezone.utc).isoformat(),
        )

        self.graph.add_node(
            source_id,
            source_type,
            content,
            record.metadata,
        )
        return record
