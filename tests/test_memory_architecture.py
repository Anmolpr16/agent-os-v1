from agent_os.memory import (
    MemoryRetriever,
    MemoryStore,
    Provenance,
)


def test_retrieval(tmp_path):
    store = MemoryStore(
        str(tmp_path / "memory.db")
    )

    store.add_memory(
        "provenance matters for reliable memory",
        kind="semantic",
    )

    store.add_memory(
        "unrelated information",
        kind="episodic",
    )

    retriever = MemoryRetriever(store)

    results = retriever.search(
        "provenance reliable",
    )

    assert results
    assert results[0].content.startswith(
        "provenance matters"
    )
    assert results[0].score > 0.0

    store.close()


def test_provenance_hash():
    provenance = Provenance.from_content(
        "important source content",
        uri="https://example.test/source",
        title="Example Source",
    )

    assert provenance.uri == (
        "https://example.test/source"
    )
    assert provenance.title == "Example Source"
    assert len(provenance.content_hash) == 64
    assert provenance.created_at
