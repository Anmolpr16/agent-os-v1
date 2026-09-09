from agent_os.skills import load_skill


def test_skill_load():
    skill = load_skill("skills/research/SKILL.md")

    assert skill.procedure
    assert len(skill.procedure) > 0
