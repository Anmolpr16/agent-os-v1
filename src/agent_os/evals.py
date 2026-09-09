import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass
class EvalCase:
    id: str
    prompt: str
    expected_keywords: list[str]


@dataclass
class EvalResult:
    case_id: str
    passed: bool
    score: float
    missing: list[str]


def load_jsonl(path: str | Path) -> list[EvalCase]:
    cases = []

    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            cases.append(
                EvalCase(**json.loads(line))
            )

    return cases


def evaluate(
    output: str,
    case: EvalCase,
) -> EvalResult:
    text = output.lower()

    missing = [
        keyword
        for keyword in case.expected_keywords
        if keyword.lower() not in text
    ]

    score = 1.0 - (
        len(missing) /
        max(1, len(case.expected_keywords))
    )

    return EvalResult(
        case_id=case.id,
        passed=len(missing) == 0,
        score=score,
        missing=missing,
    )


def run_suite(
    dataset: str | Path,
    system: Callable[[str], str],
) -> list[EvalResult]:

    results = []

    for case in load_jsonl(dataset):
        output = system(case.prompt)
        results.append(
            evaluate(output, case)
        )

    return results


def baseline_system(prompt: str) -> str:
    """
    Deterministic V1 baseline.

    This is intentionally not an LLM. It exists so that the
    evaluation infrastructure can be tested before connecting
    an actual model provider.
    """

    return (
        f"Research task received: {prompt}. "
        "Create a plan, gather evidence, perform verification of the evidence, "
        "track provenance and source information, identify "
        "contradictions, and record uncertainty."
    )


def main() -> None:
    dataset = (
        Path(__file__).resolve().parents[2]
        / "evals"
        / "datasets"
        / "research.jsonl"
    )

    results = run_suite(
        dataset,
        baseline_system,
    )

    passed = 0

    for result in results:
        status = "PASS" if result.passed else "FAIL"

        print(
            f"{result.case_id}: "
            f"{status} "
            f"score={result.score:.2f} "
            f"missing={result.missing}"
        )

        if result.passed:
            passed += 1

    print()
    print(
        f"RESULT: {passed}/{len(results)} cases passed"
    )


if __name__ == "__main__":
    main()
