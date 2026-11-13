"""Tests for session persistence and AI brand profiling."""
import pytest
from pathlib import Path

from app.core.brand_profiler import (
    BUILTIN_PROFILES,
    generate_brand_profile,
    get_available_presets,
)
from app.core.config import (
    clear_session_cache,
    client_config,
    load_session_cache,
    save_client_config,
    save_session_cache,
)


def test_session_cache_save_load_clear(tmp_path, monkeypatch):
    """Session cache should correctly save to disk, load, and clear."""
    monkeypatch.setattr("app.core.config.CACHE_DIR", tmp_path)

    sample_state = {
        "records": [{"review_id": "r1", "review": "Great app", "sentiment": "positive"}],
        "analytics": {"total_reviews": 1, "net_sentiment_score": 100},
        "provider": "mock",
        "statuses": {"r1": "approved"},
        "responses": {"r1": "Thank you!"},
        "analyzed_at": "2026-09-30 12:00:00",
        "target_query": "Test Run",
    }

    # Save
    save_session_cache(sample_state)

    # Load
    loaded = load_session_cache()
    assert loaded is not None
    assert len(loaded["records"]) == 1
    assert loaded["records"][0]["review_id"] == "r1"
    assert loaded["target_query"] == "Test Run"
    assert loaded["statuses"]["r1"] == "approved"

    # Clear
    clear_session_cache()
    assert load_session_cache() is None


def test_builtin_brand_profiles():
    """Builtin profiles should match schema and contain required keys."""
    presets = get_available_presets()
    assert len(presets) >= 4
    assert "Spotify" in presets
    assert "Stripe" in presets
    assert "OpenAI" in presets

    spotify_prof = generate_brand_profile("Spotify")
    assert spotify_prof["client"]["name"] == "Spotify"
    assert "music" in spotify_prof["client"]["industry"].lower()
    assert "categories" in spotify_prof
    assert len(spotify_prof["categories"]) >= 3


def test_brand_profile_heuristic_fallback():
    """Unknown brands should generate valid heuristic profiles without crashing."""
    prof = generate_brand_profile("Zephyr Global Logistics", "logistics")
    assert prof["client"]["name"] == "Zephyr Global Logistics"
    assert "client" in prof
    assert "brand" in prof
    assert "response" in prof
    assert "risk" in prof
    assert "categories" in prof
    assert len(prof["categories"]) >= 3


def test_save_and_load_client_config(tmp_path, monkeypatch):
    """save_client_config should persist yaml cleanly."""
    fake_config_path = tmp_path / "config" / "client.yaml"
    monkeypatch.setattr("app.core.config.PROJECT_ROOT", tmp_path)

    test_cfg = {
        "client": {"name": "Acme Corp", "industry": "retail"},
        "brand": {"tone": "friendly"},
        "response": {"enabled": True},
        "risk": {"escalation_threshold": 40},
        "categories": ["billing", "general"],
    }

    save_client_config(test_cfg)
    assert fake_config_path.exists()

    loaded = client_config()
    assert loaded["client"]["name"] == "Acme Corp"
    assert loaded["risk"]["escalation_threshold"] == 40
