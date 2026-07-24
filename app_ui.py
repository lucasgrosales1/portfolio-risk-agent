"""Shared UI for the Advisor Workbench web app — branding, theme, navigation.

Kept separate from the page content so the look-and-feel lives in one place and
the firm name is a single constant to swap. The analytics package (`pra`) has no
dependency on any of this; the web layer is a thin shell over the real engine.
"""

from __future__ import annotations

import streamlit as st

# --------------------------------------------------------------------------
# Branding — swap FIRM_NAME for any firm's name.
# --------------------------------------------------------------------------
FIRM_NAME = "WealthSync Advisors"
FIRM_TAGLINE = "Portfolio intelligence for the modern advisor"

# Navigation: (label, page-key). Page keys drive the router in streamlit_app.py.
NAV_ITEMS = [
    ("Home", "Home"),
    ("Dashboard", "Dashboard"),
    ("Portfolio Analysis", "Portfolio Analysis"),
    ("Rebalancing", "Rebalancing"),
    ("Planning", "Planning"),
    ("Reports", "Reports"),
    ("Settings", "Settings"),
]

# Palette (mirrors .streamlit/config.toml and the spec).
NAVY = "#1a4d7a"
NAVY_DARK = "#0d2b4a"
TEAL = "#17a2b8"
BG_SOFT = "#f4f7fa"
INK = "#1f2937"
BORDER = "#d1d5db"
POS = "#10b981"
NEG = "#ef4444"


def inject_theme() -> None:
    """Global CSS. Targets Streamlit's stable test-ids plus our own classes."""
    st.markdown(
        f"""
        <style>
          /* Hide default Streamlit chrome for an app-like feel. */
          #MainMenu {{ visibility: hidden; }}
          footer {{ visibility: hidden; }}
          [data-testid="stToolbar"] {{ visibility: hidden; }}
          header[data-testid="stHeader"] {{ background: transparent; }}

          .block-container {{
            padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1180px;
          }}
          html, body, [class*="css"] {{ color: {INK}; }}
          h1, h2, h3 {{ letter-spacing: -0.01em; color: {NAVY_DARK}; }}

          /* --- Top navigation bar --- */
          .aw-brand {{
            display: flex; align-items: center; gap: 12px;
            padding: 4px 2px 10px;
          }}
          .aw-brand .mark {{
            width: 38px; height: 38px; border-radius: 9px;
            background: linear-gradient(135deg, {NAVY} 0%, {TEAL} 100%);
            display: flex; align-items: center; justify-content: center;
            color: #fff; font-weight: 800; font-size: 18px;
          }}
          .aw-brand .name {{ font-size: 19px; font-weight: 700; color: {NAVY_DARK}; }}
          .aw-brand .tag  {{ font-size: 12px; color: #6b7280; margin-top: -2px; }}

          /* Nav buttons styled as a tab row */
          div[data-testid="stHorizontalBlock"]:has(.aw-navrow) + div button,
          .aw-nav button {{ border-radius: 8px; }}

          /* --- Hero --- */
          .aw-hero {{
            background:
              radial-gradient(1200px 400px at 10% -20%, rgba(23,162,184,.25), transparent),
              linear-gradient(135deg, {NAVY_DARK} 0%, {NAVY} 60%, #245c92 100%);
            color: #fff; border-radius: 18px; padding: 46px 44px;
            box-shadow: 0 10px 30px rgba(13,43,74,.18);
          }}
          .aw-hero h1 {{ color: #fff; font-size: 34px; margin: 0 0 12px; max-width: 20ch; }}
          .aw-hero p  {{ color: #e6eef6; font-size: 16px; line-height: 1.6; max-width: 60ch; margin: 0; }}
          .aw-hero .eyebrow {{
            text-transform: uppercase; letter-spacing: .12em; font-size: 12px;
            color: {TEAL}; font-weight: 700; margin-bottom: 14px;
          }}

          /* --- Feature / content cards --- */
          .aw-card {{
            background: #fff; border: 1px solid {BORDER}; border-radius: 14px;
            padding: 22px 22px; height: 100%;
            box-shadow: 0 1px 2px rgba(16,24,40,.04);
          }}
          .aw-card h3 {{ margin: 6px 0 6px; font-size: 17px; }}
          .aw-card p  {{ color: #4b5563; font-size: 14px; line-height: 1.55; margin: 0; }}
          .aw-card .ico {{
            width: 40px; height: 40px; border-radius: 10px; background: {BG_SOFT};
            display: flex; align-items: center; justify-content: center; font-size: 20px;
            border: 1px solid {BORDER};
          }}

          .aw-section-label {{
            text-transform: uppercase; letter-spacing: .1em; font-size: 12px;
            color: {TEAL}; font-weight: 700; margin: 4px 0 2px;
          }}

          /* Metric cards */
          [data-testid="stMetric"] {{
            background: #fff; border: 1px solid {BORDER}; border-radius: 12px;
            padding: 14px 18px; box-shadow: 0 1px 2px rgba(16,24,40,.04);
          }}
          [data-testid="stMetricValue"] {{ font-size: 22px; color: {NAVY_DARK}; }}

          /* Primary buttons in the brand color */
          .stButton button[kind="primary"] {{
            background: {NAVY}; border-color: {NAVY};
          }}
          .stButton button[kind="primary"]:hover {{
            background: {NAVY_DARK}; border-color: {NAVY_DARK};
          }}

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
    """Render the branded top bar and navigation. Returns the active page key.

    A custom nav (branded bar + a row of buttons) rather than st.navigation, so
    the styling and the active state are fully under our control.
    """
    st.session_state.setdefault("page", "Home")

    left, right = st.columns([3, 2], vertical_alignment="center")
    with left:
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
    with right:
        st.markdown(
            '<div style="text-align:right;padding-top:8px;color:#6b7280;font-size:13px">'
            "👤 Advisor &nbsp;·&nbsp; Demo</div>",
            unsafe_allow_html=True,
        )

    st.markdown('<div class="aw-nav aw-navrow"></div>', unsafe_allow_html=True)
    cols = st.columns(len(NAV_ITEMS))
    for col, (label, key) in zip(cols, NAV_ITEMS):
        active = st.session_state["page"] == key
        if col.button(
            label,
            key=f"nav_{key}",
            type="primary" if active else "secondary",
            width="stretch",
        ):
            st.session_state["page"] = key
            st.rerun()

    st.divider()
    return st.session_state["page"]


def go_to(page_key: str) -> None:
    """Programmatic navigation (used by hero CTA buttons)."""
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
