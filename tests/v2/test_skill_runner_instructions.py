from agent_os.skill_runtime.loader import Skill
from agent_os.skill_runtime.runner import SkillRunner


def test_runner_propagates_instruction_context():
    skill = Skill(
        name="research",
        version="1.0.0",
        objective="Research and verify evidence",
        procedure=["Gather evidence", "Verify evidence"],
        instructions="Repository policy: verify outputs.",
        instruction_sources=["/repo/AGENTS.md"],
    )

    result = SkillRunner().run(skill)

    assert result.passed
    assert result.instructions == skill.instructions
    assert result.instruction_sources == [
        "/repo/AGENTS.md"
    ]


def test_runner_preserves_instructions_on_failure():
    skill = Skill(
        name="research",
        version="1.0.0",
        objective="Research",
        procedure=["Gather evidence", ""],
        instructions="Do not skip verification.",
        instruction_sources=["/repo/AGENTS.md"],
    )

    result = SkillRunner().run(skill)

    assert not result.passed
    assert result.status == "failed"
    assert result.instructions == "Do not skip verification."
    assert result.instruction_sources == [
        "/repo/AGENTS.md"
    ]


def test_runner_without_instructions_remains_backward_compatible():
    skill = Skill(
        name="basic",
        version="1.0.0",
        objective="Basic task",
        procedure=["Execute"],
    )

    result = SkillRunner().run(skill)

    assert result.passed
    assert result.instructions == ""
    assert result.instruction_sources == []
