"""Kontras warna design system harus memenuhi WCAG 2.x AA (>= 4.5:1 untuk teks normal)."""

import pytest

from holygrail.ui.theme import PAIRS, SEGMENT_COLORS, TOKENS, css


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


@pytest.mark.parametrize("fg,bg,name", PAIRS)
def test_text_pairs_meet_aa(fg, bg, name):
    assert ratio(TOKENS[fg], TOKENS[bg]) >= 4.5, f"{name}: {ratio(TOKENS[fg], TOKENS[bg]):.2f}"


def test_focus_ring_and_chart_colors_have_non_text_contrast():
    for surface in ("paper", "surface"):
        assert ratio(TOKENS["focus"], TOKENS[surface]) >= 3.0
    for name, color in SEGMENT_COLORS.items():
        assert ratio(color, TOKENS["surface"]) >= 3.0, name


def test_css_has_accessibility_rules():
    out = css()
    assert "font-variant-numeric:tabular-nums" in out
    assert "min-height:44px" in out
    assert ":focus-visible" in out
    assert "prefers-reduced-motion" in out
