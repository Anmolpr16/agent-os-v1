from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class HealthStatus:
    status: str
    version: str
    checks: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "version": self.version,
            "checks": dict(self.checks),
        }

def health(version: str = "2.0.0") -> HealthStatus:
    return HealthStatus(
        status="ok",
        version=version,
        checks={
            "runtime": "ok",
            "governance": "ok",
            "security": "ok",
            "evaluation": "ok",
        },
    )
