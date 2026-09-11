from __future__ import annotations

from typing import Any


def extract_score(result: Any) -> float:
    """Extract a numeric evaluation score from supported result shapes.

    Supported forms:
    - numeric values
    - mappings containing score/overall_score/value
    - mappings containing numeric metrics
    - objects exposing score/overall_score/value
    - objects exposing numeric metrics
    """
    if isinstance(result, (int, float)):
        return float(result)

    if isinstance(result, dict):
        for key in ("score", "overall_score", "value"):
            value = result.get(key)
            if isinstance(value, (int, float)):
                return float(value)

        metrics = result.get("metrics")
        if isinstance(metrics, dict):
            values = [
                float(value)
                for value in metrics.values()
                if isinstance(value, (int, float))
            ]
            if values:
                return sum(values) / len(values)

    for key in ("score", "overall_score", "value"):
        value = getattr(result, key, None)
        if isinstance(value, (int, float)):
            return float(value)

    metrics = getattr(result, "metrics", None)
    if isinstance(metrics, dict):
        values = [
            float(value)
            for value in metrics.values()
            if isinstance(value, (int, float))
        ]
        if values:
            return sum(values) / len(values)

    raise ValueError(
        "evaluation result does not contain a numeric score"
    )
