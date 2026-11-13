"""Configurable customer-response providers with an explicit human approval step."""
from __future__ import annotations

from abc import ABC, abstractmethod
import os
from typing import Any

from app.core.config import analyzer_mode


class ResponseGeneratorError(RuntimeError):
    """Safe error presented when a response cannot be generated."""


class BaseResponseGenerator(ABC):
    """Common interface for local and hosted response providers."""

    @abstractmethod
    def generate(self, review: dict[str, Any], analysis: dict[str, Any]) -> str:
        """Return a draft response without publishing it."""

    def generate_response(self, review: dict[str, Any], analysis: dict[str, Any]) -> str:
        return self.generate(review, analysis)


class MockResponseGenerator(BaseResponseGenerator):
    """Deterministic, offline response drafts for development and testing."""

    def __init__(self, config: dict[str, Any], client: Any | None = None) -> None:
        self.config = config
        self.response_config = config.get("response", {})

    def generate(self, review: dict[str, Any], analysis: dict[str, Any]) -> str:
        if not self.response_config.get("enabled", True):
            raise ResponseGeneratorError("Response generation is disabled in client configuration.")
        client = self.config.get("client", {}).get("name", "our team")
        sentiment = str(analysis.get("sentiment", "neutral"))
        topic = str(analysis.get("topic", "concern")).replace("_", " ")
        if not self.response_config.get("allow_compensation_promises", False) and analysis.get("intent") == "refund_request":
            topic = "this concern"
        if sentiment == "positive":
            return f"Thank you for sharing your feedback. We appreciate your support and are glad to hear about your experience. — {client}"
        if sentiment == "neutral":
            opening = "Thank you for taking the time to share your feedback."
        else:
            opening = f"We're sorry to hear about your experience with {topic}."
        next_step = " We'd appreciate the opportunity to review your concern and help resolve it."
        if analysis.get("requires_escalation") and self.response_config.get("request_contact_for_escalation", True):
            next_step = " Please contact our support team with your order details so we can review this and assist you further."
        elif self.response_config.get("allow_compensation_promises", False) and analysis.get("intent") == "refund_request":
            next_step = " Please contact our support team so we can review your request and discuss available options."
        return f"{opening}{next_step} — {client}"


class NVIDIAResponseGenerator(BaseResponseGenerator):
    """NVIDIA NIM response provider."""

    def __init__(self, config: dict[str, Any], client: Any | None = None) -> None:
        self.config = config
        self.response_config = config.get("response", {})
        self.api_key = os.getenv("NVIDIA_API_KEY", "").strip()
        self.model = os.getenv("NVIDIA_MODEL", "").strip()
        self.base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1").strip()
        if client is None:
            if not self.api_key:
                raise ResponseGeneratorError("NVIDIA_API_KEY is not configured. Switch to mock analysis or configure NVIDIA.")
            if not self.model:
                raise ResponseGeneratorError("NVIDIA_MODEL is not configured.")
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise ResponseGeneratorError("The openai package is required for NVIDIA response generation.") from exc
            client = OpenAI(base_url=self.base_url, api_key=self.api_key, timeout=60.0, max_retries=0)
        self.client = client

    def generate(self, review: dict[str, Any], analysis: dict[str, Any]) -> str:
        """Return a draft response, bounded by configured behavior and length."""
        if not self.response_config.get("enabled", True):
            raise ResponseGeneratorError("Response generation is disabled in client configuration.")
        try:
            result = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._system_prompt()},
                    {"role": "user", "content": self._user_prompt(review, analysis)},
                ],
                temperature=0.3,
                max_tokens=int(self.response_config.get("max_length", 120)) + 80,
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            )
            content = result.choices[0].message.content
        except Exception as exc:
            raise ResponseGeneratorError("Response generation failed. Please try again or draft a response manually.") from exc
        if not content or not content.strip():
            raise ResponseGeneratorError("NVIDIA returned an empty response draft.")
        return content.strip()

    def _system_prompt(self) -> str:
        client = self.config.get("client", {})
        brand = self.config.get("brand", {})
        response = self.response_config
        return (
            "You are a Customer Reputation Response Specialist. Write only a concise customer-facing response. "
            f"Client: {client.get('name', 'the business')}; industry: {client.get('industry', 'general')}. "
            f"Tone: {response.get('tone', brand.get('tone', 'professional'))}; "
            f"style: {response.get('style', brand.get('response_style', 'empathetic'))}. "
            "Be professional and empathetic. Do not argue, reveal analysis, claim an action already occurred, "
            "invent compensation, or make unsupported promises. Never say that you have escalated, investigated, "
            "contacted, or resolved anything; instead, say that the concern will be reviewed. "
            f"Compensation promises allowed: {bool(response.get('allow_compensation_promises', False))}. "
            f"For escalations, request direct contact: {bool(response.get('request_contact_for_escalation', True))}. "
            f"Keep the draft under {int(response.get('max_length', 120))} words."
        )

    @staticmethod
    def _user_prompt(review: dict[str, Any], analysis: dict[str, Any]) -> str:
        return (
            "Draft a response to this review.\n"
            f"Review: {review.get('review', '')}\n"
            f"Sentiment: {analysis.get('sentiment', '')}; emotion: {analysis.get('emotion', '')}; "
            f"topic: {analysis.get('topic', '')}; intent: {analysis.get('intent', '')}.\n"
            f"Summary: {analysis.get('summary', '')}\n"
            f"Recommended action: {analysis.get('recommended_action', '')}\n"
            f"Risk level: {analysis.get('risk_level', '')}; "
            f"Escalation required: {analysis.get('requires_escalation', False)}."
        )


def get_response_generator(provider: str, config: dict[str, Any], client: Any | None = None) -> BaseResponseGenerator:
    """Select one response provider at the application boundary."""
    normalized = provider.strip().lower()
    if normalized == "mock":
        return MockResponseGenerator(config, client)
    if normalized == "nvidia":
        return NVIDIAResponseGenerator(config, client)
    raise ValueError(f"Unknown response provider '{provider}'. Use 'mock' or 'nvidia'.")


class ResponseGenerator:
    """Backward-compatible provider-selected response generator."""

    def __new__(cls, config: dict[str, Any], client: Any | None = None, provider: str | None = None) -> BaseResponseGenerator:
        return get_response_generator(provider or analyzer_mode(), config, client)
