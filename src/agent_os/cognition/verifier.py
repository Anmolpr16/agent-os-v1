from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class VerificationResult:
    """Result of checking an output against a criterion."""

    passed: bool
    criterion: str
    details: str = ""


class Verifier:
    """Small, deterministic verification engine."""

    def verify(
        self,
        output: Any,
        criterion: str,
        check: Callable[[Any], bool],
    ) -> VerificationResult:

        passed = bool(check(output))

        return VerificationResult(
            passed=passed,
            criterion=criterion,
            details=(
                "criterion satisfied"
                if passed
                else "criterion failed"
            ),
        )
