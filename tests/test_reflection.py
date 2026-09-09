from agent_os.cognition.reflection import reflect


def test_reflection():
    result = reflect(
        outcome="task completed",
        what_worked=["planning"],
        what_failed=["initial attempt"],
        lessons=["verify the result"],
        confidence=0.8,
    )

    assert result.outcome == "task completed"
    assert result.has_failures
    assert result.has_lessons
    assert result.confidence == 0.8


def test_confidence_is_bounded():
    assert reflect("test", confidence=2.0).confidence == 1.0
    assert reflect("test", confidence=-1.0).confidence == 0.0
