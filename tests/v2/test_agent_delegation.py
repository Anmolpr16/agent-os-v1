from agent_os.agents.delegation import (
    AgentWorker,
    DelegatedResult,
    DelegatedTask,
)


def test_delegated_task_is_structured():
    task = DelegatedTask(
        task_id="worker-1",
        objective="perform subtask",
        metadata={"priority": "high"},
    )

    assert task.task_id == "worker-1"
    assert task.objective == "perform subtask"
    assert task.metadata == {"priority": "high"}


def test_delegated_result_can_represent_success():
    result = DelegatedResult(
        task_id="worker-1",
        success=True,
        output="done",
    )

    assert result.success is True
    assert result.output == "done"
    assert result.error is None


def test_worker_contract_requires_execution():
    worker = AgentWorker()

    try:
        worker.execute(
            DelegatedTask(
                task_id="worker-1",
                objective="perform subtask",
            )
        )
    except NotImplementedError:
        pass
    else:
        raise AssertionError("expected NotImplementedError")


def test_manager_delegates_to_registered_agent():
    from agent_os.agents import Agent, AgentContext, AgentManager
    from agent_os.providers import MockProvider

    manager = AgentManager()
    manager.register(
        "worker",
        Agent(MockProvider(response="delegated output")),
    )

    result = manager.delegate(
        "worker",
        DelegatedTask(
            task_id="task-1",
            objective="complete subtask",
        ),
    )

    assert result.success is True
    assert result.task_id == "task-1"
    assert result.output == "delegated output"
    assert result.error is None


def test_manager_rejects_unknown_agent():
    from agent_os.agents import AgentManager

    result = AgentManager().delegate(
        "missing",
        DelegatedTask(
            task_id="task-1",
            objective="complete subtask",
        ),
    )

    assert result.success is False
    assert result.error == "agent_not_registered:missing"


def test_manager_rejects_invalid_delegated_task():
    from agent_os.agents import AgentManager

    manager = AgentManager()

    missing_task_id = manager.delegate(
        "worker",
        DelegatedTask(
            task_id="",
            objective="complete subtask",
        ),
    )

    missing_objective = manager.delegate(
        "worker",
        DelegatedTask(
            task_id="task-1",
            objective="",
        ),
    )

    assert missing_task_id.error == "task_id_missing"
    assert missing_objective.error == "objective_missing"
