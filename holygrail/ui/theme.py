"""Design system Holy Grail POS: token warna/tipografi + CSS global.

Konsep: nota warung & tiket dapur. Terang (kafe dengan cahaya kuat), kontras tinggi, target sentuh >= 44px.
Semua pasangan warna teks/latar di PAIRS diuji >= 4.5:1 (WCAG AA) di tests/unit/test_theme_contrast.py.
"""

from __future__ import annotations

import streamlit as st

TOKENS = {
    "paper": "#F2F4F0",       # latar halaman (porselen sage)
    "surface": "#FFFFFF",     # kartu & panel
    "ink": "#14211C",         # teks utama (hijau-hitam)
    "ink_muted": "#44544D",   # teks sekunder
    "line": "#B9C6BF",        # garis/pembatas
    "brand": "#0F5C4D",       # hijau pandan
    "on_brand": "#FFFFFF",
    "brand_soft": "#DCEEE8",  # tint merek
    "turmeric": "#F2B01E",    # kunyit — isian aksen, teks di atasnya = ink
    "chili": "#A8231B",       # bahaya / stok tipis
    "chili_soft": "#FBE7E4",
    "focus": "#0B57D0",       # cincin fokus keyboard
}

# (teks, latar, nama) — dipakai tes kontras
PAIRS = [
    ("ink", "paper", "teks utama di halaman"),
    ("ink", "surface", "teks utama di kartu"),
    ("ink_muted", "paper", "teks sekunder di halaman"),
    ("ink_muted", "surface", "teks sekunder di kartu"),
    ("on_brand", "brand", "teks tombol utama"),
    ("brand", "surface", "teks merek di kartu"),
    ("brand", "brand_soft", "teks merek di tint"),
    ("ink", "turmeric", "teks di atas kunyit"),
    ("chili", "surface", "teks bahaya di kartu"),
    ("chili", "chili_soft", "teks bahaya di tint"),
    ("ink", "brand_soft", "teks utama di tint"),
]

# Warna seri grafik (dibedakan juga lewat label/posisi, bukan warna saja)
SEGMENT_COLORS = {"Diamond": "#0F5C4D", "Platinum": "#2F7F8F", "Gold": "#B07A00", "Silver": "#5E6D66", "Bronze": "#8A4B2A"}

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
  --brand:{t['brand']}; --on-brand:{t['on_brand']}; --brand-soft:{t['brand_soft']}; --turmeric:{t['turmeric']};
  --chili:{t['chili']}; --chili-soft:{t['chili_soft']}; --focus:{t['focus']};
  --font-display:'Bricolage Grotesque','Segoe UI',system-ui,sans-serif;
  --font-body:'Plus Jakarta Sans','Segoe UI',system-ui,sans-serif;
  --font-mono:'IBM Plex Mono',ui-monospace,Consolas,monospace;
  --r-sm:8px; --r-md:12px;
}}
html, body, .stApp, [data-testid="stAppViewContainer"] {{ background:var(--paper) !important; color:var(--ink); }}
.stApp, .stApp p, .stApp label, .stApp li, .stApp span, .stApp button, .stApp input, .stApp textarea, .stApp select {{
  font-family:var(--font-body); font-variant-numeric:tabular-nums; }}
/* Jangan timpa font ikon Material (kalau tertimpa, ikon tampil sebagai teks) */
.stApp [data-testid="stIconMaterial"], .stApp [data-testid="stAlertDynamicIcon"], .stApp span[translate="no"][aria-hidden="true"],
.stApp .material-symbols-rounded, .stApp [class*="material-symbols"] {{
  font-family:'Material Symbols Rounded' !important; font-variant-numeric:normal; }}
.stApp h1, .stApp h2, .stApp h3 {{ font-family:var(--font-display); letter-spacing:-0.01em; color:var(--ink); font-weight:700; }}
.stApp h1 {{ font-size:1.9rem; line-height:1.15; }}
.stApp h2 {{ font-size:1.35rem; }} .stApp h3 {{ font-size:1.1rem; }}
[data-testid="stHeader"] {{ background:transparent; }}
[data-testid="stToolbar"], #MainMenu, footer {{ visibility:hidden; height:0; }}
.block-container {{ padding:1.2rem 2rem 4rem; max-width:1480px; }}
.stApp [data-testid="stCaptionContainer"], .stApp small {{ color:var(--muted) !important; }}

/* Fokus keyboard yang selalu terlihat */
.stApp *:focus-visible {{ outline:3px solid var(--focus) !important; outline-offset:2px !important; border-radius:6px; }}

/* Tombol: target >= 44px */
.stApp button, .stApp [data-testid^="stBaseButton"] {{ min-height:44px; border-radius:var(--r-sm); font-weight:600; cursor:pointer;
  transition:background-color .15s ease, border-color .15s ease, transform .1s ease; }}
.stApp button:active {{ transform:scale(.98); }}
.stApp [data-testid="stBaseButton-primary"] {{ background:var(--brand); color:var(--on-brand); border:1px solid var(--brand); }}
.stApp [data-testid="stBaseButton-primary"]:hover {{ background:#0B4A3E; border-color:#0B4A3E; color:var(--on-brand); }}
.stApp [data-testid="stBaseButton-secondary"] {{ background:var(--surface); color:var(--ink); border:1px solid var(--line); }}
.stApp [data-testid="stBaseButton-secondary"]:hover {{ border-color:var(--brand); color:var(--brand); background:var(--brand-soft); }}
.stApp button:disabled {{ opacity:.55; cursor:not-allowed; }}

/* Input */
.stApp input, .stApp textarea, .stApp [data-baseweb="select"] > div {{ background:var(--surface) !important; color:var(--ink) !important;
  border-radius:var(--r-sm) !important; min-height:44px; }}
.stApp [data-baseweb="input"], .stApp [data-baseweb="base-input"] {{ border-radius:var(--r-sm) !important; background:var(--surface) !important; }}
.stApp label p {{ font-weight:600; color:var(--ink); }}

/* Kartu (container border) */
.stApp [data-testid="stVerticalBlockBorderWrapper"] {{ background:var(--surface); border-color:var(--line); border-radius:var(--r-md); }}

/* Tab */
.stApp [data-baseweb="tab-list"] {{ gap:4px; border-bottom:1px solid var(--line); }}
.stApp [data-baseweb="tab"] {{ min-height:44px; padding:0 16px; color:var(--muted); font-weight:600; }}
.stApp [data-baseweb="tab"][aria-selected="true"] {{ color:var(--brand); }}
.stApp [data-baseweb="tab-highlight"] {{ background:var(--brand) !important; height:3px; }}

/* Bilah atas */
.hg-brand {{ display:flex; align-items:center; gap:12px; padding:6px 0; }}
.hg-brand svg {{ width:34px; height:34px; stroke:var(--brand); fill:none; stroke-width:2; stroke-linecap:round; stroke-linejoin:round; }}
.hg-brand b {{ font-family:var(--font-display); font-size:1.3rem; letter-spacing:-0.01em; }}
.hg-brand span {{ display:block; font-size:.8rem; color:var(--muted); font-weight:500; }}

/* KPI */
.kpi {{ background:var(--surface); border:1px solid var(--line); border-radius:var(--r-md); padding:16px 18px; min-height:128px; }}
.kpi .l {{ font-size:.85rem; color:var(--muted); font-weight:600; }}
.kpi .v {{ font-family:var(--font-display); font-size:1.5rem; font-weight:700; margin:4px 0 2px; line-height:1.15; overflow-wrap:anywhere; }}
.kpi .h {{ font-size:.8rem; color:var(--muted); }}
.kpi.warn .v {{ color:var(--chili); }}

/* Harga & lencana */
.price {{ font-weight:700; font-size:1.05rem; }}
.badge {{ display:inline-block; padding:2px 10px; border-radius:999px; font-size:.78rem; font-weight:600; background:var(--brand-soft); color:var(--brand); }}
.badge.low {{ background:var(--chili-soft); color:var(--chili); }}
.badge.sun {{ background:var(--turmeric); color:var(--ink); }}
.menu-name {{ font-weight:700; line-height:1.3; min-height:2.6em; overflow-wrap:anywhere; }}
.reason {{ font-size:.8rem; color:var(--muted); min-height:2.4em; }}

/* Nota (struk) — elemen khas: kertas termal bergerigi */
.st-key-nota {{ position:sticky; top:1rem; max-height:calc(100vh - 2rem); overflow-y:auto; padding:2px 6px 8px 2px; }}
.nota {{ position:relative; background:var(--surface); border:1px solid var(--line); border-bottom:none; padding:18px 18px 26px;
  font-family:var(--font-mono); font-size:.88rem; color:var(--ink);
  -webkit-mask:conic-gradient(from -45deg at bottom, #0000, #000 1deg 89deg, #0000 90deg) 50%/14px 100%;
          mask:conic-gradient(from -45deg at bottom, #0000, #000 1deg 89deg, #0000 90deg) 50%/14px 100%; }}
.nota h4 {{ font-family:var(--font-display); font-size:1.15rem; text-align:center; margin:0 0 2px; }}
.nota .meta {{ text-align:center; color:var(--muted); font-size:.8rem; }}
.nota hr {{ border:none; border-top:2px dashed var(--line); margin:10px 0; }}
.nota .row {{ display:flex; justify-content:space-between; gap:10px; }}
.nota .row span:first-child {{ overflow-wrap:anywhere; }}
.nota .total {{ font-weight:600; font-size:1.05rem; }}
.nota .thanks {{ text-align:center; margin-top:8px; }}
.total-big {{ font-family:var(--font-display); font-size:1.9rem; font-weight:700; }}

/* Tablet: kisi kartu 2 kolom, nota menumpuk di bawah pada layar sempit */
.stApp button p {{ white-space:nowrap; }}
@media (max-width: 1180px) {{
  [class*="st-key-grid"] [data-testid="stHorizontalBlock"] {{ flex-wrap:wrap !important; row-gap:.75rem; }}
  [class*="st-key-grid"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{ flex:1 1 calc(50% - 1rem) !important; min-width:calc(50% - 1rem) !important; }}
}}
@media (max-width: 860px) {{
  [data-testid="stHorizontalBlock"]:has(.st-key-nota) {{ flex-wrap:wrap !important; }}
  [data-testid="stHorizontalBlock"]:has(.st-key-nota) > [data-testid="stColumn"] {{ flex:1 1 100% !important; min-width:100% !important; }}
}}
@media (max-width: 900px) {{
  .block-container {{ padding:1rem 1rem 4rem; }}
  .st-key-nota {{ position:static; }}
  .stApp h1 {{ font-size:1.5rem; }}
}}
@media (prefers-reduced-motion: reduce) {{ .stApp * {{ transition:none !important; animation:none !important; }} }}
</style>
"""


def inject() -> None:
    st.markdown(css(), unsafe_allow_html=True)


BRAND_SVG = (
    '<svg viewBox="0 0 32 32" aria-hidden="true" focusable="false"><path d="M8 4h16v6a8 8 0 0 1-16 0z"/>'
    '<path d="M16 18v7M11 28h10M12.5 25h7"/></svg>'
)
