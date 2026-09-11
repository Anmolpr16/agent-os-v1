from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .memory_graph import MemoryEdge, MemoryGraph, MemoryNode


class PersistentMemoryGraph:
    """JSON-backed persistent wrapper around MemoryGraph."""

    def __init__(self, path: str | Path = ".agent_os/memory_graph.json"):
        self.path = Path(path)
        self.graph = MemoryGraph()
        self.load()

    def add_node(
        self,
        node_id: str,
        kind: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryNode:
        node = self.graph.add_node(node_id, kind, content, metadata)
        self.save()
        return node

    def add_edge(
        self,
        source: str,
        relation: str,
        target: str,
        weight: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEdge:
        edge = self.graph.add_edge(
            source,
            relation,
            target,
            weight,
            metadata,
        )
        self.save()
        return edge

    def search(self, query: str) -> list[MemoryNode]:
        return self.graph.search(query)

    def related(self, node_id: str, depth: int = 1) -> list[MemoryNode]:
        return self.graph.related(node_id, depth)

    def nodes(self) -> list[MemoryNode]:
        return self.graph.nodes()

    def edges(self) -> list[MemoryEdge]:
        return self.graph.edges()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "nodes": [
                {
                    "node_id": n.node_id,
                    "kind": n.kind,
                    "content": n.content,
                    "metadata": n.metadata,
                    "created_at": n.created_at,
                }
                for n in self.graph.nodes()
            ],
            "edges": [
                {
                    "source": e.source,
                    "relation": e.relation,
                    "target": e.target,
                    "weight": e.weight,
                    "metadata": e.metadata,
                }
                for e in self.graph.edges()
            ],
        }
        self.path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def load(self) -> None:
        if not self.path.exists():
            return

        payload = json.loads(
            self.path.read_text(encoding="utf-8")
        )

        for node in payload.get("nodes", []):
            restored = self.graph.add_node(
                node["node_id"],
                node["kind"],
                node["content"],
                node.get("metadata", {}),
            )
            if node.get("created_at"):
                self.graph._nodes[node["node_id"]] = MemoryNode(
                    node_id=restored.node_id,
                    kind=restored.kind,
                    content=restored.content,
                    metadata=dict(restored.metadata),
                    created_at=node["created_at"],
                )

        for edge in payload.get("edges", []):
            if (
                edge["source"] in {
                    n.node_id for n in self.graph.nodes()
                }
                and edge["target"] in {
                    n.node_id for n in self.graph.nodes()
                }
            ):
                self.graph.add_edge(
                    edge["source"],
                    edge["relation"],
                    edge["target"],
                    edge.get("weight", 1.0),
                    edge.get("metadata", {}),
                )
