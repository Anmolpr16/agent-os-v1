from agent_os.agents import Agent
from agent_os.core.orchestrator import Orchestrator, Task
from agent_os.providers import MockProvider
from agent_os.skill_runtime import Skill, SkillRegistry


def test_orchestrator_exposes_skill_instructions_to_agent():
    registry = SkillRegistry()

    registry.register(
        Skill(
            name="research",
            version="1.0.0",
            objective="Research and verify evidence",
            procedure=["Gather evidence"],
            instructions="Repository policy: verify outputs.",
            instruction_sources=["/repo/AGENTS.md"],
        )
    )

    class CapturingProvider(MockProvider):
        def generate(self, request):
            self.metadata = request.metadata
            return super().generate(request)

    provider = CapturingProvider(response="completed")
    agent = Agent(provider)

    with Orchestrator(
        agent=agent,
        skill_registry=registry,
    ) as orchestrator:
        run = orchestrator.run(
        Task(
            id="instruction-test",
            objective="Research and verify evidence",
        )
    )

    assert run.output == "completed"
    assert provider.metadata["skill"]["instructions"] == (
        "Repository policy: verify outputs."
    )
    assert provider.metadata["skill"]["instruction_sources"] == [
        "/repo/AGENTS.md"
    ]


def test_orchestrator_preserves_empty_instruction_context():
    registry = SkillRegistry()

    registry.register(
        Skill(
            name="basic",
            version="1.0.0",
            objective="Basic execution task",
            procedure=["Execute"],
        )
    )

    class CapturingProvider(MockProvider):
        def generate(self, request):
            self.metadata = request.metadata
            return super().generate(request)

    provider = CapturingProvider(response="completed")

    with Orchestrator(
        agent=Agent(provider),
        skill_registry=registry,
    ) as orchestrator:
        orchestrator.run(
        Task(
            id="empty-instruction-test",
            objective="Basic execution task",
        )
    )

    assert provider.metadata["skill"]["instructions"] == ""
    assert provider.metadata["skill"]["instruction_sources"] == []
