from dataclasses import dataclass


@dataclass(frozen=True)
class MetricResult:
    name: str
    score: float

    @property
    def passed(self) -> bool:
        return self.score >= 1.0


def keyword_coverage(
    output: str,
    required: list[str],
) -> MetricResult:
    if not required:
        return MetricResult(
            name="keyword_coverage",
            score=1.0,
        )

    text = output.lower()

    matched = sum(
        1
        for keyword in required
        if keyword.lower() in text
    )

    return MetricResult(
        name="keyword_coverage",
        score=matched / len(required),
    )
