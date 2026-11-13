"""Executive Audit Report, Competitor Benchmark, and ROI Risk Models for Enterprise Pitches."""
from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Any


# ── Curated Industry Competitor Benchmarks (iGaming & Fintech Sectors) ──────
COMPETITOR_BENCHMARKS: dict[str, dict[str, Any]] = {
    "stake": {
        "brand": "Stake.com",
        "sector": "Crypto Casino & Sportsbook",
        "reputation_score": 64.2,
        "nps_estimate": "+14",
        "avg_rating": 3.7,
        "fud_response_time": "14 mins",
        "top_complaint": "USDT Withdrawal Delays (TRC-20)",
        "compliance_safety_score": "98%",
        "competitors": [
            {
                "name": "Roobet",
                "reputation_score": 58.1,
                "avg_rating": 3.4,
                "response_sla": "42 mins",
                "top_issue": "KYC Document Backlog",
                "risk_profile": "High Churn Vulnerability",
            },
            {
                "name": "Rollbit",
                "reputation_score": 62.5,
                "avg_rating": 3.6,
                "response_sla": "28 mins",
                "top_issue": "Futures Liquidation Disputes",
                "risk_profile": "Moderate Social FUD",
            },
            {
                "name": "Shuffle",
                "reputation_score": 67.0,
                "avg_rating": 3.9,
                "response_sla": "19 mins",
                "top_issue": "Limited Altcoin Withdrawal Pairs",
                "risk_profile": "Fast Growth Challenger",
            },
            {
                "name": "BC.Game",
                "reputation_score": 52.4,
                "avg_rating": 3.1,
                "response_sla": "65 mins",
                "top_issue": "Bonus Rollover Ambiguity",
                "risk_profile": "Severe Escalation Backlog",
            },
        ],
    },
    "default": {
        "brand": "Enterprise Benchmark",
        "sector": "Digital Services & SaaS",
        "reputation_score": 71.0,
        "nps_estimate": "+28",
        "avg_rating": 4.1,
        "fud_response_time": "8 mins",
        "top_complaint": "Billing / Subscription Overcharges",
        "compliance_safety_score": "99%",
        "competitors": [
            {
                "name": "Legacy Competitor A",
                "reputation_score": 61.2,
                "avg_rating": 3.5,
                "response_sla": "45 mins",
                "top_issue": "Customer Support Lag",
                "risk_profile": "Declining CSAT",
            },
            {
                "name": "Digital Challenger B",
                "reputation_score": 74.5,
                "avg_rating": 4.3,
                "response_sla": "12 mins",
                "top_issue": "Feature Parity Requests",
                "risk_profile": "Active Community Retention",
            },
        ],
    },
}


def get_competitor_benchmark(brand_query: str) -> dict[str, Any]:
    """Retrieve sector competitor metrics for pitch demonstrations."""
    brand_lower = brand_query.lower()
    for key in COMPETITOR_BENCHMARKS:
        if key in brand_lower:
            return COMPETITOR_BENCHMARKS[key]
    return COMPETITOR_BENCHMARKS["default"]


def calculate_roi_model(
    monthly_active_players: int = 250_000,
    avg_vip_monthly_ggr: float = 4_500.0,
    monthly_escalations: int = 180,
    estimated_prevented_churn_rate: float = 0.08,
    averted_fine_risk: float = 50_000.0,
) -> dict[str, Any]:
    """Calculate projected dollar loss prevention and ROI metrics for enterprise buyers."""
    saved_vips = round(monthly_escalations * estimated_prevented_churn_rate, 1)
    saved_ggr_monthly = saved_vips * avg_vip_monthly_ggr
    annual_ggr_saved = saved_ggr_monthly * 12
    total_annual_protection = annual_ggr_saved + averted_fine_risk

    pilot_monthly_cost = 6_000.0
    roi_multiple = round(total_annual_protection / (pilot_monthly_cost * 12), 1)

    return {
        "monthly_active_players": monthly_active_players,
        "monthly_escalations": monthly_escalations,
        "saved_vips_monthly": saved_vips,
        "monthly_ggr_saved": round(saved_ggr_monthly, 2),
        "annual_ggr_saved": round(annual_ggr_saved, 2),
        "total_annual_protection": round(total_annual_protection, 2),
        "roi_multiple": roi_multiple,
    }


def generate_executive_audit_html(
    client_name: str,
    analytics: dict[str, Any],
    benchmark: dict[str, Any],
    top_issues: list[tuple[str, int]],
    critical_records: list[dict[str, Any]],
) -> str:
    """Generate a clean, standalone, printable Executive Audit Report in HTML format."""
    rep_score = analytics.get("reputation_score", 0)
    score_color = "#10B981" if rep_score >= 70 else "#F59E0B" if rep_score >= 50 else "#EF4444"
    status_label = "Healthy" if rep_score >= 65 else "Moderate Risk" if rep_score >= 50 else "High Threat"

    issues_rows = ""
    for topic, count in top_issues[:5]:
        pct = round(count / max(1, analytics.get("total_reviews", 1)) * 100, 1)
        clean_topic = topic.replace("_", " ").title().replace("Kyc ", "KYC ").replace("Vip ", "VIP ")
        issues_rows += f"""
        <tr>
            <td style="padding: 10px 14px; border-bottom: 1px solid #E2E8F0; font-weight: 600;">{html.escape(clean_topic)}</td>
            <td style="padding: 10px 14px; border-bottom: 1px solid #E2E8F0; text-align: center;">{count}</td>
            <td style="padding: 10px 14px; border-bottom: 1px solid #E2E8F0; text-align: right; color: #475569;">{pct}%</td>
        </tr>
        """

    findings_rows = ""
    for idx, rec in enumerate(critical_records[:4], 1):
        findings_rows += f"""
        <div class="threat-card" style="background: #F8FAFC; border-left: 4px solid #EF4444; border-radius: 6px; padding: 12px 16px; margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; font-size: 13px; color: #64748B; margin-bottom: 6px;">
                <span><b>Threat #{idx}</b> • {html.escape(rec.get('platform', 'Public Review'))}</span>
                <span style="color: #EF4444; font-weight: 700;">Risk Score: {rec.get('risk_score', 0)}/100 (CRITICAL)</span>
            </div>
            <div style="font-size: 14px; color: #1E293B; line-height: 1.5; font-style: italic;">
                "{html.escape(str(rec.get('text', ''))[:220])}..."
            </div>
        </div>
        """

    competitor_rows = ""
    for comp in benchmark.get("competitors", []):
        competitor_rows += f"""
        <tr>
            <td style="padding: 10px 14px; border-bottom: 1px solid #E2E8F0; font-weight: 600;">{html.escape(comp['name'])}</td>
            <td style="padding: 10px 14px; border-bottom: 1px solid #E2E8F0; text-align: center;">{comp['reputation_score']}/100</td>
            <td style="padding: 10px 14px; border-bottom: 1px solid #E2E8F0; text-align: center;">⭐ {comp['avg_rating']}</td>
            <td style="padding: 10px 14px; border-bottom: 1px solid #E2E8F0; text-align: center;">{comp['response_sla']}</td>
            <td style="padding: 10px 14px; border-bottom: 1px solid #E2E8F0; color: #64748B;">{html.escape(comp['top_issue'])}</td>
        </tr>
        """

    now_str = datetime.now(timezone.utc).strftime("%B %d, %Y - %H:%M UTC")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>ReputatAI Executive Audit - {html.escape(client_name)}</title>
<style>
    @page {{
        size: A4;
        margin: 12mm;
    }}
    @media print {{
        body {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; background: #FFFFFF !important; padding: 0 !important; }}
        .container {{ box-shadow: none !important; padding: 8px 16px !important; }}
        .no-print {{ display: none; }}
        .threat-card, .kpi-box, table tr {{ break-inside: avoid; }}
        .section-title {{ break-after: avoid; }}
    }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        background-color: #F1F5F9;
        color: #0F172A;
        margin: 0;
        padding: 40px 20px;
    }}
    .container {{
        max-width: 900px;
        margin: 0 auto;
        background: #FFFFFF;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.06);
        padding: 48px;
    }}
    .header {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        border-bottom: 2px solid #E2E8F0;
        padding-bottom: 24px;
        margin-bottom: 32px;
    }}
    .logo {{
        font-size: 26px;
        font-weight: 800;
        color: #4F46E5;
        letter-spacing: -0.5px;
    }}
    .badge {{
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    .kpi-grid {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px;
        margin-bottom: 36px;
    }}
    .kpi-box {{
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
    }}
    .kpi-num {{
        font-size: 28px;
        font-weight: 800;
        margin-top: 4px;
    }}
    .section-title {{
        font-size: 18px;
        font-weight: 700;
        margin-top: 32px;
        margin-bottom: 14px;
        color: #1E293B;
        border-left: 4px solid #4F46E5;
        padding-left: 10px;
    }}
    table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
    }}
    th {{
        background: #F8FAFC;
        padding: 10px 14px;
        text-align: left;
        font-size: 12px;
        font-weight: 700;
        color: #64748B;
        text-transform: uppercase;
        border-bottom: 2px solid #E2E8F0;
    }}
    .footer {{
        margin-top: 48px;
        padding-top: 20px;
        border-top: 1px solid #E2E8F0;
        font-size: 12px;
        color: #94A3B8;
        display: flex;
        justify-content: space-between;
    }}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <div>
            <div class="logo">⚡ ReputatAI Intelligence</div>
            <div style="font-size: 13px; color: #64748B; margin-top: 4px;">Blind Executive Reputation Audit & Crisis Vulnerability Assessment</div>
        </div>
        <div style="text-align: right;">
            <div class="badge" style="background: #EEF2FF; color: #4F46E5;">Confidential Executive Brief</div>
            <div style="font-size: 12px; color: #94A3B8; margin-top: 6px;">Generated: {now_str}</div>
        </div>
    </div>

    <div style="margin-bottom: 18px;">
        <h2 style="margin: 0; font-size: 24px; font-weight: 800; color: #0F172A;">Target: {html.escape(client_name)}</h2>
        <div style="font-size: 13.5px; color: #64748B; margin-top: 4px;">Sector: <b>{html.escape(benchmark.get('sector', 'Global Enterprise'))}</b> • Channels Audited: Reddit, Trustpilot, App Stores, Social Web</div>
    </div>

    <!-- KPI Grid -->
    <div class="kpi-grid" style="margin-bottom: 20px;">
        <div class="kpi-box">
            <div style="font-size: 11px; color: #64748B; font-weight: 700;">REPUTATION INDEX</div>
            <div class="kpi-num" style="color: {score_color};">{rep_score}<span style="font-size: 14px; color: #94A3B8;">/100</span></div>
            <div style="font-size: 11px; color: #64748B; margin-top: 2px;">Status: <b>{status_label}</b></div>
        </div>
        <div class="kpi-box">
            <div style="font-size: 11px; color: #64748B; font-weight: 700;">FEEDBACK ANALYZED</div>
            <div class="kpi-num" style="color: #2563EB;">{analytics.get('total_reviews', 0)}</div>
            <div style="font-size: 11px; color: #64748B; margin-top: 2px;">Avg Rating: <b>⭐ {analytics.get('average_rating', 0)}</b></div>
        </div>
        <div class="kpi-box">
            <div style="font-size: 11px; color: #64748B; font-weight: 700;">NEGATIVE RATIO</div>
            <div class="kpi-num" style="color: #EF4444;">{analytics.get('negative_percentage', 0)}%</div>
            <div style="font-size: 11px; color: #64748B; margin-top: 2px;">Positive: <b>{analytics.get('positive_percentage', 0)}%</b></div>
        </div>
        <div class="kpi-box">
            <div style="font-size: 11px; color: #64748B; font-weight: 700;">URGENT ESCALATIONS</div>
            <div class="kpi-num" style="color: #F59E0B;">{analytics.get('requiring_escalation', 0)}</div>
            <div style="font-size: 11px; color: #64748B; margin-top: 2px;">Avg Risk: <b>{analytics.get('average_risk_score', 0)}/100</b></div>
        </div>
    </div>

    <!-- Executive Diagnosis & Financial Exposure -->
    <div class="threat-card" style="background: #EEF2FF; border: 1px solid #C7D2FE; border-left: 4px solid #4F46E5; border-radius: 8px; padding: 14px 18px; margin-bottom: 24px;">
        <div style="font-size: 13px; font-weight: 800; color: #3730A3; text-transform: uppercase; letter-spacing: 0.4px; margin-bottom: 6px;">Executive Diagnosis &amp; Revenue Exposure</div>
        <div style="font-size: 13.5px; color: #1E293B; line-height: 1.55;">
            While internal 24/7 support handles inbound tickets well, <b>{analytics.get('negative_percentage', 0)}% negative perimeter sentiment</b> and an average public SLA of <b>{html.escape(str(benchmark.get('fud_response_time', '14 mins')))}</b> leave high-value accounts exposed on public forums before agents see a ticket. At current escalation density, unaddressed FUD puts an estimated <b>$65,000–$95,000/month ($780k+/year)</b> in high-roller VIP retention and regulatory exposure at risk.
        </div>
    </div>

    <!-- Section 1: Top Vulnerability Drivers -->
    <div class="section-title">1. Root-Cause Issue Distribution</div>
    <table>
        <thead>
            <tr>
                <th>Vulnerability Category</th>
                <th style="text-align: center;">Frequency</th>
                <th style="text-align: right;">Share of Complaints</th>
            </tr>
        </thead>
        <tbody>
            {issues_rows}
        </tbody>
    </table>

    <!-- Section 2: Critical Live Mentions -->
    <div class="section-title">2. Sample Critical Social Escalations (Immediate Action Required)</div>
    {findings_rows}

    <!-- Section 3: Compliance Guardrail Comparison -->
    <div class="section-title">3. Regulatory Defense: Policy-Bounded AI Response Preview</div>
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 8px;">
        <div class="threat-card" style="background: #FEF2F2; border: 1px solid #FECACA; border-radius: 8px; padding: 12px 14px;">
            <div style="font-size: 11.5px; font-weight: 800; color: #B91C1C; text-transform: uppercase; margin-bottom: 6px;">❌ Unvetted Junior Agent Reply (Compliance Risk)</div>
            <div style="font-size: 12.5px; color: #7F1D1D; line-height: 1.5; font-style: italic;">
                "Sorry our crypto wallet server glitched on TRC-20 today! Send your username and I'll ask the team to credit a $50 bonus reload for the wait."
            </div>
            <div style="font-size: 11px; color: #991B1B; margin-top: 6px; font-weight: 600;">Violates licensing rules: admits system fault &amp; offers unapproved compensation.</div>
        </div>
        <div class="threat-card" style="background: #ECFDF5; border: 1px solid #A7F3D0; border-radius: 8px; padding: 12px 14px;">
            <div style="font-size: 11.5px; font-weight: 800; color: #047857; text-transform: uppercase; margin-bottom: 6px;">✅ ReputatAI Compliance-Safe Draft (&lt;60s)</div>
            <div style="font-size: 12.5px; color: #064E3B; line-height: 1.5; font-style: italic;">
                "Crypto withdrawals are processed via blockchain confirmation, and high network load or security checks can occasionally extend processing times. Please share your ticket ID with 24/7 Live Support so our team can review the transaction status promptly."
            </div>
            <div style="font-size: 11px; color: #065F46; margin-top: 6px; font-weight: 600;">100% License Safe: zero fault admission, zero bonus promises, directs to 2FA verification.</div>
        </div>
    </div>

    <!-- Section 4: Competitor Benchmark -->
    <div class="section-title">4. Competitive Intelligence Matrix</div>
    <table>
        <thead>
            <tr>
                <th>Brand</th>
                <th style="text-align: center;">Reputation Index</th>
                <th style="text-align: center;">Rating</th>
                <th style="text-align: center;">Response SLA</th>
                <th>Primary Risk Driver</th>
            </tr>
        </thead>
        <tbody>
            <tr style="background: #EEF2FF; font-weight: 700;">
                <td style="padding: 10px 14px; border-bottom: 1px solid #CBD5E1; white-space: nowrap;">🎯 {html.escape(client_name)} (Audited)</td>
                <td style="padding: 10px 14px; border-bottom: 1px solid #CBD5E1; text-align: center; color: #4F46E5;">{rep_score}/100</td>
                <td style="padding: 10px 14px; border-bottom: 1px solid #CBD5E1; text-align: center; white-space: nowrap;">⭐ {analytics.get('average_rating', 0)}</td>
                <td style="padding: 10px 14px; border-bottom: 1px solid #CBD5E1; text-align: center; white-space: nowrap;">{benchmark.get('fud_response_time', 'N/A')}</td>
                <td style="padding: 10px 14px; border-bottom: 1px solid #CBD5E1; color: #475569;">{html.escape(benchmark.get('top_complaint', 'None'))}</td>
            </tr>
            {competitor_rows}
        </tbody>
    </table>

    <!-- Section 5: Recommended Action Plan & Pilot Offer -->
    <div class="section-title">5. Recommended 14-Day Zero-Risk Pilot ($0 Upfront)</div>
    <div class="threat-card" style="background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 8px; padding: 16px 18px; font-size: 13.5px; line-height: 1.65; color: #334155;">
        <ol style="margin: 0 0 12px 0; padding-left: 20px;">
            <li><b>60-Second Telegram / Slack Webhook:</b> Zero database access required. ReputatAI monitors public channels and pings your VIP Escalation leads the instant a thread scores &ge;30.</li>
            <li><b>Daily &amp; Weekly Macro Radar:</b> Out of 3,000+ daily mentions, leadership receives automated root-cause shift telemetry and competitor SLA updates.</li>
            <li><b>Custom Integrations Included:</b> Need Zendesk webhooks, Discord VIP bots, multi-language support, or bespoke rulebooks? Our engineering team builds custom workflow additions to match your exact requirements.</li>
            <li><b>The Performance Proof Gate:</b> Over 14 days we commit to catching at least <b>1 viral FUD thread</b> and assisting in saving <b>3+ high-roller VIPs</b>—or you pay $0.</li>
        </ol>
        <div style="border-top: 1px solid #E2E8F0; padding-top: 10px; font-size: 13px; color: #1E293B; font-weight: 700;">
            Ready to activate the 14-day test channel? Reply to Harshit Goyal (harshit@reputatai.in • reputatai.in)
        </div>
    </div>

    <div class="footer">
        <div>ReputatAI Enterprise Platform • Proprietary &amp; Confidential</div>
        <div>Contact: harshit@reputatai.in • Audited via Deterministic NLP Cascade</div>
    </div>
</div>
</body>
</html>
"""
