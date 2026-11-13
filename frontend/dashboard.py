"""ReputeAI Enterprise Reputation Intelligence & ORM Dashboard.

A high-fidelity, aesthetic, and dynamic Streamlit interface.
"""
from __future__ import annotations

import html
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ai_engine.analyzer import AnalyzerError
from app.analytics.analytics import generate_business_insights
from app.core.brand_profiler import BUILTIN_PROFILES, generate_brand_profile, get_available_presets
from app.core.config import (
    DATA_DIR,
    analyzer_mode,
    clear_session_cache,
    client_config,
    load_session_cache,
    save_client_config,
    save_session_cache,
)
from app.core.pitch_dossier import generate_interactive_pitch_dossier_html, render_html_to_pdf_bytes
from app.core.pitch_models import (
    calculate_roi_model,
    generate_executive_audit_html,
    get_competitor_benchmark,
)
from app.ingestion.appstore_connector import AppStoreConnector
from app.ingestion.csv_loader import load_reviews
from app.ingestion.hackernews_connector import HackerNewsConnector
from app.ingestion.reddit_connector import RedditConnector
from app.ingestion.trustpilot_connector import TrustpilotConnector
from app.main import get_analyzer
from app.pipeline import process_reviews
from app.response_engine.generator import ResponseGeneratorError, get_response_generator

st.set_page_config(
    page_title="ReputatAI | Reputation Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS Design System
# ---------------------------------------------------------------------------
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Background & Containers */
.main .block-container {
    padding-top: 1.5rem;
    padding-bottom: 3rem;
    max-width: 1400px;
}

/* Glassmorphism Header */
.rep-header {
    background: linear-gradient(135deg, rgba(15, 23, 42, 0.9) 0%, rgba(30, 41, 59, 0.8) 100%);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    padding: 1.5rem 2rem;
    margin-bottom: 1.8rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.3);
}

.rep-title {
    font-size: 1.8rem;
    font-weight: 800;
    background: linear-gradient(90deg, #60A5FA 0%, #A78BFA 50%, #F472B6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0;
    letter-spacing: -0.5px;
}

.rep-subtitle {
    font-size: 0.9rem;
    color: #94A3B8;
    margin-top: 4px;
}

/* KPI Metric Cards */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    margin-bottom: 1.8rem;
}

.kpi-card {
    background: rgba(30, 41, 59, 0.5);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 1.2rem;
    transition: all 0.25s ease;
    position: relative;
    overflow: hidden;
}

.kpi-card:hover {
    transform: translateY(-3px);
    border-color: rgba(99, 102, 241, 0.4);
    box-shadow: 0 12px 24px -10px rgba(99, 102, 241, 0.25);
}

.kpi-accent-blue { border-top: 3px solid #3B82F6; }
.kpi-accent-emerald { border-top: 3px solid #10B981; }
.kpi-accent-amber { border-top: 3px solid #F59E0B; }
.kpi-accent-rose { border-top: 3px solid #EF4444; }
.kpi-accent-purple { border-top: 3px solid #8B5CF6; }
.kpi-accent-cyan { border-top: 3px solid #06B6D4; }

.kpi-label {
    font-size: 0.78rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: #94A3B8;
    margin-bottom: 0.5rem;
}

.kpi-value {
    font-size: 1.85rem;
    font-weight: 700;
    color: #F8FAFC;
    line-height: 1.2;
}

.kpi-sub {
    font-size: 0.75rem;
    color: #64748B;
    margin-top: 0.4rem;
}

/* Badges */
.badge {
    display: inline-flex;
    align-items: center;
    padding: 3px 10px;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: capitalize;
    letter-spacing: 0.3px;
}

.badge-pos { background: rgba(16, 185, 129, 0.15); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.3); }
.badge-neu { background: rgba(148, 163, 184, 0.15); color: #CBD5E1; border: 1px solid rgba(148, 163, 184, 0.3); }
.badge-neg { background: rgba(239, 68, 68, 0.15); color: #F87171; border: 1px solid rgba(239, 68, 68, 0.3); }

.badge-crit { background: rgba(225, 29, 72, 0.2); color: #FB7185; border: 1px solid rgba(225, 29, 72, 0.4); animation: pulse 2s infinite; }
.badge-high { background: rgba(249, 115, 22, 0.15); color: #FB923C; border: 1px solid rgba(249, 115, 22, 0.3); }
.badge-med { background: rgba(245, 158, 11, 0.15); color: #FBBF24; border: 1px solid rgba(245, 158, 11, 0.3); }
.badge-low { background: rgba(16, 185, 129, 0.15); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.3); }

.badge-prov { background: rgba(99, 102, 241, 0.15); color: #A5B4FC; border: 1px solid rgba(99, 102, 241, 0.3); }

/* Review Detail Container */
.review-box {
    background: rgba(30, 41, 59, 0.4);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 1.5rem;
    margin-bottom: 1rem;
}

.review-quote {
    font-size: 1.05rem;
    font-style: italic;
    color: #E2E8F0;
    line-height: 1.6;
    border-left: 3px solid #6366F1;
    padding-left: 1rem;
    margin: 1rem 0;
}

/* Insight Cards */
.insight-item {
    background: rgba(30, 41, 59, 0.4);
    border-left: 4px solid #6366F1;
    border-radius: 0 12px 12px 0;
    padding: 1rem 1.25rem;
    margin-bottom: 0.8rem;
    color: #E2E8F0;
    font-size: 0.95rem;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.6; }
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def _initialise() -> None:
    # Auto-restore persistent disk cache on fresh session / browser refresh
    if "records" not in st.session_state or st.session_state.records is None:
        cached = load_session_cache()
        if cached:
            st.session_state.records = cached.get("records")
            st.session_state.analytics = cached.get("analytics")
            st.session_state.provider = cached.get("provider", analyzer_mode())
            st.session_state.statuses = cached.get("statuses", {})
            st.session_state.responses = cached.get("responses", {})
            st.session_state.analyzed_at = cached.get("analyzed_at")
            st.session_state.target_query = cached.get("target_query", "Restored Session")
        else:
            st.session_state.records = None
            st.session_state.analytics = None
            st.session_state.provider = analyzer_mode()
            st.session_state.statuses = {}
            st.session_state.responses = {}
            st.session_state.analyzed_at = None
            st.session_state.target_query = None
    else:
        st.session_state.setdefault("analytics", None)
        st.session_state.setdefault("statuses", {})
        st.session_state.setdefault("responses", {})
        st.session_state.setdefault("provider", analyzer_mode())
        st.session_state.setdefault("analyzed_at", None)
        st.session_state.setdefault("target_query", None)


def _frame() -> pd.DataFrame:
    return pd.DataFrame(st.session_state.records or [])


def _label(value: str) -> str:
    return str(value).replace("_", " ").title()


def _get_badge_html(kind: str, value: str) -> str:
    val_str = str(value).lower()
    if kind == "sentiment":
        cls = "badge-pos" if "pos" in val_str else "badge-neg" if "neg" in val_str else "badge-neu"
    elif kind == "risk":
        cls = "badge-crit" if "crit" in val_str else "badge-high" if "high" in val_str else "badge-med" if "med" in val_str else "badge-low"
    else:
        cls = "badge-prov"
    return f'<span class="badge {cls}">{html.escape(_label(value))}</span>'


def _load_demo() -> None:
    loaded = load_reviews(DATA_DIR / "reviews.csv")
    if loaded.errors or not loaded.records:
        st.sidebar.error("The sample dataset could not be loaded.")
        return
    try:
        analyzer = get_analyzer("mock", client_config())
        records, analytics = process_reviews(loaded.records, analyzer, "mock")
        st.session_state.records = records
        st.session_state.analytics = analytics
        st.session_state.provider = "mock"
        st.session_state.statuses = {}
        st.session_state.responses = {}
        st.session_state.analyzed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.target_query = "Sample Dataset (20 Reviews)"

        save_session_cache({
            "records": records,
            "analytics": analytics,
            "provider": "mock",
            "statuses": {},
            "responses": {},
            "analyzed_at": st.session_state.analyzed_at,
            "target_query": st.session_state.target_query,
        })
    except (AnalyzerError, ValueError) as exc:
        st.sidebar.error(f"Sample analysis failed: {exc}")


def _run_pipeline(records: list[dict[str, Any]], mode: str, query_label: str = "") -> None:
    if not records:
        st.sidebar.error("No valid reviews found to process.")
        return
    try:
        analyzer = get_analyzer(mode, client_config())
    except (AnalyzerError, ValueError) as exc:
        st.sidebar.error(str(exc))
        return

    progress_bar = st.sidebar.progress(0, text="Initializing AI analysis pipeline...")
    status_text = st.sidebar.empty()

    def update_progress(index: int, total: int, rec: dict[str, Any]) -> None:
        pct = index / total
        progress_bar.progress(pct, text=f"Analyzing feedback ({index}/{total})...")
        status_text.caption(f"Processing #{rec.get('review_id')} from {rec.get('platform')}")

    analyzed, analytics = process_reviews(records, analyzer, mode, update_progress)
    st.session_state.records = analyzed
    st.session_state.analytics = analytics
    st.session_state.provider = mode
    st.session_state.statuses = {}
    st.session_state.responses = {}
    st.session_state.analyzed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.target_query = query_label or f"{len(analyzed)} records"

    # Persist session state to disk so page reloads do not lose data
    save_session_cache({
        "records": analyzed,
        "analytics": analytics,
        "provider": mode,
        "statuses": {},
        "responses": {},
        "analyzed_at": st.session_state.analyzed_at,
        "target_query": st.session_state.target_query,
    })

    progress_bar.empty()
    status_text.empty()
    st.sidebar.success(f"Analyzed {len(analyzed)} feedback records!")


def _sidebar_controls() -> None:
    with st.sidebar:
        st.markdown("### ⚡ **ReputatAI Engine**")
        st.caption("AI-Powered Reputation Intelligence & Deterministic Risk Management")
        st.divider()

        mode = st.selectbox(
            "AI Analyzer Provider",
            ["mock", "nvidia"],
            index=0 if analyzer_mode() == "mock" else 1,
            help="Mock: Offline fast heuristic; NVIDIA: Cloud NIM LLM analysis",
        )

        auto_adapt_brand = st.checkbox(
            "✨ Auto-Adapt Brand Voice with AI",
            value=True,
            help="Automatically creates tailored brand identity, industry, tone, and issue categories using AI for whatever company you search.",
        )

        st.subheader("Data Source")
        source_mode = st.radio(
            "Select Ingestion Channel",
            ["📁 CSV File / Sample", "🔴 Live Reddit Search", "🟠 Hacker News Social", "🍏 Apple App Store", "⭐ Trustpilot Reviews"],
            index=0,
        )

        if source_mode == "📁 CSV File / Sample":
            upload = st.file_uploader("Upload Reviews CSV", type="csv", help="Must contain review_id, date, rating, platform, customer, review")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📊 Sample Data", use_container_width=True):
                    _load_demo()
                    if st.session_state.records:
                        st.success("Loaded 20 reviews.")
            with col2:
                if st.button("🚀 Run CSV", use_container_width=True, type="primary"):
                    if upload is None:
                        st.error("Upload a CSV file or choose Sample Data.")
                    else:
                        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
                            tmp.write(upload.getvalue())
                            tmp_path = Path(tmp.name)
                        try:
                            loaded = load_reviews(tmp_path)
                        finally:
                            try:
                                tmp_path.unlink()
                            except OSError:
                                pass
                        if loaded.errors:
                            st.warning("Validation Warnings:\n\n" + "\n".join(f"- {e}" for e in loaded.errors))
                        _run_pipeline(loaded.records, mode, query_label="Uploaded CSV File")

        elif source_mode == "🔴 Live Reddit Search":
            reddit_query = st.text_input("Brand / Topic Keyword", value="OpenAI", placeholder="e.g. Shopify, Nike, Stripe")
            reddit_sub = st.text_input("Subreddit (optional)", value="all", placeholder="e.g. all, technology, eCommerce")
            reddit_limit = st.slider("Max Posts to Fetch", min_value=5, max_value=50, value=20)
            if st.button("🚀 Fetch & Analyze Reddit", use_container_width=True, type="primary"):
                if auto_adapt_brand and reddit_query.strip():
                    new_prof = generate_brand_profile(reddit_query.strip())
                    save_client_config(new_prof)
                    st.toast(f"🎯 Brand Voice adapted to: {new_prof['client']['name']}")

                with st.spinner("Connecting to Reddit live search..."):
                    conn = RedditConnector(query=reddit_query, subreddit=reddit_sub, limit=reddit_limit)
                    result = conn.fetch()
                    if result.errors:
                        st.error("\n".join(result.errors))
                    if result.records:
                        legacy_records = [r.to_legacy_record() for r in result.records]
                        _run_pipeline(legacy_records, mode, query_label=f"Reddit: '{reddit_query}'")

        elif source_mode == "🟠 Hacker News Social":
            hn_query = st.text_input("Brand / Tech Keyword", value="OpenAI", placeholder="e.g. OpenAI, Stripe, Claude, Notion")

            # Show disambiguation suggestions for ambiguous keywords.
            from app.ingestion.relevance import expand_query as _expand, get_expansion_suggestions
            suggestions = get_expansion_suggestions(hn_query) if hn_query else []
            if suggestions:
                st.caption(f"🎯 Auto-expanding to: **{_expand(hn_query)}**")
                st.caption(f"Also known as: {', '.join(suggestions)}")

            hn_context = st.text_input(
                "Context (optional)",
                value="",
                placeholder="e.g. AI assistant, betting app, payment platform",
                help="Helps disambiguate generic keywords. E.g. for 'Claude' → 'AI assistant by Anthropic'",
            )
            hn_limit = st.slider("Max Discussions", min_value=5, max_value=50, value=20)

            with st.expander("⚙️ Relevance Filter Settings", expanded=False):
                hn_use_filter = st.checkbox("Enable smart relevance filtering", value=True)
                hn_use_ce = st.checkbox("Use cross-encoder neural re-ranking (FlashRank)", value=True,
                                        help="~30ms, 34MB ONNX model. Best accuracy for disambiguation.")
                hn_use_llm = st.checkbox("Use LLM fallback (NVIDIA NIM)", value=True,
                                         help="Only used if cross-encoder unavailable. ~1-2s, uses API tokens.")

            if st.button("🚀 Fetch & Analyze Hacker News", use_container_width=True, type="primary"):
                if auto_adapt_brand and hn_query.strip():
                    new_prof = generate_brand_profile(hn_query.strip(), hn_context)
                    save_client_config(new_prof)
                    st.toast(f"🎯 Brand Voice adapted to: {new_prof['client']['name']}")

                with st.spinner(f"Fetching & filtering live discussions for '{hn_query}' from Hacker News..."):
                    conn = HackerNewsConnector(
                        query=hn_query,
                        context=hn_context,
                        limit=hn_limit,
                        use_relevance_filter=hn_use_filter,
                        use_crossencoder=hn_use_ce,
                        use_llm_filter=hn_use_llm,
                    )
                    result = conn.fetch()
                    if result.errors:
                        for err in result.errors:
                            if err.startswith("🔍"):
                                st.info(err)
                            else:
                                st.error(err)
                    if result.records:
                        legacy_records = [r.to_legacy_record() for r in result.records]
                        _run_pipeline(legacy_records, mode, query_label=f"Hacker News: '{hn_query}'")

        elif source_mode == "🍏 Apple App Store":
            app_target = st.text_input("App Name or Numeric ID", value="Spotify", placeholder="e.g. Spotify, Notion, Slack, or 324684580")
            app_country = st.selectbox("Store Country", ["us", "gb", "ca", "au", "in", "de", "fr"], index=0)
            app_limit = st.slider("Max Reviews", min_value=10, max_value=80, value=25)
            if st.button("🚀 Fetch & Analyze App Store", use_container_width=True, type="primary"):
                if auto_adapt_brand and app_target.strip():
                    new_prof = generate_brand_profile(app_target.strip())
                    save_client_config(new_prof)
                    st.toast(f"🎯 Brand Voice adapted to: {new_prof['client']['name']}")

                with st.spinner(f"Fetching reviews for '{app_target}' from App Store ({app_country.upper()})..."):
                    conn = AppStoreConnector(app_id_or_name=app_target, country=app_country, limit=app_limit)
                    result = conn.fetch()
                    if result.errors:
                        st.error("\n".join(result.errors))
                    if result.records:
                        legacy_records = [r.to_legacy_record() for r in result.records]
                        _run_pipeline(legacy_records, mode, query_label=f"App Store: '{app_target}'")

        elif source_mode == "⭐ Trustpilot Reviews":
            tp_domain = st.text_input("Company Domain or Brand Name", value="stake.com", placeholder="e.g. stake.com, spotify.com, stripe.com")
            tp_limit = st.slider("Max Reviews", min_value=5, max_value=50, value=20)
            if st.button("🚀 Fetch & Analyze Trustpilot", use_container_width=True, type="primary"):
                if auto_adapt_brand and tp_domain.strip():
                    new_prof = generate_brand_profile(tp_domain.strip())
                    save_client_config(new_prof)
                    st.toast(f"🎯 Brand Voice adapted to: {new_prof['client']['name']}")

                with st.spinner(f"Fetching verified customer reviews for '{tp_domain}' from Trustpilot..."):
                    conn = TrustpilotConnector(domain_or_name=tp_domain, limit=tp_limit)
                    result = conn.fetch()
                    if result.errors:
                        for err in result.errors:
                            if "Retrieved" in err:
                                st.info(err)
                            else:
                                st.error(err)
                    if result.records:
                        legacy_records = [r.to_legacy_record() for r in result.records]
                        _run_pipeline(legacy_records, mode, query_label=f"Trustpilot: '{tp_domain}'")

        st.divider()
        if st.session_state.records:
            st.markdown(f"**Loaded Records:** `{len(st.session_state.records)}`")
            st.markdown(f"**Provider:** `{st.session_state.provider.upper()}`")
            if st.session_state.target_query:
                st.caption(f"Source: **{st.session_state.target_query}**")
            if st.session_state.analyzed_at:
                st.caption(f"Last updated: {st.session_state.analyzed_at}")

            st.caption("💾 *Session saved to disk cache (persists on reload)*")
            if st.button("🗑️ Clear Cache & Reset", use_container_width=True):
                clear_session_cache()
                st.session_state.records = None
                st.session_state.analytics = None
                st.session_state.statuses = {}
                st.session_state.responses = {}
                st.session_state.analyzed_at = None
                st.session_state.target_query = None
                st.rerun()


def _render_header() -> None:
    config = client_config()
    client_name = config.get("client", {}).get("name", "Enterprise Brand")
    industry = config.get("client", {}).get("industry", "Global Commerce")
    mode_label = (st.session_state.get("provider") or "mock").upper()

    st.markdown(
        f"""
        <div class="rep-header">
            <div>
                <h1 class="rep-title">{html.escape(client_name)} Intelligence Hub</h1>
                <div class="rep-subtitle">Sector: <b>{html.escape(industry.title())}</b> • Live AI Monitoring & Brand Protection</div>
            </div>
            <div>
                <span class="badge badge-prov">⚡ Engine: {html.escape(mode_label)}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _require_data() -> bool:
    if st.session_state.records is None:
        _render_header()
        st.info("👋 **Welcome to ReputatAI.** Please upload a review dataset or click **'Sample Data'** in the sidebar to begin.")
        st.markdown("""
        ### What ReputatAI provides:
        * 🔍 **Automated Feedback Extraction:** Standardized multi-source ingestion.
        * 🧠 **AI Semantic Signals:** Sentiment confidence, emotion, intent & issue classification.
        * 🛡️ **Deterministic Risk Intelligence:** Audit-grade compliance and escalation detection.
        * 💬 **Human-in-the-Loop Response Studio:** Brand-aligned response drafting and one-click approval.
        """)
        return False
    return True


# ---------------------------------------------------------------------------
# Dashboard Overview Page
# ---------------------------------------------------------------------------
def dashboard_page() -> None:
    if not _require_data():
        return
    _render_header()
    summary = st.session_state.analytics
    data = _frame()

    # 1. KPI Cards Grid
    rep_score = summary["reputation_score"]
    rep_color = "#10B981" if rep_score >= 70 else "#F59E0B" if rep_score >= 50 else "#EF4444"
    rep_status = "Excellent" if rep_score >= 75 else "Healthy" if rep_score >= 60 else "Attention Needed" if rep_score >= 45 else "Critical Alert"

    kpi_html = f"""
    <div class="kpi-grid">
        <div class="kpi-card kpi-accent-purple">
            <div class="kpi-label">Reputation Index</div>
            <div class="kpi-value" style="color: {rep_color};">{rep_score}<span style="font-size: 1rem; color: #94A3B8;">/100</span></div>
            <div class="kpi-sub">Status: <b>{rep_status}</b></div>
        </div>
        <div class="kpi-card kpi-accent-blue">
            <div class="kpi-label">Total Feedback</div>
            <div class="kpi-value">{summary["total_reviews"]}</div>
            <div class="kpi-sub">Avg Rating: <b>⭐ {summary["average_rating"]} / 5.0</b></div>
        </div>
        <div class="kpi-card kpi-accent-emerald">
            <div class="kpi-label">Positive Sentiment</div>
            <div class="kpi-value" style="color: #34D399;">{summary["positive_percentage"]}%</div>
            <div class="kpi-sub">Neutral: {summary["neutral_percentage"]}%</div>
        </div>
        <div class="kpi-card kpi-accent-rose">
            <div class="kpi-label">Negative Ratio</div>
            <div class="kpi-value" style="color: #F87171;">{summary["negative_percentage"]}%</div>
            <div class="kpi-sub">High/Critical Risk: <b>{summary["high_risk_reviews"] + summary["critical_reviews"]}</b></div>
        </div>
        <div class="kpi-card kpi-accent-amber">
            <div class="kpi-label">Escalations Required</div>
            <div class="kpi-value" style="color: #FBBF24;">{summary["requiring_escalation"]}</div>
            <div class="kpi-sub">Avg Risk Score: <b>{summary["average_risk_score"]}/100</b></div>
        </div>
    </div>
    """
    st.markdown(kpi_html, unsafe_allow_html=True)

    # 2. Charts Row 1: Sentiment Donut & Risk Spectrum
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("#### 🍩 Sentiment Breakdown")
        sentiments = summary["sentiment_counts"]
        colors = {"positive": "#10B981", "neutral": "#64748B", "negative": "#EF4444"}
        fig_donut = go.Figure(
            data=[
                go.Pie(
                    labels=[_label(k) for k in sentiments.keys()],
                    values=list(sentiments.values()),
                    hole=0.55,
                    marker=dict(colors=[colors.get(k.lower(), "#3B82F6") for k in sentiments.keys()]),
                    textinfo="label+percent",
                    hoverinfo="label+value+percent",
                )
            ]
        )
        fig_donut.update_layout(
            margin=dict(t=10, b=10, l=10, r=10),
            height=280,
            showlegend=True,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94A3B8"),
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    with col2:
        st.markdown("#### 🛡️ Risk Severity Distribution")
        risk_counts = summary["risk_level_counts"]
        risk_order = ["low", "medium", "high", "critical"]
        risk_vals = [risk_counts.get(k, 0) for k in risk_order]
        risk_colors = ["#10B981", "#F59E0B", "#FB923C", "#EF4444"]

        fig_bar = go.Figure(
            data=[
                go.Bar(
                    x=[_label(k) for k in risk_order],
                    y=risk_vals,
                    marker=dict(color=risk_colors, cornerradius=6),
                    text=risk_vals,
                    textposition="auto",
                )
            ]
        )
        fig_bar.update_layout(
            margin=dict(t=10, b=10, l=10, r=10),
            height=280,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94A3B8"),
            xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.05)", title="Reviews Count"),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # 3. Charts Row 2: Customer Issues & Time-Series Trend
    col3, col4 = st.columns([1, 1])

    with col3:
        st.markdown("#### 🏷️ Top Customer Issues & Drivers")
        topic_counts = summary["topic_counts"]
        sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
        top_df = pd.DataFrame(sorted_topics, columns=["Topic", "Reviews"])
        top_df["Topic"] = top_df["Topic"].apply(_label)

        fig_topics = px.bar(
            top_df,
            x="Reviews",
            y="Topic",
            orientation="h",
            color="Reviews",
            color_continuous_scale="Viridis",
        )
        fig_topics.update_layout(
            margin=dict(t=10, b=10, l=10, r=10),
            height=300,
            yaxis=dict(autorange="reversed"),
            coloraxis_showscale=False,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94A3B8"),
        )
        st.plotly_chart(fig_topics, use_container_width=True)

    with col4:
        st.markdown("#### 📈 Multi-Day Volume & Sentiment Trends")
        trend_data = summary.get("trend_data", [])
        if not trend_data or len(trend_data) == 0:
            st.info("Trend analytics unavailable (no valid ISO dates detected).")
        else:
            trend_df = pd.DataFrame(trend_data)
            fig_trend = go.Figure()
            fig_trend.add_trace(
                go.Scatter(
                    x=trend_df["date"],
                    y=trend_df["reviews"],
                    name="Daily Volume",
                    line=dict(color="#3B82F6", width=2.5),
                    mode="lines+markers",
                )
            )
            fig_trend.add_trace(
                go.Scatter(
                    x=trend_df["date"],
                    y=trend_df["negative_reviews"],
                    name="Negative Issues",
                    line=dict(color="#EF4444", width=2, dash="dot"),
                    mode="lines+markers",
                )
            )
            fig_trend.update_layout(
                margin=dict(t=10, b=10, l=10, r=10),
                height=300,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94A3B8"),
                xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
                yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
                legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
            )
            st.plotly_chart(fig_trend, use_container_width=True)

    # 4. Urgent Escalation Watchlist
    urgent = data[data["requires_escalation"] == True]
    if not urgent.empty:
        st.markdown("### 🚨 Critical & High-Priority Attention Queue")
        st.caption(f"Displaying **{len(urgent)}** feedback items flagged for immediate escalation.")
        cols = st.columns(min(3, len(urgent)))
        for idx, (_, row) in enumerate(urgent.head(3).iterrows()):
            with cols[idx % 3]:
                st.markdown(
                    f"""
                    <div class="review-box" style="border-color: rgba(239, 68, 68, 0.4);">
                        <div>{_get_badge_html('risk', row['risk_level'])} <span style="font-size: 0.8rem; color: #94A3B8; margin-left: 8px;">Score: <b>{row['risk_score']}</b></span></div>
                        <div class="review-quote">“{html.escape(str(row['review']))}”</div>
                        <div style="font-size: 0.8rem; color: #94A3B8;"><b>Author:</b> {html.escape(str(row['customer']))} ({html.escape(str(row['platform']))})</div>
                        <div style="font-size: 0.8rem; color: #FCA5A5; margin-top: 4px;"><b>Action:</b> {html.escape(str(row['recommended_action']))}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


# ---------------------------------------------------------------------------
# Review Explorer Page
# ---------------------------------------------------------------------------
def reviews_page() -> None:
    if not _require_data():
        return
    _render_header()
    data = _frame()

    st.markdown("### 🔍 Feedback Explorer & Deep Inspection")

    # Filter Bar
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        query = st.text_input("🔎 Search text or customer", placeholder="e.g. late delivery, refund, Customer A")
    with col2:
        sent_filter = st.multiselect("Sentiment", sorted(data["sentiment"].dropna().unique()), placeholder="All")
    with col3:
        risk_filter = st.multiselect("Risk Level", sorted(data["risk_level"].dropna().unique()), placeholder="All")
    with col4:
        topic_filter = st.multiselect("Topic", sorted(data["topic"].dropna().unique()), placeholder="All")

    filtered = data.copy()
    if query:
        filtered = filtered[
            filtered["review"].str.contains(query, case=False, na=False)
            | filtered["customer"].str.contains(query, case=False, na=False)
        ]
    if sent_filter:
        filtered = filtered[filtered["sentiment"].isin(sent_filter)]
    if risk_filter:
        filtered = filtered[filtered["risk_level"].isin(risk_filter)]
    if topic_filter:
        filtered = filtered[filtered["topic"].isin(topic_filter)]

    st.markdown(f"Showing **{len(filtered)}** of **{len(data)}** feedback records")

    display_cols = ["review_id", "date", "rating", "platform", "customer", "sentiment", "topic", "risk_level", "risk_score", "requires_escalation"]
    st.dataframe(
        filtered[display_cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "rating": st.column_config.NumberColumn("Rating ⭐", format="%d ⭐"),
            "risk_score": st.column_config.ProgressColumn("Risk Score", min_value=0, max_value=100, format="%d"),
            "requires_escalation": st.column_config.CheckboxColumn("Escalate?"),
        },
    )

    st.divider()
    st.markdown("#### 🎯 Direct Review Inspector")
    if not filtered.empty:
        selected_id = st.selectbox("Select Review ID to Inspect", filtered["review_id"].astype(str).tolist())
        selected_row = filtered[filtered["review_id"].astype(str) == selected_id].iloc[0]

        col_left, col_right = st.columns([1.2, 1])
        with col_left:
            st.markdown(
                f"""
                <div class="review-box">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 1.2rem; font-weight: 700; color: #F8FAFC;">Review #{html.escape(str(selected_row['review_id']))}</span>
                        <span>{'⭐' * int(selected_row['rating'])}</span>
                    </div>
                    <div class="review-quote">“{html.escape(str(selected_row['review']))}”</div>
                    <div style="display: flex; gap: 1rem; color: #94A3B8; font-size: 0.85rem;">
                        <span>👤 <b>{html.escape(str(selected_row['customer']))}</b></span>
                        <span>🌐 <b>{html.escape(str(selected_row['platform']))}</b></span>
                        <span>📅 <b>{html.escape(str(selected_row['date']))}</b></span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_right:
            st.markdown(
                f"""
                <div class="review-box">
                    <h4 style="margin-top: 0; color: #A5B4FC;">🧠 AI Analysis Breakdown</h4>
                    <div style="margin-bottom: 8px;"><b>Sentiment:</b> {_get_badge_html('sentiment', selected_row['sentiment'])} (Confidence: {float(selected_row['sentiment_score'])*100:.0f}%)</div>
                    <div style="margin-bottom: 8px;"><b>Emotion:</b> `{selected_row['emotion']}` • <b>Intent:</b> `{selected_row['intent']}`</div>
                    <div style="margin-bottom: 8px;"><b>Risk Level:</b> {_get_badge_html('risk', selected_row['risk_level'])} • <b>Score:</b> {selected_row['risk_score']}/100</div>
                    <div style="margin-bottom: 8px; font-size: 0.88rem; color: #CBD5E1;"><b>Summary:</b> {html.escape(str(selected_row['summary']))}</div>
                    <div style="font-size: 0.88rem; color: #60A5FA;"><b>Recommended Action:</b> {html.escape(str(selected_row['recommended_action']))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# AI Response Studio Page (Human-in-the-Loop)
# ---------------------------------------------------------------------------
def responses_page() -> None:
    if not _require_data():
        return
    _render_header()
    data = _frame()

    st.markdown("### ✍️ AI Response Studio & Approval Workflow")
    st.caption("Human-in-the-loop: Generate, edit, and approve brand responses with policy safeguards.")

    # Status summary bar & Export Button
    statuses = st.session_state.statuses
    approved_count = sum(1 for s in statuses.values() if s == "approved")
    escalated_count = sum(1 for s in statuses.values() if s == "escalated")
    draft_count = len(st.session_state.responses)

    top_col1, top_col2 = st.columns([3, 1])
    with top_col1:
        st.markdown(
            f"""
            <div style="display: flex; gap: 1.5rem; align-items: center; background: rgba(30, 41, 59, 0.4); padding: 0.8rem 1.2rem; border-radius: 10px;">
                <span>✅ <b>Approved:</b> {approved_count}</span>
                <span>🚨 <b>Escalated:</b> {escalated_count}</span>
                <span>📝 <b>Drafts Active:</b> {draft_count}</span>
                <span>📊 <b>Total Feedback:</b> {len(data)}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with top_col2:
        if st.session_state.responses or statuses:
            export_rows = []
            for _, row in data.iterrows():
                r_id = str(row["review_id"])
                if r_id in st.session_state.responses or r_id in statuses:
                    export_rows.append({
                        "review_id": r_id,
                        "customer": row.get("customer", ""),
                        "rating": row.get("rating", ""),
                        "review": row.get("review", ""),
                        "status": statuses.get(r_id, "draft"),
                        "response_draft": st.session_state.responses.get(r_id, ""),
                    })
            if export_rows:
                export_df = pd.DataFrame(export_rows)
                st.download_button(
                    label="📥 Export Responses CSV",
                    data=export_df.to_csv(index=False).encode("utf-8"),
                    file_name="reputateai_approved_responses.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

    st.divider()

    selected_id = st.selectbox("Choose Review to Draft/Approve Response", data["review_id"].astype(str).tolist())
    row = data[data["review_id"].astype(str) == selected_id].iloc[0]
    review_id = str(row["review_id"])
    response_key = f"response_draft_{review_id}"
    status = st.session_state.statuses.get(review_id, "pending")

    col_ctx, col_editor = st.columns([1.1, 1.2])

    with col_ctx:
        st.markdown("#### 📄 Feedback Context")
        st.markdown(
            f"""
            <div class="review-box">
                <div style="font-size: 1.1rem; font-weight: 700; color: #F8FAFC;">{html.escape(str(row['customer']))} ({html.escape(str(row['platform']))})</div>
                <div style="color: #FBBF24; margin: 4px 0;">{'⭐' * int(row['rating'])}</div>
                <div class="review-quote">“{html.escape(str(row['review']))}”</div>
                <div style="font-size: 0.85rem; color: #94A3B8;">
                    Sentiment: {_get_badge_html('sentiment', row['sentiment'])} | Risk: {_get_badge_html('risk', row['risk_level'])}
                </div>
                <div style="margin-top: 8px; font-size: 0.85rem; color: #CBD5E1;">
                    <b>Issue Category:</b> `{row['topic']}` • <b>Intent:</b> `{row['intent']}`
                </div>
                <div style="margin-top: 6px; font-size: 0.85rem; color: #60A5FA;">
                    <b>Action:</b> {html.escape(str(row['recommended_action']))}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_editor:
        st.markdown("#### 💬 AI Draft & Approval")

        gen_col1, gen_col2 = st.columns([1, 1])
        with gen_col1:
            if st.button("✨ Generate AI Response Draft", key=f"btn_gen_{review_id}", use_container_width=True, type="primary"):
                try:
                    generator = get_response_generator(
                        row.get("analysis_provider", st.session_state.get("provider", analyzer_mode())),
                        client_config(),
                    )
                    draft = generator.generate(row.to_dict(), row.to_dict())
                    st.session_state.responses[review_id] = draft
                    st.session_state[response_key] = draft
                    st.session_state.statuses[review_id] = "generated"
                    st.rerun()
                except ResponseGeneratorError as exc:
                    st.error(str(exc))

        current_val = st.session_state.responses.get(review_id, "")
        st.session_state.setdefault(response_key, current_val)

        edited_draft = st.text_area(
            "Response Draft (Editable)",
            key=response_key,
            height=140,
            help="Review and edit the AI response before approval. Responses are never published automatically.",
        )
        if edited_draft != current_val:
            st.session_state.responses[review_id] = edited_draft

        act_col1, act_col2 = st.columns(2)
        with act_col1:
            if st.button("✅ Approve Draft", key=f"btn_app_{review_id}", disabled=not edited_draft, use_container_width=True):
                st.session_state.statuses[review_id] = "approved"
                st.success("Response approved and queued!")
                st.rerun()
        with act_col2:
            if st.button("🚨 Escalate to Human Lead", key=f"btn_esc_{review_id}", use_container_width=True):
                st.session_state.statuses[review_id] = "escalated"
                st.warning("Review marked for escalation!")
                st.rerun()

        st.caption(f"Current Status: **{st.session_state.statuses.get(review_id, status).upper()}**")


# ---------------------------------------------------------------------------
# Business Insights Page
# ---------------------------------------------------------------------------
def insights_page() -> None:
    if not _require_data():
        return
    _render_header()
    summary = st.session_state.analytics
    insights_list = generate_business_insights(st.session_state.records, summary)

    st.markdown("### 💡 Executive Intelligence & Actionable Insights")
    st.caption("Deterministic, evidence-based recommendations derived from aggregate feedback data.")

    icons = ["🚨", "📈", "⚠️", "💡", "🎯"]
    for idx, text in enumerate(insights_list):
        icon = icons[idx % len(icons)]
        st.markdown(
            f"""
            <div class="insight-item">
                <span style="font-size: 1.2rem; margin-right: 8px;">{icon}</span>
                <b>Insight #{idx + 1}:</b> {html.escape(text)}
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()
    st.markdown("#### 📋 Strategic ORM Action Plan")
    st.markdown(
        """
        1. **Immediate Escalations:** Assign high-risk cases to customer relations specialists within 2 business hours.
        2. **Hotspot Issue Mitigation:** Address root causes in top complaint categories identified above.
        3. **Positive Engagement Loop:** Activate brand promoters who left 5-star praise with tailored referral workflows.
        """
    )


# ---------------------------------------------------------------------------
# Configuration & Guardrails Page
# ---------------------------------------------------------------------------
def configuration_page() -> None:
    _render_header()
    config = client_config()

    st.markdown("### ⚙️ Organization Profile, Brand Voice & Risk Guardrails")
    st.caption("Define your company identity, response voice, risk tolerance, and custom issue categories. You can auto-generate these with AI or customize them manually.")

    # ── Section 1: AI Brand Profiler & Preset Switcher ───────────────────────
    with st.expander("✨ **AI Brand Auto-Profiler & Presets** (Instant Setup for Any Company)", expanded=True):
        st.markdown("Generate a tailored brand profile, voice tone, escalation rules, and industry issue categories using AI.")
        pcol1, pcol2, pcol3 = st.columns([2, 2, 1.5])
        with pcol1:
            gen_brand_name = st.text_input("Company / Brand Name", value="", placeholder="e.g. Airbnb, Tesla, Duolingo, Nike")
        with pcol2:
            gen_industry_hint = st.text_input("Industry / Context Hint (optional)", value="", placeholder="e.g. EV Automotive, Hospitality")
        with pcol3:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("🪄 Generate with AI", use_container_width=True, type="primary"):
                if gen_brand_name.strip():
                    with st.spinner(f"Generating AI reputation profile for '{gen_brand_name}'..."):
                        new_prof = generate_brand_profile(gen_brand_name.strip(), gen_industry_hint.strip())
                        save_client_config(new_prof)
                        st.success(f"Generated & saved brand profile for **{new_prof['client']['name']}**!")
                        st.rerun()
                else:
                    st.error("Enter a company name first.")

        st.markdown("---")
        st.markdown("**Or load a curated preset profile:**")
        preset_cols = st.columns(len(BUILTIN_PROFILES))
        for idx, (pkey, pdata) in enumerate(BUILTIN_PROFILES.items()):
            with preset_cols[idx]:
                if st.button(f"🏢 {pdata['client']['name']}", key=f"preset_{pkey}", use_container_width=True):
                    save_client_config(pdata)
                    st.success(f"Loaded profile for **{pdata['client']['name']}**!")
                    st.rerun()

    st.divider()

    # ── Section 2: Interactive Configuration Editor ──────────────────────────
    st.markdown("#### 🛠️ **Edit Active Configuration**")
    with st.form("edit_config_form"):
        ecol1, ecol2 = st.columns(2)

        with ecol1:
            st.markdown("##### 🏢 Client & Brand Identity")
            cfg_client_name = st.text_input("Organization Name", value=config.get("client", {}).get("name", "Demo Brand"))
            cfg_industry = st.text_input("Industry / Sector", value=config.get("client", {}).get("industry", "general"))
            cfg_brand_tone = st.text_area("Brand Tone Adjectives", value=config.get("client", {}).get("brand_tone", "professional, warm and customer-focused"), height=80)
            cfg_response_style = st.text_input("Brand Response Style", value=config.get("brand", {}).get("response_style", "empathetic"))

        with ecol2:
            st.markdown("##### 🛡️ Risk & Response Policy Guardrails")
            cfg_escalation_thresh = st.slider(
                "Risk Escalation Threshold (Score)",
                min_value=10,
                max_value=90,
                value=int(config.get("risk", {}).get("escalation_threshold", 50)),
                help="Reviews with risk score >= this threshold trigger mandatory human escalation alerts.",
            )
            cfg_max_length = st.number_input("Max Response Word Count", min_value=30, max_value=300, value=int(config.get("response", {}).get("max_length", 120)))
            cfg_allow_comp = st.checkbox("Allow AI Compensation Promises (refunds/vouchers)", value=bool(config.get("response", {}).get("allow_compensation_promises", False)))
            cfg_req_contact = st.checkbox("Request Contact Details for Escalations", value=bool(config.get("response", {}).get("request_contact_for_escalation", True)))

        st.markdown("##### 🏷️ Monitored Issue Categories (Domain-Specific)")
        current_cats = ", ".join(config.get("categories", ["general"]))
        cfg_categories_raw = st.text_area(
            "Categories (comma-separated)",
            value=current_cats,
            height=70,
            help="AI will categorize incoming reviews into these issue buckets.",
        )

        submitted = st.form_submit_button("💾 Save System Configuration", use_container_width=True, type="primary")
        if submitted:
            parsed_cats = [c.strip().replace(" ", "_") for c in cfg_categories_raw.split(",") if c.strip()]
            if "general" not in parsed_cats:
                parsed_cats.append("general")

            updated_config: dict[str, Any] = {
                "client": {
                    "name": cfg_client_name.strip(),
                    "industry": cfg_industry.strip(),
                    "brand_tone": cfg_brand_tone.strip(),
                },
                "brand": {
                    "tone": config.get("brand", {}).get("tone", "professional"),
                    "response_style": cfg_response_style.strip(),
                },
                "response": {
                    "enabled": True,
                    "tone": config.get("response", {}).get("tone", "professional"),
                    "style": cfg_response_style.strip(),
                    "max_length": int(cfg_max_length),
                    "allow_compensation_promises": bool(cfg_allow_comp),
                    "request_contact_for_escalation": bool(cfg_req_contact),
                },
                "risk": {
                    "escalation_threshold": int(cfg_escalation_thresh),
                },
                "categories": parsed_cats,
            }

            save_client_config(updated_config)
            st.success("✅ Configuration saved to `config/client.yaml` successfully!")
            st.rerun()

    # ── Section 3: Live Schema Inspection ────────────────────────────────────
    with st.expander("🔍 View Raw `config/client.yaml` (YAML / JSON)", expanded=False):
        st.json(config)


# ---------------------------------------------------------------------------
# Live Crisis & AI Chatbot Simulator Page (Stake & Enterprise Pitch Feature)
# ---------------------------------------------------------------------------
def chatbot_page() -> None:
    _render_header()
    config = client_config()
    client_name = config.get("client", {}).get("name", "Enterprise Brand")
    provider = st.session_state.get("provider", analyzer_mode())

    st.markdown("### 🤖 **Live Crisis & Support Chatbot Simulator**")
    st.caption(
        f"Simulate live player inquiries, crisis escalations, or public forum complaints for **{client_name}**. "
        "Test deterministic risk scoring, compliance guardrails, and policy-aligned AI responses in real-time."
    )

    st.session_state.setdefault("chat_history", [])
    st.session_state.setdefault("chatbot_input_box", "")

    # Quick crisis simulation presets
    st.markdown("##### ⚡ **Quick Crisis & Support Scenarios (One-Click Test)**")
    scen_col1, scen_col2, scen_col3, scen_col4 = st.columns(4)

    with scen_col1:
        if st.button("🚨 Withdrawal Delay FUD", use_container_width=True):
            st.session_state["chatbot_input_box"] = "I requested a $10,000 USDT withdrawal 5 hours ago and it's still pending! Support is ignoring me, Stake is exit scamming!"
            st.rerun()
    with scen_col2:
        if st.button("🔒 KYC Verification Stuck", use_container_width=True):
            st.session_state["chatbot_input_box"] = "Why is my account locked for Level 2 KYC right after I won $25,000? This is unfair extortion, unlock my funds immediately!"
            st.rerun()
    with scen_col3:
        if st.button("🎲 Provably Fair Accusation", use_container_width=True):
            st.session_state["chatbot_input_box"] = "Your Dice and Plinko games are 100% rigged. I lost 22 bets in a row on 50% chance. I'm reporting this to Curacao gaming license!"
            st.rerun()
    with scen_col4:
        if st.button("💎 VIP Host Inactivity", use_container_width=True):
            st.session_state["chatbot_input_box"] = "I am a Platinum IV VIP player and my dedicated VIP host has ignored my reload bonus request for 48 hours. I'm moving to Roobet."
            st.rerun()

    st.divider()

    # Chat Input and Execution
    col_input, col_meta = st.columns([2.5, 1.5])

    with col_input:
        st.markdown("#### 💬 **Interactive Customer / Player Input**")

        # Explicit engine selector for the simulator
        sim_engine_col1, sim_engine_col2 = st.columns([1, 1])
        with sim_engine_col1:
            chat_engine = st.selectbox(
                "Simulator Engine Provider",
                ["mock", "nvidia"],
                index=0 if provider == "mock" else 1,
                help="Mock: Sub-millisecond deterministic offline analysis; NVIDIA: Cloud NIM LLM",
                key="chatbot_engine_select",
            )
        with sim_engine_col2:
            st.caption("💡 *Tip: 'mock' runs offline with zero API latency. Switch to 'nvidia' if you have active NVIDIA NIM credits.*")

        user_message = st.text_area(
            "Customer Message / Forum Post:",
            height=110,
            placeholder="Type any player complaint, support query, or public accusation...",
            key="chatbot_input_box",
        )

        sim_col1, sim_col2 = st.columns([1.5, 1])
        with sim_col1:
            run_sim = st.button("🚀 Analyze & Generate Compliance Response", use_container_width=True, type="primary")
        with sim_col2:
            if st.button("🗑️ Clear Simulation History", use_container_width=True):
                st.session_state.chat_history = []
                st.session_state["chatbot_input_box"] = ""
                st.rerun()

        if run_sim and user_message.strip():
            with st.spinner("Analyzing sentiment, calculating risk score & drafting compliant response..."):
                rec_dict = {
                    "review_id": f"sim_{int(datetime.now().timestamp())}",
                    "review": user_message.strip(),
                    "customer": "Simulated User",
                    "platform": "Live Chat / Forum",
                    "rating": 1,
                }

                # 1. AI Analysis with automatic Mock fallback
                used_engine = chat_engine
                try:
                    analyzer = get_analyzer(used_engine, config)
                    analysis = analyzer.analyze(rec_dict)
                except Exception as ana_err:
                    if used_engine == "nvidia":
                        st.warning(f"NVIDIA API unreachable ({ana_err}). Automatically falling back to local deterministic mock analyzer.")
                        used_engine = "mock"
                        analyzer = get_analyzer("mock", config)
                        analysis = analyzer.analyze(rec_dict)
                    else:
                        st.error(f"Analysis error: {ana_err}")
                        analysis = None

                if analysis is not None:
                    # 2. Response Generation with automatic Mock fallback
                    try:
                        generator = get_response_generator(used_engine, config)
                        analysis_dict = analysis.model_dump()
                        draft_reply = generator.generate(rec_dict, analysis_dict)
                    except Exception as gen_err:
                        if used_engine == "nvidia":
                            st.warning("NVIDIA generation failed. Using compliant policy generator fallback.")
                            generator = get_response_generator("mock", config)
                            draft_reply = generator.generate(rec_dict, analysis.model_dump())
                        else:
                            st.error(f"Response error: {gen_err}")
                            draft_reply = f"Thank you for contacting us regarding your concern. Our team is reviewing this promptly. — {client_name}"

                    st.session_state.chat_history.insert(0, {
                        "user_message": user_message.strip(),
                        "analysis": analysis.model_dump(),
                        "response": draft_reply,
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                    })

        # Display history
        st.markdown("#### 📜 **Simulation Stream**")
        if not st.session_state.chat_history:
            st.info("No simulations yet. Select a scenario above or type a customer message to begin.")
        else:
            for item in st.session_state.chat_history[:5]:
                ana = item["analysis"]
                st.markdown(
                    f"""
                    <div class="review-box" style="border-left: 4px solid #6366F1;">
                        <div style="font-size: 0.85rem; color: #94A3B8; margin-bottom: 4px;">
                            ⏰ {item['timestamp']} • Sentiment: {_get_badge_html('sentiment', ana.get('sentiment', 'neutral'))} • Risk: {_get_badge_html('risk', ana.get('risk_level', 'low'))} ({ana.get('risk_score')}/100)
                        </div>
                        <div style="font-size: 0.95rem; color: #F8FAFC; margin-bottom: 8px;">
                            <b>Player:</b> “{html.escape(item['user_message'])}”
                        </div>
                        <div style="font-size: 0.85rem; color: #A5B4FC; margin-bottom: 6px;">
                            <b>Detected Issue:</b> `{ana.get('topic')}` • <b>Intent:</b> `{ana.get('intent')}` • <b>Escalate:</b> {'🚨 YES' if ana.get('requires_escalation') else '✅ NO'}
                        </div>
                        <div style="background: rgba(99, 102, 241, 0.1); border-radius: 8px; padding: 10px; margin-top: 8px; border: 1px solid rgba(99, 102, 241, 0.2);">
                            <div style="font-size: 0.8rem; color: #818CF8; font-weight: 700; margin-bottom: 4px;">🛡️ {client_name.upper()} COMPLIANCE-SAFE AI RESPONSE:</div>
                            <div style="font-size: 0.95rem; color: #E2E8F0; line-height: 1.5;">{html.escape(item['response'])}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with col_meta:
        st.markdown("#### 🛡️ **Active Compliance Guardrails**")
        st.markdown(
            f"""
            <div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 1.25rem;">
                <div style="font-size: 1rem; font-weight: 700; color: #F8FAFC; margin-bottom: 8px;">🎯 {html.escape(client_name)} Policy Rules</div>
                <ul style="color: #CBD5E1; font-size: 0.85rem; line-height: 1.6; padding-left: 1.2rem;">
                    <li><b>Tone:</b> {html.escape(config.get('client', {}).get('brand_tone', 'Professional'))}</li>
                    <li><b>Strict Anti-Compensation:</b> AI is strictly prohibited from offering free bonus money, refunds, or admitting system guilt.</li>
                    <li><b>Escalation Threshold:</b> Triggered at Risk Score &ge; <b>{config.get('risk', {}).get('escalation_threshold', 30)}</b></li>
                    <li><b>24/7 Channel Ready:</b> Can be connected to Telegram bot, Zendesk webhook, or Intercom live chat.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("#### 📈 **Pitch Value Props for Stake**")
        st.markdown(
            """
            - **Prevent Viral FUD:** Detect panic threads on Reddit/Telegram in <30 seconds.
            - **VIP Retention:** Identify disgruntled high-roller accounts immediately.
            - **Regulatory Safety:** Guarantee 100% compliance adherence across all support agents.
            """
        )


# ---------------------------------------------------------------------------
# Executive Pitch, Audit & Competitor Benchmarks Page
# ---------------------------------------------------------------------------
def pitch_deck_page() -> None:
    _render_header()
    config = client_config()
    client_name = config.get("client", {}).get("name", "Stake.com")
    bench = get_competitor_benchmark(client_name)
    analytics = st.session_state.analytics or {
        "reputation_score": 64.2,
        "total_reviews": 50,
        "average_rating": 3.7,
        "positive_percentage": 52.0,
        "negative_percentage": 34.0,
        "average_risk_score": 42.5,
        "requiring_escalation": 12,
        "topic_counts": {"deposit_withdrawal_delays": 18, "kyc_verification": 12, "gameplay_fairness": 8},
    }

    st.markdown("### 💼 **Executive Reputation Audit & Enterprise Pitch Hub**")
    st.caption(
        f"Confidential pitch intelligence, blind audit benchmarks, competitor matrix, and financial ROI models for **{client_name}**."
    )

    # ── Section 1: Executive Audit Download Bar ──────────────────────────────
    top_issues = sorted(analytics.get("topic_counts", {}).items(), key=lambda x: x[1], reverse=True)
    records = st.session_state.records or []
    critical_records = [r for r in records if r.get("risk_level") in ("critical", "high")]
    if not critical_records:
        critical_records = [
            {"platform": "Reddit (r/Stake)", "risk_score": 88, "text": "I requested a $10,000 USDT withdrawal 5 hours ago and it's still pending! Support is ignoring me, Stake is exit scamming!"},
            {"platform": "Trustpilot", "risk_score": 82, "text": "Level 2 KYC verification pending for 5 days with zero human support replies. Account locked right after deposit."},
        ]

    audit_html = generate_executive_audit_html(
        client_name=client_name,
        analytics=analytics,
        benchmark=bench,
        top_issues=top_issues,
        critical_records=critical_records,
    )

    dossier_html = generate_interactive_pitch_dossier_html()

    @st.cache_data(show_spinner=False)
    def _cached_pdf(html_payload: str) -> bytes | None:
        return render_html_to_pdf_bytes(html_payload)

    audit_pdf = _cached_pdf(audit_html)
    dossier_pdf = _cached_pdf(dossier_html)

    dcol1, dcol2, dcol3 = st.columns([2.5, 1.2, 1.2])
    with dcol1:
        st.markdown(
            f"""
            <div style="background: rgba(99, 102, 241, 0.12); border: 1px solid rgba(99, 102, 241, 0.35); border-radius: 12px; padding: 14px 18px;">
                <div style="font-size: 1.05rem; font-weight: 700; color: #EEF2FF;">📄 Executive Audit & Pitch Dossier Ready</div>
                <div style="font-size: 0.82rem; color: #CBD5E1; margin-top: 4px;">
                    Generated complete deliverables for <b>{html.escape(client_name)}</b> including vulnerability drivers, case studies, risk spectrum, and 14-day pilot guarantee.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with dcol2:
        st.download_button(
            label="📥 Download Audit Brief (PDF)" if audit_pdf else "📥 Download Audit Brief (HTML)",
            data=audit_pdf if audit_pdf else audit_html,
            file_name=f"ReputatAI_Executive_Audit_{client_name.replace(' ', '_')}.{'pdf' if audit_pdf else 'html'}",
            mime="application/pdf" if audit_pdf else "text/html",
            use_container_width=True,
            type="secondary",
        )
    with dcol3:
        st.download_button(
            label="🏆 Full Pitch & Case Studies (PDF)" if dossier_pdf else "🏆 Full Pitch & Case Studies (HTML)",
            data=dossier_pdf if dossier_pdf else dossier_html,
            file_name=f"ReputatAI_Stake_Executive_Pitch_Dossier.{'pdf' if dossier_pdf else 'html'}",
            mime="application/pdf" if dossier_pdf else "text/html",
            use_container_width=True,
            type="primary",
        )

    st.divider()

    # ── Section 2: Competitive Benchmark Intelligence ────────────────────────
    st.markdown("#### 🏆 **Competitive Intelligence Matrix (Sector Benchmark)**")
    st.caption(f"Comparing **{client_name}** against primary competitors in the {bench.get('sector', 'digital')} sector across response SLA, reputation index, and top vulnerability drivers.")

    comp_list = bench.get("competitors", [])
    comp_cols = st.columns(len(comp_list) + 1)

    # Column 0: Target Client
    with comp_cols[0]:
        st.markdown(
            f"""
            <div style="background: rgba(99, 102, 241, 0.18); border: 2px solid #6366F1; border-radius: 12px; padding: 16px; text-align: center;">
                <div style="font-size: 0.8rem; font-weight: 700; color: #A5B4FC; text-transform: uppercase;">Target Account</div>
                <div style="font-size: 1.3rem; font-weight: 800; color: #FFFFFF; margin: 4px 0;">🎯 {html.escape(client_name)}</div>
                <div style="font-size: 1.8rem; font-weight: 800; color: #60A5FA;">{analytics.get('reputation_score', 0)}<span style="font-size: 0.9rem; color: #94A3B8;">/100</span></div>
                <div style="font-size: 0.8rem; color: #CBD5E1; margin-top: 6px;">Avg Rating: <b>⭐ {analytics.get('average_rating', 0)}</b></div>
                <div style="font-size: 0.8rem; color: #CBD5E1;">Response SLA: <b>{bench.get('fud_response_time', '14 mins')}</b></div>
                <div style="font-size: 0.75rem; color: #EF4444; margin-top: 8px; font-weight: 600;">Top Risk: {html.escape(bench.get('top_complaint', 'None'))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Columns 1..N: Competitors
    for idx, comp in enumerate(comp_list, 1):
        with comp_cols[idx]:
            st.markdown(
                f"""
                <div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 16px; text-align: center;">
                    <div style="font-size: 0.8rem; font-weight: 600; color: #94A3B8; text-transform: uppercase;">Competitor</div>
                    <div style="font-size: 1.2rem; font-weight: 700; color: #F8FAFC; margin: 4px 0;">{html.escape(comp['name'])}</div>
                    <div style="font-size: 1.8rem; font-weight: 800; color: #F59E0B;">{comp['reputation_score']}<span style="font-size: 0.9rem; color: #94A3B8;">/100</span></div>
                    <div style="font-size: 0.8rem; color: #CBD5E1; margin-top: 6px;">Avg Rating: <b>⭐ {comp['avg_rating']}</b></div>
                    <div style="font-size: 0.8rem; color: #CBD5E1;">Response SLA: <b>{comp['response_sla']}</b></div>
                    <div style="font-size: 0.75rem; color: #F87171; margin-top: 8px; font-weight: 600;">Issue: {html.escape(comp['top_issue'])}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.divider()

    # ── Section 3: Interactive ROI & Loss Prevention Calculator ───────────────
    st.markdown("#### 💰 **Financial Impact & Loss Prevention Calculator**")
    st.caption("Demonstrate exact dollar savings to C-suite buyers: quantify retained high-rollers, avoided VIP churn, and eliminated regulatory fine exposure.")

    rcol1, rcol2 = st.columns([1.2, 1])

    with rcol1:
        inp_players = st.number_input("Monthly Active Players / Users", min_value=10_000, max_value=5_000_000, value=250_000, step=25_000)
        inp_vip_ggr = st.number_input("Average High-Roller / VIP Monthly Value ($)", min_value=500.0, max_value=50_000.0, value=4_500.0, step=500.0)
        inp_escalations = st.slider("Monthly Severe Complaints & FUD Escalations", min_value=20, max_value=1_000, value=180, step=10)
        inp_churn_pct = st.slider("Estimated VIP Churn Prevented by <5 Min SLA (%)", min_value=2, max_value=25, value=8, step=1)
        inp_fine_risk = st.number_input("Averted Regulatory / Licensing Fines ($/year)", min_value=0.0, max_value=500_000.0, value=50_000.0, step=10_000.0)

        roi_data = calculate_roi_model(
            monthly_active_players=int(inp_players),
            avg_vip_monthly_ggr=float(inp_vip_ggr),
            monthly_escalations=int(inp_escalations),
            estimated_prevented_churn_rate=float(inp_churn_pct) / 100.0,
            averted_fine_risk=float(inp_fine_risk),
        )

    with rcol2:
        st.markdown(
            f"""
            <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.35); border-radius: 14px; padding: 22px;">
                <div style="font-size: 0.9rem; font-weight: 700; color: #34D399; text-transform: uppercase; letter-spacing: 0.5px;">PROJECTED ANNUAL VALUE</div>
                <div style="font-size: 2.4rem; font-weight: 800; color: #10B981; margin: 8px 0;">${roi_data['total_annual_protection']:,.0f}</div>
                <div style="font-size: 0.95rem; color: #E2E8F0; margin-bottom: 16px;">
                    Projected ROI Multiple: <span style="font-size: 1.3rem; font-weight: 800; color: #FBBF24;">{roi_data['roi_multiple']}x</span>
                </div>
                <hr style="border-color: rgba(255,255,255,0.08); margin: 12px 0;">
                <div style="font-size: 0.85rem; color: #CBD5E1; line-height: 1.8;">
                    • <b>VIP Accounts Saved:</b> ~{roi_data['saved_vips_monthly']} accounts / month<br>
                    • <b>Monthly Revenue Retained:</b> ${roi_data['monthly_ggr_saved']:,.0f}<br>
                    • <b>Annual Churn Loss Prevented:</b> ${roi_data['annual_ggr_saved']:,.0f}<br>
                    • <b>Compliance Fine Protection:</b> ${inp_fine_risk:,.0f}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Section 4: The 14-Day Zero-Risk Pilot Offer ──────────────────────────
    st.markdown("#### 🚀 **The 14-Day Executive PoC Agreement**")
    pcol1, pcol2, pcol3 = st.columns(3)
    with pcol1:
        st.markdown(
            """
            <div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 18px;">
                <div style="font-size: 1rem; font-weight: 700; color: #60A5FA;">1. Zero Engineering Setup</div>
                <p style="color: #94A3B8; font-size: 0.85rem; margin-top: 6px;">
                    ReputatAI operates via public edge listeners. Zero access to internal databases or player credentials required to begin.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with pcol2:
        st.markdown(
            """
            <div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 18px;">
                <div style="font-size: 1rem; font-weight: 700; color: #F59E0B;">2. Instant 60-Sec Alerts</div>
                <p style="color: #94A3B8; font-size: 0.85rem; margin-top: 6px;">
                    Dedicated webhook alerts into Stake VIP host channels on Telegram/Slack whenever a high-roller threatens escalation.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with pcol3:
        st.markdown(
            """
            <div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 18px;">
                <div style="font-size: 1rem; font-weight: 700; color: #10B981;">3. Guaranteed ROI Gate</div>
                <p style="color: #94A3B8; font-size: 0.85rem; margin-top: 6px;">
                    If ReputatAI doesn't catch at least 1 viral FUD thread and protect at least 3 high-value accounts during the 14 days, you owe zero.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Main App Router
# ---------------------------------------------------------------------------
def main() -> None:
    _initialise()
    _sidebar_controls()

    tabs = st.tabs([
        "📊 Overview",
        "🔍 Review Explorer",
        "✍️ AI Response Studio",
        "🤖 Crisis Chatbot Simulator",
        "💼 Pitch & Audit Hub",
        "💡 Insights",
        "⚙️ Configuration",
    ])
    with tabs[0]:
        dashboard_page()
    with tabs[1]:
        reviews_page()
    with tabs[2]:
        responses_page()
    with tabs[3]:
        chatbot_page()
    with tabs[4]:
        pitch_deck_page()
    with tabs[5]:
        insights_page()
    with tabs[6]:
        configuration_page()


# Backwards-compatible aliases
dashboard = dashboard_page
reviews = reviews_page
responses = responses_page
chatbot = chatbot_page
pitch_deck = pitch_deck_page
insights = insights_page
configuration = configuration_page

if __name__ == "__main__":
    main()

