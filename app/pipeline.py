"""Reusable application layer for processing validated review records."""
from __future__ import annotations

from typing import Any, Callable

from app.ai_engine.analyzer import AnalyzerError, ReviewAnalyzer
from app.analytics.analytics import calculate_analytics
from app.risk_engine.risk import calculate_risk


def _failed_record(record: dict[str, Any], provider: str, error: str, escalation_threshold: int = 50) -> dict[str, Any]:
    """Preserve a failed provider row so it remains visible for manual review."""
    risk = calculate_risk(int(record["rating"]), "neutral", "neutral", "feedback", str(record["review"]), escalation_threshold=escalation_threshold)
    return {**record, "sentiment": "neutral", "sentiment_score": 0.0, "emotion": "neutral", "topic": "general",
            "intent": "feedback", "risk_level": risk.level, "risk_score": risk.score,
            "requires_escalation": risk.requires_escalation, "summary": "Analysis failed; no LLM summary available.",
            "recommended_action": "Manually review this feedback.", "analysis_provider": provider,
            "analysis_status": "failed", "analysis_error": error}


def process_reviews(
    records: list[dict[str, Any]], analyzer: ReviewAnalyzer, provider: str,
    on_progress: Callable[[int, int, dict[str, Any]], None] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Analyze records sequentially, retaining failed LLM rows for manual review."""
    analyzed: list[dict[str, Any]] = []
    threshold = int(getattr(analyzer, "config", {}).get("risk", {}).get("escalation_threshold", 50)) if hasattr(analyzer, "config") else 50
    for index, record in enumerate(records, start=1):
        try:
            analysis = analyzer.analyze(record)
            analyzed.append({**record, **analysis.model_dump(), "analysis_provider": provider,
                             "analysis_status": "success", "analysis_error": ""})
        except AnalyzerError as exc:
            analyzed.append(_failed_record(record, provider, str(exc), escalation_threshold=threshold))
        if on_progress:
            on_progress(index, len(records), record)
    return analyzed, calculate_analytics(analyzed)
