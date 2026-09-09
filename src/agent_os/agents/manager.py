from .base import Agent


class AgentManager:
    """Registry and lifecycle manager for named agents."""

    def __init__(self):
        self._agents: dict[str, Agent] = {}

    def register(self, name: str, agent: Agent) -> None:
        if not name.strip():
            raise ValueError("agent_name_missing")

        if name in self._agents:
            raise ValueError(
                f"agent_already_registered:{name}"
            )

        self._agents[name] = agent

    def get(self, name: str) -> Agent:
        try:
            return self._agents[name]
        except KeyError:
            raise KeyError(
                f"agent_not_registered:{name}"
            ) from None

    def list(self) -> list[str]:
        return sorted(self._agents)
