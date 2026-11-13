"""Hacker News live social & developer review connector with intelligent relevance filtering.

Uses the HN Algolia API (100% free, no auth, no blocks) combined with a
multi-layer relevance pipeline:

  Layer 0 — Algolia Advanced Syntax (server-side): Boolean operators, phrase
             matching, and negation filter out 70-80% of junk at the API edge.
  Layer 1 — Query Expansion: Auto-expands "Claude" → "Claude AI" using curated
             brand disambiguation profiles.
  Layer 2 — BM25 Re-ranking: Pure-Python keyword scoring in <1ms.
  Layer 3 — FlashRank Cross-Encoder: Semantic neural re-ranking (~30ms, 34MB
             ONNX model, no PyTorch needed).
  Layer 4 — LLM Fallback: NVIDIA NIM batch judging if FlashRank unavailable.
"""
from __future__ import annotations

import html
import json
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.ingestion.base_connector import ConnectorResult, FeedbackConnector
from app.ingestion.normalizer import NormalizedFeedback
from app.ingestion.relevance import (
    build_algolia_query,
    expand_query,
    filter_relevant_results,
    get_expansion_suggestions,
)


class HackerNewsConnector(FeedbackConnector):
    """Fetch live public discussions from Hacker News with smart relevance filtering.

    Args:
        query: Search keyword or brand name.
        context: Optional disambiguation hint (e.g. "AI assistant by Anthropic").
                 If empty, the system auto-expands known ambiguous terms.
        limit: Maximum results to return (after filtering).
        use_relevance_filter: Enable the multi-layer relevance pipeline.
        use_crossencoder: Enable FlashRank cross-encoder neural re-ranking.
        use_llm_filter: Enable the LLM semantic filter (fallback if no FlashRank).
        llm_min_confidence: Minimum LLM confidence to keep a result (0.0–1.0).
    """

    def __init__(
        self,
        query: str,
        context: str = "",
        limit: int = 25,
        *,
        use_relevance_filter: bool = True,
        use_crossencoder: bool = True,
        use_llm_filter: bool = True,
        llm_min_confidence: float = 0.6,
    ) -> None:
        self.query = query.strip()
        self.context = context.strip()
        self.limit = min(max(1, limit), 100)
        self.use_relevance_filter = use_relevance_filter
        self.use_crossencoder = use_crossencoder
        self.use_llm_filter = use_llm_filter
        self.llm_min_confidence = llm_min_confidence

        # Over-fetch when filtering is on, so we have enough after filtering.
        self._fetch_limit = min(self.limit * 3, 100) if use_relevance_filter else self.limit

    def fetch(self) -> ConnectorResult:
        if not self.query:
            return ConnectorResult([], ["Search query cannot be empty."])

        # Layer 0 + 1: Build advanced Algolia query with expansion + negation.
        algolia_query = build_algolia_query(self.query, self.context)
        display_query = expand_query(self.query, self.context)

        params: dict[str, str] = {
            "query": algolia_query,
            "tags": "(story,comment)",
            "hitsPerPage": str(self._fetch_limit),
            "advancedSyntax": "true",
        }
        # Use relevance-sorted endpoint instead of chronological for better initial ranking.
        url = f"https://hn.algolia.com/api/v1/search?{urlencode(params)}"
        req = Request(url, headers={"User-Agent": "ReputatAI/1.0", "Accept": "application/json"})

        try:
            with urlopen(req, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            return ConnectorResult([], [f"Hacker News API error: {exc}"])

        hits = payload.get("hits", [])
        if not hits:
            suggestions = get_expansion_suggestions(self.query)
            hint = ""
            if suggestions:
                hint = f" Try more specific terms like: {', '.join(suggestions)}"
            return ConnectorResult([], [f"No Hacker News discussions found matching '{display_query}'.{hint}"])

        # Parse all raw hits.
        raw_records = self._parse_hits(hits)
        if not raw_records:
            return ConnectorResult([], [f"No readable text feedback found for query '{display_query}'."])

        # Layer 2 + 3 + 4: Apply relevance filtering.
        if self.use_relevance_filter and len(raw_records) > 1:
            texts = [r.text for r in raw_records]
            scored = filter_relevant_results(
                query=self.query,
                context=self.context,
                texts=texts,
                use_bm25=True,
                use_crossencoder=self.use_crossencoder,
                use_llm=self.use_llm_filter,
                llm_min_confidence=self.llm_min_confidence,
            )

            if scored:
                filtered_records = []
                for item in scored:
                    idx = item["index"]
                    if 0 <= idx < len(raw_records):
                        rec = raw_records[idx]
                        enriched_meta = dict(rec.metadata)
                        enriched_meta["relevance_score"] = item["final_score"]
                        enriched_meta["bm25_score"] = item["bm25_score"]
                        enriched_meta["filter_method"] = item.get("filter_method", "unknown")
                        if "crossencoder_score" in item:
                            enriched_meta["crossencoder_score"] = item["crossencoder_score"]
                        if "llm_relevant" in item:
                            enriched_meta["llm_relevant"] = item["llm_relevant"]
                            enriched_meta["llm_confidence"] = item.get("llm_confidence", 0.0)
                        filtered_records.append(
                            NormalizedFeedback(
                                id=rec.id,
                                date=rec.date,
                                platform=rec.platform,
                                author=rec.author,
                                text=rec.text,
                                rating=rec.rating,
                                source_url=rec.source_url,
                                metadata=enriched_meta,
                            )
                        )
                raw_records = filtered_records[: self.limit]

                n_filtered = len(texts) - len(filtered_records)
                errors: list[str] = []
                if n_filtered > 0:
                    method = scored[0].get("filter_method", "unknown") if scored else "unknown"
                    errors.append(
                        f"🔍 Relevance filter ({method}): removed {n_filtered} off-topic result(s) "
                        f"out of {len(texts)} fetched."
                    )
                return ConnectorResult(raw_records, errors)

        return ConnectorResult(raw_records[: self.limit], [])

    def _parse_hits(self, hits: list[dict]) -> list[NormalizedFeedback]:
        """Parse raw Algolia hits into normalized feedback records."""
        records: list[NormalizedFeedback] = []
        for hit in hits:
            raw_text = hit.get("comment_text") or hit.get("story_text") or hit.get("title") or ""
            text = html.unescape(raw_text).replace("<p>", "\n\n").replace("</p>", "").strip()
            text = re.sub("<[^<]+?>", " ", text).strip()
            if not text or len(text) < 10:
                continue

            date_str = str(hit.get("created_at", ""))[:10]
            author = str(hit.get("author", "hn_user"))
            object_id = str(hit.get("objectID", ""))
            story_id = str(hit.get("story_id") or object_id)
            source_url = f"https://news.ycombinator.com/item?id={object_id}"
            points = int(hit.get("points") or 1)

            records.append(
                NormalizedFeedback(
                    id=f"hn_{object_id}",
                    date=date_str or "2026-01-01",
                    platform="Hacker News",
                    author=author,
                    text=text,
                    rating=3,
                    source_url=source_url,
                    metadata={"points": points, "story_id": story_id},
                )
            )
        return records
