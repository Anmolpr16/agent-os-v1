from pathlib import Path

import pytest

from agent_os.instruction_loader import (
    InstructionResolver,
    discover_instructions,
    load_instructions,
)


def test_discovers_repository_agents_file():
    root = Path(__file__).resolve().parents[2]

    documents = discover_instructions(
        root / "skills" / "research" / "SKILL.md",
        root=root,
    )

    assert [document.name for document in documents] == ["AGENTS.md"]
    assert "Operating Contract" in documents[0].content


def test_discovers_hierarchical_instructions_in_scope_order(tmp_path):
    root = tmp_path / "repo"
    nested = root / "skills" / "research"
    nested.mkdir(parents=True)

    (root / "AGENTS.md").write_text(
        "# Root instructions\nUse repository policy.",
        encoding="utf-8",
    )
    (root / "skills" / "AGENTS.md").write_text(
        "# Skills instructions\nFollow skill policy.",
        encoding="utf-8",
    )
    (nested / "CLAUDE.md").write_text(
        "# Research instructions\nFollow research policy.",
        encoding="utf-8",
    )
    (nested / "SKILL.md").write_text(
        "# Research Skill\n",
        encoding="utf-8",
    )

    documents = InstructionResolver(root=root).discover(
        nested / "SKILL.md"
    )

    assert [(item.name, item.scope) for item in documents] == [
        ("AGENTS.md", str(root)),
        ("AGENTS.md", str(root / "skills")),
        ("CLAUDE.md", str(nested)),
    ]


def test_nearest_scope_can_be_resolved_with_both_instruction_types(tmp_path):
    root = tmp_path / "repo"
    nested = root / "project"
    nested.mkdir(parents=True)

    (root / "AGENTS.md").write_text(
        "ROOT POLICY",
        encoding="utf-8",
    )
    (root / "CLAUDE.md").write_text(
        "ROOT CLAUDE POLICY",
        encoding="utf-8",
    )
    (nested / "AGENTS.md").write_text(
        "LOCAL POLICY",
        encoding="utf-8",
    )

    resolved = load_instructions(nested, root=root)

    assert resolved.index("ROOT POLICY") < resolved.index("LOCAL POLICY")
    assert "ROOT CLAUDE POLICY" in resolved


def test_empty_instruction_files_are_ignored(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()

    (root / "AGENTS.md").write_text("", encoding="utf-8")
    (root / "CLAUDE.md").write_text("  \n", encoding="utf-8")

    assert InstructionResolver(root=root).discover(root) == []


def test_path_outside_explicit_root_is_rejected(tmp_path):
    root = tmp_path / "repo"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()

    with pytest.raises(ValueError, match="instruction_path_outside_root"):
        InstructionResolver(root=root).discover(outside)


def test_instruction_order_is_deterministic(tmp_path):
    root = tmp_path / "repo"
    nested = root / "nested"
    nested.mkdir(parents=True)

    (root / "CLAUDE.md").write_text("CLAUDE ROOT", encoding="utf-8")
    (root / "AGENTS.md").write_text("AGENTS ROOT", encoding="utf-8")
    (nested / "CLAUDE.md").write_text("CLAUDE NESTED", encoding="utf-8")
    (nested / "AGENTS.md").write_text("AGENTS NESTED", encoding="utf-8")

    resolver = InstructionResolver(root=root)

    first = resolver.discover(nested)
    second = resolver.discover(nested)

    assert first == second
    assert [item.name for item in first] == [
        "AGENTS.md",
        "CLAUDE.md",
        "AGENTS.md",
        "CLAUDE.md",
    ]
