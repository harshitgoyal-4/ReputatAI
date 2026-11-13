"""CSV feedback connector and backward-compatible loading adapter."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.ingestion.base_connector import ConnectorResult, FeedbackConnector
from app.ingestion.normalizer import NormalizedFeedback


REQUIRED_COLUMNS = ("review_id", "date", "rating", "platform", "customer", "review")


class LoadResult:
    def __init__(self, records: list[dict[str, object]], errors: list[str]) -> None:
        self.records = records
        self.errors = errors


class CSVConnector(FeedbackConnector):
    """Load CSV feedback, validate rows, and return normalized objects."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def fetch(self) -> ConnectorResult:
        try:
            frame = pd.read_csv(self.path, dtype={"review_id": "string"})
        except (OSError, pd.errors.ParserError, UnicodeDecodeError) as exc:
            return ConnectorResult([], [f"Could not read CSV: {exc}"])

        missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
        if missing:
            return ConnectorResult([], [f"Missing required columns: {', '.join(missing)}"])

        records: list[NormalizedFeedback] = []
        errors: list[str] = []
        for row_number, row in frame.iterrows():
            display_row = row_number + 2
            review_id = row["review_id"]
            review = row["review"]
            rating = pd.to_numeric(row["rating"], errors="coerce")
            if pd.isna(review_id) or not str(review_id).strip():
                errors.append(f"Row {display_row}: review_id cannot be empty.")
                continue
            if pd.isna(review) or not str(review).strip():
                errors.append(f"Row {display_row} (review {review_id}): review text cannot be empty.")
                continue
            if pd.isna(rating) or rating < 1 or rating > 5 or float(rating) != int(rating):
                errors.append(f"Row {display_row} (review {review_id}): rating must be an integer from 1 to 5.")
                continue
            records.append(NormalizedFeedback(
                id=str(review_id).strip(),
                date=str(row["date"]),
                platform=str(row["platform"]),
                author=str(row["customer"]),
                text=str(review).strip(),
                rating=int(rating),
            ))
        return ConnectorResult(records, errors)


def load_reviews(path: Path) -> LoadResult:
    """Load valid CSV rows with the legacy dictionary shape preserved."""
    result = CSVConnector(path).fetch()
    return LoadResult([record.to_legacy_record() for record in result.records], result.errors)
