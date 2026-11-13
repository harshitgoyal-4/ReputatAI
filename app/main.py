"""Command-line entry point for the local ReputeAI MVP."""
from __future__ import annotations

import json

import pandas as pd

from app.ai_engine.analyzer import AnalyzerError, MockReviewAnalyzer, NVIDIAReviewAnalyzer, ReviewAnalyzer
from app.analytics.analytics import calculate_analytics
from app.core.config import DATA_DIR, OUTPUT_DIR, analyzer_mode, client_config, max_reviews
from app.ingestion.csv_loader import load_reviews
from app.pipeline import _failed_record, process_reviews


def get_analyzer(mode: str, config: dict[str, object] | None = None) -> ReviewAnalyzer:
    if mode == "mock":
        return MockReviewAnalyzer(config or client_config())
    if mode == "nvidia":
        return NVIDIAReviewAnalyzer(config or client_config())
    raise ValueError(f"Unknown ANALYZER_MODE '{mode}'. Use 'mock' or 'nvidia'.")


def run_pipeline() -> tuple[list[dict[str, object]], dict[str, object]]:
    mode = analyzer_mode()
    config = client_config()
    analyzer = get_analyzer(mode, config)
    limit = max_reviews()
    display_mode = "NVIDIA" if mode == "nvidia" else "Mock"
    print(f"## ReputeAI MVP Pipeline\nAnalyzer Mode: {display_mode}")
    if mode == "nvidia":
        print(f"Provider: NVIDIA\nModel: {analyzer.model}")
    print("\nLoading reviews...")
    loaded = load_reviews(DATA_DIR / "reviews.csv")
    print(f"{len(loaded.records)} valid reviews loaded.")
    if loaded.errors:
        print(f"Validation warnings ({len(loaded.errors)}):")
        for error in loaded.errors:
            print(f"- {error}")
    if not loaded.records:
        raise RuntimeError("No valid reviews to analyze.")

    records = loaded.records[:limit] if limit else loaded.records
    if limit:
        print(f"Processing limit: {len(records)} review(s) (MAX_REVIEWS={limit}).")
    print("\nProcessing reviews...")
    def report_progress(index: int, total: int, record: dict[str, object]) -> None:
        print(f"[{index}/{total}] Review {record['review_id']} processed")
    analyzed, analytics = process_reviews(records, analyzer, mode, report_progress)
    print("\nRunning risk analysis...\nGenerating analytics...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(analyzed).to_csv(OUTPUT_DIR / "analyzed_reviews.csv", index=False)
    (OUTPUT_DIR / "summary.json").write_text(json.dumps(analytics, indent=2), encoding="utf-8")
    _print_summary(analytics)
    print(f"\nOutput saved to:\n{OUTPUT_DIR / 'analyzed_reviews.csv'}\n{OUTPUT_DIR / 'summary.json'}")
    return analyzed, analytics


def _print_summary(summary: dict[str, object]) -> None:
    print("\nAnalysis complete.\n\n## REPUTATION SUMMARY")
    print(f"Total Reviews: {summary['total_reviews']}\nAverage Rating: {summary['average_rating']}\nPositive: {summary['positive_percentage']}%")
    print(f"Neutral: {summary['neutral_percentage']}%\nNegative: {summary['negative_percentage']}%\nAverage Risk: {summary['average_risk_score']}")
    print(f"High Risk: {summary['high_risk_reviews']}\nCritical: {summary['critical_reviews']}\nEscalations Required: {summary['requiring_escalation']}")
    print(f"Reputation Score: {summary['reputation_score']}/100\n\nTop Topics:")
    for index, (topic, _) in enumerate(sorted(summary['topic_counts'].items(), key=lambda item: (-item[1], item[0]))[:3], 1):
        print(f"{index}. {topic}")


if __name__ == "__main__":
    run_pipeline()
