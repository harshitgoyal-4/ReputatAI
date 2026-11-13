"""Structured output model for review analysis."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ReviewAnalysis(BaseModel):
    review_id: str
    sentiment: Literal["positive", "neutral", "negative"]
    sentiment_score: float = Field(ge=0, le=1)
    emotion: Literal["happy", "satisfied", "neutral", "disappointed", "frustrated", "angry"]
    topic: str = Field(min_length=1)
    intent: Literal["praise", "complaint", "question", "refund_request", "feedback"]
    risk_level: Literal["low", "medium", "high", "critical"]
    risk_score: int = Field(ge=0, le=100)
    requires_escalation: bool
    summary: str
    recommended_action: str


class SemanticReviewAnalysis(BaseModel):
    """LLM-provided signals, before deterministic risk enrichment."""
    sentiment: Literal["positive", "neutral", "negative"]
    sentiment_score: float = Field(ge=0, le=1)
    emotion: Literal["happy", "satisfied", "neutral", "disappointed", "frustrated", "angry"]
    topic: str = Field(min_length=1)
    intent: Literal["praise", "complaint", "question", "refund_request", "feedback"]
    summary: str = Field(min_length=1)
    recommended_action: str = Field(min_length=1)
