from dataclasses import dataclass
from typing import Callable, Iterable

@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    objective: str
    required_keywords: tuple[str, ...]

@dataclass(frozen=True)
class BenchmarkResult:
    case_id: str
    score: float
    passed: bool
    output: str

@dataclass(frozen=True)
class BenchmarkSummary:
    results: tuple[BenchmarkResult, ...]
    average_score: float
    passed: bool

class BenchmarkRunner:
    def __init__(self, evaluator: Callable[[BenchmarkCase], BenchmarkResult]):
        self.evaluator = evaluator

    def run(
        self,
        cases: Iterable[BenchmarkCase],
        threshold: float = 1.0,
    ) -> BenchmarkSummary:
        cases = list(cases)
        if threshold <= 0:
            raise ValueError("threshold_must_be_positive")
        results = tuple(self.evaluator(case) for case in cases)
        average = (
            sum(result.score for result in results) / len(results)
            if results else 0.0
        )
        return BenchmarkSummary(
            results=results,
            average_score=average,
            passed=bool(results)
            and average >= threshold
            and all(result.passed for result in results),
        )
