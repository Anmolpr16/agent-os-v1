from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeConfig:
    memory_path: str = ":memory:"
    provider_response: str = "task completed"
    provider_name: str = "mock"
    provider_model: str = "mock-v1"

    def __post_init__(self) -> None:
        for field_name in (
            "memory_path",
            "provider_name",
            "provider_model",
            "provider_response",
        ):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} must not be empty")


__all__ = ["RuntimeConfig"]
