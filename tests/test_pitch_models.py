"""Tests for Executive Audit, Competitor Benchmark, and ROI models."""
from app.core.pitch_models import (
    COMPETITOR_BENCHMARKS,
    calculate_roi_model,
    generate_executive_audit_html,
    get_competitor_benchmark,
)


def test_get_competitor_benchmark_for_stake() -> None:
    bench = get_competitor_benchmark("stake.com")
    assert bench["brand"] == "Stake.com"
    assert len(bench["competitors"]) >= 3
    comp_names = [c["name"] for c in bench["competitors"]]
    assert "Roobet" in comp_names
    assert "Rollbit" in comp_names


def test_get_competitor_benchmark_fallback() -> None:
    bench = get_competitor_benchmark("UnknownBrand123")
    assert bench["brand"] == "Enterprise Benchmark"
    assert len(bench["competitors"]) >= 2


def test_calculate_roi_model_returns_positive_protection() -> None:
    model = calculate_roi_model(
        monthly_active_players=200_000,
        avg_vip_monthly_ggr=4_000.0,
        monthly_escalations=150,
        estimated_prevented_churn_rate=0.10,
        averted_fine_risk=25_000.0,
    )
    assert model["saved_vips_monthly"] == 15.0
    assert model["monthly_ggr_saved"] == 60_000.0
    assert model["annual_ggr_saved"] == 720_000.0
    assert model["total_annual_protection"] == 745_000.0
    assert model["roi_multiple"] > 0


def test_generate_executive_audit_html_has_branding_and_kpis() -> None:
    mock_analytics = {
        "reputation_score": 64.2,
        "total_reviews": 50,
        "average_rating": 3.7,
        "positive_percentage": 52.0,
        "negative_percentage": 34.0,
        "average_risk_score": 42.5,
        "requiring_escalation": 12,
    }
    bench = get_competitor_benchmark("stake")
    top_issues = [("withdrawal_delay", 15), ("kyc_verification", 8)]
    records = [{"platform": "Reddit", "risk_score": 88, "text": "Stuck withdrawal"}]

    html_out = generate_executive_audit_html("Stake", mock_analytics, bench, top_issues, records)
    assert "<!DOCTYPE html>" in html_out
    assert "ReputatAI Intelligence" in html_out
    assert "Target: Stake" in html_out
    assert "Roobet" in html_out
    assert "Withdrawal Delay" in html_out
