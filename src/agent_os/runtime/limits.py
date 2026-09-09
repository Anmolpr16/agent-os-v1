from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionLimits:
    """Explicit resource limits for coordinated execution."""

    max_tasks: int = 100
    max_workers: int = 8

    def __post_init__(self) -> None:
        if self.max_tasks <= 0:
            raise ValueError("max_tasks must be positive")
        if self.max_workers <= 0:
            raise ValueError("max_workers must be positive")
        if self.max_workers > self.max_tasks:
            raise ValueError(
                "max_workers must not exceed max_tasks"
            )
