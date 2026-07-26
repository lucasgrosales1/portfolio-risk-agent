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
    """Global CSS — a designed, refined-coastal system.

    Font pairing (Fraunces display serif + Inter body), a consistent spacing
    scale, unified card/section treatments, hover states, and the professional
    marketing components (trust strip, process timeline, service tiers, team,
    testimonials, insights, disclosures footer).
    """
    st.markdown(
        f"""
        <style>
          @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600;700&display=swap');

          :root {{
            --navy: {NAVY}; --navy-dark: {NAVY_DARK}; --teal: {TEAL};
            --teal-light: {TEAL_LIGHT}; --sand: {SAND}; --coral: {CORAL}; --gold: {GOLD};
            --ink: {INK}; --border: {BORDER}; --bg-soft: {BG_SOFT};
            --muted: #5b6b73; --serif: 'Fraunces', Georgia, serif;
            --shadow-sm: 0 1px 2px rgba(16,24,40,.05);
            --shadow-md: 0 6px 20px rgba(12,58,77,.10);
            --shadow-lg: 0 14px 40px rgba(12,58,77,.16);
          }}

          #MainMenu {{ visibility: hidden; }}
          footer {{ visibility: hidden; }}
          [data-testid="stToolbar"] {{ visibility: hidden; }}
          header[data-testid="stHeader"] {{ background: transparent; }}

          /* Warm coastal background — soft sand-to-seafoam wash, subtle texture. */
          [data-testid="stAppViewContainer"] {{
            background:
              radial-gradient(circle at 1px 1px, rgba(18,85,110,.035) 1px, transparent 0)
                0 0 / 26px 26px,
              linear-gradient(180deg, #ffffff 0%, #f4fafb 55%, #eaf4f2 100%);
          }}

          .block-container {{ padding-top: 1.1rem; padding-bottom: 3rem; max-width: 1180px; }}
          html, body, [class*="css"], .stMarkdown, p, li {{
            color: var(--ink); font-family: 'Inter', -apple-system, system-ui, sans-serif;
          }}
          h1, h2, h3, h4, h5 {{
            font-family: var(--serif); letter-spacing: -0.012em; color: var(--navy-dark);
            font-weight: 600;
          }}

          /* --- Top bar --- */
          .aw-brand {{ display: flex; align-items: center; gap: 12px; padding: 2px 2px 8px; }}
          .aw-brand .mark {{
            width: 42px; height: 42px; border-radius: 11px;
            background: linear-gradient(135deg, {NAVY} 0%, {TEAL} 100%);
            display: flex; align-items: center; justify-content: center;
            color: #fff; font-weight: 700; font-size: 17px; font-family: var(--serif);
            box-shadow: var(--shadow-sm);
          }}
          .aw-brand .name {{ font-size: 20px; font-weight: 600; color: {NAVY_DARK};
            font-family: var(--serif); }}
          .aw-brand .tag  {{ font-size: 12px; color: var(--muted); margin-top: -1px; }}
          .aw-advisor {{ text-align: right; color: var(--muted); font-size: 13px; padding-top: 8px; }}

          .aw-navsep {{ border: none; border-top: 1px solid #e5edf0; margin: 8px 0 18px; opacity: 1; }}

          /* --- Hero (coastal, two-column) --- */
          .aw-hero {{
            background:
              radial-gradient(900px 300px at 90% -10%, rgba(227,200,147,.30), transparent),
              radial-gradient(700px 320px at 8% 120%, rgba(28,155,179,.35), transparent),
              linear-gradient(135deg, {NAVY_DARK} 0%, {NAVY} 55%, #1a6f88 100%);
            color: #fff; border-radius: 20px; padding: 46px 46px;
            box-shadow: var(--shadow-lg);
          }}
          .aw-hero-grid {{ display: flex; gap: 34px; align-items: center; }}
          .aw-hero-text {{ flex: 1.5; min-width: 0; }}
          .aw-hero-media {{ flex: 1; min-width: 0; }}
          .aw-hero-media img, .aw-hero-media svg {{
            width: 100%; border-radius: 15px; object-fit: cover; max-height: 310px;
            box-shadow: 0 10px 26px rgba(0,0,0,.24);
          }}
          .aw-hero h1 {{ color: #fff; font-size: 40px; margin: 0 0 14px; max-width: 20ch;
            line-height: 1.1; font-weight: 600; }}
          .aw-hero p  {{ color: #eaf3f6; font-size: 16px; line-height: 1.65; margin: 0; max-width: 46ch; }}
          .aw-hero .eyebrow {{
            text-transform: uppercase; letter-spacing: .14em; font-size: 11.5px;
            color: {SAND}; font-weight: 700; margin-bottom: 14px; font-family: 'Inter';
          }}

          /* --- Trust strip --- */
          .aw-trust {{
            display: flex; flex-wrap: wrap; gap: 10px; margin: 16px 0 4px;
          }}
          .aw-trust .item {{
            flex: 1 1 0; min-width: 150px; display: flex; align-items: center; gap: 11px;
            background: #fff; border: 1px solid var(--border); border-radius: 13px;
            padding: 13px 16px; box-shadow: var(--shadow-sm);
          }}
          .aw-trust .item svg {{ flex: none; }}
          .aw-trust .item b {{ display: block; font-size: 13.5px; color: var(--navy-dark);
            font-weight: 600; font-family: var(--serif); }}
          .aw-trust .item span {{ font-size: 11.5px; color: var(--muted); }}

          /* --- Section label + heading --- */
          .aw-section-label {{
            text-transform: uppercase; letter-spacing: .12em; font-size: 11.5px;
            color: var(--teal); font-weight: 700; margin: 4px 0 2px; font-family: 'Inter';
          }}
          .aw-section-head {{ font-family: var(--serif); font-size: 25px; color: var(--navy-dark);
            font-weight: 600; margin: 2px 0 4px; letter-spacing: -.01em; }}
          .aw-section-sub {{ color: var(--muted); font-size: 14.5px; margin: 0 0 8px; max-width: 62ch; }}

          /* --- Sub-section header (within a page) --- */
          .aw-subhead {{ display: flex; align-items: baseline; gap: 9px; margin: 6px 0 10px; }}
          .aw-subhead b {{ font-family: var(--serif); font-size: 18px; font-weight: 600;
            color: var(--navy-dark); letter-spacing: -.01em; }}
          .aw-subhead span {{ font-size: 13px; color: var(--muted); }}

          /* --- Bordered containers (client rows, forms) --- */
          [data-testid="stVerticalBlockBorderWrapper"] > div > [data-testid="stVerticalBlock"] {{ }}
          div[data-testid="stExpander"] details {{ background: #fff; }}

          /* --- Survey section banners --- */
          .aw-survey-section {{
            background: linear-gradient(90deg, {NAVY} 0%, {TEAL} 100%);
            color: #fff; border-radius: 12px; padding: 13px 20px; margin: 26px 0 4px;
            font-weight: 600; font-size: 17px; font-family: var(--serif);
            box-shadow: 0 3px 10px rgba(12,58,77,.14);
          }}
          .aw-survey-section span {{ opacity: .9; font-weight: 500; font-size: 13.5px;
            font-family: 'Inter'; }}
          .aw-survey-body {{
            border: 1px solid {BORDER}; border-top: none;
            border-radius: 0 0 12px 12px; padding: 18px 20px 8px; margin-bottom: 8px;
            background: #ffffff;
          }}

          /* --- Cards --- */
          .aw-card {{
            background: #fff; border: 1px solid {BORDER}; border-radius: 16px;
            padding: 24px; height: 100%; box-shadow: var(--shadow-sm);
            transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;
          }}
          .aw-card:hover {{ transform: translateY(-3px); box-shadow: var(--shadow-md);
            border-color: #c6dbe1; }}
          .aw-card h3 {{ margin: 12px 0 7px; font-size: 18px; font-family: var(--serif);
            font-weight: 600; }}
          .aw-card p  {{ color: var(--muted); font-size: 14px; line-height: 1.6; margin: 0; }}
          .aw-card .ico {{
            width: 46px; height: 46px; border-radius: 13px;
            background: linear-gradient(135deg, rgba(28,155,179,.12), rgba(18,85,110,.10));
            display: flex; align-items: center; justify-content: center;
            border: 1px solid #d7e7ec; color: var(--navy);
          }}

          /* --- Process timeline --- */
          .aw-steps {{ display: flex; gap: 0; margin: 8px 0 4px; counter-reset: step; }}
          .aw-step {{ flex: 1; position: relative; padding: 4px 18px 4px 0; }}
          .aw-step .n {{
            width: 40px; height: 40px; border-radius: 50%; font-family: var(--serif);
            background: #fff; border: 2px solid var(--teal); color: var(--navy-dark);
            display: flex; align-items: center; justify-content: center; font-weight: 600;
            font-size: 17px; position: relative; z-index: 2; box-shadow: var(--shadow-sm);
          }}
          .aw-step:not(:last-child)::after {{
            content: ""; position: absolute; top: 20px; left: 34px; right: 6px; height: 2px;
            background: linear-gradient(90deg, var(--teal), #cfe6ec); z-index: 1;
          }}
          .aw-step h4 {{ font-size: 16px; margin: 12px 0 5px; font-family: var(--serif);
            font-weight: 600; }}
          .aw-step p {{ font-size: 13px; color: var(--muted); line-height: 1.55; margin: 0;
            padding-right: 12px; }}

          /* --- Service / fee tiers --- */
          .aw-tier {{
            background: #fff; border: 1px solid var(--border); border-radius: 16px;
            padding: 26px 24px; height: 100%; box-shadow: var(--shadow-sm);
            transition: transform .18s ease, box-shadow .18s ease;
            display: flex; flex-direction: column;
          }}
          .aw-tier:hover {{ transform: translateY(-3px); box-shadow: var(--shadow-md); }}
          .aw-tier.feat {{ border: 1.5px solid var(--teal);
            box-shadow: 0 10px 30px rgba(28,155,179,.16); }}
          .aw-tier .badge {{ align-self: flex-start; background: var(--teal); color: #fff;
            font-size: 10.5px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase;
            padding: 4px 10px; border-radius: 999px; margin-bottom: 10px; }}
          .aw-tier h3 {{ font-family: var(--serif); font-size: 20px; margin: 0 0 2px;
            font-weight: 600; color: var(--navy-dark); }}
          .aw-tier .price {{ font-size: 15px; color: var(--teal); font-weight: 600; margin: 0 0 12px; }}
          .aw-tier ul {{ list-style: none; padding: 0; margin: 0; }}
          .aw-tier li {{ font-size: 13.5px; color: var(--muted); padding: 6px 0 6px 24px;
            position: relative; line-height: 1.45; }}
          .aw-tier li::before {{ content: "✓"; position: absolute; left: 0; top: 6px;
            color: var(--teal); font-weight: 700; }}

          /* --- Team / advisor --- */
          .aw-team {{ display: flex; gap: 22px; align-items: center; }}
          .aw-team .photo {{
            width: 118px; height: 118px; border-radius: 16px; flex: none;
            background: linear-gradient(135deg, var(--navy) 0%, var(--teal) 100%);
            display: flex; align-items: center; justify-content: center;
            color: #fff; font-family: var(--serif); font-size: 38px; font-weight: 600;
            box-shadow: var(--shadow-md);
          }}
          .aw-team .photo img {{ width: 100%; height: 100%; object-fit: cover; border-radius: 16px; }}
          .aw-team h3 {{ margin: 0 0 2px; font-size: 20px; font-family: var(--serif); }}
          .aw-team .role {{ color: var(--teal); font-size: 13.5px; font-weight: 600; margin: 0 0 8px; }}
          .aw-team .creds {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }}
          .aw-team .creds span {{ font-size: 11.5px; background: var(--bg-soft);
            border: 1px solid var(--border); color: var(--navy-dark); padding: 3px 10px;
            border-radius: 999px; font-weight: 500; }}
          .aw-team p {{ font-size: 14px; color: var(--muted); line-height: 1.6; margin: 4px 0 0; }}

          /* --- Testimonials --- */
          .aw-quote {{
            background: #fff; border: 1px solid var(--border); border-radius: 16px;
            padding: 24px; height: 100%; box-shadow: var(--shadow-sm); position: relative;
          }}
          .aw-quote .mark {{ font-family: var(--serif); font-size: 46px; color: var(--sand);
            line-height: .5; display: block; height: 22px; }}
          .aw-quote p {{ font-size: 14.5px; color: var(--ink); line-height: 1.6; margin: 6px 0 14px;
            font-style: italic; }}
          .aw-quote .who {{ display: flex; align-items: center; gap: 10px; }}
          .aw-quote .av {{ width: 34px; height: 34px; border-radius: 50%; flex: none;
            background: linear-gradient(135deg, var(--teal), var(--navy)); color: #fff;
            display: flex; align-items: center; justify-content: center; font-size: 13px;
            font-weight: 600; font-family: var(--serif); }}
          .aw-quote .who b {{ font-size: 13px; color: var(--navy-dark); display: block;
            font-family: var(--serif); font-weight: 600; }}
          .aw-quote .who span {{ font-size: 11.5px; color: var(--muted); }}

          /* --- Insights --- */
          .aw-insight {{
            background: #fff; border: 1px solid var(--border); border-radius: 16px;
            overflow: hidden; height: 100%; box-shadow: var(--shadow-sm);
            transition: transform .18s ease, box-shadow .18s ease;
          }}
          .aw-insight:hover {{ transform: translateY(-3px); box-shadow: var(--shadow-md); }}
          .aw-insight .top {{ height: 80px;
            background: linear-gradient(135deg, var(--navy) 0%, var(--teal) 100%);
            display: flex; align-items: center; justify-content: flex-start; padding: 0 20px; }}
          .aw-insight .top span {{ color: rgba(255,255,255,.92); font-size: 11px;
            text-transform: uppercase; letter-spacing: .1em; font-weight: 700; }}
          .aw-insight .body {{ padding: 16px 20px 20px; }}
          .aw-insight h4 {{ font-size: 16px; margin: 0 0 6px; font-family: var(--serif);
            font-weight: 600; line-height: 1.3; }}
          .aw-insight p {{ font-size: 13px; color: var(--muted); line-height: 1.55; margin: 0; }}
          .aw-insight .meta {{ font-size: 11.5px; color: var(--teal); font-weight: 600; margin-top: 10px; }}

          /* --- Disclosures footer --- */
          .aw-foot {{
            margin-top: 30px; border-top: 1px solid var(--border); padding-top: 22px;
            color: var(--muted); font-size: 12px; line-height: 1.65;
          }}
          .aw-foot .cols {{ display: flex; gap: 40px; flex-wrap: wrap; margin-bottom: 16px; }}
          .aw-foot .cols b {{ color: var(--navy-dark); font-family: var(--serif);
            font-size: 13.5px; display: block; margin-bottom: 6px; font-weight: 600; }}
          .aw-foot .cols div {{ font-size: 12.5px; }}
          .aw-foot .fine {{ font-size: 11px; color: #8a97a0; border-top: 1px dashed var(--border);
            padding-top: 12px; }}

          /* --- Metrics --- */
          [data-testid="stMetric"] {{
            background: #fff; border: 1px solid {BORDER}; border-radius: 13px;
            padding: 15px 18px; box-shadow: var(--shadow-sm);
          }}
          [data-testid="stMetricValue"] {{ font-size: 23px; color: {NAVY_DARK};
            font-family: var(--serif); font-weight: 600; }}
          [data-testid="stMetricLabel"] {{ color: var(--muted); }}

          /* --- Buttons --- */
          .stButton button, .stFormSubmitButton button {{
            border-radius: 10px; font-weight: 600; transition: all .15s ease;
          }}
          /* Primary: white label on navy, for every nested text node Streamlit renders. */
          .stButton button[kind="primary"], .stButton button[kind="primaryFormSubmit"],
          .stFormSubmitButton button[kind="primaryFormSubmit"] {{
            background: {NAVY}; border-color: {NAVY}; color: #ffffff;
          }}
          .stButton button[kind="primary"] *, .stButton button[kind="primaryFormSubmit"] *,
          .stFormSubmitButton button[kind="primaryFormSubmit"] * {{ color: #ffffff !important; }}
          .stButton button[kind="primary"]:hover, .stButton button[kind="primaryFormSubmit"]:hover,
          .stFormSubmitButton button[kind="primaryFormSubmit"]:hover {{
            background: {NAVY_DARK}; border-color: {NAVY_DARK}; color: #ffffff;
            transform: translateY(-1px); box-shadow: var(--shadow-md);
          }}
          /* Secondary: navy label on white, teal edge on hover. */
          .stButton button[kind="secondary"] {{ color: {NAVY_DARK}; border-color: var(--border); }}
          .stButton button[kind="secondary"]:hover {{
            color: {NAVY_DARK}; border-color: {TEAL};
            background: var(--bg-soft); transform: translateY(-1px);
          }}
          hr {{ opacity: .5; }}
          [data-testid="stExpander"] {{ border-radius: 12px; border-color: var(--border); }}

          @media (max-width: 820px) {{
            .aw-hero {{ padding: 32px 26px; }}
            .aw-hero h1 {{ font-size: 30px; }}
            .aw-hero-grid {{ flex-direction: column; }}
            .aw-steps {{ flex-direction: column; gap: 16px; }}
            .aw-step:not(:last-child)::after {{ display: none; }}
            .aw-team {{ flex-direction: column; text-align: center; align-items: center; }}
            .aw-team .creds {{ justify-content: center; }}
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


def advisor_photo_html(initials: str = "LR") -> str:
    """Advisor headshot from assets/advisor.* if present, else styled initials.

    Drop a licensed headshot at assets/advisor.jpg (or .png/.webp) to replace
    the monogram with a real photo.
    """
    assets = Path(__file__).parent / "assets"
    for ext in ("jpg", "jpeg", "png", "webp"):
        f = assets / f"advisor.{ext}"
        if f.exists():
            b64 = base64.b64encode(f.read_bytes()).decode()
            mime = "jpeg" if ext == "jpg" else ext
            return f'<img src="data:image/{mime};base64,{b64}" alt="Advisor headshot"/>'
    return initials


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


# --------------------------------------------------------------------------
# Icon set — clean 1.6px line icons, inherit color via currentColor.
# --------------------------------------------------------------------------
_ICON_PATHS = {
    "family": '<circle cx="8" cy="7" r="2.4"/><circle cx="16" cy="7" r="2.4"/>'
              '<path d="M3.5 19c0-2.8 2-4.5 4.5-4.5S12.5 16.2 12.5 19"/>'
              '<path d="M11.5 19c0-2.8 2-4.5 4.5-4.5S20.5 16.2 20.5 19"/>',
    "compass": '<circle cx="12" cy="12" r="9"/>'
               '<path d="M15.5 8.5 13 13l-4.5 2.5L11 11z"/>',
    "chart": '<path d="M4 20V4"/><path d="M4 20h16"/>'
             '<rect x="7" y="12" width="2.6" height="5"/><rect x="12" y="8" width="2.6" height="9"/>'
             '<rect x="17" y="5" width="2.6" height="12"/>',
    "shield": '<path d="M12 3 5 6v5c0 4.2 2.9 7.6 7 9 4.1-1.4 7-4.8 7-9V6z"/>'
              '<path d="M9 12l2 2 4-4"/>',
    "scale": '<path d="M12 3v16"/><path d="M6 21h12"/><path d="M4 8h16"/>'
             '<path d="M4 8l-2 5a3 3 0 0 0 6 0z"/><path d="M20 8l-2 5a3 3 0 0 0 6 0z"/>',
    "handshake": '<path d="M8 12l3-3 3 3 3-3"/><path d="M3 8l4-2 5 3"/>'
                 '<path d="M21 8l-4-2-3 2"/><path d="M8 12l2 2 2-2 2 2"/>',
    "seedling": '<path d="M12 20v-7"/><path d="M12 13c0-3 2-5 6-5 0 3-2 5-6 5z"/>'
                '<path d="M12 15c0-2.5-2-4-5-4 0 2.5 2 4 5 4z"/>',
    "search": '<circle cx="11" cy="11" r="6"/><path d="M20 20l-4.5-4.5"/>',
    "doc": '<path d="M7 3h7l4 4v14H7z"/><path d="M14 3v4h4"/>'
           '<path d="M9.5 12h5M9.5 15h5"/>',
    "calendar": '<rect x="4" y="5" width="16" height="16" rx="2"/><path d="M4 9h16"/>'
                '<path d="M8 3v4M16 3v4"/>',
}


def icon(name: str, size: int = 22) -> str:
    """Return an inline SVG line-icon that inherits the surrounding color."""
    body = _ICON_PATHS.get(name, "")
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
            f'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" '
            f'stroke-linejoin="round">{body}</svg>')


def section_header(label: str, title: str, subtitle: str = "") -> None:
    """A consistent 'eyebrow + display heading + subtitle' section opener."""
    sub = f'<div class="aw-section-sub">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f'<div class="aw-section-label">{label}</div>'
        f'<div class="aw-section-head">{title}</div>{sub}',
        unsafe_allow_html=True,
    )


def subhead(title: str, note: str = "") -> None:
    """A lighter serif sub-section header for use within a page."""
    n = f"<span>{note}</span>" if note else ""
    st.markdown(f'<div class="aw-subhead"><b>{title}</b>{n}</div>', unsafe_allow_html=True)


def trust_strip() -> None:
    """Fiduciary / fee-only trust badges — the first thing an RIA prospect scans for."""
    items = [
        ("shield", "Fiduciary duty", "Your interest, first — always"),
        ("scale", "Fee-only", "Paid for advice, never products"),
        ("handshake", "Independent", "No proprietary funds or quotas"),
        ("chart", "Evidence-based", "Every figure computed, not guessed"),
    ]
    cells = "".join(
        f'<div class="item">{icon(nm, 24)}<div><b>{t}</b><span>{s}</span></div></div>'
        for nm, t, s in items
    )
    st.markdown(f'<div class="aw-trust">{cells}</div>', unsafe_allow_html=True)


def disclosures_footer() -> None:
    """Regulatory-style footer: registration line, ADV pointers, and disclaimers.

    Placeholder content for a demo — a real firm swaps in its CRD/registration.
    """
    st.markdown(
        f"""
        <div class="aw-foot">
          <div class="cols">
            <div>
              <b>{FIRM_NAME}</b>
              1200 Harborview Blvd, Suite 300<br>Sarasota, FL 34236<br>
              (941) 555-0192 · hello@wealthsyncadvisors.com
            </div>
            <div>
              <b>Disclosures</b>
              <div>Form ADV Part 2A &amp; 2B — available on request</div>
              <div>Privacy Policy · Business Continuity</div>
              <div>Client Relationship Summary (Form CRS)</div>
            </div>
            <div>
              <b>Registration</b>
              <div>Investment advisory services offered through<br>{FIRM_NAME}, a registered
                   investment adviser.</div>
              <div>Registered in the State of Florida.</div>
            </div>
          </div>
          <div class="fine">
            This website is for informational purposes only and does not constitute investment,
            tax, or legal advice, nor an offer or solicitation to buy or sell any security. Advisory
            services are offered only where {FIRM_NAME} is registered or exempt from registration.
            Investing involves risk, including possible loss of principal; past performance is not a
            guarantee of future results. All names, figures, and scenarios shown are synthetic and
            illustrative — this is an educational demonstration project, not a live advisory offering.
            © 2026 {FIRM_NAME}. All rights reserved.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
