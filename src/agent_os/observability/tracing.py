from contextlib import contextmanager
from dataclasses import dataclass
from time import perf_counter
from typing import Iterator


@dataclass(frozen=True)
class TraceSpan:
    """Measured execution span."""

    name: str
    duration_ms: float


@contextmanager
def span(name: str) -> Iterator[dict[str, float]]:
    """Measure a bounded operation."""

    started = perf_counter()
    result = {}

    try:
        yield result
    finally:
        result["duration_ms"] = (
            perf_counter() - started
        ) * 1000.0
