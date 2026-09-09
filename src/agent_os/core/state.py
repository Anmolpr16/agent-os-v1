from enum import Enum


class State(str, Enum):
    INTAKE = "intake"
    MEMORY_RETRIEVAL = "memory_retrieval"
    PLANNING = "planning"
    EXECUTION = "execution"
    VERIFICATION = "verification"
    FINALIZATION = "finalization"
    MEMORY_CONSOLIDATION = "memory_consolidation"
    COMPLETE = "complete"
    FAILED = "failed"


DEFAULT_ORDER = [
    State.INTAKE,
    State.MEMORY_RETRIEVAL,
    State.PLANNING,
    State.EXECUTION,
    State.VERIFICATION,
    State.FINALIZATION,
    State.MEMORY_CONSOLIDATION,
    State.COMPLETE,
]
