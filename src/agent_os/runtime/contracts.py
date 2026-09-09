
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class RuntimeRequest:
    task_id: str
    objective: str
    required_keywords: tuple[str, ...] = ()
    metadata: dict[str, Any] | None = None

@dataclass(frozen=True)
class RuntimeResponse:
    success: bool
    task_id: str
    output: str | None
    error: str | None = None
    metadata: dict[str, Any] | None = None

def validate_request(request: RuntimeRequest) -> None:
    if not request.task_id.strip():
        raise ValueError("task_id_required")
    if not request.objective.strip():
        raise ValueError("objective_required")
    if request.metadata is not None and not isinstance(
        request.metadata, dict
    ):
        raise ValueError("metadata_object_required")
