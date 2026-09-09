from agent_os.runtime import SkillEvolution, TaskGraph, TaskNode
from agent_os.evaluation import BenchmarkCase, BenchmarkResult, BenchmarkRunner

def test_skill_evolution_only_activates_passing_revision():
    evolution = SkillEvolution(
        "initial",
        proposer=lambda current, feedback: current + "\nfix",
    )
    proposal = evolution.propose(["coverage"])
    revision = evolution.evaluate_revision(proposal, 0.5, ["still weak"])
    assert revision.passed is False
    assert evolution.version == 1
    assert evolution.active == "initial"

    revision = evolution.evaluate_revision(proposal, 1.0, [])
    assert revision.passed is True
    assert evolution.version == 2
    assert evolution.active == proposal

def test_benchmark_runner():
    runner = BenchmarkRunner(
        lambda case: BenchmarkResult(
            case.case_id, 1.0, True, case.objective
        )
    )
    summary = runner.run([
        BenchmarkCase("a", "A", ("A",)),
        BenchmarkCase("b", "B", ("B",)),
    ])
    assert summary.passed is True
    assert summary.average_score == 1.0

def test_dag_accepts_forward_dependency():
    graph = TaskGraph([
        TaskNode("b", "B", ("a",)),
        TaskNode("a", "A"),
    ])
    assert [task.task_id for task in graph.topological_order()] == ["a", "b"]
