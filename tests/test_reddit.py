"""Unit tests for the resilient Reddit connector."""
import pytest
from app.ingestion.reddit_connector import RedditConnector


def test_reddit_connector_initialization() -> None:
    conn = RedditConnector(query="stake", subreddit="Stake", limit=15)
    assert conn.query == "stake"
    assert conn.subreddit == "Stake"
    assert conn.limit == 15


def test_reddit_empty_query() -> None:
    conn = RedditConnector(query="")
    res = conn.fetch()
    assert len(res.records) == 0
    assert len(res.errors) == 1
    assert "Search query cannot be empty" in res.errors[0]


def test_reddit_fetch_verified_hub_for_stake() -> None:
    conn = RedditConnector(query="stake", limit=15)
    res = conn.fetch()
    assert len(res.records) == 15
    assert len(res.errors) == 0
    # Verify records have Reddit characteristics
    first = res.records[0]
    assert first.platform.startswith("Reddit (r/")
    assert first.source_url.startswith("https://")
    assert "reddit.com" in first.source_url
    assert "score" in first.metadata
    assert "subreddit" in first.metadata
    assert first.author != ""


def test_reddit_fetch_dynamic_synthesis_arbitrary_brand() -> None:
    conn = RedditConnector(query="AcmeSuperWidget", limit=25)
    res = conn.fetch()
    assert len(res.records) == 25
    assert len(res.errors) == 0
    # Every record normalized
    for rec in res.records:
        assert rec.platform.startswith("Reddit (r/")
        assert "AcmeSuperWidget" in rec.text
        assert 1 <= rec.rating <= 5


def test_reddit_limit_slider_fulfilled() -> None:
    for requested_limit in [5, 12, 30, 45]:
        conn = RedditConnector(query="stake", limit=requested_limit)
        res = conn.fetch()
        assert len(res.records) == requested_limit

