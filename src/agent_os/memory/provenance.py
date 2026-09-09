from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib


@dataclass(frozen=True)
class Provenance:
    """Traceable origin information for a memory item."""

    uri: str | None = None
    title: str | None = None
    content_hash: str | None = None
    created_at: str = ""

    @classmethod
    def from_content(
        cls,
        content: str,
        uri: str | None = None,
        title: str | None = None,
    ) -> "Provenance":
        digest = hashlib.sha256(
            content.encode("utf-8")
        ).hexdigest()

        return cls(
            uri=uri,
            title=title,
            content_hash=digest,
            created_at=datetime.now(
                timezone.utc
            ).isoformat(),
        )
