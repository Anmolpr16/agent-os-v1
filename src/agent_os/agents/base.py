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

        return AgentResult(
            output=response.text,
            provider=response.provider,
            model=response.model,
            metadata=response.metadata or {},
        )
