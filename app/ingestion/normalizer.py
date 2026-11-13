"""Source-independent feedback representation and legacy record conversion."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class NormalizedFeedback:
    """Common feedback shape returned by every connector."""

    id: str
    date: str
    platform: str
    author: str
    text: str
    rating: int | float | None = None
    source_url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_legacy_record(self) -> dict[str, object]:
        """Keep the current core and UI compatible with normalized feedback."""
        record: dict[str, object] = {
            "review_id": self.id,
            "date": self.date,
            "rating": int(self.rating) if self.rating is not None else 3,
            "platform": self.platform,
            "customer": self.author,
            "review": self.text,
        }
        if self.source_url is not None:
            record["source_url"] = self.source_url
        if self.metadata:
            record["metadata"] = self.metadata
        return record