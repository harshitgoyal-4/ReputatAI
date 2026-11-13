"""Centralized prompts for LLM review analysis."""
from __future__ import annotations

import json
from typing import Any


def system_prompt(config: dict[str, Any]) -> str:
    """Build concise, client-aware instructions for structured review analysis."""
    categories = config.get("categories", ["general"])
    client = config.get("client", {})
    brand = config.get("brand", {})
    return (
        "You are a Business Reputation Intelligence Analyst. Analyze customer feedback objectively "
        "and convert it into structured business intelligence. Do not invent information, assume "
        "facts not present, or exaggerate sentiment. Return ONLY one JSON object with: sentiment, "
        "sentiment_score, emotion, topic, intent, summary, recommended_action. "
        "sentiment must be positive, neutral, or negative; sentiment_score is confidence from 0.0 to 1.0. "
        "emotion must be happy, satisfied, neutral, disappointed, frustrated, or angry. "
        f"topic must be one of: {', '.join(categories)}. "
        "intent must be praise, complaint, question, refund_request, or feedback. "
        f"Client: {client.get('name', 'Unknown')} ({client.get('industry', 'general')}); "
        f"recommended-action tone: {brand.get('tone', 'professional')}, "
        f"style: {brand.get('response_style', 'empathetic')}. Do not repeat the input review or include markdown."
    )


def review_prompt(review: dict[str, Any]) -> str:
    """Serialize only the review context the model needs."""
    payload = {key: review[key] for key in ("review_id", "rating", "platform", "review")}
    return f"Analyze this review:\n{json.dumps(payload, ensure_ascii=False)}"
