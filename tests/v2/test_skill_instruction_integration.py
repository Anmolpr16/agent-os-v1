from pathlib import Path

from agent_os.skill_runtime.loader import load_skill


def test_skill_loads_repository_instructions():
    skill = load_skill("skills/research/SKILL.md")

    assert skill.name == "research"
    assert skill.instructions
    assert any(
        path.endswith("AGENTS.md")
        for path in skill.instruction_sources
    )
    assert "Agent OS" in skill.instructions


def test_skill_can_disable_instruction_loading():
    skill = load_skill(
        "skills/research/SKILL.md",
        include_instructions=False,
    )

    assert skill.instructions == ""
    assert skill.instruction_sources == []


def test_skill_supports_explicit_instruction_root(tmp_path: Path):
    root = tmp_path / "repo"
    skills = root / "skills" / "demo"
    skills.mkdir(parents=True)

    (root / "AGENTS.md").write_text(
        "# Repository Rules\n\n- Verify outputs.\n",
        encoding="utf-8",
    )

    skill_file = skills / "SKILL.md"

    skill_file.write_text(
        """# Demo Skill
## Name
demo
## Version
1.0.0
## Objective
Test instruction integration.
## Procedure
1. Execute.
""",
        encoding="utf-8",
    )

    skill = load_skill(
        skill_file,
        instruction_root=root,
    )

    assert "Verify outputs." in skill.instructions
    assert len(skill.instruction_sources) == 1
