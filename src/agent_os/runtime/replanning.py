from dataclasses import dataclass
from typing import Callable

@dataclass(frozen=True)
class ReplanDecision:
    required: bool
    objective: str
    reason: str

class Replanner:
    def __init__(self, strategy: Callable[[str, str], str] | None = None):
        self.strategy = strategy

    def decide(self, output: str, error: str | None = None) -> ReplanDecision:
        if not output.strip():
            return ReplanDecision(True, "produce a valid non-empty result",
                                  "empty_output")
        if error:
            if self.strategy is None:
                return ReplanDecision(False, output, "replanning_strategy_unavailable")
            return ReplanDecision(
                True,
                self.strategy(output, error),
                "execution_error",
            )
        return ReplanDecision(False, output, "no_replan_required")
