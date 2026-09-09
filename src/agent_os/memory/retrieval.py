from dataclasses import dataclass
from typing import Any

from .store import MemoryStore


@dataclass
class MemoryMatch:
    """A retrieved memory with a deterministic relevance score."""

    id: int
    kind: str
    content: str
    score: float
    metadata: dict[str, Any]


class MemoryRetriever:
    """Deterministic V1 memory retrieval layer."""

    def __init__(self, store: MemoryStore):
        self.store = store

    def search(
        self,
        query: str,
        limit: int = 10,
    ) -> list[MemoryMatch]:
        terms = [
            term.strip().lower()
            for term in query.split()
            if term.strip()
        ]

        if not terms:
            return []

        rows_by_id = {}

        for term in terms:
            rows = self.store.search(
                term,
                limit=limit,
            )

            for row in rows:
                rows_by_id[row["id"]] = row

        matches = []

        for row in rows_by_id.values():
            content = row["content"]
            content_lower = content.lower()

            matched_terms = sum(
                1
                for term in terms
                if term in content_lower
            )

            score = matched_terms / len(terms)

            matches.append(
                MemoryMatch(
                    id=row["id"],
                    kind=row["kind"],
                    content=content,
                    score=score,
                    metadata=row["metadata_json"],
                )
            )

        matches.sort(
            key=lambda item: (
                -item.score,
                -item.id,
            )
        )

        return matches[:limit]

    def search_entity_graph(
        self,
        entity_id: int,
        depth: int = 1,
        limit: int = 50,
    ) -> list[dict]:
        if depth <= 0 or limit <= 0:
            return []

        visited = {entity_id}
        frontier = [entity_id]
        results = []

        for _ in range(depth):
            next_frontier = []

            for current_id in frontier:
                for neighbor in self.store.get_neighbors(
                    current_id,
                    limit=limit,
                ):
                    neighbor_id = neighbor["entity_id"]

                    if neighbor_id in visited:
                        continue

                    visited.add(neighbor_id)
                    next_frontier.append(neighbor_id)

                    results.append(
                        {
                            **neighbor,
                            "depth": _ + 1,
                        }
                    )

                    if len(results) >= limit:
                        return results

            frontier = next_frontier

            if not frontier:
                break

        return results
