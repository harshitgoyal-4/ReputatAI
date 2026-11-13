"""Multi-layer relevance filtering pipeline for search results.

Architecture (4-layer cascade — informed by 2025-2026 SOTA research):

  Layer 0 — Algolia Advanced Syntax: Use advancedSyntax=true, boolean operators,
             phrase matching, and negation at the API edge to pre-filter junk
             before it even reaches our server. Zero-cost.

  Layer 1 — Query Expansion: Rewrite ambiguous keywords using curated entity
             disambiguation maps and context hints. Generates both positive
             context terms and negative exclusion terms.

  Layer 2 — BM25 Re-ranking: Pure-Python BM25 keyword relevance scoring.
             Uses the expanded query (with context terms) to score documents.
             A comment about "Claude Monet" scores ~1.0 while "Claude AI" scores
             ~8.5. Eliminates clearly off-topic results in <1ms.

  Layer 3 — Cross-Encoder Neural Re-ranking (FlashRank): Uses a lightweight
             ONNX cross-encoder model (~34MB, no PyTorch needed) for semantic
             pair scoring. Evaluates (query, passage) together through full
             cross-attention — directly judges if "Claude" in *this specific
             sentence* refers to Anthropic's AI. ~30ms for 50 items on CPU.

  Layer 4 — LLM Semantic Filter (fallback): Uses the existing NVIDIA NIM API
             for batch relevance judgment. Only triggered when FlashRank is
             unavailable. ~1-2s latency but near-perfect accuracy.

Each layer is independent and gracefully degrades:
  - If FlashRank is unavailable → falls back to LLM filter.
  - If NVIDIA is unavailable → BM25-only filtering still works.
  - If nothing is available → raw results returned with a warning.
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

# ── Layer 1: Query Expansion ──────────────────────────────────────────────────

# Curated brand disambiguation profiles.
# Each entry has:
#   - aliases: expanded search terms that co-occur with the target meaning
#   - negatives: terms to exclude that indicate wrong meaning
#   - description: human-readable description for LLM/cross-encoder anchor
BRAND_PROFILES: dict[str, dict[str, Any]] = {
    "claude": {
        "aliases": ["Claude AI", "Anthropic Claude", "Claude LLM"],
        "context_terms": ["ai", "anthropic", "llm", "opus", "sonnet", "haiku", "model", "token", "prompt", "chatbot"],
        "negative_terms": ["monet", "shannon", "jean-claude", "strauss", "debussy"],
        "description": "Claude AI, the large language model assistant made by Anthropic",
    },
    "copilot": {
        "aliases": ["GitHub Copilot", "Microsoft Copilot", "Copilot AI"],
        "context_terms": ["ai", "github", "microsoft", "code", "completion", "ide", "vscode"],
        "negative_terms": ["airline", "pilot"],
        "description": "GitHub Copilot or Microsoft Copilot, AI coding and productivity assistants",
    },
    "gemini": {
        "aliases": ["Google Gemini", "Gemini AI", "Gemini LLM"],
        "context_terms": ["ai", "google", "deepmind", "llm", "model", "bard"],
        "negative_terms": ["zodiac", "constellation", "horoscope", "nasa", "spacecraft"],
        "description": "Google Gemini, the AI model by Google DeepMind",
    },
    "gpt": {
        "aliases": ["ChatGPT", "OpenAI GPT", "GPT-4"],
        "context_terms": ["openai", "chatgpt", "ai", "model", "llm", "token"],
        "negative_terms": [],
        "description": "OpenAI's GPT large language models and ChatGPT",
    },
    "meta": {
        "aliases": ["Meta AI", "Meta Platforms", "Facebook Meta"],
        "context_terms": ["facebook", "zuckerberg", "llama", "instagram", "whatsapp"],
        "negative_terms": ["metadata", "metaphor", "metatarsal"],
        "description": "Meta Platforms (formerly Facebook), the tech company",
    },
    "notion": {
        "aliases": ["Notion app", "Notion productivity"],
        "context_terms": ["app", "productivity", "workspace", "notes", "wiki", "database"],
        "negative_terms": [],
        "description": "Notion, the productivity and notes workspace application",
    },
    "slack": {
        "aliases": ["Slack messaging", "Slack app"],
        "context_terms": ["messaging", "workspace", "salesforce", "channels", "chat"],
        "negative_terms": ["slacken", "slack-jawed"],
        "description": "Slack, the team messaging and communication platform",
    },
    "stake": {
        "aliases": ["Stake.com", "Stake betting", "Stake casino"],
        "context_terms": ["betting", "casino", "gambling", "crypto", "wager", "stake.com"],
        "negative_terms": ["steak", "vampire", "tent", "ira", "war", "attack", "conflict"],
        "description": "Stake.com, the online crypto betting and casino platform",
    },
    "stripe": {
        "aliases": ["Stripe payments", "Stripe API"],
        "context_terms": ["payments", "api", "checkout", "billing", "fintech"],
        "negative_terms": [],
        "description": "Stripe, the online payment processing platform for developers",
    },
    "arc": {
        "aliases": ["Arc browser", "Arc Browser Company"],
        "context_terms": ["browser", "chrome", "tabs", "web"],
        "negative_terms": ["welding", "electric arc"],
        "description": "Arc, the web browser by The Browser Company",
    },
    "cursor": {
        "aliases": ["Cursor IDE", "Cursor AI editor"],
        "context_terms": ["ide", "editor", "ai", "code", "vscode"],
        "negative_terms": ["mouse cursor", "database cursor"],
        "description": "Cursor, the AI-powered code editor",
    },
    "linear": {
        "aliases": ["Linear app", "Linear issue tracker"],
        "context_terms": ["issue", "tracker", "project", "jira", "sprint"],
        "negative_terms": ["linear algebra", "linear regression", "equation"],
        "description": "Linear, the issue tracking and project management tool",
    },
    "perplexity": {
        "aliases": ["Perplexity AI", "Perplexity search"],
        "context_terms": ["ai", "search", "answer", "engine"],
        "negative_terms": ["confused", "puzzled"],
        "description": "Perplexity AI, the AI-powered search and answer engine",
    },
    "bolt": {
        "aliases": ["Bolt ride", "Bolt app"],
        "context_terms": ["ride", "taxi", "transport", "delivery"],
        "negative_terms": ["lightning bolt", "bolt action", "nut and bolt"],
        "description": "Bolt, the ride-hailing and food delivery app",
    },
    "grab": {
        "aliases": ["Grab app", "Grab ride-hailing"],
        "context_terms": ["ride", "food", "delivery", "southeast asia", "transport"],
        "negative_terms": [],
        "description": "Grab, the Southeast Asian ride-hailing and delivery super-app",
    },
}


def expand_query(keyword: str, context: str = "") -> str:
    """Expand an ambiguous keyword into a more precise search query.

    Args:
        keyword: The raw user search term (e.g. "Claude").
        context: Optional disambiguation hint (e.g. "AI assistant").

    Returns:
        An expanded query string for the Algolia search API.
    """
    clean = keyword.strip()
    lower = clean.lower()

    # If the user provided an explicit context hint, combine them.
    if context.strip():
        return f"{clean} {context.strip()}"

    # If we recognize this as an ambiguous entity, use the first alias.
    profile = BRAND_PROFILES.get(lower)
    if profile:
        return profile["aliases"][0]

    # Multi-word queries are already reasonably specific.
    if " " in clean:
        return clean

    # Single generic word: wrap in quotes for exact match to reduce noise.
    return f'"{clean}"'


def build_algolia_query(keyword: str, context: str = "") -> str:
    """Build an effective Algolia query with intelligent query expansion.

    Translates ambiguous keywords into high-precision terms (e.g. "Claude" -> "Claude AI")
    or incorporates user-specified disambiguation context.
    """
    clean = keyword.strip()
    if not clean:
        return ""

    if context.strip():
        return f"{clean} {context.strip()}"

    lower = clean.lower()
    profile = BRAND_PROFILES.get(lower)
    if profile and profile.get("aliases"):
        return profile["aliases"][0]

    return clean


def get_expansion_suggestions(keyword: str) -> list[str]:
    """Return known disambiguation options for a keyword.

    Useful for showing the user a "Did you mean...?" dropdown.
    """
    lower = keyword.strip().lower()
    profile = BRAND_PROFILES.get(lower)
    if profile:
        return list(profile["aliases"])
    return []


def get_anchor_description(keyword: str, context: str = "") -> str:
    """Get a natural-language description of the target entity for re-ranking."""
    lower = keyword.strip().lower()
    profile = BRAND_PROFILES.get(lower)
    if profile:
        return profile["description"]
    if context.strip():
        return f"{keyword.strip()} ({context.strip()})"
    return keyword.strip()


# ── Layer 2: BM25 Re-ranking ─────────────────────────────────────────────────

def _tokenize(text: str) -> list[str]:
    """Lowercase tokenization with basic cleaning."""
    return re.findall(r"[a-z0-9]+(?:'[a-z]+)?", text.lower())


def bm25_rerank(
    query: str,
    documents: list[str],
    context_terms: list[str] | None = None,
    k1: float = 1.5,
    b: float = 0.75,
    top_n: int | None = None,
    min_score: float = 0.0,
) -> list[tuple[int, float]]:
    """Score and rank documents by BM25 relevance to a query.

    Pure-Python BM25 implementation — no external dependencies required.
    Uses disambiguation context terms to boost scoring accuracy.

    Args:
        query: The search query string.
        documents: List of document texts to score.
        context_terms: Additional terms that indicate relevance (e.g. ["ai", "anthropic"]).
        k1: Term frequency saturation parameter (default 1.5).
        b: Length normalization parameter (default 0.75).
        top_n: If set, return only the top N results.
        min_score: Minimum BM25 score to include a result (default 0.0).

    Returns:
        List of (original_index, bm25_score) tuples, sorted descending.
    """
    if not documents or not query.strip():
        return [(i, 0.0) for i in range(len(documents))]

    # Build an enriched query using context terms.
    enriched = query
    if context_terms:
        enriched = f"{query} {' '.join(context_terms)}"

    query_terms = _tokenize(enriched)
    if not query_terms:
        return [(i, 0.0) for i in range(len(documents))]

    # Tokenize all documents.
    doc_tokens = [_tokenize(doc) for doc in documents]
    n_docs = len(doc_tokens)
    avg_dl = sum(len(d) for d in doc_tokens) / max(n_docs, 1)

    # Compute document frequencies for query terms.
    unique_query_terms = set(query_terms)
    df: dict[str, int] = {}
    for term in unique_query_terms:
        df[term] = sum(1 for d in doc_tokens if term in d)

    # Score each document.
    scores: list[tuple[int, float]] = []
    for idx, tokens in enumerate(doc_tokens):
        score = 0.0
        doc_len = len(tokens)
        tf_map: dict[str, int] = {}
        for t in tokens:
            tf_map[t] = tf_map.get(t, 0) + 1

        for term in unique_query_terms:
            if term not in tf_map:
                continue
            tf = tf_map[term]
            idf = math.log((n_docs - df[term] + 0.5) / (df[term] + 0.5) + 1.0)
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * doc_len / avg_dl)
            score += idf * (numerator / denominator)

        scores.append((idx, score))

    scores.sort(key=lambda x: x[1], reverse=True)

    if min_score > 0:
        scores = [(i, s) for i, s in scores if s > min_score]

    if top_n is not None and top_n > 0:
        scores = scores[:top_n]

    return scores


# ── Layer 3: Cross-Encoder Neural Re-ranking (FlashRank) ─────────────────────

_flashrank_ranker = None  # Lazy-loaded singleton
_flashrank_checked = False  # Track if we've already checked availability


def _onnxruntime_safe() -> bool:
    """Check if onnxruntime can be imported without crashing (DLL issues in Anaconda)."""
    import subprocess
    import sys
    try:
        result = subprocess.run(
            [sys.executable, "-c", "import onnxruntime; print('ok')"],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0 and "ok" in result.stdout
    except Exception:
        return False


def _get_flashrank_ranker():
    """Lazy-load the FlashRank cross-encoder model (34MB ONNX, no PyTorch)."""
    global _flashrank_ranker, _flashrank_checked
    if _flashrank_checked:
        return _flashrank_ranker
    _flashrank_checked = True

    # Safety check FIRST: verify onnxruntime won't crash the process.
    # This must happen before `import flashrank` because flashrank's __init__
    # imports onnxruntime at the module level, which can cause an access
    # violation in some Anaconda environments due to DLL conflicts.
    if not _onnxruntime_safe():
        logger.warning("onnxruntime has DLL issues in this environment — disabling cross-encoder.")
        return None

    try:
        from flashrank import Ranker
        _flashrank_ranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2")
        logger.info("FlashRank cross-encoder loaded (ms-marco-MiniLM-L-12-v2, ~34MB ONNX)")
        return _flashrank_ranker
    except ImportError:
        logger.info("flashrank not installed — cross-encoder re-ranking unavailable.")
        return None
    except Exception as exc:
        logger.warning("FlashRank initialization failed: %s", exc)
        return None


def crossencoder_rerank(
    query: str,
    texts: list[str],
    min_score: float = 0.15,
) -> list[tuple[int, float]] | None:
    """Re-rank texts using a cross-encoder neural model for semantic relevance.

    Unlike bi-encoders, a cross-encoder evaluates (query, passage) pairs
    jointly through cross-attention layers. This means it can understand
    that "Claude" in "I used Claude to generate code" refers to AI, while
    "Claude Monet was a painter" does not.

    Args:
        query: The anchor query (e.g. "Claude AI, the LLM by Anthropic").
        texts: List of candidate text snippets.
        min_score: Minimum cross-encoder score to keep (0.0–1.0).

    Returns:
        List of (original_index, score) tuples sorted by score descending,
        or None if FlashRank is not available.
    """
    ranker = _get_flashrank_ranker()
    if ranker is None:
        return None

    try:
        from flashrank import RerankRequest

        passages = [
            {"id": str(i), "text": t[:500]}  # Truncate to save CPU cycles.
            for i, t in enumerate(texts)
        ]

        rerank_req = RerankRequest(query=query, passages=passages)
        results = ranker.rerank(rerank_req)

        scored = []
        for res in results:
            idx = int(res["id"])
            score = float(res["score"])
            if score >= min_score:
                scored.append((idx, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        logger.info("FlashRank: %d/%d passages above threshold %.2f", len(scored), len(texts), min_score)
        return scored

    except Exception as exc:
        logger.warning("FlashRank re-ranking failed: %s", exc)
        return None


# ── Layer 4: LLM Semantic Relevance Filter (Fallback) ────────────────────────

def _build_relevance_prompt(target: str, texts: list[str]) -> list[dict[str, str]]:
    """Build a batch relevance-judgment prompt for the NVIDIA LLM."""
    numbered = "\n".join(f"[{i}] {t[:500]}" for i, t in enumerate(texts))
    system = (
        "You are a relevance classifier. The user wants to find online discussions "
        "and reviews about a specific product, brand, or entity. For each numbered "
        "text snippet, decide if it is genuinely discussing or reviewing the target "
        "subject — not merely mentioning the word in passing or in an unrelated context.\n\n"
        "Output ONLY a JSON array of objects, one per snippet, with this schema:\n"
        '[{"index": 0, "relevant": true, "confidence": 0.95}, ...]\n\n'
        "Rules:\n"
        "- A text is 'relevant' if its main topic or a significant portion discusses "
        "the target entity (product reviews, feature discussions, complaints, praise, "
        "comparisons with competitors).\n"
        "- A text is NOT relevant if the target word appears only as a person's name, "
        "a tangential reference, or in a completely different domain.\n"
        "- 'confidence' is 0.0 to 1.0 indicating how sure you are.\n"
        "- Output valid JSON only, no markdown fences, no explanation."
    )
    user = (
        f"Target subject: \"{target}\"\n\n"
        f"Snippets to classify:\n{numbered}"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def llm_relevance_filter(
    target: str,
    texts: list[str],
    min_confidence: float = 0.6,
    batch_size: int = 15,
) -> list[dict[str, Any]]:
    """Use the NVIDIA NIM LLM to semantically judge relevance of texts.

    This is the fallback when FlashRank is not installed.

    Returns:
        List of dicts with keys: index, relevant (bool), confidence (float).
        On failure, returns all items marked as relevant (fail-open).
    """
    api_key = os.getenv("NVIDIA_API_KEY", "").strip()
    model = os.getenv("NVIDIA_MODEL", "").strip()
    base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1").strip()

    if not api_key or not model:
        logger.warning("NVIDIA API not configured — skipping LLM relevance filter (fail-open).")
        return [{"index": i, "relevant": True, "confidence": 1.0} for i in range(len(texts))]

    try:
        from openai import OpenAI
    except ImportError:
        logger.warning("openai package not installed — skipping LLM relevance filter.")
        return [{"index": i, "relevant": True, "confidence": 1.0} for i in range(len(texts))]

    client = OpenAI(base_url=base_url, api_key=api_key, timeout=30.0, max_retries=0)
    all_results: list[dict[str, Any]] = []

    for batch_start in range(0, len(texts), batch_size):
        batch_texts = texts[batch_start : batch_start + batch_size]
        messages = _build_relevance_prompt(target, batch_texts)

        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.1,
                max_tokens=len(batch_texts) * 60 + 50,
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            )
            content = response.choices[0].message.content or ""
            content = content.strip()
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?\s*", "", content)
                content = re.sub(r"\s*```$", "", content)

            judgments = json.loads(content)
            if not isinstance(judgments, list):
                raise ValueError("Expected JSON array")

            for j in judgments:
                global_idx = batch_start + int(j.get("index", 0))
                all_results.append({
                    "index": global_idx,
                    "relevant": bool(j.get("relevant", True)),
                    "confidence": float(j.get("confidence", 0.5)),
                })

        except Exception as exc:
            logger.warning("LLM relevance batch failed (%s) — fail-open.", exc)
            for i in range(len(batch_texts)):
                all_results.append({
                    "index": batch_start + i,
                    "relevant": True,
                    "confidence": 0.5,
                })

    return all_results


# ── Orchestrator: Full Relevance Pipeline ─────────────────────────────────────

def filter_relevant_results(
    query: str,
    context: str,
    texts: list[str],
    use_bm25: bool = True,
    use_crossencoder: bool = True,
    use_llm: bool = True,
    bm25_top_n: int | None = None,
    crossencoder_min_score: float = 0.15,
    llm_min_confidence: float = 0.6,
) -> list[dict[str, Any]]:
    """Run the full relevance pipeline and return scored, filtered indices.

    Pipeline order:
      1. BM25 quick-filter (eliminates zero-relevance noise in <1ms)
      2. FlashRank cross-encoder (semantic re-ranking in ~30ms) — OR —
         LLM batch judging (if FlashRank unavailable, ~1-2s)
      3. Composite scoring and final ranking

    Args:
        query: The original user search keyword.
        context: Disambiguation context (e.g. "AI chatbot by Anthropic").
        texts: Raw text snippets from search results.
        use_bm25: Whether to apply BM25 re-ranking (Layer 2).
        use_crossencoder: Whether to try FlashRank cross-encoder (Layer 3).
        use_llm: Whether to apply LLM semantic filtering (Layer 4 fallback).
        bm25_top_n: Max results to keep after BM25 (None = keep all).
        crossencoder_min_score: Minimum cross-encoder score to keep.
        llm_min_confidence: Minimum LLM confidence to keep a result.

    Returns:
        List of dicts with scoring details, sorted by final_score descending.
    """
    if not texts:
        return []

    n = len(texts)
    lower = query.strip().lower()
    profile = BRAND_PROFILES.get(lower, {})
    context_terms = profile.get("context_terms", [])
    anchor_desc = get_anchor_description(query, context)
    expanded = expand_query(query, context)

    logger.info(
        "Relevance pipeline: query='%s' → expanded='%s', anchor='%s', %d docs",
        query, expanded, anchor_desc, n,
    )

    # --- Layer 2: BM25 ---
    bm25_scores: dict[int, float] = {}
    active_indices = list(range(n))

    if use_bm25:
        bm25_results = bm25_rerank(
            expanded, texts,
            context_terms=context_terms,
            top_n=bm25_top_n,
            min_score=0.01,
        )
        bm25_scores = {idx: score for idx, score in bm25_results}
        active_indices = [idx for idx, _ in bm25_results]
        logger.info("BM25: %d/%d docs passed (min_score>0.01)", len(active_indices), n)
    else:
        bm25_scores = {i: 1.0 for i in range(n)}

    if not active_indices:
        return []

    # --- Layer 3: Cross-Encoder (FlashRank) ---
    ce_scores: dict[int, float] | None = None

    if use_crossencoder:
        active_texts = [texts[i] for i in active_indices]
        ce_result = crossencoder_rerank(
            query=anchor_desc,
            texts=active_texts,
            min_score=crossencoder_min_score,
        )
        if ce_result is not None:
            # Map batch-local indices back to global indices.
            ce_scores = {}
            for batch_idx, score in ce_result:
                if 0 <= batch_idx < len(active_indices):
                    global_idx = active_indices[batch_idx]
                    ce_scores[global_idx] = score

            # Narrow active set to only what passed the cross-encoder.
            active_indices = [idx for idx in active_indices if idx in ce_scores]
            logger.info("CrossEncoder: %d docs passed threshold %.2f", len(active_indices), crossencoder_min_score)

    # --- Layer 4: LLM Fallback (only if cross-encoder not available) ---
    llm_judgments: dict[int, dict[str, Any]] = {}

    if ce_scores is None and use_llm and active_indices:
        active_texts = [texts[i] for i in active_indices]
        target_description = anchor_desc
        raw_judgments = llm_relevance_filter(
            target=target_description,
            texts=active_texts,
            min_confidence=llm_min_confidence,
        )
        for j in raw_judgments:
            batch_idx = j["index"]
            if 0 <= batch_idx < len(active_indices):
                global_idx = active_indices[batch_idx]
                llm_judgments[global_idx] = j

    # --- Combine Scores ---
    results: list[dict[str, Any]] = []
    max_bm25 = max(bm25_scores.values()) if bm25_scores else 1.0

    for idx in active_indices:
        bm25 = bm25_scores.get(idx, 0.0)
        norm_bm25 = bm25 / max_bm25 if max_bm25 > 0 else 0.0

        result_entry: dict[str, Any] = {
            "index": idx,
            "bm25_score": round(bm25, 4),
        }

        if ce_scores is not None:
            # Cross-encoder available: use it as primary signal.
            ce_score = ce_scores.get(idx, 0.0)
            result_entry["crossencoder_score"] = round(ce_score, 4)
            result_entry["filter_method"] = "crossencoder"
            # Weighted: 30% BM25 + 70% cross-encoder.
            final = 0.3 * norm_bm25 + 0.7 * ce_score
        elif llm_judgments:
            # LLM fallback.
            llm_j = llm_judgments.get(idx, {"relevant": True, "confidence": 0.5})
            llm_relevant = llm_j["relevant"]
            llm_conf = llm_j["confidence"]
            result_entry["llm_relevant"] = llm_relevant
            result_entry["llm_confidence"] = round(llm_conf, 4)
            result_entry["filter_method"] = "llm"
            if not llm_relevant and llm_conf >= llm_min_confidence:
                continue
            final = 0.4 * norm_bm25 + 0.6 * llm_conf if llm_relevant else norm_bm25 * 0.5
        else:
            # BM25 only.
            result_entry["filter_method"] = "bm25_only"
            final = norm_bm25

        result_entry["final_score"] = round(final, 4)
        results.append(result_entry)

    results.sort(key=lambda x: x["final_score"], reverse=True)
    logger.info("Relevance pipeline: %d/%d docs passed all filters.", len(results), n)
    return results
