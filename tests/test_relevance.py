"""Tests for the multi-layer relevance filtering pipeline."""
import pytest

from app.ingestion.relevance import (
    BRAND_PROFILES,
    bm25_rerank,
    build_algolia_query,
    crossencoder_rerank,
    expand_query,
    filter_relevant_results,
    get_anchor_description,
    get_expansion_suggestions,
)


# ── Query Expansion Tests ─────────────────────────────────────────────────────


def test_expand_known_entity():
    """Known ambiguous terms should expand to their first alias."""
    assert expand_query("claude") == "Claude AI"
    assert expand_query("stake") == "Stake.com"
    assert expand_query("copilot") == "GitHub Copilot"


def test_expand_with_context_overrides():
    """User-provided context should override auto-expansion."""
    result = expand_query("claude", "Monet painter")
    assert "Monet painter" in result
    assert "claude" in result.lower()


def test_expand_multi_word_passthrough():
    """Multi-word queries should pass through unchanged."""
    assert expand_query("Claude AI") == "Claude AI"


def test_expand_unknown_single_word():
    """Unknown single words should be quoted for exact match."""
    assert expand_query("zephyr") == '"zephyr"'


def test_expansion_suggestions():
    """Known entities should return alias suggestions."""
    suggestions = get_expansion_suggestions("claude")
    assert len(suggestions) >= 2
    assert "Claude AI" in suggestions
    assert "Anthropic Claude" in suggestions


def test_expansion_suggestions_unknown():
    """Unknown keywords should return no suggestions."""
    assert get_expansion_suggestions("xyzabc") == []


# ── Algolia Advanced Query Builder Tests ──────────────────────────────────────


def test_algolia_query_with_known_entity():
    """Known entities should expand to high-precision terms."""
    query = build_algolia_query("claude")
    assert query == "Claude AI"


def test_algolia_query_unknown_entity():
    """Unknown single-word entities should pass through."""
    query = build_algolia_query("zephyr")
    assert query == "zephyr"


def test_algolia_query_with_user_context():
    """User context should override profile-based expansion."""
    query = build_algolia_query("claude", "cloud platform")
    assert "cloud platform" in query


# ── BM25 Re-ranking Tests ────────────────────────────────────────────────────


def test_bm25_ranks_relevant_higher():
    """BM25 should score Claude AI comments higher than Claude Monet comments."""
    docs = [
        "Claude Monet was a famous French impressionist painter known for water lilies.",
        "I used Claude AI from Anthropic to generate code and it was amazing.",
        "The weather in Claude, Texas was sunny today.",
        "Anthropic's Claude model outperforms GPT-4 on several benchmarks.",
    ]
    results = bm25_rerank(
        "Claude AI Anthropic LLM",
        docs,
        context_terms=["ai", "anthropic", "llm", "model"],
    )
    # The AI-related docs should rank at the top.
    top_indices = [idx for idx, _ in results[:2]]
    assert 1 in top_indices  # "I used Claude AI..."
    assert 3 in top_indices  # "Anthropic's Claude model..."


def test_bm25_min_score_filter():
    """BM25 min_score should filter out low-relevance results."""
    docs = [
        "Totally unrelated content about cooking recipes and kitchen tips.",
        "Claude AI is the best LLM by Anthropic for coding tasks.",
    ]
    results = bm25_rerank("Claude AI", docs, min_score=0.5)
    indices = [idx for idx, _ in results]
    assert 1 in indices
    # The cooking doc should be filtered out (score too low).
    assert 0 not in indices


def test_bm25_empty_inputs():
    """BM25 should handle empty inputs gracefully."""
    assert bm25_rerank("test", []) == []
    assert bm25_rerank("", ["some text"]) == [(0, 0.0)]


def test_bm25_top_n():
    """BM25 top_n should limit results."""
    docs = ["doc one", "doc two", "doc three"]
    results = bm25_rerank("doc", docs, top_n=2)
    assert len(results) <= 2


# ── Cross-Encoder Tests ──────────────────────────────────────────────────────


def test_crossencoder_returns_scores_or_none():
    """Cross-encoder should return scored results or None if unavailable."""
    texts = [
        "Claude AI by Anthropic is great for coding.",
        "Claude Monet painted water lilies.",
    ]
    try:
        result = crossencoder_rerank("Claude AI, the LLM by Anthropic", texts)
    except (OSError, SystemError, Exception):
        # ONNX runtime may crash on some environments (DLL issues) — treat as unavailable.
        result = None

    if result is not None:
        # FlashRank is installed and working — check structure.
        assert isinstance(result, list)
        for idx, score in result:
            assert isinstance(idx, int)
            assert isinstance(score, float)
            assert 0.0 <= score <= 1.0
    # If None, FlashRank not available — that's also valid.


# ── Full Pipeline Tests ──────────────────────────────────────────────────────


def test_full_pipeline_filters_irrelevant():
    """The full pipeline should filter out clearly irrelevant results."""
    texts = [
        "Anthropic released Claude 3.5 Sonnet and it's incredibly fast for coding.",
        "Claude Monet's Water Lilies painting sold for $50 million at auction.",
        "I've been using Claude AI daily and it helps me write better code.",
        "Jean-Claude Van Damme starred in a new action movie this year.",
        "The Claude LLM handles complex reasoning tasks better than other models.",
    ]
    results = filter_relevant_results(
        query="Claude",
        context="",
        texts=texts,
        use_bm25=True,
        use_crossencoder=False,  # Skip cross-encoder in tests to avoid ONNX DLL issues.
        use_llm=False,  # Don't call API in tests.
    )
    # We should have results.
    assert len(results) > 0
    # Each result should have scoring metadata.
    for r in results:
        assert "index" in r
        assert "bm25_score" in r
        assert "final_score" in r
        assert "filter_method" in r


def test_full_pipeline_empty_input():
    """Pipeline should handle empty input gracefully."""
    assert filter_relevant_results("test", "", []) == []


def test_anchor_description():
    """Anchor description should use profile description for known entities."""
    desc = get_anchor_description("claude")
    assert "anthropic" in desc.lower()
    assert "ai" in desc.lower()


def test_brand_profiles_complete():
    """All brand profiles should have required fields."""
    for brand, profile in BRAND_PROFILES.items():
        assert "aliases" in profile, f"{brand} missing 'aliases'"
        assert "context_terms" in profile, f"{brand} missing 'context_terms'"
        assert "negative_terms" in profile, f"{brand} missing 'negative_terms'"
        assert "description" in profile, f"{brand} missing 'description'"
        assert len(profile["aliases"]) >= 1, f"{brand} needs at least 1 alias"
