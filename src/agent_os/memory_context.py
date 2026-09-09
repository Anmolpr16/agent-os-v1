from __future__ import annotations

from typing import Any


class MemoryContextBuilder:
    """Converts graph retrieval into bounded AgentContext metadata."""

    def __init__(self, memory, max_items: int = 8):
        self.memory = memory
        self.max_items = max(1, max_items)

    def build(self, objective: str) -> dict[str, Any]:
        if self.memory is None:
            return {}

        nodes = self.memory.search(objective)[: self.max_items]

        return {
            "memory_context": [
                {
                    "node_id": node.node_id,
                    "kind": node.kind,
                    "content": node.content,
                    "metadata": dict(node.metadata),
                }
                for node in nodes
            ]
        }
