from agent_os.memory import MemoryStore


def test_memory_roundtrip(tmp_path):
    store = MemoryStore(str(tmp_path / "memory.db"))

    store.add_memory(
        "provenance matters",
        kind="semantic",
    )

    results = store.search("provenance")

    assert len(results) == 1
    assert results[0]["content"] == "provenance matters"

    store.close()
