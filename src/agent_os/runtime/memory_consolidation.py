from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class ConsolidationRecord:
    task_id: str
    output: str
    metadata: dict[str, Any]

class MemoryConsolidator:
    def __init__(self, store):
        self.store = store

    def consolidate(
        self,
        task_id: str,
        output: str,
        metadata: dict[str, Any] | None = None,
    ) -> ConsolidationRecord:
        if not task_id.strip():
            raise ValueError("task_id_required")
        if not output.strip():
            raise ValueError("output_required")

        data = dict(metadata or {})
        data.setdefault("task_id", task_id)
        self.store.add_memory(
            output,
            kind="episodic",
            metadata=data,
        )
        return ConsolidationRecord(task_id, output, data)
