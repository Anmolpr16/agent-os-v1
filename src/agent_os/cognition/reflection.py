from dataclasses import dataclass, field


@dataclass
class Reflection:
    """Structured analysis of a completed task step."""

    outcome: str
    what_worked: list[str] = field(default_factory=list)
    what_failed: list[str] = field(default_factory=list)
    lessons: list[str] = field(default_factory=list)
    confidence: float = 0.5

    @property
    def has_failures(self) -> bool:
        return bool(self.what_failed)

    @property
    def has_lessons(self) -> bool:
        return bool(self.lessons)


def reflect(
    outcome: str,
    what_worked: list[str] | None = None,
    what_failed: list[str] | None = None,
    lessons: list[str] | None = None,
    confidence: float = 0.5,
) -> Reflection:
    """Create a structured reflection from an outcome."""

    return Reflection(
        outcome=outcome,
        what_worked=what_worked or [],
        what_failed=what_failed or [],
        lessons=lessons or [],
        confidence=max(0.0, min(1.0, confidence)),
    )
