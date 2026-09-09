from agent_os.evals import EvalCase, evaluate


def test_eval_pass():
    case = EvalCase(
        id="test",
        prompt="test",
        expected_keywords=[
            "evidence",
            "verification",
        ],
    )

    result = evaluate(
        "Evidence was gathered and verification was completed.",
        case,
    )

    assert result.passed
    assert result.score == 1.0
