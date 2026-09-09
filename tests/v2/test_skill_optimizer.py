from agent_os.skill_evolution import SkillEvolutionEngine
from agent_os.skill_optimizer import SkillOptimizer
from agent_os.skill_registry import SkillRegistry


def test_optimizer_accepts_only_improved_revision():
    registry = SkillRegistry()
    registry.register("research", "Research carefully")

    engine = SkillEvolutionEngine(registry)
    optimizer = SkillOptimizer(registry, engine)

    result = optimizer.optimize(
        "research",
        "Improve evidence verification",
        score_before=0.60,
        score_after=0.85,
        instructions="Research carefully and verify evidence",
    )

    assert result.improved is True
    assert result.previous_version == 1
    assert result.new_version == 2
    assert registry.latest("research").version == 2


def test_optimizer_rejects_non_improvement():
    registry = SkillRegistry()
    registry.register("research", "Research carefully")

    engine = SkillEvolutionEngine(registry)
    optimizer = SkillOptimizer(registry, engine)

    result = optimizer.optimize(
        "research",
        "Change the procedure",
        score_before=0.80,
        score_after=0.75,
        instructions="Worse procedure",
    )

    assert result.improved is False
    assert result.new_version == 1
    assert registry.latest("research").instructions == "Research carefully"


def test_optimizer_rejects_equal_score():
    registry = SkillRegistry()
    registry.register("coding", "Implement and test")

    engine = SkillEvolutionEngine(registry)
    optimizer = SkillOptimizer(registry, engine)

    result = optimizer.optimize(
        "coding",
        "Add more checks",
        score_before=0.80,
        score_after=0.80,
        instructions="Implement and test more",
    )

    assert result.improved is False
    assert registry.latest("coding").version == 1


def test_optimizer_can_create_improved_first_version():
    registry = SkillRegistry()
    engine = SkillEvolutionEngine(registry)
    optimizer = SkillOptimizer(registry, engine)

    result = optimizer.optimize(
        "planning",
        "Create a planning procedure",
        score_before=0.0,
        score_after=0.90,
        instructions="Plan before execution",
    )

    assert result.improved is True
    assert result.previous_version == 0
    assert result.new_version == 1
