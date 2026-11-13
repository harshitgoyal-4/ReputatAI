"""Tests for Trustpilot & Web Reviews Connector."""
import pytest

from app.ingestion.trustpilot_connector import TrustpilotConnector


def test_trustpilot_connector_initialization():
    """TrustpilotConnector should clean URLs and parse domain accurately."""
    conn1 = TrustpilotConnector("https://www.stake.com/")
    assert conn1.domain == "stake.com"
    assert conn1.brand_key == "stake"

    conn2 = TrustpilotConnector("spotify")
    assert conn2.domain == "spotify.com"
    assert conn2.brand_key == "spotify"


def test_trustpilot_fetch_verified_hub():
    """Fetching verified reviews for Stake should return structured NormalizedFeedback."""
    conn = TrustpilotConnector("stake.com", limit=5)
    res = conn.fetch()

    assert len(res.records) >= 5
    assert len(res.records) <= 5

    rec = res.records[0]
    assert "Trustpilot" in rec.platform
    assert rec.author != ""
    assert rec.rating in [1, 2, 3, 4, 5]
    assert "stake.com" in rec.source_url
    assert "tp_" in rec.id


def test_trustpilot_to_legacy_record():
    """Trustpilot NormalizedFeedback should cleanly convert to legacy dict."""
    conn = TrustpilotConnector("stake.com", limit=2)
    res = conn.fetch()
    legacy = [r.to_legacy_record() for r in res.records]

    assert len(legacy) == 2
    assert "review_id" in legacy[0]
    assert "review" in legacy[0]
    assert "rating" in legacy[0]
    assert "customer" in legacy[0]
    assert "platform" in legacy[0]


def test_trustpilot_empty_input():
    """Empty domain should return an error gracefully."""
    conn = TrustpilotConnector("", limit=5)
    res = conn.fetch()
    assert len(res.records) == 0
    assert len(res.errors) >= 1

