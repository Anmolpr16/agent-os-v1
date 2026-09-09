
from dataclasses import dataclass

@dataclass(frozen=True)
class RuntimePolicy:
    require_approval: bool = True
    require_evaluation: bool = True
    allow_parallel: bool = True
    max_output_length: int = 100000

    def __post_init__(self):
        if self.max_output_length <= 0:
            raise ValueError("max_output_length must be positive")

    def validate_output(self, output: str) -> None:
        if not isinstance(output, str):
            raise TypeError("output_must_be_string")
        if len(output) > self.max_output_length:
            raise ValueError("output_limit_exceeded")
