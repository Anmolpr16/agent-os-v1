from agent_os.agents import Agent, AgentContext
from agent_os.agents.correction import CorrectionEngine
from agent_os.providers import MockProvider


def test_correction_engine_passes_first_attempt():
    engine = CorrectionEngine(
        Agent(MockProvider(response="python result")),
    )

    result = engine.run(
        AgentContext("task-1", "produce python result"),
        ["python"],
    )

    assert result.success is True
    assert result.output == "python result"
    assert len(result.attempts) == 1
    assert result.attempts[0].examination.passed is True


def test_correction_engine_reports_failed_evaluation():
    engine = CorrectionEngine(
        Agent(MockProvider(response="wrong")),
    )

    result = engine.run(
        AgentContext("task-1", "produce python result"),
        ["python"],
    )

    assert result.success is False
    assert result.output == "wrong"
    assert len(result.attempts) == 1
    assert result.error == "correction_strategy_unavailable"


def test_correction_engine_retries_with_corrected_objective():
    responses = iter(["wrong", "python result"])

    class SequenceProvider:
        def generate(self, request):
            from agent_os.providers import ProviderResponse

            return ProviderResponse(
                text=next(responses),
                provider="sequence",
                model="test",
            )

    engine = CorrectionEngine(
        Agent(SequenceProvider()),
        max_attempts=2,
        corrector=lambda output, examination: (
            "produce python result"
        ),
    )

    result = engine.run(
        AgentContext("task-1", "initial objective"),
        ["python"],
    )

    assert result.success is True
    assert result.output == "python result"
    assert len(result.attempts) == 2
    assert result.attempts[0].examination.passed is False
    assert result.attempts[1].examination.passed is True


def test_correction_engine_validates_attempt_limit():
    try:
        CorrectionEngine(
            Agent(MockProvider()),
            max_attempts=0,
        )
    except ValueError as exc:
        assert str(exc) == "max_attempts must be positive"
    else:
        raise AssertionError("expected ValueError")


def test_correction_engine_reports_empty_correction():
    engine = CorrectionEngine(
        Agent(MockProvider(response="wrong")),
        corrector=lambda output, examination: "",
    )

    result = engine.run(
        AgentContext("task-1", "initial objective"),
        ["python"],
    )

    assert result.success is False
    assert result.error == "correction_objective_empty"
