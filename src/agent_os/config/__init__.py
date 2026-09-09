from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeConfig:
    memory_path: str = ":memory:"
    provider_response: str = "task completed"
    provider_name: str = "mock"
    provider_model: str = "mock-v1"


__all__ = ["RuntimeConfig"]
