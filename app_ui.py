"""Shared UI for the Advisor Workbench web app — branding, theme, navigation.

Kept separate from the page content so the look-and-feel lives in one place and
the firm name is a single constant to swap. The analytics package (`pra`) has no
dependency on any of this; the web layer is a thin shell over the real engine.
"""

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

# --------------------------------------------------------------------------
# Branding — swap FIRM_NAME for any firm's name.
# --------------------------------------------------------------------------
FIRM_NAME = "WealthSync Advisors"
FIRM_TAGLINE = "Florida-based planning that keeps your family on track"

# Top-nav items (Settings lives behind the gear icon, not the nav row).
NAV_ITEMS = [
    ("Home", "Home"),
    ("Dashboard", "Dashboard"),
    ("Portfolio Analysis", "Portfolio Analysis"),
    ("Client Survey", "Client Survey"),
]

# Palette — Florida coastal: deep ocean navy/teal with warm sand and coral accents.
NAVY = "#12556e"          # deep ocean teal
NAVY_DARK = "#0c3a4d"
TEAL = "#1c9bb3"          # aqua
TEAL_LIGHT = "#7fd3e0"
SAND = "#e3c893"          # warm sand
CORAL = "#e8785a"         # sunset coral accent
GOLD = "#d9a441"
BG_SOFT = "#f2f8fa"
INK = "#1f2937"
BORDER = "#d3dde2"
POS = "#10b981"
NEG = "#ef4444"


def coastal_svg() -> str:
    """A clean Florida-coastal hero graphic — the fallback when no photo is set."""
    return f"""
    <svg viewBox="0 0 460 300" width="100%" xmlns="http://www.w3.org/2000/svg"
         style="border-radius:14px;display:block">
      <defs>
        <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#ffe1b0"/><stop offset="45%" stop-color="#f6b57e"/>
          <stop offset="100%" stop-color="#ef9a7a"/>
        </linearGradient>
        <linearGradient id="sea" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#1c9bb3"/><stop offset="100%" stop-color="#12556e"/>
        </linearGradient>
      </defs>
      <rect width="460" height="300" fill="url(#sky)"/>
      <circle cx="330" cy="95" r="46" fill="#fff2d6" opacity="0.95"/>
      <circle cx="330" cy="95" r="46" fill="#ffd98a" opacity="0.55"/>
      <rect y="188" width="460" height="112" fill="url(#sea)"/>
      <path d="M0,196 q40,-12 80,0 t80,0 t80,0 t80,0 t80,0 t80,0 v6 H0 Z" fill="#2bb0c6" opacity="0.6"/>
      <path d="M0,210 q46,-10 92,0 t92,0 t92,0 t92,0 t92,0 v90 H0 Z" fill="#15768f" opacity="0.5"/>
      <!-- palm -->
      <path d="M90,300 C96,250 96,210 92,182" stroke="#5a3d24" stroke-width="7" fill="none" stroke-linecap="round"/>
      <g fill="#2f8f5b">
        <path d="M92,182 C60,168 40,172 24,186 C48,176 70,178 92,190 Z"/>
        <path d="M92,182 C124,166 148,168 166,182 C142,172 116,174 92,190 Z"/>
        <path d="M92,182 C74,150 60,138 44,132 C68,140 84,156 94,186 Z"/>
        <path d="M92,182 C110,150 126,140 144,136 C120,144 104,158 94,186 Z"/>
        <path d="M92,182 C92,146 96,128 104,112 C100,140 98,160 96,188 Z"/>
      </g>
    </svg>
    """


def inject_theme() -> None:
    """Global CSS. Stable test-ids plus our own classes."""
    st.markdown(
        f"""
        <style>
          #MainMenu {{ visibility: hidden; }}
          footer {{ visibility: hidden; }}
          [data-testid="stToolbar"] {{ visibility: hidden; }}
          header[data-testid="stHeader"] {{ background: transparent; }}

          /* Warm coastal background — soft sand-to-seafoam wash, subtle texture. */
          [data-testid="stAppViewContainer"] {{
            background:
              radial-gradient(circle at 1px 1px, rgba(18,85,110,.04) 1px, transparent 0)
                0 0 / 24px 24px,
              linear-gradient(180deg, #ffffff 0%, #f3f9fb 55%, #eaf4f2 100%);
          }}

          .block-container {{ padding-top: 1.1rem; padding-bottom: 3rem; max-width: 1180px; }}
          html, body, [class*="css"] {{ color: {INK}; }}
          h1, h2, h3 {{ letter-spacing: -0.01em; color: {NAVY_DARK}; }}

          /* --- Top bar --- */
          .aw-brand {{ display: flex; align-items: center; gap: 12px; padding: 2px 2px 8px; }}
          .aw-brand .mark {{
            width: 40px; height: 40px; border-radius: 10px;
            background: linear-gradient(135deg, {NAVY} 0%, {TEAL} 100%);
            display: flex; align-items: center; justify-content: center;
            color: #fff; font-weight: 800; font-size: 18px;
          }}
          .aw-brand .name {{ font-size: 19px; font-weight: 700; color: {NAVY_DARK}; }}
          .aw-brand .tag  {{ font-size: 12px; color: #6b7280; margin-top: -2px; }}
          .aw-advisor {{ text-align: right; color: #6b7280; font-size: 13px; padding-top: 8px; }}

          .aw-navsep {{ border: none; border-top: 1px solid #e5e7eb; margin: 8px 0 18px; opacity: 1; }}

          /* --- Hero (coastal, two-column) --- */
          .aw-hero {{
            background:
              radial-gradient(900px 300px at 90% -10%, rgba(227,200,147,.30), transparent),
              radial-gradient(700px 320px at 8% 120%, rgba(28,155,179,.35), transparent),
              linear-gradient(135deg, {NAVY_DARK} 0%, {NAVY} 55%, #1a6f88 100%);
            color: #fff; border-radius: 18px; padding: 40px 42px;
            box-shadow: 0 12px 34px rgba(12,58,77,.22);
          }}
          .aw-hero-grid {{ display: flex; gap: 30px; align-items: center; }}
          .aw-hero-text {{ flex: 1.5; min-width: 0; }}
          .aw-hero-media {{ flex: 1; min-width: 0; }}
          .aw-hero-media img, .aw-hero-media svg {{
            width: 100%; border-radius: 14px; object-fit: cover; max-height: 300px;
            box-shadow: 0 8px 22px rgba(0,0,0,.22);
          }}
          .aw-hero h1 {{ color: #fff; font-size: 33px; margin: 0 0 12px; max-width: 20ch; line-height:1.15; }}
          .aw-hero p  {{ color: #eaf3f6; font-size: 16px; line-height: 1.6; margin: 0; }}
          .aw-hero .eyebrow {{
            text-transform: uppercase; letter-spacing: .12em; font-size: 12px;
            color: {SAND}; font-weight: 700; margin-bottom: 14px;
          }}

          /* --- Survey section banners (make sections stand out) --- */
          .aw-survey-section {{
            background: linear-gradient(90deg, {NAVY} 0%, {TEAL} 100%);
            color: #fff; border-radius: 11px; padding: 13px 20px; margin: 26px 0 4px;
            font-weight: 700; font-size: 17px;
            box-shadow: 0 3px 10px rgba(12,58,77,.14);
          }}
          .aw-survey-section span {{ opacity: .9; font-weight: 500; font-size: 13.5px; }}
          .aw-survey-body {{
            border: 1px solid {BORDER}; border-top: none;
            border-radius: 0 0 11px 11px; padding: 18px 20px 8px; margin-bottom: 8px;
            background: #ffffff;
          }}

          /* --- Cards --- */
          .aw-card {{
            background: #fff; border: 1px solid {BORDER}; border-radius: 14px;
            padding: 22px; height: 100%; box-shadow: 0 1px 2px rgba(16,24,40,.05);
          }}
          .aw-card h3 {{ margin: 6px 0 6px; font-size: 17px; }}
          .aw-card p  {{ color: #4b5563; font-size: 14px; line-height: 1.55; margin: 0; }}
          .aw-card .ico {{
            width: 42px; height: 42px; border-radius: 11px; background: {BG_SOFT};
            display: flex; align-items: center; justify-content: center; font-size: 21px;
            border: 1px solid {BORDER};
          }}
          .aw-section-label {{
            text-transform: uppercase; letter-spacing: .1em; font-size: 12px;
            color: {TEAL}; font-weight: 700; margin: 4px 0 2px;
          }}

          [data-testid="stMetric"] {{
            background: #fff; border: 1px solid {BORDER}; border-radius: 12px;
            padding: 14px 18px; box-shadow: 0 1px 2px rgba(16,24,40,.05);
          }}
          [data-testid="stMetricValue"] {{ font-size: 22px; color: {NAVY_DARK}; }}

          .stButton button[kind="primary"] {{ background: {NAVY}; border-color: {NAVY}; }}
          .stButton button[kind="primary"]:hover {{ background: {NAVY_DARK}; border-color: {NAVY_DARK}; }}
          hr {{ opacity: .5; }}

          @media (max-width: 720px) {{
            .aw-hero {{ padding: 30px 24px; }}
            .aw-hero h1 {{ font-size: 26px; }}
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def top_nav() -> str:
    """Branded top bar + nav row. Settings sits behind the gear icon."""
    st.session_state.setdefault("page", "Home")

    c_brand, c_adv, c_gear = st.columns([6, 2, 1], vertical_alignment="center")
    with c_brand:
        st.markdown(
            f"""
            <div class="aw-brand">
              <div class="mark">WS</div>
              <div>
                <div class="name">{FIRM_NAME}</div>
                <div class="tag">{FIRM_TAGLINE}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c_adv:
        st.markdown('<div class="aw-advisor">👤 Advisor</div>', unsafe_allow_html=True)
    with c_gear:
        if st.button("⚙", key="nav_gear", help="Settings"):
            go_to("Settings")

    st.markdown('<div class="aw-nav"></div>', unsafe_allow_html=True)
    cols = st.columns(len(NAV_ITEMS))
    for col, (label, key) in zip(cols, NAV_ITEMS):
        active = st.session_state["page"] == key
        if col.button(label, key=f"nav_{key}",
                      type="primary" if active else "secondary", width="stretch"):
            st.session_state["page"] = key
            st.rerun()

    st.markdown('<hr class="aw-navsep">', unsafe_allow_html=True)
    return st.session_state["page"]


def hero_media_html() -> str:
    """The hero image: a photo from assets/hero.* if present, else the coastal SVG.

    Drop a licensed photo at assets/hero.jpg (or .png/.webp) to replace the
    graphic — a real family photo reads as genuinely professional.
    """
    assets = Path(__file__).parent / "assets"
    for ext in ("jpg", "jpeg", "png", "webp"):
        f = assets / f"hero.{ext}"
        if f.exists():
            b64 = base64.b64encode(f.read_bytes()).decode()
            mime = "jpeg" if ext == "jpg" else ext
            return f'<img src="data:image/{mime};base64,{b64}" alt="Client family"/>'
    return coastal_svg()


def go_to(page_key: str) -> None:
    st.session_state["page"] = page_key
    st.rerun()


def page_title(title: str, subtitle: str = "") -> None:
    st.markdown(f"### {title}")
    if subtitle:
        st.caption(subtitle)


def card(icon: str, title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="aw-card">
          <div class="ico">{icon}</div>
          <h3>{title}</h3>
          <p>{body}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
