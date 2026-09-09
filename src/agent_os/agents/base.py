from dataclasses import dataclass, field
from typing import Any

from agent_os.providers import Provider, ProviderRequest
from agent_os.tools import ToolExecutor


@dataclass
class AgentContext:
    """Runtime context supplied to an agent."""

    task_id: str
    objective: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Structured result produced by an agent."""

    output: str
    provider: str
    model: str
    metadata: dict[str, Any] = field(default_factory=dict)


class Agent:
    """Provider-backed agent with explicit tool access."""

    def __init__(
        self,
        provider: Provider,
        tool_executor: ToolExecutor | None = None,
    ):
        self.provider = provider
        self.tool_executor = tool_executor

    def run(self, context: AgentContext) -> AgentResult:
        response = self.provider.generate(
            ProviderRequest(
                prompt=context.objective,
                metadata=context.metadata,
            )
        )

        metadata = {
            **(response.metadata or {}),
        }

        tool_results = []

        for request in context.metadata.get(
            "tool_calls",
            [],
        ):
            if self.tool_executor is None:
                tool_results.append(
                    {
                        "tool_name": request["name"],
                        "success": False,
                        "output": None,
                        "error": "tool_executor_unavailable",
                    }
                )
                continue

            result = self.tool_executor.execute(
                request["name"],
                **request.get("arguments", {}),
            )

            tool_results.append(
                {
                    "tool_name": result.tool_name,
                    "success": result.success,
                    "output": result.output,
                    "error": result.error,
                }
            )

        metadata["tool_calls"] = tool_results

        return AgentResult(
            output=response.text,
            provider=response.provider,
            model=response.model,
            metadata=metadata,
        )
