from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProviderRequest:
    prompt: str
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class ProviderResponse:
    text: str
    provider: str
    model: str
    metadata: dict[str, Any] | None = None


class Provider(ABC):
    """Provider-neutral interface for model backends."""

    @abstractmethod
    def generate(
        self,
        request: ProviderRequest,
    ) -> ProviderResponse:
        raise NotImplementedError
