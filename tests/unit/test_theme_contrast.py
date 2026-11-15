"""Kontras warna design system harus memenuhi WCAG 2.x AA: teks >= 4.5:1, komponen non-teks >= 3:1."""

import pytest

from holygrail.ui.theme import NON_TEXT, PAIRS, SEGMENT_COLORS, TOKENS, css


def _lin(c: float) -> float:
    c /= 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def ratio(a: str, b: str) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def test_palette_matches_requested_brief():
    assert TOKENS["paper"] == "#F8FAFC" and TOKENS["surface"] == "#FFFFFF"
    assert TOKENS["line"] == "#E2E8F0" and TOKENS["ink"] == "#0F172A"


@pytest.mark.parametrize("fg,bg,name", PAIRS)
def test_text_pairs_meet_aa(fg, bg, name):
    assert ratio(TOKENS[fg], TOKENS[bg]) >= 4.5, f"{name}: {ratio(TOKENS[fg], TOKENS[bg]):.2f}"


@pytest.mark.parametrize("fg,bg,name", NON_TEXT)
def test_non_text_components_meet_3_to_1(fg, bg, name):
    assert ratio(TOKENS[fg], TOKENS[bg]) >= 3.0, f"{name}: {ratio(TOKENS[fg], TOKENS[bg]):.2f}"


@pytest.mark.parametrize("name,color", SEGMENT_COLORS.items())
def test_chart_segment_colors_are_visible_on_white(name, color):
    assert ratio(color, TOKENS["surface"]) >= 3.0


def test_segment_ramp_is_single_hue_not_rainbow():
    # semua warna segmen: kanal hijau dominan (tidak ada merah/biru/ungu mencolok)
    for color in SEGMENT_COLORS.values():
        r, g, b = (int(color[i : i + 2], 16) for i in (1, 3, 5))
        assert g > r and g >= b


def test_css_has_accessibility_rules():
    out = css()
    assert "font-variant-numeric:tabular-nums" in out
    assert "min-height:44px" in out
    assert ":focus-visible" in out
    assert "prefers-reduced-motion" in out


def test_css_hides_streamlit_chrome_but_keeps_sidebar_toggle():
    out = css()
    for hidden in ("stDecoration", "stToolbar", "stMainMenu", "stFooter", "footer", "stAppDeployButton"):
        assert hidden in out
    assert "stExpandSidebarButton" in out  # tombol buka sidebar tetap terjangkau di tablet


def test_css_avoids_ai_template_patterns():
    out = css().lower()
    assert "linear-gradient" not in out and "radial-gradient" not in out  # tanpa gradasi dekoratif
    assert "backdrop-filter" not in out
    assert "box-shadow:none" in out
