from agent_os.core.orchestrator import Orchestrator, Task


def test_cognition_integration():
    run = Orchestrator().run(
        Task(
            id="cognition-001",
            objective="Test cognition integration",
        )
    )

    assert run.prediction_error == 0.0

    assert run.reflection is not None
    assert run.reflection.confidence == 0.9

    execution_event = next(
        event
        for event in run.events
        if event["state"] == "execution"
    )

    assert execution_event["prediction"]["action"] == "execute_task"
    assert execution_event["prediction_error"] == 0.0

    verification_event = next(
        event
        for event in run.events
        if event["state"] == "verification"
    )

    assert verification_event["verification"]["passed"] is True

    finalization_event = next(
        event
        for event in run.events
        if event["state"] == "finalization"
    )

    assert finalization_event["reflection"]["has_lessons"] is True


def test_lifecycle_event_count():
    run = Orchestrator().run(
        Task(
            id="cognition-002",
            objective="Test event contract",
        )
    )

    assert len(run.events) == len(Orchestrator.ORDER)


def test_planner_integration():
    run = Orchestrator().run(
        Task(
            id="planner-001",
            objective="Build a verified research workflow",
        )
    )

    assert run.plan is not None
    assert run.plan.objective == "Build a verified research workflow"
    assert len(run.plan.steps) == 3
    assert run.plan.is_valid

    assert [step.id for step in run.plan.steps] == [
        "understand",
        "execute",
        "verify",
    ]

    assert run.plan.steps[1].dependencies == [
        "understand",
    ]

    assert run.plan.steps[2].dependencies == [
        "execute",
    ]

    planning_event = next(
        event
        for event in run.events
        if event["state"] == "planning"
    )

    assert planning_event["plan"]["valid"] is True
    assert planning_event["plan"]["steps"] == 3
    assert planning_event["plan"]["validation_errors"] == []
