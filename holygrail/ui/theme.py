"""Design system Holy Grail POS (v3 — app-shell SaaS/POS komersial).

Permukaan datar, garis tipis 1px, radius 8–12px, densitas informasi tinggi, satu aksen korporat (hijau pandan).
Semua pasangan teks/latar di PAIRS dan warna non-teks di NON_TEXT diuji WCAG AA di
tests/unit/test_theme_contrast.py. Chrome bawaan Streamlit (header, garis dekorasi, menu, footer) disembunyikan.
"""

from __future__ import annotations

import streamlit as st

TOKENS = {
    "paper": "#F8FAFC",        # latar aplikasi
    "surface": "#FFFFFF",      # kartu, sidebar
    "ink": "#0F172A",          # teks utama
    "ink_muted": "#475569",    # teks sekunder
    "line": "#E2E8F0",         # garis kartu (dekoratif)
    "line_strong": "#7C8BA1",  # batas kontrol input/tombol (>= 3:1)
    "hover": "#F1F5F9",        # hover netral
    "brand": "#0F5C4D",        # satu-satunya aksen korporat
    "brand_dark": "#0B4A3E",
    "on_brand": "#FFFFFF",
    "brand_soft": "#E7F1EE",
    "warn_soft": "#FEF3C7",
    "warn_text": "#8A4B08",
    "danger": "#A8231B",
    "danger_soft": "#FEE9E7",
    "focus": "#0B57D0",
}

# (teks, latar, deskripsi) — wajib >= 4.5:1
PAIRS = [
    ("ink", "paper", "teks utama di halaman"),
    ("ink", "surface", "teks utama di kartu"),
    ("ink", "hover", "teks utama saat hover"),
    ("ink_muted", "paper", "teks sekunder di halaman"),
    ("ink_muted", "surface", "teks sekunder di kartu"),
    ("ink_muted", "hover", "teks sekunder saat hover"),
    ("ink_muted", "brand_soft", "teks sekunder di tint merek"),
    ("on_brand", "brand", "teks tombol utama"),
    ("on_brand", "brand_dark", "teks tombol utama saat hover"),
    ("brand", "surface", "teks merek di kartu"),
    ("brand", "brand_soft", "teks nav aktif"),
    ("ink", "brand_soft", "teks utama di tint merek"),
    ("warn_text", "warn_soft", "lencana peringatan"),
    ("danger", "danger_soft", "lencana bahaya"),
    ("danger", "surface", "teks bahaya di kartu"),
]

# (warna, latar, deskripsi) — komponen non-teks, wajib >= 3:1 (WCAG 1.4.11)
NON_TEXT = [
    ("line_strong", "surface", "batas input di kartu"),
    ("line_strong", "paper", "batas input di halaman"),
    ("focus", "paper", "cincin fokus di halaman"),
    ("focus", "surface", "cincin fokus di kartu"),
    ("brand", "surface", "indikator nav & aksen grafik"),
]

# Rampa satu-hue (gelap → terang) untuk segmen pelanggan; label teks tetap menyertai.
SEGMENT_COLORS = {"Diamond": "#0A3D33", "Platinum": "#0F5C4D", "Gold": "#1F7A66", "Silver": "#3A8F7B", "Bronze": "#5BA08C"}

FONTS_URL = (
    "https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700"
    "&family=IBM+Plex+Mono:wght@400;500;600&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap"
)


def css() -> str:
    t = TOKENS
    return f"""
<style>
@import url('{FONTS_URL}');
:root {{
  --paper:{t['paper']}; --surface:{t['surface']}; --ink:{t['ink']}; --muted:{t['ink_muted']}; --line:{t['line']};
  --line-strong:{t['line_strong']}; --hover:{t['hover']}; --brand:{t['brand']}; --brand-dark:{t['brand_dark']};
  --on-brand:{t['on_brand']}; --brand-soft:{t['brand_soft']}; --warn-soft:{t['warn_soft']}; --warn-text:{t['warn_text']};
  --danger:{t['danger']}; --danger-soft:{t['danger_soft']}; --focus:{t['focus']};
  --font-display:'Bricolage Grotesque','Segoe UI',system-ui,sans-serif;
  --font-body:'Plus Jakarta Sans','Segoe UI',system-ui,sans-serif;
  --font-mono:'IBM Plex Mono',ui-monospace,Consolas,monospace;
  --r-sm:8px; --r-md:12px; --sidebar-w:256px;
}}

/* ---------- 1. Hilangkan chrome Streamlit ---------- */
[data-testid="stDecoration"], [data-testid="stToolbar"], [data-testid="stMainMenu"], [data-testid="stAppDeployButton"],
[data-testid="stStatusWidget"], [data-testid="stFooter"], #MainMenu, footer, .stDeployButton, .viewerBadge_container__r5tak {{
  display:none !important; visibility:hidden !important; height:0 !important; }}
header[data-testid="stHeader"] {{ background:transparent !important; height:0 !important; min-height:0 !important; border:0 !important; }}
/* Tombol buka-sidebar tetap terjangkau (tablet) */
[data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapsedControl"] {{
  display:flex !important; visibility:visible !important; position:fixed; top:10px; left:10px; z-index:1000;
  background:var(--surface); border:1px solid var(--line-strong); border-radius:var(--r-sm); }}

/* ---------- 2. Dasar ---------- */
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {{ background:var(--paper) !important; color:var(--ink); }}
.stApp, .stApp p, .stApp label, .stApp li, .stApp span, .stApp button, .stApp input, .stApp textarea, .stApp select, .stApp div {{
  font-family:var(--font-body); font-variant-numeric:tabular-nums; }}
/* Jangan timpa font ikon Material (kalau tertimpa, ikon tampil sebagai teks) */
.stApp [data-testid="stIconMaterial"], .stApp [data-testid="stAlertDynamicIcon"], .stApp span[translate="no"][aria-hidden="true"],
.stApp .material-symbols-rounded, .stApp [class*="material-symbols"], .stApp .ms {{
  font-family:'Material Symbols Rounded' !important; font-variant-numeric:normal; }}
.ms {{ font-weight:400; font-style:normal; font-size:20px; line-height:1; letter-spacing:normal; text-transform:none; display:inline-block;
  white-space:nowrap; direction:ltr; -webkit-font-smoothing:antialiased; vertical-align:middle; user-select:none; }}
.stApp h1, .stApp h2, .stApp h3, .stApp h4 {{ font-family:var(--font-body); color:var(--ink); letter-spacing:-0.01em; font-weight:700; }}
.stApp h1 {{ font-size:1.4rem; line-height:1.2; margin:0; padding:0; }}
.stApp h2 {{ font-size:1.15rem; }} .stApp h3 {{ font-size:1rem; margin:0 0 .5rem; }}
.block-container {{ padding:1.25rem 1.75rem 4rem; max-width:1560px; }}
.stApp [data-testid="stCaptionContainer"], .stApp small {{ color:var(--muted) !important; }}
.stApp *:focus-visible {{ outline:3px solid var(--focus) !important; outline-offset:2px !important; border-radius:6px; }}
.stApp hr {{ border-color:var(--line); }}

/* ---------- 3. Tombol & input ---------- */
.stApp button, .stApp [data-testid^="stBaseButton"] {{ min-height:44px; border-radius:var(--r-sm); font-weight:600; font-size:.9rem; cursor:pointer;
  box-shadow:none !important; transition:background-color .15s ease, border-color .15s ease, color .15s ease; }}
.stApp button:active {{ transform:scale(.985); }}
.stApp [data-testid="stBaseButton-primary"] {{ background:var(--brand); color:var(--on-brand); border:1px solid var(--brand); }}
.stApp [data-testid="stBaseButton-primary"]:hover {{ background:var(--brand-dark); border-color:var(--brand-dark); color:var(--on-brand); }}
.stApp [data-testid="stBaseButton-secondary"] {{ background:var(--surface); color:var(--ink); border:1px solid var(--line-strong); }}
.stApp [data-testid="stBaseButton-secondary"]:hover {{ background:var(--hover); border-color:var(--ink); color:var(--ink); }}
.stApp button:disabled {{ opacity:.5; cursor:not-allowed; }}
.stApp input, .stApp textarea, .stApp [data-baseweb="select"] > div {{ background:var(--surface) !important; color:var(--ink) !important; min-height:44px; }}
.stApp [data-baseweb="input"], .stApp [data-baseweb="base-input"], .stApp [data-baseweb="select"] > div, .stApp [data-baseweb="textarea"] {{
  border-radius:var(--r-sm) !important; border-color:var(--line-strong) !important; background:var(--surface) !important; }}
.stApp label p {{ font-weight:600; font-size:.85rem; color:var(--ink); }}
/* Pills & segmented control */
.stApp [data-testid="stBaseButton-pills"], .stApp [data-testid="stBaseButton-segmented_control"] {{
  background:var(--surface); color:var(--ink); border:1px solid var(--line-strong); min-height:40px; }}
.stApp [data-testid="stButtonGroup"] {{ flex-wrap:wrap; gap:6px; }}
.stApp [data-testid="stBaseButton-pills"] {{ border-radius:999px; }}
.stApp [data-testid="stBaseButton-pills"]:hover, .stApp [data-testid="stBaseButton-segmented_control"]:hover {{ background:var(--hover); }}
.stApp [data-testid="stBaseButton-pillsActive"], .stApp [data-testid="stBaseButton-segmented_controlActive"] {{
  background:var(--brand-soft); color:var(--brand); border:1px solid var(--brand); font-weight:700; min-height:40px; }}
.stApp [data-testid="stBaseButton-pillsActive"] {{ border-radius:999px; }}
.stApp [data-testid="stBaseButton-segmented_control"], .stApp [data-testid="stBaseButton-segmented_controlActive"] {{ min-height:44px; }}
.stApp [data-testid="stBaseButton-segmented_controlActive"] p, .stApp [data-testid="stBaseButton-pillsActive"] p {{ color:var(--brand); }}

/* ---------- 4. Kartu ---------- */
.stApp [data-testid="stVerticalBlockBorderWrapper"] {{ background:var(--surface); border:1px solid var(--line); border-radius:var(--r-md); box-shadow:none; }}
.card-title {{ font-weight:700; font-size:.95rem; margin:0 0 2px; }}
.card-sub {{ font-size:.8rem; color:var(--muted); margin:0 0 8px; }}
.stApp [data-baseweb="tab-list"] {{ gap:4px; border-bottom:1px solid var(--line); }}
.stApp [data-baseweb="tab"] {{ min-height:44px; padding:0 14px; color:var(--muted); font-weight:600; }}
.stApp [data-baseweb="tab"][aria-selected="true"] {{ color:var(--brand); }}
.stApp [data-baseweb="tab-highlight"] {{ background:var(--brand) !important; height:3px; }}

/* ---------- 5. Sidebar (app shell) ---------- */
section[data-testid="stSidebar"] {{ background:var(--surface) !important; border-right:1px solid var(--line); }}
section[data-testid="stSidebar"] {{ width:var(--sidebar-w) !important; min-width:var(--sidebar-w) !important; }}
[data-testid="stSidebarHeader"] {{ display:none; }}
[data-testid="stSidebarContent"] {{ background:var(--surface); }}
/* Footer profil menempel di dasar sidebar (rantai flex dari konten sampai pembungkus footer) */
[data-testid="stSidebarUserContent"] {{ padding:14px 12px 12px; min-height:100vh; box-sizing:border-box; display:flex; flex-direction:column; }}
[data-testid="stSidebarUserContent"] > div {{ flex:1; display:flex; flex-direction:column; }}
[data-testid="stSidebarUserContent"] > div > [data-testid="stVerticalBlock"] {{ flex:1; }}
[data-testid="stSidebarUserContent"] [data-testid="stVerticalBlock"] {{ gap:.25rem; }}
[data-testid="stLayoutWrapper"]:has(> .st-key-side_footer) {{ margin-top:auto; }}
.side-brand {{ display:flex; align-items:center; gap:10px; padding:4px 6px 14px; border-bottom:1px solid var(--line); margin-bottom:6px; }}
.side-brand svg {{ width:30px; height:30px; stroke:var(--brand); fill:none; stroke-width:2; stroke-linecap:round; stroke-linejoin:round; flex:none; }}
.side-brand b {{ font-family:var(--font-display); font-size:1.1rem; display:block; line-height:1.1; }}
.side-brand span {{ font-size:.74rem; color:var(--muted); }}
.stApp p.side-group {{ font-size:.72rem; font-weight:700; color:var(--muted); padding:0 8px; margin:0; line-height:16px; letter-spacing:.02em; }}
/* Streamlit memberi pembungkus markdown tinggi 0 untuk HTML tanpa blok; paksa tinggi sebenarnya agar label tidak tertimpa */
[data-testid="stElementContainer"]:has(.side-group), [data-testid="stMarkdown"]:has(.side-group), [data-testid="stMarkdown"]:has(.side-group) > div {{
  height:auto !important; min-height:16px !important; }}
[data-testid="stElementContainer"]:has(.side-group) {{ margin-top:12px; }}
[class*="st-key-nav_item"] button {{ width:100%; justify-content:flex-start !important; background:transparent !important; border:1px solid transparent !important;
  color:var(--muted) !important; font-weight:600; padding:0 12px; position:relative; }}
[class*="st-key-nav_item"] button > div {{ justify-content:flex-start !important; gap:10px; }}
[class*="st-key-nav_item"] button:hover {{ background:var(--hover) !important; color:var(--ink) !important; }}
[class*="st-key-nav_item_on_"] button {{ background:var(--brand-soft) !important; color:var(--brand) !important; font-weight:700; }}
[class*="st-key-nav_item_on_"] button::before {{ content:""; position:absolute; left:0; top:9px; bottom:9px; width:3px; border-radius:3px; background:var(--brand); }}
[class*="st-key-nav_item_on_"] button p {{ color:var(--brand) !important; }}
.st-key-side_footer {{ border-top:1px solid var(--line); padding-top:12px; }}
.profile {{ display:flex; align-items:center; gap:10px; padding:2px 4px 8px; }}
.avatar {{ width:36px; height:36px; border-radius:var(--r-sm); background:var(--brand-soft); color:var(--brand); display:flex; align-items:center;
  justify-content:center; font-weight:700; flex:none; }}
.profile b {{ display:block; font-size:.88rem; line-height:1.2; overflow-wrap:anywhere; }}
.profile span.role {{ font-size:.74rem; color:var(--muted); }}
.dbstat {{ display:flex; align-items:center; gap:8px; font-size:.78rem; color:var(--muted); padding:0 4px 8px; }}
.dot {{ width:8px; height:8px; border-radius:50%; background:var(--brand); flex:none; }}
.dot.off {{ background:var(--danger); }}

/* ---------- 6. Top context bar ---------- */
.topbar {{ display:flex; justify-content:space-between; align-items:center; gap:12px 20px; flex-wrap:wrap; padding:2px 0 14px; margin-bottom:14px;
  border-bottom:1px solid var(--line); }}
.topbar .sub {{ font-size:.82rem; color:var(--muted); margin-top:2px; }}
.chips {{ display:flex; gap:8px; flex-wrap:wrap; }}
.chip {{ display:inline-flex; align-items:center; gap:6px; background:var(--surface); border:1px solid var(--line); border-radius:var(--r-sm);
  padding:6px 10px; font-size:.8rem; color:var(--muted); white-space:nowrap; }}
.chip b {{ color:var(--ink); font-weight:700; }}
.chip .ms {{ font-size:17px; color:var(--brand); }}
.chip.warn {{ background:var(--warn-soft); border-color:var(--warn-soft); color:var(--warn-text); }}
.chip.warn b, .chip.warn .ms {{ color:var(--warn-text); }}

/* ---------- 7. KPI (bento) ---------- */
.kpi {{ background:var(--surface); border:1px solid var(--line); border-radius:var(--r-md); padding:14px 16px; min-height:116px; }}
.kpi .top {{ display:flex; justify-content:space-between; align-items:center; color:var(--muted); font-size:.82rem; font-weight:600; }}
.kpi .top .ms {{ color:var(--brand); background:var(--brand-soft); border-radius:var(--r-sm); padding:5px; font-size:18px; }}
.kpi .v {{ font-size:clamp(1.2rem, 2.1vw, 1.7rem); font-weight:700; margin:8px 0 2px; line-height:1.15; letter-spacing:-0.02em; white-space:nowrap; }}
.kpi .v.sm {{ font-size:1.1rem; line-height:1.3; white-space:normal; overflow-wrap:break-word; }}
.kpi .h {{ font-size:.78rem; color:var(--muted); }}

/* ---------- 8. Produk, lencana, harga ---------- */
.p-cat {{ font-size:.72rem; color:var(--muted); font-weight:600; }}
.menu-name {{ font-weight:700; line-height:1.3; min-height:2.6em; overflow-wrap:anywhere; font-size:.92rem; }}
.p-row {{ display:flex; justify-content:space-between; align-items:center; gap:6px; margin:2px 0 4px; flex-wrap:wrap; }}
.price {{ font-weight:700; font-size:1rem; }}
.badge {{ display:inline-block; padding:2px 9px; border-radius:999px; font-size:.72rem; font-weight:600; background:var(--brand-soft); color:var(--brand); white-space:nowrap; }}
.badge.low {{ background:var(--warn-soft); color:var(--warn-text); }}
.badge.out {{ background:var(--danger-soft); color:var(--danger); }}
.badge.neutral {{ background:var(--hover); color:var(--muted); }}
.reason {{ font-size:.76rem; color:var(--muted); min-height:3.4em; }}
.stApp [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"] {{ gap:.45rem; }}

/* ---------- 9. Panel pesanan (sticky) & nota ---------- */
.st-key-nota {{ position:sticky; top:1rem; max-height:calc(100vh - 2rem); overflow-y:auto; background:var(--surface); border:1px solid var(--line);
  border-radius:var(--r-md); padding:14px 14px 16px; }}
/* Panel pesanan tidak boleh menyempit di bawah 340px agar tombol -/+ tetap >= 44px */
[data-testid="stHorizontalBlock"]:has(.st-key-nota) {{ flex-wrap:nowrap; }}
[data-testid="stHorizontalBlock"]:has(.st-key-nota) > [data-testid="stColumn"]:first-child {{ min-width:0; }}
[data-testid="stHorizontalBlock"]:has(.st-key-nota) > [data-testid="stColumn"]:last-child {{ min-width:340px; }}
.cart-head {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:2px; }}
.cart-head b {{ font-size:1rem; }}
.cart-line {{ font-weight:600; font-size:.88rem; line-height:1.25; overflow-wrap:anywhere; }}
.cart-sub {{ font-size:.76rem; color:var(--muted); }}
.qty {{ text-align:center; font-weight:700; font-size:1rem; }}
.line-total {{ text-align:right; font-weight:700; font-size:.9rem; }}
.sum-row {{ display:flex; justify-content:space-between; align-items:baseline; font-size:.88rem; color:var(--muted); }}
.total-big {{ font-size:1.7rem; font-weight:700; color:var(--ink); letter-spacing:-0.02em; }}
.nota {{ position:relative; background:var(--surface); border:1px solid var(--line); border-bottom:none; padding:16px 16px 24px;
  font-family:var(--font-mono); font-size:.86rem; color:var(--ink);
  -webkit-mask:conic-gradient(from -45deg at bottom, #0000, #000 1deg 89deg, #0000 90deg) 50%/14px 100%;
          mask:conic-gradient(from -45deg at bottom, #0000, #000 1deg 89deg, #0000 90deg) 50%/14px 100%; }}
.nota *, .nota {{ font-family:var(--font-mono) !important; }}
.nota h4 {{ font-family:var(--font-display) !important; font-size:1.1rem; text-align:center; margin:0 0 2px; }}
.nota .meta {{ text-align:center; color:var(--muted); font-size:.78rem; }}
.nota hr {{ border:none; border-top:2px dashed var(--line-strong); margin:10px 0; }}
.nota .row {{ display:flex; justify-content:space-between; gap:10px; }}
.nota .row span:first-child {{ overflow-wrap:anywhere; }}
.nota .total {{ font-weight:600; font-size:1.02rem; }}
.nota .thanks {{ text-align:center; margin-top:8px; }}

/* ---------- 10. Login ---------- */
.login-brand {{ display:flex; align-items:center; gap:10px; margin-bottom:6px; }}
.login-brand svg {{ width:36px; height:36px; stroke:var(--brand); fill:none; stroke-width:2; stroke-linecap:round; stroke-linejoin:round; }}
.login-brand b {{ font-family:var(--font-display); font-size:1.3rem; }}

/* ---------- 11. Responsif ---------- */
@media (max-width: 1180px) {{
  .block-container {{ padding:1rem 1rem 4rem; }}
  [class*="st-key-grid"] [data-testid="stHorizontalBlock"] {{ flex-wrap:wrap !important; row-gap:.75rem; }}
  [class*="st-key-grid"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{ flex:0 0 calc(50% - .5rem) !important; min-width:calc(50% - .5rem) !important; }}
}}
@media (max-width: 900px) {{
  [data-testid="stHorizontalBlock"]:has(.st-key-nota) {{ flex-wrap:wrap !important; }}
  [data-testid="stHorizontalBlock"]:has(.st-key-nota) > [data-testid="stColumn"] {{ flex:1 1 100% !important; min-width:100% !important; }}
  .st-key-nota {{ position:static; max-height:none; }}
  [class*="st-key-bento"] [data-testid="stHorizontalBlock"] {{ flex-wrap:wrap !important; row-gap:.75rem; }}
  [class*="st-key-bento"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{ flex:1 1 calc(50% - .5rem) !important; min-width:calc(50% - .5rem) !important; }}
  .stApp h1 {{ font-size:1.2rem; }}
}}
@media (prefers-reduced-motion: reduce) {{ .stApp * {{ transition:none !important; animation:none !important; }} }}
</style>
"""


def inject() -> None:
    st.markdown(css(), unsafe_allow_html=True)


def hide_sidebar() -> None:
    """Halaman login tidak memakai sidebar."""
    st.markdown(
        '<style>section[data-testid="stSidebar"], [data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapsedControl"]'
        "{display:none !important;} [data-testid=\"stMain\"]{margin-left:0 !important;} "
        ".block-container{max-width:460px !important;margin:0 auto !important;padding-top:12vh;}</style>",
        unsafe_allow_html=True,
    )


BRAND_SVG = (
    '<svg viewBox="0 0 32 32" aria-hidden="true" focusable="false"><path d="M8 4h16v6a8 8 0 0 1-16 0z"/>'
    '<path d="M16 18v7M11 28h10M12.5 25h7"/></svg>'
)
