"""Analytics and transparent reputation score calculation."""
from __future__ import annotations

from collections import Counter
from typing import Any


def calculate_analytics(records: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(records)
    if not total:
        return {"total_reviews": 0, "reputation_score": 0, "topic_counts": {}, "sentiment_counts": {},
                "risk_level_counts": {}, "positive_percentage": 0, "neutral_percentage": 0,
                "negative_percentage": 0, "average_rating": 0, "average_risk_score": 0,
                "high_risk_reviews": 0, "critical_reviews": 0, "requiring_escalation": 0,
                "reputation_score_formula": REPUTATION_SCORE_FORMULA, "trend_data": []}
    sentiments, topics, levels = (Counter(row["sentiment"] for row in records), Counter(row["topic"] for row in records), Counter(row["risk_level"] for row in records))
    positive_pct, neutral_pct, negative_pct = (round(sentiments[name] / total * 100, 2) for name in ("positive", "neutral", "negative"))
    average_rating = round(sum(float(row["rating"]) for row in records) / total, 2)
    average_risk = round(sum(float(row["risk_score"]) for row in records) / total, 2)
    reputation = max(0, min(100, average_rating / 5 * 50 + positive_pct * .35 + neutral_pct * .15 - average_risk * .25))
    return {"total_reviews": total, "positive_percentage": positive_pct, "neutral_percentage": neutral_pct,
            "negative_percentage": negative_pct, "average_rating": average_rating, "average_risk_score": average_risk,
            "high_risk_reviews": levels["high"], "critical_reviews": levels["critical"],
            "requiring_escalation": sum(bool(row["requires_escalation"]) for row in records), "topic_counts": dict(topics),
            "sentiment_counts": dict(sentiments), "risk_level_counts": dict(levels), "reputation_score": round(reputation, 2),
            "trend_data": _trend_data(records),
            "reputation_score_formula": REPUTATION_SCORE_FORMULA}


REPUTATION_SCORE_FORMULA = "(average_rating / 5 * 50) + (positive_percentage * 0.35) + (neutral_percentage * 0.15) - (average_risk_score * 0.25), clamped to 0-100"


def _trend_data(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return daily metrics for records with usable dates."""
    grouped: dict[str, dict[str, Any]] = {}
    for record in records:
        date = str(record.get("date", ""))[:10]
        if len(date) != 10 or date[4] != "-" or date[7] != "-":
            continue
        try:
            year, month, day = (int(part) for part in date.split("-"))
            from datetime import date as date_type
            date_type(year, month, day)
        except (TypeError, ValueError):
            continue
        bucket = grouped.setdefault(date, {"date": date, "reviews": 0, "rating_total": 0.0, "negative_reviews": 0})
        bucket["reviews"] += 1
        bucket["rating_total"] += float(record.get("rating", 0))
        bucket["negative_reviews"] += int(record.get("sentiment") == "negative")
    return [{"date": bucket["date"], "reviews": bucket["reviews"], "negative_reviews": bucket["negative_reviews"],
             "average_rating": round(bucket["rating_total"] / bucket["reviews"], 2)}
            for _, bucket in sorted(grouped.items())]


def generate_business_insights(records: list[dict[str, Any]], analytics: dict[str, Any] | None = None) -> list[str]:
    """Return deterministic, evidence-based observations for the presentation layer."""
    if not records:
        return ["No analyzed reviews are available yet."]
    summary = analytics or calculate_analytics(records)
    insights: list[str] = []
    sentiment = max(summary["sentiment_counts"], key=summary["sentiment_counts"].get, default=None)
    if sentiment and summary[f"{sentiment}_percentage"] > 50:
        insights.append(f"Customer sentiment is predominantly {sentiment} ({summary[f'{sentiment}_percentage']}%).")
    negative_topics = Counter(row["topic"] for row in records if row.get("sentiment") == "negative")
    if negative_topics and negative_topics.most_common(1)[0][1] / max(1, sum(negative_topics.values())) >= 0.5:
        topic, count = negative_topics.most_common(1)[0]
        insights.append(f"{topic.replace('_', ' ').title()} is the most frequent negative issue ({count} review(s)).")
    high_risk = summary["high_risk_reviews"] + summary["critical_reviews"]
    if high_risk:
        insights.append(f"{high_risk} high- or critical-risk review(s) require human attention.")
    escalation_topics = Counter(row["topic"] for row in records if bool(row.get("requires_escalation")))
    if escalation_topics:
        topic, count = escalation_topics.most_common(1)[0]
        insights.append(f"{topic.replace('_', ' ').title()} accounts for {count} review(s) requiring escalation.")
    return insights
