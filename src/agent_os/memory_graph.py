from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class MemoryNode:
    node_id: str
    kind: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""


@dataclass(frozen=True)
class MemoryEdge:
    source: str
    relation: str
    target: str
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


class MemoryGraph:
    def __init__(self):
        self._nodes: dict[str, MemoryNode] = {}
        self._edges: list[MemoryEdge] = []

    def add_node(
        self,
        node_id: str,
        kind: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryNode:
        if not node_id.strip():
            raise ValueError("node_id_required")
        if not kind.strip():
            raise ValueError("node_kind_required")
        if not content.strip():
            raise ValueError("node_content_required")

        node = MemoryNode(
            node_id=node_id,
            kind=kind,
            content=content,
            metadata=dict(metadata or {}),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._nodes[node_id] = node
        return node

    def add_edge(
        self,
        source: str,
        relation: str,
        target: str,
        weight: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEdge:
        if source not in self._nodes:
            raise KeyError("source_node_missing")
        if target not in self._nodes:
            raise KeyError("target_node_missing")
        if not relation.strip():
            raise ValueError("edge_relation_required")
        if weight < 0:
            raise ValueError("edge_weight_invalid")

        edge = MemoryEdge(
            source=source,
            relation=relation,
            target=target,
            weight=weight,
            metadata=dict(metadata or {}),
        )
        self._edges.append(edge)
        return edge

    def node(self, node_id: str) -> MemoryNode | None:
        return self._nodes.get(node_id)

    def nodes(self) -> list[MemoryNode]:
        return list(self._nodes.values())

    def edges(self) -> list[MemoryEdge]:
        return list(self._edges)

    def neighbors(
        self,
        node_id: str,
        relation: str | None = None,
    ) -> list[MemoryNode]:
        targets = []
        for edge in self._edges:
            if edge.source != node_id:
                continue
            if relation is not None and edge.relation != relation:
                continue
            node = self._nodes.get(edge.target)
            if node is not None:
                targets.append(node)
        return targets

    def related(
        self,
        node_id: str,
        depth: int = 1,
    ) -> list[MemoryNode]:
        if depth < 0:
            raise ValueError("depth_invalid")

        visited = {node_id}
        frontier = [node_id]
        result = []

        for _ in range(depth):
            next_frontier = []
            for current in frontier:
                for node in self.neighbors(current):
                    if node.node_id in visited:
                        continue
                    visited.add(node.node_id)
                    result.append(node)
                    next_frontier.append(node.node_id)
            frontier = next_frontier

        return result

    def search(self, query: str) -> list[MemoryNode]:
        terms = [x for x in query.lower().split() if x]
        if not terms:
            return []

        scored = []
        for node in self._nodes.values():
            text = f"{node.kind} {node.content}".lower()
            score = sum(term in text for term in terms)
            if score:
                scored.append((score, node))

        scored.sort(key=lambda item: (-item[0], item[1].node_id))
        return [node for _, node in scored]
