"""Unit tests for the pitch dossier generator and PDF export."""
from app.core.pitch_dossier import (
    _find_headless_browsers,
    generate_interactive_pitch_dossier_html,
    render_html_to_pdf_bytes,
)


def test_generate_interactive_pitch_dossier_html() -> None:
    html_content = generate_interactive_pitch_dossier_html()
    assert "<!DOCTYPE html>" in html_content
    assert "ReputatAI × Stake" in html_content
    assert "Inbound Chat vs. Public Perimeter" in html_content
    assert "Minute 00:00" in html_content
    assert "Roobet" in html_content
    assert "Tier-1 Crypto Derivatives Exchange" in html_content
    assert "14-Day Zero-Risk Pilot" in html_content
    assert "harshit@reputatai.in" in html_content


def test_render_html_to_pdf_bytes() -> None:
    if not _find_headless_browsers():
        return
    pdf_bytes = render_html_to_pdf_bytes("<html><body><h1>ReputatAI Test PDF</h1></body></html>")
    assert pdf_bytes is not None
    assert pdf_bytes.startswith(b"%PDF")
