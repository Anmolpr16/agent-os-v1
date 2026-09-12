
from dataclasses import dataclass, field
from typing import Any

from agent_os.agents import AgentContext
from agent_os.governance import ApprovalStatus
from agent_os.runtime.audit import AuditLog
from agent_os.runtime.policy import RuntimePolicy
from agent_os.runtime.recovery import RecoveryController

@dataclass(frozen=True)
class PipelineResult:
    success: bool
    task_id: str
    output: str | None
    attempts: int
    approval: str | None
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

class EndToEndPipeline:
    def __init__(
        self,
        runtime,
        policy: RuntimePolicy | None = None,
        recovery: RecoveryController | None = None,
        audit: AuditLog | None = None,
    ):
        self.runtime = runtime
        self.policy = policy if policy is not None else runtime.policy
        self.recovery = recovery or RecoveryController(3)
        self.audit = audit or runtime.audit

    def run(
        self,
        task_id: str,
        objective: str,
        required_keywords: list[str],
    ) -> PipelineResult:
        if not task_id.strip():
            return PipelineResult(
                False, task_id, None, 0, None,
                error="task_id_required",
            )
        if not objective.strip():
            return PipelineResult(
                False, task_id, None, 0, None,
                error="objective_required",
            )

        self.audit.record("pipeline_started", "pipeline", task_id)
        if hasattr(self.runtime, "lifecycle"):
            self.runtime.lifecycle.emit("pipeline_started", task_id)

        holder = {}

        def execute():
            result = self.runtime.execute_closed_loop(
                task_id,
                objective,
                required_keywords,
            )
            holder["result"] = result
            if not result.success and result.approval is None:
                raise RuntimeError(
                    result.error or "pipeline_execution_failed"
                )
            return result

        recovered = self.recovery.run(execute)

        if not recovered.success:
            self.audit.record(
                "pipeline_failed",
                "pipeline",
                task_id,
                {"error": recovered.error},
            )
            if hasattr(self.runtime, "lifecycle"):
                self.runtime.lifecycle.emit(
                    "pipeline_failed",
                    task_id,
                    {"error": recovered.error},
                )
            return PipelineResult(
                False,
                task_id,
                None,
                recovered.attempts,
                None,
                error=recovered.error,
            )

        result = holder["result"]

        if result.approval == ApprovalStatus.PENDING:
            self.audit.record(
                "pipeline_pending_approval",
                "pipeline",
                task_id,
            )
            return PipelineResult(
                False,
                task_id,
                result.output,
                recovered.attempts,
                ApprovalStatus.PENDING.value,
                metadata={
                    "loop_attempts": len(result.attempts),
                    "runtime": self.runtime.snapshot(),
                },
                error=result.error or "human_approval_required",
            )

        if not result.success:
            self.audit.record(
                "pipeline_failed",
                "pipeline",
                task_id,
                {"error": result.error},
            )
            return PipelineResult(
                False,
                task_id,
                result.output,
                recovered.attempts,
                (
                    result.approval.value
                    if result.approval is not None
                    else None
                ),
                error=result.error or "pipeline_execution_failed",
            )
        if result.output is not None:
            self.policy.validate_output(result.output)

        approval = (
            result.approval.value
            if result.approval is not None
            else None
        )

        self.audit.record(
            "pipeline_completed",
            "pipeline",
            task_id,
            {
                "success": result.success,
                "approval": approval,
                "attempts": len(result.attempts),
            },
        )
        if hasattr(self.runtime, "lifecycle"):
            self.runtime.lifecycle.emit("pipeline_completed", task_id)

        return PipelineResult(
            True,
            task_id,
            result.output,
            recovered.attempts,
            approval,
            metadata={
                "loop_attempts": len(result.attempts),
                "runtime": self.runtime.snapshot(),
            },
        )
