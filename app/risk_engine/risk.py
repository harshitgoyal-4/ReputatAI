"""Deterministic risk scoring rules."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


SEVERE_KEYWORDS = {"scam": 25, "never again": 15, "legal": 25, "fraud": 30, "unsafe": 30, "police": 30}
FORCE_ESCALATION = {"fraud", "legal", "unsafe", "police"}


@dataclass(frozen=True)
class RiskResult:
    score: int
    level: Literal["low", "medium", "high", "critical"]
    requires_escalation: bool


def calculate_risk(
    rating: int,
    sentiment: str,
    emotion: str,
    intent: str,
    review_text: str,
    escalation_threshold: int = 50,
) -> RiskResult:
    """Score risk with documented, auditable rules; never uses a model-generated score."""
    score = {1: 35, 2: 25, 3: 10}.get(rating, 0)
    score += 20 if sentiment == "negative" else 0
    score += {"disappointed": 5, "frustrated": 10, "angry": 20}.get(emotion, 0)
    score += {"complaint": 10, "refund_request": 15}.get(intent, 0)
    text = review_text.lower()
    matched_forced = any(keyword in text for keyword in FORCE_ESCALATION)
    score += sum(points for keyword, points in SEVERE_KEYWORDS.items() if keyword in text)
    score = max(0, min(100, score))
    level = "low" if score <= 24 else "medium" if score <= 49 else "high" if score <= 74 else "critical"
    return RiskResult(score, level, score >= escalation_threshold or matched_forced)
