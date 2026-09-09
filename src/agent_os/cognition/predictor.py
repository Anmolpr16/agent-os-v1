from dataclasses import dataclass
from typing import Any


@dataclass
class Prediction:
    """Expected outcome of an action."""

    action: str
    expected: Any
    confidence: float = 0.5


@dataclass
class PredictionError:
    """Difference between an expected and observed outcome."""

    action: str
    expected: Any
    observed: Any
    magnitude: float


def compare(
    prediction: Prediction,
    observed: Any,
) -> PredictionError:
    """Compare a prediction with an observation."""

    if prediction.expected == observed:
        magnitude = 0.0
    else:
        magnitude = 1.0

    return PredictionError(
        action=prediction.action,
        expected=prediction.expected,
        observed=observed,
        magnitude=magnitude,
    )
