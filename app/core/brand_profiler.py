"""AI Brand Auto-Profiler & Dynamic Configuration Engine.

Generates brand identity, industry classification, response voice & tone,
risk tolerance thresholds, and domain-specific issue categories for any
searched company using NVIDIA LLM with robust offline heuristics.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import yaml

from app.core.config import PROJECT_ROOT

logger = logging.getLogger(__name__)

# ── Built-in Curated Brand Archetypes & Profiles ──────────────────────────────
BUILTIN_PROFILES: dict[str, dict[str, Any]] = {
    "openai": {
        "client": {
            "name": "OpenAI",
            "industry": "artificial_intelligence",
            "brand_tone": "innovative, intellectual, safety-oriented and precise",
        },
        "brand": {
            "tone": "objective and helpful",
            "response_style": "clear, technical yet approachable",
        },
        "response": {
            "enabled": True,
            "tone": "professional",
            "style": "informative",
            "max_length": 120,
            "allow_compensation_promises": False,
            "request_contact_for_escalation": True,
        },
        "risk": {
            "escalation_threshold": 45,
        },
        "categories": [
            "model_hallucination",
            "api_availability_latency",
            "subscription_chatgpt_plus",
            "content_safety_filtering",
            "developer_experience",
            "account_access",
            "general",
        ],
    },
    "claude": {
        "client": {
            "name": "Anthropic (Claude)",
            "industry": "artificial_intelligence",
            "brand_tone": "thoughtful, nuanced, safety-conscious and developer-friendly",
        },
        "brand": {
            "tone": "empathetic and articulate",
            "response_style": "concise, transparent and technically sound",
        },
        "response": {
            "enabled": True,
            "tone": "professional",
            "style": "empathetic",
            "max_length": 120,
            "allow_compensation_promises": False,
            "request_contact_for_escalation": True,
        },
        "risk": {
            "escalation_threshold": 45,
        },
        "categories": [
            "model_intelligence_reasoning",
            "claude_pro_subscription",
            "api_rate_limits",
            "context_window_usage",
            "system_prompt_adherence",
            "customer_support",
            "general",
        ],
    },
    "spotify": {
        "client": {
            "name": "Spotify",
            "industry": "music_and_audio_streaming",
            "brand_tone": "youthful, music-loving, dynamic and approachable",
        },
        "brand": {
            "tone": "friendly and vibrant",
            "response_style": "casual yet helpful",
        },
        "response": {
            "enabled": True,
            "tone": "friendly",
            "style": "casual",
            "max_length": 100,
            "allow_compensation_promises": False,
            "request_contact_for_escalation": True,
        },
        "risk": {
            "escalation_threshold": 55,
        },
        "categories": [
            "playback_audio_bugs",
            "premium_subscription_billing",
            "recommendation_algorithm",
            "lyrics_and_features",
            "ads_frequency",
            "device_sync_connect",
            "general",
        ],
    },
    "stripe": {
        "client": {
            "name": "Stripe",
            "industry": "fintech_and_payments",
            "brand_tone": "developer-first, rigorous, authoritative and reliable",
        },
        "brand": {
            "tone": "professional and precise",
            "response_style": "direct, technically accurate",
        },
        "response": {
            "enabled": True,
            "tone": "authoritative",
            "style": "professional",
            "max_length": 120,
            "allow_compensation_promises": False,
            "request_contact_for_escalation": True,
        },
        "risk": {
            "escalation_threshold": 35,  # Financial services demand faster escalation
        },
        "categories": [
            "payout_delays",
            "disputes_chargebacks",
            "api_integration_docs",
            "account_underwriting_hold",
            "fraud_prevention_radar",
            "pricing_fees",
            "general",
        ],
    },
    "stake": {
        "client": {
            "name": "Stake.com",
            "industry": "online_gaming_and_betting",
            "brand_tone": "energetic, transparent, security-focused and community-driven",
        },
        "brand": {
            "tone": "calm, compliant and clear",
            "response_style": "reassuring and procedure-oriented",
        },
        "response": {
            "enabled": True,
            "tone": "calm",
            "style": "compliant",
            "max_length": 100,
            "allow_compensation_promises": False,
            "request_contact_for_escalation": True,
        },
        "risk": {
            "escalation_threshold": 30,  # High compliance sensitivity
        },
        "categories": [
            "deposit_withdrawal_delays",
            "kyc_verification",
            "vip_rewards_bonuses",
            "gameplay_fairness",
            "account_security_2fa",
            "support_responsiveness",
            "general",
        ],
    },
    "notion": {
        "client": {
            "name": "Notion",
            "industry": "productivity_software",
            "brand_tone": "creative, organized, thoughtful and empowering",
        },
        "brand": {
            "tone": "warm and encouraging",
            "response_style": "helpful and solution-oriented",
        },
        "response": {
            "enabled": True,
            "tone": "warm",
            "style": "supportive",
            "max_length": 110,
            "allow_compensation_promises": False,
            "request_contact_for_escalation": True,
        },
        "risk": {
            "escalation_threshold": 50,
        },
        "categories": [
            "workspace_sync_lag",
            "database_formula_bugs",
            "ai_features_pricing",
            "offline_mode_request",
            "mobile_app_experience",
            "collaboration_permissions",
            "general",
        ],
    },
}


def _heuristic_profile(company_name: str, industry_hint: str = "") -> dict[str, Any]:
    """Generate a clean profile for unknown brands using heuristics."""
    clean_name = company_name.strip() or "Brand"
    ind = industry_hint.strip().lower() or "technology_services"

    return {
        "client": {
            "name": clean_name,
            "industry": ind,
            "brand_tone": f"professional, customer-focused, responsive and dedicated to quality in {ind}",
        },
        "brand": {
            "tone": "professional and empathetic",
            "response_style": "clear, warm and solution-oriented",
        },
        "response": {
            "enabled": True,
            "tone": "professional",
            "style": "empathetic",
            "max_length": 120,
            "allow_compensation_promises": False,
            "request_contact_for_escalation": True,
        },
        "risk": {
            "escalation_threshold": 50,
        },
        "categories": [
            "product_quality",
            "customer_service",
            "pricing_billing",
            "app_platform_performance",
            "delivery_fulfillment",
            "feature_request",
            "general",
        ],
    }


def generate_brand_profile(company_name: str, industry_hint: str = "") -> dict[str, Any]:
    """Generate a comprehensive brand profile using LLM or built-in intelligence.

    Args:
        company_name: Name of the company/brand (e.g. "Airbnb", "Tesla", "Duolingo").
        industry_hint: Optional industry or context hint.

    Returns:
        Structured dictionary matching the schema of config/client.yaml.
    """
    clean_name = company_name.strip()
    if not clean_name:
        return _heuristic_profile("Demo Brand", industry_hint)

    lower = clean_name.lower()

    # 1. Check curated presets first for instant, perfect profiles
    for key, profile in BUILTIN_PROFILES.items():
        if key in lower or lower in key:
            return profile

    # 2. Try LLM Generation via NVIDIA NIM if API key is present
    api_key = os.getenv("NVIDIA_API_KEY", "").strip()
    model = os.getenv("NVIDIA_MODEL", "").strip()
    base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1").strip()

    if api_key and model:
        try:
            from openai import OpenAI

            client = OpenAI(base_url=base_url, api_key=api_key, timeout=15.0, max_retries=0)

            prompt = (
                f"You are a Brand Reputation & ORM Architect. Generate a complete reputation management configuration "
                f"profile for the company/brand: \"{clean_name}\" (Industry hint: \"{industry_hint or 'infer automatically'}\").\n\n"
                "Return ONLY a valid JSON object matching this exact schema:\n"
                "{\n"
                '  "client": {\n'
                f'    "name": "{clean_name}",\n'
                '    "industry": "specific_industry_in_snake_case",\n'
                '    "brand_tone": "2-3 descriptive tone adjectives (e.g. innovative, friendly, authoritative)"\n'
                "  },\n"
                '  "brand": {\n'
                '    "tone": "primary tone (e.g. professional, playful, empathetic)",\n'
                '    "response_style": "short style description (e.g. direct and solution-oriented)"\n'
                "  },\n"
                '  "response": {\n'
                '    "enabled": true,\n'
                '    "tone": "professional",\n'
                '    "style": "empathetic",\n'
                '    "max_length": 120,\n'
                '    "allow_compensation_promises": false,\n'
                '    "request_contact_for_escalation": true\n'
                "  },\n"
                '  "risk": {\n'
                '    "escalation_threshold": 45\n'
                "  },\n"
                '  "categories": [\n'
                '    "5_to_7_domain_specific_issue_categories_in_snake_case",\n'
                '    "general"\n'
                "  ]\n"
                "}\n"
                "Return valid JSON only. Do not wrap in markdown or explanation."
            )

            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a JSON-only configuration generator."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=400,
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            )

            content = resp.choices[0].message.content or ""
            content = content.strip()
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?\s*", "", content)
                content = re.sub(r"\s*```$", "", content)

            parsed = json.loads(content)
            if isinstance(parsed, dict) and "client" in parsed and "categories" in parsed:
                logger.info("Successfully generated AI brand profile for '%s'", clean_name)
                return parsed

        except Exception as exc:
            logger.warning("AI Brand Profiler LLM call failed (%s) — using smart heuristic profile.", exc)

    # 3. Fallback to smart heuristic
    return _heuristic_profile(clean_name, industry_hint)


def get_available_presets() -> list[str]:
    """Return list of available curated brand profiles."""
    return [p["client"]["name"] for p in BUILTIN_PROFILES.values()]
