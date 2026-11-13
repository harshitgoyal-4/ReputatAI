"""Configuration and session persistence helpers."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
import yaml

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = DATA_DIR / "output"
CACHE_DIR = DATA_DIR / "cache"


def analyzer_mode() -> str:
    """Return the configured analyzer mode, defaulting to the free mock mode."""
    load_dotenv(PROJECT_ROOT / ".env")
    return os.getenv("ANALYZER_MODE", "mock").strip().lower()


def max_reviews() -> int | None:
    """Return an optional positive processing limit for API-cost control."""
    value = os.getenv("MAX_REVIEWS", "").strip()
    if not value:
        return None
    try:
        limit = int(value)
    except ValueError as exc:
        raise ValueError("MAX_REVIEWS must be a positive integer.") from exc
    if limit < 1:
        raise ValueError("MAX_REVIEWS must be a positive integer.")
    return limit


def client_config() -> dict[str, Any]:
    """Load the small, extension-ready client configuration."""
    load_dotenv(PROJECT_ROOT / ".env")
    path = PROJECT_ROOT / "config" / "client.yaml"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def save_client_config(config: dict[str, Any]) -> None:
    """Persist the client configuration back to config/client.yaml."""
    path = PROJECT_ROOT / "config" / "client.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        yaml.safe_dump(config, file, default_flow_style=False, sort_keys=False)
    logger.info("Saved client configuration to %s", path)


# ── Persistent Session Cache ──────────────────────────────────────────────────

def save_session_cache(state_data: dict[str, Any]) -> None:
    """Save the current analyzed session state to disk so page reloads persist data."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = CACHE_DIR / "latest_session.json"
        with cache_file.open("w", encoding="utf-8") as file:
            json.dump(state_data, file, ensure_ascii=False, indent=2)
        logger.info("Saved session cache to %s (%d records)", cache_file, len(state_data.get("records") or []))
    except Exception as exc:
        logger.warning("Failed to save session cache: %s", exc)


def load_session_cache() -> dict[str, Any] | None:
    """Load the last analyzed session state from disk on page refresh."""
    try:
        cache_file = CACHE_DIR / "latest_session.json"
        if not cache_file.exists():
            return None
        with cache_file.open(encoding="utf-8") as file:
            data = json.load(file)
            if isinstance(data, dict) and data.get("records"):
                return data
    except Exception as exc:
        logger.warning("Failed to load session cache: %s", exc)
    return None


def clear_session_cache() -> None:
    """Clear the persistent session cache file."""
    try:
        cache_file = CACHE_DIR / "latest_session.json"
        if cache_file.exists():
            cache_file.unlink()
            logger.info("Cleared session cache.")
    except Exception as exc:
        logger.warning("Failed to clear session cache: %s", exc)
