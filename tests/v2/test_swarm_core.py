from agent_os.swarm import (
    AgentCoordinator,
    AgentResult,
    AgentSpec,
    AgentStatus,
)


def test_agent_registration_and_lookup():
    coordinator = AgentCoordinator()
    agent = AgentSpec(
        agent_id="researcher",
        role="research",
        capabilities=("search", "evidence"),
    )

    coordinator.register(agent, lambda task: "research complete")

    assert coordinator.get_agent("researcher") == agent
    assert coordinator.agents() == (agent,)


def test_delegate_creates_pending_task():
    coordinator = AgentCoordinator()
    coordinator.register(
        AgentSpec("researcher", "research"),
        lambda task: "done",
    )

    task = coordinator.delegate(
        "Investigate the evidence",
        "researcher",
        constraints=("cite sources",),
        metadata={"priority": "high"},
    )

    assert task.objective == "Investigate the evidence"
    assert task.assigned_agent == "researcher"
    assert task in coordinator.pending()
    assert coordinator.result(task.task_id) is None


def test_execute_wraps_plain_handler_output():
    coordinator = AgentCoordinator()
    coordinator.register(
        AgentSpec("analyst", "analysis"),
        lambda task: {"finding": "supported"},
    )

    task = coordinator.delegate("Analyze evidence", "analyst")
    result = coordinator.execute(task)

    assert result.task_id == task.task_id
    assert result.agent_id == "analyst"
    assert result.status == AgentStatus.SUCCEEDED
    assert result.output == {"finding": "supported"}
    assert coordinator.result(task.task_id) == result
    assert coordinator.pending() == ()


def test_execute_preserves_structured_result():
    coordinator = AgentCoordinator()

    expected = AgentResult(
        task_id="placeholder",
        agent_id="verifier",
        status=AgentStatus.SUCCEEDED,
        output="verified",
        evidence=("source-a",),
    )

    def handler(task):
        return AgentResult(
            task_id=task.task_id,
            agent_id=task.assigned_agent,
            status=expected.status,
            output=expected.output,
            evidence=expected.evidence,
        )

    coordinator.register(AgentSpec("verifier", "verification"), handler)

    task = coordinator.delegate("Verify the claim", "verifier")
    result = coordinator.execute(task)

    assert result.status == AgentStatus.SUCCEEDED
    assert result.output == "verified"
    assert result.evidence == ("source-a",)


def test_handler_failure_becomes_failed_result():
    coordinator = AgentCoordinator()

    def handler(task):
        raise RuntimeError("verification unavailable")

    coordinator.register(AgentSpec("verifier", "verification"), handler)

    task = coordinator.delegate("Verify the claim", "verifier")
    result = coordinator.execute(task)

    assert result.status == AgentStatus.FAILED
    assert result.error == "RuntimeError: verification unavailable"
    assert result.task_id == task.task_id


def test_result_identity_mismatch_is_rejected():
    coordinator = AgentCoordinator()

    def handler(task):
        return AgentResult(
            task_id="wrong-task",
            agent_id=task.assigned_agent,
            status=AgentStatus.SUCCEEDED,
            output="bad",
        )

    coordinator.register(AgentSpec("agent-a", "general"), handler)

    task = coordinator.delegate("Do work", "agent-a")
    result = coordinator.execute(task)

    assert result.status == AgentStatus.FAILED
    assert "different task" in result.error


def test_failed_result_requires_error():
    try:
        AgentResult(
            task_id="task-1",
            agent_id="agent-1",
            status=AgentStatus.FAILED,
        )
    except ValueError as exc:
        assert str(exc) == "failed results require an error"
    else:
        raise AssertionError("expected ValueError")


def test_unknown_agent_cannot_receive_work():
    coordinator = AgentCoordinator()

    try:
        coordinator.delegate("Do work", "missing")
    except KeyError as exc:
        assert "unknown agent" in str(exc)
    else:
        raise AssertionError("expected KeyError")


def test_duplicate_agent_registration_is_rejected():
    coordinator = AgentCoordinator()
    agent = AgentSpec("agent-a", "general")

    coordinator.register(agent, lambda task: "one")

    try:
        coordinator.register(agent, lambda task: "two")
    except ValueError as exc:
        assert "already registered" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_swarm_delegation_and_completion_are_audited():
    from agent_os.runtime.audit import AuditLog

    audit = AuditLog()
    coordinator = AgentCoordinator(audit=audit)

    coordinator.register(
        AgentSpec("researcher", "research"),
        lambda task: "research complete",
    )

    task = coordinator.delegate("Investigate the evidence", "researcher")
    result = coordinator.execute(task)

    assert result.status == AgentStatus.SUCCEEDED

    events = audit.for_task(task.task_id)
    assert [event.event for event in events] == [
        "swarm_task_delegated",
        "swarm_task_completed",
    ]
    assert events[0].metadata["assigned_agent"] == "researcher"
    assert events[1].metadata["status"] == AgentStatus.SUCCEEDED.value


def test_swarm_failure_is_audited():
    from agent_os.runtime.audit import AuditLog

    audit = AuditLog()
    coordinator = AgentCoordinator(audit=audit)

    def handler(task):
        raise RuntimeError("agent unavailable")

    coordinator.register(AgentSpec("worker", "execution"), handler)

    task = coordinator.delegate("Execute task", "worker")
    result = coordinator.execute(task)

    assert result.status == AgentStatus.FAILED

    events = audit.for_task(task.task_id)
    assert events[-1].event == "swarm_task_failed"
    assert events[-1].metadata["status"] == AgentStatus.FAILED.value


def test_execute_many_runs_all_tasks_and_preserves_input_order():
    import time

    coordinator = AgentCoordinator()

    def handler(task):
        if task.objective == "slow":
            time.sleep(0.08)
        return task.objective

    coordinator.register(AgentSpec("worker", "general"), handler)

    first = coordinator.delegate("slow", "worker")
    second = coordinator.delegate("fast", "worker")

    started = time.monotonic()
    results = coordinator.execute_many((first, second), max_workers=2)
    elapsed = time.monotonic() - started

    assert [result.output for result in results] == ["slow", "fast"]
    assert all(result.status == AgentStatus.SUCCEEDED for result in results)
    assert elapsed < 0.15


def test_execute_many_isolates_agent_failure():
    coordinator = AgentCoordinator()

    def handler(task):
        if task.objective == "fail":
            raise RuntimeError("worker failed")
        return "success"

    coordinator.register(AgentSpec("worker", "general"), handler)

    failed = coordinator.delegate("fail", "worker")
    successful = coordinator.delegate("success", "worker")

    results = coordinator.execute_many((failed, successful), max_workers=2)

    assert results[0].status == AgentStatus.FAILED
    assert results[0].error == "RuntimeError: worker failed"
    assert results[1].status == AgentStatus.SUCCEEDED
    assert results[1].output == "success"


def test_execute_many_audits_each_task():
    from agent_os.runtime.audit import AuditLog

    audit = AuditLog()
    coordinator = AgentCoordinator(audit=audit)

    coordinator.register(
        AgentSpec("worker", "general"),
        lambda task: task.objective,
    )

    first = coordinator.delegate("one", "worker")
    second = coordinator.delegate("two", "worker")

    results = coordinator.execute_many((first, second), max_workers=2)

    assert len(results) == 2

    for task in (first, second):
        events = audit.for_task(task.task_id)
        assert [event.event for event in events] == [
            "swarm_task_delegated",
            "swarm_task_completed",
        ]


def test_execute_many_rejects_duplicate_tasks():
    coordinator = AgentCoordinator()
    coordinator.register(
        AgentSpec("worker", "general"),
        lambda task: "done",
    )

    task = coordinator.delegate("work", "worker")

    try:
        coordinator.execute_many((task, task))
    except ValueError as exc:
        assert "duplicate task" in str(exc)
    else:
        raise AssertionError("expected ValueError")
