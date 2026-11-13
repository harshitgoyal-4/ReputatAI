"""Interfaces shared by feedback data-source connectors."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.ingestion.normalizer import NormalizedFeedback


@dataclass
class ConnectorResult:
    """Normalized records and non-fatal validation or read errors."""

    records: list[NormalizedFeedback]
    errors: list[str]


class FeedbackConnector(ABC):
    """Contract for connectors that bring feedback into ReputeAI."""

    @abstractmethod
    def fetch(self) -> ConnectorResult:
        """Fetch and normalize feedback from the connector's configured source."""