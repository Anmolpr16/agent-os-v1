from dataclasses import dataclass, field
from threading import RLock
from typing import Any


@dataclass
class SharedState:
    """Thread-safe shared state for coordinated agent execution."""

    values: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._lock = RLock()

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self.values.get(key, default)

    def set(self, key: str, value: Any) -> None:
        if not key.strip():
            raise ValueError("state_key_required")
        with self._lock:
            self.values[key] = value

    def update(self, values: dict[str, Any]) -> None:
        for key in values:
            if not key.strip():
                raise ValueError("state_key_required")
        with self._lock:
            self.values.update(values)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return dict(self.values)


@dataclass(frozen=True)
class AgentMessage:
    sender: str
    recipient: str
    task_id: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


class MessageBus:
    """In-process message bus for bounded agent communication."""

    def __init__(self) -> None:
        self._messages: list[AgentMessage] = []
        self._lock = RLock()

    def send(self, message: AgentMessage) -> None:
        if not message.sender.strip():
            raise ValueError("sender_required")
        if not message.recipient.strip():
            raise ValueError("recipient_required")
        if not message.task_id.strip():
            raise ValueError("task_id_required")
        if not message.content.strip():
            raise ValueError("message_content_required")

        with self._lock:
            self._messages.append(message)

    def receive(
        self,
        recipient: str,
        task_id: str | None = None,
    ) -> list[AgentMessage]:
        with self._lock:
            return [
                message
                for message in self._messages
                if message.recipient == recipient
                and (
                    task_id is None
                    or message.task_id == task_id
                )
            ]

    def all(self) -> list[AgentMessage]:
        with self._lock:
            return list(self._messages)
