from __future__ import annotations

from typing import Any


class MemoryContextBuilder:
    """Converts graph retrieval into bounded AgentContext metadata."""

    def __init__(self, memory, max_items: int = 8, graph_depth: int = 1):
        self.memory = memory
        self.max_items = max(1, max_items)
        self.graph_depth = max(0, graph_depth)

    def build(self, objective: str) -> dict[str, Any]:
        if self.memory is None:
            return {}

        nodes = self.memory.search(objective)
        selected = list(nodes[: self.max_items])
        selected_ids = {node.node_id for node in selected}

        if self.graph_depth > 0:
            for node in list(selected):
                for related in self.memory.related(node.node_id, self.graph_depth):
                    if related.node_id in selected_ids:
                        continue
                    selected.append(related)
                    selected_ids.add(related.node_id)
                    if len(selected) >= self.max_items:
                        break
                if len(selected) >= self.max_items:
                    break

        selected = selected[: self.max_items]

        return {
            "memory_context": [
                {
                    "node_id": node.node_id,
                    "kind": node.kind,
                    "content": node.content,
                    "metadata": dict(node.metadata),
                }
                for node in selected
            ]
        }
