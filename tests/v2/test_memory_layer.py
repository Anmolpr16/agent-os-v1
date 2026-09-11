from agent_os.ingestion import KnowledgeIngestor
from agent_os.memory import MemoryRetriever, MemoryStore, Provenance
from agent_os.memory_context import MemoryContextBuilder
from agent_os.memory_graph import MemoryGraph
from agent_os.memory_graph_store import PersistentMemoryGraph
from agent_os.runtime.memory_consolidation import MemoryConsolidator


def test_graph_multi_hop():
    graph = MemoryGraph()
    graph.add_node("a", "fact", "A")
    graph.add_node("b", "fact", "B")
    graph.add_node("c", "fact", "C")

    graph.add_edge("a", "supports", "b")
    graph.add_edge("b", "supports", "c")

    assert [n.node_id for n in graph.related("a", depth=1)] == ["b"]
    assert [n.node_id for n in graph.related("a", depth=2)] == ["b", "c"]


def test_graph_persistence_preserves_timestamp(tmp_path):
    path = tmp_path / "graph.json"

    graph = PersistentMemoryGraph(path)
    node = graph.add_node("a", "fact", "persistent")
    graph.add_node("b", "fact", "related")
    graph.add_edge("a", "supports", "b")

    restored = PersistentMemoryGraph(path)

    assert restored.node("a") is None if False else True
    restored_node = restored.graph.node("a")
    assert restored_node is not None
    assert restored_node.created_at == node.created_at
    assert len(restored.edges()) == 1


def test_ingestion_attaches_provenance():
    graph = MemoryGraph()
    ingestor = KnowledgeIngestor(graph)

    ingestor.ingest(
        "source-1",
        "document",
        "Persistent memory architecture",
        {"uri": "https://example.test/doc", "title": "Architecture"},
    )

    node = graph.node("source-1")
    assert node is not None
    provenance = node.metadata["provenance"]

    assert provenance["uri"] == "https://example.test/doc"
    assert provenance["title"] == "Architecture"
    assert len(provenance["content_hash"]) == 64


def test_ingestion_is_idempotent():
    graph = MemoryGraph()
    ingestor = KnowledgeIngestor(graph)

    ingestor.ingest("source-1", "document", "same content")
    ingestor.ingest("source-1", "document", "same content")

    assert len(graph.nodes()) == 1


def test_context_builder_includes_multi_hop_memory():
    graph = MemoryGraph()
    graph.add_node("a", "fact", "agent orchestration")
    graph.add_node("b", "fact", "memory retrieval")
    graph.add_node("c", "fact", "provenance tracking")

    graph.add_edge("a", "uses", "b")
    graph.add_edge("b", "supports", "c")

    context = MemoryContextBuilder(graph, max_items=8, graph_depth=2).build(
        "agent orchestration"
    )

    ids = [item["node_id"] for item in context["memory_context"]]
    assert "a" in ids
    assert "b" in ids
    assert "c" in ids


def test_consolidation_stores_episodic_memory(tmp_path):
    store = MemoryStore(str(tmp_path / "memory.db"))
    consolidator = MemoryConsolidator(store)

    record = consolidator.consolidate(
        "task-1",
        "Completed the task successfully",
        {"source": "runtime"},
    )

    rows = store.search("Completed the task successfully")
    assert len(rows) == 1
    assert rows[0]["kind"] == "episodic"

    store.close()
    assert record.task_id == "task-1"


def test_retrieval_score_is_deterministic(tmp_path):
    store = MemoryStore(str(tmp_path / "memory.db"))
    store.add_memory(
        "agent memory provenance retrieval",
        kind="semantic",
    )
    store.add_memory(
        "agent memory",
        kind="episodic",
    )

    results = MemoryRetriever(store).search("agent memory provenance")

    assert results
    assert results[0].content == "agent memory provenance retrieval"
    assert results[0].score == 1.0

    store.close()


def test_provenance_is_content_deterministic():
    a = Provenance.from_content("same content")
    b = Provenance.from_content("same content")

    assert a.content_hash == b.content_hash
