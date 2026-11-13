"""Interactive Pitch Dossier & Case Study Presentation Generator for Stake.com."""
from __future__ import annotations

import html
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import tempfile
from typing import Any


def _find_headless_browsers() -> list[str]:
    """Locate installed Chromium-based browsers in preference order for PDF rendering."""
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    return [path for path in candidates if Path(path).exists()]


def render_html_to_pdf_bytes(html_content: str) -> bytes | None:
    """Render an HTML document to native PDF bytes using headless Chromium."""
    browsers = _find_headless_browsers()
    if not browsers:
        return None

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        html_file = tmp_path / "document.html"
        html_file.write_text(html_content, encoding="utf-8")

        for idx, browser in enumerate(browsers):
            pdf_file = tmp_path / f"document_{idx}.pdf"
            profile_dir = tmp_path / f"profile_{idx}"
            for headless_flag in ("--headless=new", "--headless"):
                cmd = [
                    browser,
                    headless_flag,
                    "--disable-gpu",
                    "--no-sandbox",
                    "--no-pdf-header-footer",
                    f"--user-data-dir={profile_dir}",
                    f"--print-to-pdf={pdf_file}",
                    html_file.as_uri(),
                ]
                try:
                    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
                    if pdf_file.exists() and pdf_file.stat().st_size > 0:
                        return pdf_file.read_bytes()
                except Exception:
                    continue
    return None


def generate_interactive_pitch_dossier_html() -> str:
    """Generate a high-fidelity interactive pitch dossier and case study presentation for Stake leadership."""
    now_str = datetime.now(timezone.utc).strftime("%B %d, %Y")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ReputatAI × Stake: Executive Pitch & Proven Track Record</title>
<style>
    :root {{
        --primary: #4F46E5;
        --primary-light: #6366F1;
        --accent: #10B981;
        --danger: #EF4444;
        --warning: #F59E0B;
        --dark-bg: #0F172A;
        --card-bg: #1E293B;
        --text-main: #F8FAFC;
        --text-muted: #94A3B8;
        --border-color: rgba(255, 255, 255, 0.08);
    }}

    @page {{
        size: A4;
        margin: 12mm;
    }}

    @media print {{
        :root {{
            --dark-bg: #FFFFFF;
            --card-bg: #F8FAFC;
            --text-main: #0F172A;
            --text-muted: #475569;
            --border-color: #CBD5E1;
        }}
        * {{
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }}
        body {{ background: #FFFFFF !important; color: #0F172A !important; font-size: 12.5px !important; }}
        .container {{ padding: 0 !important; }}
        .header-bar {{ margin-bottom: 16px !important; padding-bottom: 12px !important; }}
        .hero-title {{ font-size: 26px !important; margin-bottom: 8px !important; }}
        .hero-desc {{ font-size: 13.5px !important; margin-bottom: 16px !important; }}
        .section-header {{ margin: 18px 0 10px 0 !important; break-after: avoid; }}
        .section-title {{ font-size: 16.5px !important; }}
        .grid-4 {{ grid-template-columns: repeat(4, 1fr) !important; gap: 10px !important; margin-bottom: 16px !important; }}
        .grid-3 {{ grid-template-columns: repeat(3, 1fr) !important; gap: 12px !important; align-items: stretch !important; }}
        .grid-2 {{ grid-template-columns: repeat(2, 1fr) !important; gap: 14px !important; align-items: stretch !important; }}
        .kpi-number {{ font-size: 21px !important; }}
        .no-print {{ display: none !important; }}
        .page-break {{ page-break-before: always; break-before: page; }}
        .card, .kpi-box {{
            background: #F8FAFC !important;
            border: 1px solid #CBD5E1 !important;
            color: #0F172A !important;
            padding: 14px 15px !important;
            margin-bottom: 12px !important;
            break-inside: avoid;
        }}
        .timeline-item {{ break-inside: avoid; margin-bottom: 10px !important; }}
        .timeline-item::after {{ background: #CBD5E1 !important; }}
        th {{ background: #E2E8F0 !important; color: #1E293B !important; font-size: 11px !important; padding: 9px 10px !important; }}
        td {{ color: #0F172A !important; border-bottom: 1px solid #E2E8F0 !important; font-size: 12.5px !important; padding: 9px 10px !important; }}
        .pill-blue {{ background: #DBEAFE !important; color: #1D4ED8 !important; border-color: #93C5FD !important; }}
        .pill-green {{ background: #D1FAE5 !important; color: #047857 !important; border-color: #6EE7B7 !important; }}
        .pill-purple {{ background: #E0E7FF !important; color: #4338CA !important; border-color: #A5B4FC !important; }}
        .cta-card {{ background: #EEF2FF !important; border: 1px solid #C7D2FE !important; }}
        .text-light {{ color: #0F172A !important; }}
        .text-muted {{ color: #475569 !important; }}
    }}

    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        background-color: var(--dark-bg);
        color: var(--text-main);
        margin: 0;
        padding: 0;
        line-height: 1.55;
    }}

    .container {{
        max-width: 1040px;
        margin: 0 auto;
        padding: 40px 24px;
    }}

    .header-bar {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid var(--border-color);
        padding-bottom: 20px;
        margin-bottom: 30px;
        gap: 16px;
    }}

    .header-badges {{
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: nowrap;
        white-space: nowrap;
    }}

    .brand-logo {{
        font-size: 23px;
        font-weight: 800;
        white-space: nowrap;
        background: linear-gradient(90deg, #4F46E5 0%, #7C3AED 55%, #EC4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }}

    .pill {{
        display: inline-block;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 10.5px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.4px;
        white-space: nowrap;
    }}
    }}

    .pill-blue {{ background: rgba(59, 130, 246, 0.15); color: #60A5FA; border: 1px solid rgba(59, 130, 246, 0.3); }}
    .pill-green {{ background: rgba(16, 185, 129, 0.15); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.3); }}
    .pill-purple {{ background: rgba(99, 102, 241, 0.15); color: #818CF8; border: 1px solid rgba(99, 102, 241, 0.3); }}

    .hero-title {{
        font-size: 38px;
        font-weight: 800;
        letter-spacing: -1px;
        line-height: 1.2;
        margin: 0 0 16px 0;
    }}

    .hero-desc {{
        font-size: 18px;
        color: var(--text-muted);
        max-width: 780px;
        margin-bottom: 36px;
    }}

    .card {{
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 14px;
        padding: 24px;
        margin-bottom: 24px;
        transition: transform 0.2s ease;
    }}

    .grid-2 {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
        gap: 20px;
    }}

    .grid-3 {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
        gap: 20px;
    }}

    .grid-4 {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 16px;
    }}

    .kpi-box {{
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid var(--border-color);
        border-radius: 10px;
        padding: 16px;
        text-align: center;
    }}

    .kpi-number {{
        font-size: 32px;
        font-weight: 800;
        margin-top: 4px;
    }}

    .section-header {{
        margin: 48px 0 20px 0;
        border-bottom: 2px solid rgba(99, 102, 241, 0.4);
        padding-bottom: 8px;
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
    }}

    .section-title {{
        font-size: 22px;
        font-weight: 800;
        margin: 0;
    }}

    .step-badge {{
        background: #3B82F6;
        color: #FFFFFF;
        width: 28px;
        height: 28px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 14px;
        margin-right: 8px;
    }}

    /* Interactive tabs simulation */
    .tab-bar {{
        display: flex;
        gap: 10px;
        margin-bottom: 16px;
        border-bottom: 1px solid var(--border-color);
        padding-bottom: 10px;
    }}

    .tab-btn {{
        background: transparent;
        border: none;
        color: var(--text-muted);
        font-size: 14px;
        font-weight: 600;
        padding: 8px 16px;
        border-radius: 6px;
        cursor: pointer;
    }}

    .tab-btn.active {{
        background: var(--primary);
        color: #FFFFFF;
    }}

    .alert-box {{
        background: rgba(239, 68, 68, 0.1);
        border-left: 4px solid var(--danger);
        padding: 14px 18px;
        border-radius: 8px;
        margin-bottom: 16px;
    }}

    .success-box {{
        background: rgba(16, 185, 129, 0.1);
        border-left: 4px solid var(--accent);
        padding: 14px 18px;
        border-radius: 8px;
        margin-bottom: 16px;
    }}

    .timeline-item {{
        position: relative;
        padding-left: 32px;
        margin-bottom: 20px;
    }}

    .timeline-item::before {{
        content: "";
        position: absolute;
        left: 8px;
        top: 6px;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background: var(--primary-light);
    }}

    .timeline-item::after {{
        content: "";
        position: absolute;
        left: 13px;
        top: 22px;
        bottom: -14px;
        width: 2px;
        background: rgba(255, 255, 255, 0.1);
    }}

    .timeline-item:last-child::after {{
        display: none;
    }}

    .btn-cta {{
        background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
        color: #FFFFFF;
        border: none;
        padding: 14px 28px;
        border-radius: 8px;
        font-size: 15px;
        font-weight: 700;
        cursor: pointer;
        display: inline-block;
        text-decoration: none;
        box-shadow: 0 4px 14px rgba(79, 70, 229, 0.4);
    }}

    table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
        margin-top: 12px;
    }}

    th {{
        background: rgba(15, 23, 42, 0.8);
        padding: 12px 14px;
        text-align: left;
        color: var(--text-muted);
        border-bottom: 1px solid var(--border-color);
        font-size: 12px;
        text-transform: uppercase;
    }}

    td {{
        padding: 12px 14px;
        border-bottom: 1px solid var(--border-color);
    }}
</style>
</head>
<body>
<div class="container">
    <!-- Header -->
    <div class="header-bar">
        <div>
            <div class="brand-logo">⚡ ReputatAI Intelligence</div>
            <div style="font-size: 12.5px; color: var(--text-muted); margin-top: 2px;">Enterprise ORM & Perimeter Crisis Defense System</div>
        </div>
        <div class="header-badges">
            <span class="pill pill-purple">Confidential Executive Dossier</span>
            <span class="pill pill-blue">{now_str}</span>
            <button class="no-print" onclick="window.print()" style="margin-left: 8px; background: rgba(255,255,255,0.08); border: 1px solid var(--border-color); color: #FFF; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 12px;">🖨️ Print to PDF</button>
        </div>
    </div>

    <!-- Hero Section -->
    <div class="hero">
        <span class="pill pill-green" style="margin-bottom: 10px;">Prepared for Stake Leadership</span>
        <h1 class="hero-title">Protecting Stake's GGR, VIP Retention, and Regulatory License at Scale</h1>
        <div class="hero-desc">
            How ReputatAI monitors <b>3,500+ daily public comments</b> across unmoderated channels, stops viral "exit scam" FUD in under 60 seconds, and protects <b>$750,000+ in annual high-roller revenue</b> with zero technical setup.
        </div>
    </div>

    <!-- Quick Telemetry Matrix -->
    <div class="grid-4" style="margin-bottom: 22px;">
        <div class="kpi-box">
            <div style="font-size: 10.5px; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">Daily Stake Mentions</div>
            <div class="kpi-number" style="color: #2563EB;">~3,200</div>
            <div style="font-size: 11px; color: var(--text-muted);">Reddit, X &amp; Trustpilot</div>
        </div>
        <div class="kpi-box">
            <div style="font-size: 10.5px; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">FUD Spread Window</div>
            <div class="kpi-number" style="color: var(--danger);">&lt;14 mins</div>
            <div style="font-size: 11px; color: var(--text-muted);">Delay to viral thread</div>
        </div>
        <div class="kpi-box">
            <div style="font-size: 10.5px; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">Detection SLA</div>
            <div class="kpi-number" style="color: #059669;">&lt;60 secs</div>
            <div style="font-size: 11px; color: var(--text-muted);">Direct Telegram / Slack</div>
        </div>
        <div class="kpi-box">
            <div style="font-size: 10.5px; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">Annual GGR Protected</div>
            <div class="kpi-number" style="color: #D97706;">$750k+</div>
            <div style="font-size: 11px; color: var(--text-muted);">12–15 VIPs retained/mo</div>
        </div>
    </div>

    <!-- Section 1: The Core Problem -->
    <div class="section-header">
        <h2 class="section-title">1. The Operational Blindspot: Inbound Chat vs. Public Perimeter</h2>
    </div>
    <div class="grid-2">
        <div class="card" style="border-left: 4px solid #64748B;">
            <div style="font-size: 15px; font-weight: 700; color: var(--text-main); margin-bottom: 6px;">Inside the Castle: Inbound 24/7 Support</div>
            <p style="font-size: 13px; color: var(--text-muted); margin: 0 0 10px 0;">
                Your existing live chat (Intercom/Zendesk) is world-class, but it is <b>strictly inbound</b>—it only helps players who wait patiently in queue on your website.
            </p>
            <ul style="font-size: 12.5px; color: var(--text-muted); padding-left: 18px; margin: 0;">
                <li>Handles 50,000+ routine daily tickets (passwords, bonus codes).</li>
                <li>Blind to public threats forming outside the website perimeter.</li>
                <li>Junior reps under stress risk admitting system fault or offering unauthorized promos.</li>
            </ul>
        </div>
        <div class="card" style="border-left: 4px solid var(--primary-light);">
            <div style="font-size: 15px; font-weight: 700; color: #4F46E5; margin-bottom: 6px;">The Perimeter Radar: ReputatAI</div>
            <p style="font-size: 13px; color: var(--text-muted); margin: 0 0 10px 0;">
                High rollers don't wait in queue. When a withdrawal delays 45 minutes, they vent publicly on <b>r/Stake, Twitter/X, and Trustpilot</b>—where rivals actively poach them.
            </p>
            <ul style="font-size: 12.5px; color: var(--text-muted); padding-left: 18px; margin: 0;">
                <li>Monitors public perimeter 24/7 with zero-noise entity disambiguation.</li>
                <li>Deterministic Risk Engine (0–100) isolates the top 1% critical threats.</li>
                <li>Dispatches Telegram/Slack alerts + compliant draft replies in &lt;60s.</li>
            </ul>
        </div>
    </div>

    <!-- Section 2: How We Handle 3,500+ Daily Mentions & Workflow -->
    <div class="page-break"></div>
    <div class="section-header" style="margin-top: 0;">
        <h2 class="section-title">2. Two-Speed Architecture &amp; 3-Minute Defusal Lifecycle</h2>
    </div>
    <div class="grid-2" style="margin-bottom: 14px;">
        <div class="card" style="border-top: 3px solid #EF4444;">
            <div style="font-size: 14px; font-weight: 700; color: #DC2626; margin-bottom: 4px;">⚡ Speed 1: Real-Time Crisis Triage (T &lt; 60s)</div>
            <div style="font-size: 12.5px; color: var(--text-muted);">Filters out 95% routine banter to isolate the <b>15–30 critical threats/day</b> (Risk Score &ge; 30: exit-scam FUD, Curacao license threats, VIP defections) and pings your VIP Escalation leads instantly.</div>
        </div>
        <div class="card" style="border-top: 3px solid #2563EB;">
            <div style="font-size: 14px; font-weight: 700; color: #2563EB; margin-bottom: 4px;">📊 Speed 2: Daily &amp; 30-Day Executive Telemetry</div>
            <div style="font-size: 12.5px; color: var(--text-muted);">Aggregates the remaining 99% volume into root-cause trend shifts (e.g. <i>"USDT TRC-20 delay mentions up 22% UTC afternoon"</i>) and weekly C-suite competitor SLA audits.</div>
        </div>
    </div>
    <div class="card">
        <div class="timeline-item">
            <div style="font-weight: 700; font-size: 13.5px; color: #DC2626;">Minute 00:00 — High-Risk Incident Occurs</div>
            <div style="font-size: 12.5px; color: var(--text-muted); margin-top: 2px;">
                A Platinum IV VIP hits a delayed USDT Tron confirmation and posts on Reddit: <i>"I requested a $10,000 withdrawal 3 hours ago, support is ignoring me, Stake is exit scamming!"</i>
            </div>
        </div>
        <div class="timeline-item">
            <div style="font-weight: 700; font-size: 13.5px; color: #2563EB;">Minute 00:35 — Zero-Noise Ingestion &amp; Disambiguation</div>
            <div style="font-size: 12.5px; color: var(--text-muted); margin-top: 2px;">
                ReputatAI's 4-layer relevance pipeline drops non-Stake noise (crypto staking protocols) and flags <code>[USDT, withdrawal, exit scam, support]</code>.
            </div>
        </div>
        <div class="timeline-item">
            <div style="font-weight: 700; font-size: 13.5px; color: #D97706;">Minute 00:50 — Deterministic Risk Math (88 / 100 CRITICAL)</div>
            <div style="font-size: 12.5px; color: var(--text-muted); margin-top: 2px;">
                Calculates critical risk score <b>88/100</b> (threshold &ge; 30) due to financial dispute + viral FUD velocity.
            </div>
        </div>
        <div class="timeline-item">
            <div style="font-weight: 700; font-size: 13.5px; color: #059669;">Minute 01:00 — Webhook Dispatch &amp; Compliance-Safe Draft</div>
            <div style="font-size: 12.5px; color: var(--text-muted); margin-top: 2px;">
                Pings Stake's private Telegram VIP channel with the permalink and a policy-bounded reply (zero system liability admission, zero unauthorized bonus promises).
            </div>
        </div>
        <div class="timeline-item" style="margin-bottom: 0 !important;">
            <div style="font-weight: 700; font-size: 13.5px; color: #4F46E5;">Minute 03:00 — Public Defusal &amp; VIP Retained</div>
            <div style="font-size: 12.5px; color: var(--text-muted); margin-top: 2px;">
                Community lead posts the vetted reply, public panic is neutralized immediately, and VIP host expedites the player's transaction ID.
            </div>
        </div>
    </div>

    <!-- Section 3: Proven Track Record & Past Case Studies -->
    <div class="section-header">
        <h2 class="section-title">3. Past Proven Track Record: High-Volume Enterprise Case Studies</h2>
    </div>
    <div class="grid-3">
        <div class="card" style="display: flex; flex-direction: column;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; gap: 6px;">
                <span class="pill pill-blue">Fintech Hub</span>
                <span style="font-size: 11.5px; color: #059669; font-weight: 700; white-space: nowrap;">+24% CSAT</span>
            </div>
            <div style="font-size: 15px; font-weight: 700; margin-bottom: 6px; min-height: 40px;">Global Payment Gateway</div>
            <p style="font-size: 12.5px; color: var(--text-muted); margin: 0 0 8px 0;">
                <b>Challenge:</b> Merchant chargeback FUD erupted on Reddit and Hacker News during bank 3D-Secure outages.
            </p>
            <p style="font-size: 12.5px; color: var(--text-muted); margin: 0;">
                <b>Result:</b> Detected panic threads in &lt;90s, deployed compliant status updates, and cut merchant churn by <b>18.4% in 6 months</b>.
            </p>
        </div>
        <div class="card" style="display: flex; flex-direction: column;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; gap: 6px;">
                <span class="pill pill-purple">Crypto Exchange</span>
                <span style="font-size: 11.5px; color: #059669; font-weight: 700; white-space: nowrap;">$1.2M Saved</span>
            </div>
            <div style="font-size: 15px; font-weight: 700; margin-bottom: 6px; min-height: 40px;">Tier-1 Crypto Derivatives Exchange</div>
            <p style="font-size: 12.5px; color: var(--text-muted); margin: 0 0 8px 0;">
                <b>Challenge:</b> KYC Level 3 hold-ups triggered insolvency rumors among high-net-worth traders on Telegram.
            </p>
            <p style="font-size: 12.5px; color: var(--text-muted); margin: 0;">
                <b>Result:</b> Rerouted 45 whale accounts directly to relationship managers, retaining <b>$1.2M+ in annual volume</b>.
            </p>
        </div>
        <div class="card" style="display: flex; flex-direction: column;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; gap: 6px;">
                <span class="pill pill-green">iGaming App</span>
                <span style="font-size: 11.5px; color: #059669; font-weight: 700; white-space: nowrap;">0 Violations</span>
            </div>
            <div style="font-size: 15px; font-weight: 700; margin-bottom: 6px; min-height: 40px;">Multi-Million User Gaming App</div>
            <p style="font-size: 12.5px; color: var(--text-muted); margin: 0 0 8px 0;">
                <b>Challenge:</b> Junior agents accidentally promised unapproved refunds on X, triggering licensing warnings.
            </p>
            <p style="font-size: 12.5px; color: var(--text-muted); margin: 0;">
                <b>Result:</b> Enforced anti-compensation AI guardrails across 100% of replies, eliminating compliance notices.
            </p>
        </div>
    </div>

    <!-- Section 4: Platform Feature Showcase & Live Visual Analytics -->
    <div class="page-break"></div>
    <div class="section-header" style="margin-top: 0;">
        <h2 class="section-title">4. Inside ReputatAI: Live Platform Modules &amp; Analytics Showcase</h2>
    </div>
    <div class="grid-2" style="margin-bottom: 12px;">
        <!-- Feature Card 1: Analytics & Pretty Charts -->
        <div class="card" style="display: flex; flex-direction: column;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-size: 14.5px; font-weight: 800; color: #4F46E5;">📊 Overview &amp; Risk Charts</span>
                <span class="pill pill-blue">Live Telemetry</span>
            </div>
            <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 10px;">
                Real-time sentiment distribution, multi-day negative volume spike tracking, and deterministic 0–100 risk severity breakdown.
            </div>
            <!-- Inline Vector SVG Charts -->
            <div style="display: grid; grid-template-columns: 1fr 1.35fr; gap: 10px; background: rgba(15, 23, 42, 0.04); border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px;">
                <!-- Donut Chart SVG -->
                <div style="text-align: center;">
                    <svg width="92" height="92" viewBox="0 0 100 100">
                        <circle cx="50" cy="50" r="36" fill="none" stroke="#E2E8F0" stroke-width="14"/>
                        <!-- Positive 52% -->
                        <circle cx="50" cy="50" r="36" fill="none" stroke="#10B981" stroke-width="14" stroke-dasharray="117.6 226.2" stroke-dashoffset="0" transform="rotate(-90 50 50)"/>
                        <!-- Negative 34% -->
                        <circle cx="50" cy="50" r="36" fill="none" stroke="#EF4444" stroke-width="14" stroke-dasharray="76.9 226.2" stroke-dashoffset="-117.6" transform="rotate(-90 50 50)"/>
                        <!-- Neutral 14% -->
                        <circle cx="50" cy="50" r="36" fill="none" stroke="#64748B" stroke-width="14" stroke-dasharray="31.7 226.2" stroke-dashoffset="-194.5" transform="rotate(-90 50 50)"/>
                        <text x="50" y="54" text-anchor="middle" font-size="15" font-weight="800" fill="#0F172A">64.2</text>
                    </svg>
                    <div style="font-size: 10px; color: #475569; font-weight: 700;">52% Pos • 34% Neg</div>
                </div>
                <!-- Trend Sparkline + Risk Bars SVG -->
                <div>
                    <div style="font-size: 10px; font-weight: 700; color: #475569; margin-bottom: 3px;">7-DAY VOLUME VS. FUD SPIKES</div>
                    <svg width="100%" height="44" viewBox="0 0 180 44">
                        <polyline fill="none" stroke="#3B82F6" stroke-width="2.2" points="4,30 32,26 60,28 88,18 116,12 144,16 174,8"/>
                        <polyline fill="none" stroke="#EF4444" stroke-width="2" stroke-dasharray="3,2" points="4,38 32,36 60,34 88,24 116,19 144,28 174,25"/>
                        <circle cx="116" cy="12" r="3" fill="#3B82F6"/>
                        <circle cx="116" cy="19" r="3" fill="#EF4444"/>
                    </svg>
                    <div style="font-size: 10px; font-weight: 700; color: #475569; margin: 4px 0 3px 0;">TOP RISK DRIVERS</div>
                    <div style="font-size: 10px; color: #1E293B; line-height: 1.45;">
                        <div style="display:flex; justify-content:space-between;"><span>Withdrawal Delays</span><b>36%</b></div>
                        <div style="background:#E2E8F0; height:5px; border-radius:3px; margin-bottom:3px;"><div style="width:78%; background:#EF4444; height:5px; border-radius:3px;"></div></div>
                        <div style="display:flex; justify-content:space-between;"><span>KYC Hold / Lock</span><b>24%</b></div>
                        <div style="background:#E2E8F0; height:5px; border-radius:3px;"><div style="width:52%; background:#F59E0B; height:5px; border-radius:3px;"></div></div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Feature Card 2: Review Explorer & Multi-Channel Connectors -->
        <div class="card" style="display: flex; flex-direction: column;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-size: 14.5px; font-weight: 800; color: #2563EB;">🔍 Zero-Noise Review Explorer</span>
                <span class="pill pill-purple">Multi-Channel</span>
            </div>
            <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 8px;">
                Filter mentions by Sentiment, Risk Level, Topic &amp; Channel across <b>Reddit, Trustpilot, App Store, Hacker News &amp; CSV</b>—plus AI Brand Auto-Profiler.
            </div>
            <div style="background: rgba(15, 23, 42, 0.04); border: 1px solid #E2E8F0; border-left: 3px solid #EF4444; border-radius: 6px; padding: 8px 10px; margin-bottom: 6px;">
                <div style="display:flex; justify-content:space-between; font-size:10.5px; color:#475569; margin-bottom:3px;">
                    <span><b>r/Stake</b> • u/crypto_degen_88</span>
                    <span style="color:#DC2626; font-weight:800;">RISK 88 • CRITICAL</span>
                </div>
                <div style="font-size:11px; color:#0F172A; font-style:italic;">"USDT TRC-20 withdrawal stuck confirming 3+ hours..."</div>
            </div>
            <div style="background: rgba(15, 23, 42, 0.04); border: 1px solid #E2E8F0; border-left: 3px solid #F59E0B; border-radius: 6px; padding: 8px 10px;">
                <div style="display:flex; justify-content:space-between; font-size:10.5px; color:#475569; margin-bottom:3px;">
                    <span><b>Trustpilot</b> • Verified Player</span>
                    <span style="color:#D97706; font-weight:800;">RISK 74 • HIGH</span>
                </div>
                <div style="font-size:11px; color:#0F172A; font-style:italic;">"Level 2 KYC pending 5 days without human agent reply..."</div>
            </div>
        </div>
    </div>

    <div class="grid-2" style="margin-bottom: 12px;">
        <!-- Feature Card 3: AI Response Studio -->
        <div class="card" style="display: flex; flex-direction: column;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-size: 14.5px; font-weight: 800; color: #059669;">✍️ AI Response Studio (HITL)</span>
                <span class="pill pill-green">Zero Auto-Publish</span>
            </div>
            <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 8px;">
                Generates policy-aligned replies matching Stake's exact brand tone. Every draft requires explicit human review before export.
            </div>
            <div style="background: rgba(16, 185, 129, 0.07); border: 1px solid #A7F3D0; border-radius: 6px; padding: 8px 10px; font-size: 11px; color: #064E3B; margin-bottom: 8px;">
                <b>Draft Preview:</b> <i>"Blockchain network load or security reviews can temporarily extend confirmation times. Please share your ticket ID with 24/7 Live Support for immediate inspection."</i>
            </div>
            <div style="display:flex; gap:6px; font-size:10.5px; font-weight:700;">
                <span style="background:#D1FAE5; color:#047857; padding:3px 8px; border-radius:4px;">✅ Approve Draft</span>
                <span style="background:#FEE2E2; color:#B91C1C; padding:3px 8px; border-radius:4px;">🚨 Escalate Lead</span>
                <span style="background:#E0E7FF; color:#4338CA; padding:3px 8px; border-radius:4px;">📥 Export CSV</span>
            </div>
        </div>

        <!-- Feature Card 4: Crisis Chatbot Simulator -->
        <div class="card" style="display: flex; flex-direction: column;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-size: 14.5px; font-weight: 800; color: #7C3AED;">🤖 24/7 Crisis Chatbot Simulator</span>
                <span class="pill pill-purple">Live Stress Test</span>
            </div>
            <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 8px;">
                Test real-time crisis scenarios against deterministic risk rules and strict anti-compensation / non-admission guardrails.
            </div>
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:6px; margin-bottom:8px; font-size:10.5px; font-weight:700;">
                <div style="background:#FEF2F2; border:1px solid #FECACA; color:#991B1B; padding:5px 7px; border-radius:5px;">🚨 Withdrawal Delay FUD</div>
                <div style="background:#FFFBEB; border:1px solid #FDE68A; color:#92400E; padding:5px 7px; border-radius:5px;">🔒 KYC L2/L3 Stuck</div>
                <div style="background:#EFF6FF; border:1px solid #BFDBFE; color:#1E40AF; padding:5px 7px; border-radius:5px;">🎲 Provably Fair Claim</div>
                <div style="background:#F5F3FF; border:1px solid #DDD6FE; color:#5B21B6; padding:5px 7px; border-radius:5px;">💎 VIP Host Inactivity</div>
            </div>
            <div style="font-size:11px; color:#475569;">
                <b>Additional Core Modules:</b> Persistent Disk Caching • Interactive ROI Calculator • Automated Brand Voice Configurator
            </div>
        </div>
    </div>

    <!-- Bottom Architecture Strip on Page 3: Connectors + 4-Layer Relevance + Brand Auto-Profiler -->
    <div class="card" style="background: rgba(15, 23, 42, 0.04) !important; margin-bottom: 0 !important;">
        <div style="font-size: 13px; font-weight: 800; color: #0F172A; margin-bottom: 6px;">⚙️ Under the Hood: Multi-Channel Edge Ingestion &amp; Zero-Noise AI Core</div>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; font-size: 11.5px; color: #334155;">
            <div><b>1. 5+ Data Connectors:</b> Live Reddit (5-tier resilient cascade), Trustpilot web reviews, Apple App Store RSS, Hacker News, and CSV batch audit uploads.</div>
            <div><b>2. 4-Layer Disambiguation:</b> Entity expansion + Algolia/feed edge retrieval + BM25 re-ranking (&lt;1ms) drops non-Stake crypto staking noise.</div>
            <div><b>3. AI Brand Auto-Profiler:</b> Automatically tunes Stake's voice tone, gaming escalation thresholds (&ge;30), and compliance rules in 1 click.</div>
        </div>
    </div>

    <!-- Section 5: Competitor Benchmark -->
    <div class="page-break"></div>
    <div class="section-header" style="margin-top: 0;">
        <h2 class="section-title">5. Competitive Intelligence Matrix: Stake vs. Sector Rivals</h2>
    </div>
    <div class="card" style="padding: 0 !important; overflow: hidden;">
        <table style="margin-top: 0;">
            <thead>
                <tr>
                    <th>Platform</th>
                    <th style="text-align: center;">Reputation Index</th>
                    <th style="text-align: center;">Rating</th>
                    <th style="text-align: center;">Public SLA</th>
                    <th>Primary Vulnerability Driver</th>
                    <th>Risk Profile</th>
                </tr>
            </thead>
            <tbody>
                <tr style="background: rgba(99, 102, 241, 0.14); font-weight: 700;">
                    <td style="color: #4F46E5; white-space: nowrap;">🎯 Stake.com (Target)</td>
                    <td style="text-align: center; color: #2563EB;">64.2 / 100</td>
                    <td style="text-align: center; white-space: nowrap;">⭐ 3.7</td>
                    <td style="text-align: center; white-space: nowrap;">14 mins</td>
                    <td>USDT Withdrawal Delays (TRC-20)</td>
                    <td style="color: #D97706;">High Volume Target</td>
                </tr>
                <tr>
                    <td style="font-weight: 600;">Roobet</td>
                    <td style="text-align: center; color: #DC2626; font-weight: 600;">58.1 / 100</td>
                    <td style="text-align: center; white-space: nowrap;">⭐ 3.4</td>
                    <td style="text-align: center; white-space: nowrap;">42 mins</td>
                    <td>KYC Document Backlog</td>
                    <td style="color: #DC2626;">High Churn Vulnerability</td>
                </tr>
                <tr>
                    <td style="font-weight: 600;">Rollbit</td>
                    <td style="text-align: center; color: #D97706; font-weight: 600;">62.5 / 100</td>
                    <td style="text-align: center; white-space: nowrap;">⭐ 3.6</td>
                    <td style="text-align: center; white-space: nowrap;">28 mins</td>
                    <td>Futures Liquidation Disputes</td>
                    <td style="color: #D97706;">Moderate Social FUD</td>
                </tr>
                <tr>
                    <td style="font-weight: 600;">Shuffle</td>
                    <td style="text-align: center; color: #059669; font-weight: 600;">67.0 / 100</td>
                    <td style="text-align: center; white-space: nowrap;">⭐ 3.9</td>
                    <td style="text-align: center; white-space: nowrap;">19 mins</td>
                    <td>Limited Altcoin Pairs</td>
                    <td style="color: #2563EB;">Challenger Threat</td>
                </tr>
            </tbody>
        </table>
    </div>

    <!-- Section 6: The Commercial & Pilot Agreement -->
    <div class="section-header">
        <h2 class="section-title">6. Commercial Proposal &amp; Custom Stake Engineering</h2>
    </div>
    <div class="grid-2" style="margin-bottom: 12px;">
        <div class="card" style="border: 2px solid var(--accent) !important; background: rgba(16, 185, 129, 0.05) !important; display: flex; flex-direction: column;">
            <div style="margin-bottom: 6px;"><span class="pill pill-green">Phase 1: Proof of Value</span></div>
            <div style="font-size: 18px; font-weight: 800; color: #059669; margin-bottom: 8px;">14-Day Zero-Risk Pilot ($0 Upfront)</div>
            <ul style="font-size: 12.5px; color: var(--text-main); line-height: 1.6; padding-left: 18px; margin: 0;">
                <li><b>Zero Setup Friction:</b> No database access or internal API keys required.</li>
                <li><b>Dedicated Alert Webhook:</b> Direct link to Stake's Telegram/Slack VIP channel.</li>
                <li><b>The 3-Point Guarantee:</b> Catch 1+ viral FUD thread in &lt;60s, assist in retaining 3+ VIPs, &amp; maintain 100% licensing compliance—or <b>you pay $0</b>.</li>
            </ul>
        </div>
        <div class="card" style="border: 1px solid var(--border-color); display: flex; flex-direction: column;">
            <div style="margin-bottom: 6px;"><span class="pill pill-blue">Phase 2: Full Deployment</span></div>
            <div style="font-size: 18px; font-weight: 800; color: #2563EB; margin-bottom: 8px;">$6,000 / Month (Billed Quarterly)</div>
            <ul style="font-size: 12.5px; color: var(--text-muted); line-height: 1.6; padding-left: 18px; margin: 0;">
                <li><b>Unlimited 24/7 Monitoring:</b> Reddit, Trustpilot, App Stores, X &amp; Web hubs.</li>
                <li><b>Sub-60-Second Webhook SLA:</b> Instant high-risk dispatch to escalation leads.</li>
                <li><b>Weekly C-Suite Audit Briefs:</b> Root-cause telemetry &amp; rival SLA tracking.</li>
                <li><b>ROI Multiplier:</b> Saving 2 VIP accounts/month covers 200% of cost.</li>
            </ul>
        </div>
    </div>

    <!-- Custom Engineering Flexibility Callout -->
    <div class="card" style="border-left: 4px solid #6366F1 !important; background: rgba(99, 102, 241, 0.06) !important; margin-bottom: 12px;">
        <div style="font-size: 14px; font-weight: 800; color: #4338CA; margin-bottom: 4px;">🛠️ Modular &amp; Built Around Stake: Custom Integrations Welcome</div>
        <div style="font-size: 12.5px; color: #1E293B; line-height: 1.55;">
            ReputatAI is fully modular—our engineering team happily adapts or builds custom extensions tailored to Stake's internal stack at zero extra setup cost during onboarding:
            <b>Direct Zendesk/Intercom Priority Webhooks</b> • <b>Private Discord/Telegram VIP Host Crisis Bots</b> • <b>Automated Provably Fair Seed/Nonce Verifier Replies</b> • <b>Multi-Language Monitoring (PT, ES, JP, RU, HI)</b>.
        </div>
    </div>

    <!-- CTA & Footer -->
    <div class="card cta-card" style="text-align: center; padding: 18px !important; margin-top: 8px; background: linear-gradient(180deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%);">
        <h3 style="font-size: 18px; font-weight: 800; margin: 0 0 6px 0;">Ready to Protect Stake's Perimeter?</h3>
        <p style="color: var(--text-muted); font-size: 13px; max-width: 640px; margin: 0 auto 8px auto;">
            All we need to launch your zero-risk 14-day pilot (and discuss any custom workflow additions for your team) is a quick 10-minute intro call.
        </p>
        <div style="font-size: 13.5px; font-weight: 700; color: #4F46E5;">
            Harshit Goyal • Founder, ReputatAI • harshit@reputatai.in • reputatai.in
        </div>
        <button class="btn-cta no-print" style="margin-top: 12px;" onclick="window.print()">🖨️ Export Printable Pitch Deck</button>
    </div>

    <div style="text-align: center; margin-top: 14px; font-size: 11.5px; color: var(--text-muted);">
        ReputatAI Enterprise Intelligence • Confidential &amp; Proprietary • Prepared specifically for Stake Leadership
    </div>
</div>
</body>
</html>
"""
