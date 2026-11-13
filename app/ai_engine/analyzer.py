"""Swappable local and future LLM review analyzers."""
from __future__ import annotations

from abc import ABC, abstractmethod
import json
import os
from typing import Any

from pydantic import ValidationError

from app.ai_engine.prompts import review_prompt, system_prompt
from app.ai_engine.schemas import ReviewAnalysis, SemanticReviewAnalysis
from app.ingestion.normalizer import NormalizedFeedback
from app.risk_engine.risk import calculate_risk


class AnalyzerError(RuntimeError):
    """A safe, user-facing error returned by a configured analyzer."""


class ReviewAnalyzer(ABC):
    @abstractmethod
    def analyze(self, review: dict[str, Any] | NormalizedFeedback) -> ReviewAnalysis:
        """Analyze one validated legacy record or normalized feedback object."""


class MockReviewAnalyzer(ReviewAnalyzer):
    POSITIVE = ("excellent", "amazing", "great", "good", "helpful", "friendly", "satisfied", "recommend", "love")
    NEGATIVE = ("terrible", "worst", "never again", "ridiculous", "broken", "late", "refund", "ignored", "disappointed", "useless", "scam", "defective", "damaged")
    TOPICS = {
        "refund": ("refund", "money back", "return"),
        "delivery": ("delivery", "delivered", "courier", "late", "shipping", "arrived"),
        "customer_support": ("support", "customer service", "response", "agent", "helpdesk", "nobody"),
        "product_quality": ("broken", "quality", "defective", "damaged", "stopped working"),
        "pricing": ("expensive", "overpriced", "price", "cost"),
        "staff": ("staff", "employee", "waiter", "representative"),
    }

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}

    def analyze(self, review: dict[str, Any] | NormalizedFeedback) -> ReviewAnalysis:
        review = _as_record(review)
        text, rating = str(review["review"]).lower(), int(review["rating"])
        positive_hits = sum(word in text for word in self.POSITIVE)
        negative_hits = sum(word in text for word in self.NEGATIVE)
        sentiment = "negative" if rating <= 2 or negative_hits > positive_hits else "positive" if rating >= 4 or positive_hits > negative_hits else "neutral"
        sentiment_score = {"positive": 0.75, "neutral": 0.5, "negative": 0.75}[sentiment]
        topic = next((name for name, words in self.TOPICS.items() if any(word in text for word in words)), "general")
        intent = ("refund_request" if any(word in text for word in self.TOPICS["refund"])
                  else "question" if "?" in text or any(word in text.split() for word in ("how", "when", "why"))
                  else "complaint" if sentiment == "negative"
                  else "praise" if sentiment == "positive" else "feedback")
        emotion = ("angry" if any(word in text for word in ("worst", "ridiculous", "scam", "never again"))
                   else "frustrated" if any(word in text for word in ("late", "ignored", "no response", "nobody"))
                   else "disappointed" if any(word in text for word in ("disappointed", "expected better"))
                   else "happy" if sentiment == "positive" and any(word in text for word in ("excellent", "amazing", "love"))
                   else "satisfied" if sentiment == "positive" else "neutral")
        threshold = int(self.config.get("risk", {}).get("escalation_threshold", 50))
        risk = calculate_risk(rating, sentiment, emotion, intent, text, escalation_threshold=threshold)
        summary = f"{sentiment.capitalize()} {topic.replace('_', ' ')} feedback from {review['customer']}."
        action = self._action(topic, intent, risk.requires_escalation)
        return ReviewAnalysis(review_id=str(review["review_id"]), sentiment=sentiment, sentiment_score=sentiment_score,
                              emotion=emotion, topic=topic, intent=intent, risk_level=risk.level, risk_score=risk.score,
                              requires_escalation=risk.requires_escalation, summary=summary, recommended_action=action)

    @staticmethod
    def _action(topic: str, intent: str, escalated: bool) -> str:
        if escalated: return "Escalate immediately for manual intervention."
        if intent == "praise": return "Thank the customer for their positive feedback."
        if intent == "refund_request": return "Review refund request."
        if topic == "delivery": return "Respond and investigate delivery issue."
        if topic == "product_quality": return "Investigate product defect and offer resolution."
        if topic == "customer_support": return "Escalate to customer support."
        return "No immediate action required." if intent == "feedback" else "Respond and investigate the concern."


class NVIDIAReviewAnalyzer(ReviewAnalyzer):
    """NVIDIA NIM analyzer using its documented OpenAI-compatible chat endpoint."""

    provider = "nvidia"

    def __init__(self, config: dict[str, Any], client: Any | None = None) -> None:
        self.config = config
        self.api_key = os.getenv("NVIDIA_API_KEY", "").strip()
        self.model = os.getenv("NVIDIA_MODEL", "").strip()
        self.base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1").strip()
        if not self.api_key:
            raise AnalyzerError("NVIDIA_API_KEY is not configured. Set it in .env or switch ANALYZER_MODE=mock.")
        if not self.model:
            raise AnalyzerError("NVIDIA_MODEL is not configured.")
        if client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise AnalyzerError("The openai package is required for NVIDIA mode. Run pip install -r requirements.txt.") from exc
            client = OpenAI(base_url=self.base_url, api_key=self.api_key, timeout=60.0, max_retries=0)
        self.client = client

    def analyze(self, review: dict[str, Any] | NormalizedFeedback) -> ReviewAnalysis:
        review = _as_record(review)
        last_error: Exception | None = None
        threshold = int(self.config.get("risk", {}).get("escalation_threshold", 50))
        for attempt in range(2):
            try:
                content = self._request(review, use_json_mode=attempt == 0)
                semantic = SemanticReviewAnalysis.model_validate(_extract_json(content))
                return _with_risk(str(review["review_id"]), int(review["rating"]), str(review["review"]), semantic, threshold)
            except (AnalyzerError, ValidationError, json.JSONDecodeError, KeyError, TypeError) as exc:
                last_error = exc
            except Exception as exc:  # Network, rate-limit, and provider errors are kept secret-safe.
                last_error = exc
        raise AnalyzerError(f"NVIDIA analysis failed for review {review['review_id']}: {type(last_error).__name__}: {last_error}")

    def _request(self, review: dict[str, Any], use_json_mode: bool) -> str:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "system", "content": system_prompt(self.config)}, {"role": "user", "content": review_prompt(review)}],
            "temperature": 0,
            "max_tokens": 300,
            # Nemotron reasoning traces can consume the whole response budget before JSON.
            "extra_body": {"chat_template_kwargs": {"enable_thinking": False}},
        }
        if use_json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = self.client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        if not content:
            raise AnalyzerError("NVIDIA returned an empty response.")
        return content


def _extract_json(content: str) -> dict[str, Any]:
    """Extract the semantic JSON object even if a model includes surrounding text."""
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else ""
        cleaned = cleaned.rsplit("```", 1)[0].strip()
    decoder = json.JSONDecoder()
    candidates: list[dict[str, Any]] = []
    for position, char in enumerate(cleaned):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(cleaned[position:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            candidates.append(value)
    if not candidates:
        raise AnalyzerError("NVIDIA response did not contain a JSON object.")
    required = {"sentiment", "sentiment_score", "emotion", "topic", "intent", "summary", "recommended_action"}
    return next((value for value in candidates if required.issubset(value)), candidates[0])


def _as_record(review: dict[str, Any] | NormalizedFeedback) -> dict[str, Any]:
    if isinstance(review, NormalizedFeedback):
        return review.to_legacy_record()
    return review


def _with_risk(review_id: str, rating: int, review_text: str, semantic: SemanticReviewAnalysis, escalation_threshold: int = 50) -> ReviewAnalysis:
    """Attach deterministic risk after semantic analysis; the LLM never sets risk."""
    risk = calculate_risk(rating, semantic.sentiment, semantic.emotion, semantic.intent, review_text, escalation_threshold=escalation_threshold)
    return ReviewAnalysis(review_id=review_id, **semantic.model_dump(), risk_level=risk.level, risk_score=risk.score,
                          requires_escalation=risk.requires_escalation)
