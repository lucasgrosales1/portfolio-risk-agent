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

# Palette — "The Ledger": warm printed-paper base, deep marine ink, one gold signal.
# Precision as personality — every figure is computed, and the design says so.
PAPER = "#F7F4EF"         # warm paper (page base)
PAPER2 = "#FCFAF6"        # elevated surface (cards)
NAVY = "#0E6F73"          # marine (primary) — kept name for existing references
NAVY_DARK = "#0A5155"     # marine, darker (hover)
TEAL = "#2A9AA0"          # lighter marine
TEAL_LIGHT = "#8FCBCE"
SAND = "#C08A2D"          # gold signal accent
CORAL = "#B4472E"         # brick (negative / rare signal)
GOLD = "#C08A2D"          # the single gold signal
BG_SOFT = "#FBF8F2"       # soft paper wash
INK = "#14181F"           # near-black ink
INK_SOFT = "#5A6169"      # muted ink
BORDER = "#E4DECF"        # warm hairline / ledger rule
POS = "#2F7D5B"           # restrained green
NEG = "#B4472E"           # restrained brick-red


def coastal_svg() -> str:
    """An aerial South-Beach hero graphic — the fallback when no photo is set.

    Turquoise-to-deep ocean, a diagonal white-sand beach dotted with colorful
    umbrellas, and a row of coastal condos — evoking Miami Beach from above.
    """
    # Neat, aligned rows of beach umbrellas on the sand (lower-left of the shore),
    # each row nudged to run parallel to the diagonal shoreline.
    palette = ["#e8785a", "#1c9bb3", "#d9a441", "#ffffff", "#e05b7a", "#2f8f5b"]
    umbrellas = []
    for row in range(5):
        y = 150 + row * 26
        for i in range(7):
            x = 24 + i * 30 - row * 6
            if x < 8 or x > 300:
                continue
            c = palette[(i + row) % len(palette)]
            umbrellas.append(
                f'<ellipse cx="{x}" cy="{y+5}" rx="8" ry="3" fill="#c9b483" opacity="0.5"/>'
                f'<circle cx="{x}" cy="{y}" r="6" fill="{c}"/>'
                f'<circle cx="{x}" cy="{y}" r="6" fill="#000" opacity="0.06"/>')
    umb = "".join(umbrellas)
    # A few condo towers along the far shoreline (upper-left).
    towers = ""
    for bx, bw, bh in [(14, 16, 46), (34, 12, 62), (50, 15, 40), (70, 11, 54), (86, 14, 34)]:
        towers += (f'<rect x="{bx}" y="{70-bh}" width="{bw}" height="{bh}" rx="2" '
                   f'fill="#eef3f2" stroke="#cdd8d6" stroke-width="0.6"/>')
        # window rows
        for wy in range(70 - bh + 6, 70, 8):
            towers += (f'<rect x="{bx+3}" y="{wy}" width="{bw-6}" height="3" rx="1" '
                       f'fill="#9fc2c9" opacity="0.7"/>')
    return f"""
    <svg viewBox="0 0 460 300" width="100%" xmlns="http://www.w3.org/2000/svg"
         style="border-radius:14px;display:block">
      <defs>
        <linearGradient id="ocean" x1="0.1" y1="1" x2="0.9" y2="0">
          <stop offset="0%" stop-color="#4fded0"/><stop offset="35%" stop-color="#1fb7c9"/>
          <stop offset="70%" stop-color="#1187b0"/><stop offset="100%" stop-color="#0c5f8f"/>
        </linearGradient>
        <linearGradient id="sand" x1="0" y1="1" x2="1" y2="0">
          <stop offset="0%" stop-color="#f6ecd2"/><stop offset="100%" stop-color="#e7d3a2"/>
        </linearGradient>
        <linearGradient id="shallow" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="#8ff0e4"/><stop offset="100%" stop-color="#4fded0"/>
        </linearGradient>
      </defs>
      <!-- sand base -->
      <rect width="460" height="300" fill="url(#sand)"/>
      <!-- ocean (upper-right) with a soft diagonal shoreline -->
      <path d="M150,0 L460,0 L460,235 C360,175 250,95 150,0 Z" fill="url(#ocean)"/>
      <!-- shallow turquoise water hugging the shore -->
      <path d="M150,0 C250,95 360,175 460,235 L460,255 C352,192 236,108 132,6 Z"
            fill="url(#shallow)" opacity="0.85"/>
      <!-- foam line -->
      <path d="M132,6 C236,108 352,192 460,255" stroke="#ffffff" stroke-width="3"
            fill="none" opacity="0.75" stroke-linecap="round"/>
      <path d="M120,0 C224,102 340,186 460,250" stroke="#ffffff" stroke-width="1.4"
            fill="none" opacity="0.5" stroke-dasharray="3 6"/>
      <!-- gentle wave striations in deep water -->
      <path d="M300,40 q30,10 60,4 t60,4" stroke="#ffffff" stroke-width="1" fill="none" opacity="0.18"/>
      <path d="M330,80 q30,10 60,4 t60,4" stroke="#ffffff" stroke-width="1" fill="none" opacity="0.16"/>
      {towers}
      {umb}
    </svg>
    """


def inject_theme() -> None:
    """Global CSS — "The Ledger" design system.

    Precision as personality: warm printed-paper base, deep marine ink, a single
    gold signal. Bricolage Grotesque display + Inter body, with IBM Plex Mono as
    the signature voice for every number, label, and eyebrow — the design saying,
    plainly, that each figure here was computed, not guessed.
    """
    st.markdown(
        f"""
        <style>
          @import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,500;12..96,600;12..96,700&family=IBM+Plex+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap');

          :root {{
            --paper: {PAPER}; --paper2: {PAPER2}; --ink: {INK}; --ink-soft: {INK_SOFT};
            --marine: {NAVY}; --marine-dark: {NAVY_DARK}; --teal: {TEAL};
            --gold: {GOLD}; --line: {BORDER}; --pos: {POS}; --neg: {NEG}; --soft: {BG_SOFT};
            --display: 'Bricolage Grotesque', -apple-system, system-ui, sans-serif;
            --mono: 'IBM Plex Mono', ui-monospace, Menlo, monospace;
            --sans: 'Inter', -apple-system, system-ui, sans-serif;
            --shadow-sm: 0 1px 0 rgba(20,24,31,.04);
            --shadow-md: 0 8px 24px rgba(20,24,31,.08);
          }}

          #MainMenu {{ visibility: hidden; }}
          footer {{ visibility: hidden; }}
          [data-testid="stToolbar"] {{ visibility: hidden; }}
          header[data-testid="stHeader"] {{ background: transparent; }}

          /* Warm ledger paper — faint horizontal rules like an accountant's pad. */
          [data-testid="stAppViewContainer"] {{
            background:
              repeating-linear-gradient(180deg, transparent 0 31px,
                rgba(14,111,115,.045) 31px 32px),
              {PAPER};
          }}

          .block-container {{ padding-top: 1.1rem; padding-bottom: 3rem; max-width: 1180px; }}
          html, body, [class*="css"], .stMarkdown, p, li {{
            color: var(--ink); font-family: var(--sans);
          }}
          h1, h2, h3, h4, h5 {{
            font-family: var(--display); letter-spacing: -0.02em; color: var(--ink);
            font-weight: 600;
          }}

          :focus-visible {{ outline: 2px solid var(--gold); outline-offset: 2px; }}

          /* --- Top bar --- */
          .aw-brand {{ display: flex; align-items: center; gap: 12px; padding: 2px 2px 8px; }}
          .aw-brand .mark {{ width: 42px; height: 42px; flex: none; line-height: 0; }}
          .aw-brand .name {{ font-size: 20px; font-weight: 600; color: var(--ink);
            font-family: var(--display); letter-spacing: -.02em; }}
          .aw-brand .tag  {{ font-size: 11.5px; color: var(--ink-soft); margin-top: -1px;
            font-family: var(--mono); }}
          .aw-advisor {{ text-align: right; color: var(--ink-soft); font-size: 12px;
            padding-top: 8px; font-family: var(--mono); }}
          .aw-navsep {{ display: none; }}

          /* --- Hero: a printed research sheet --- */
          .aw-hero {{
            background: var(--paper2); border: 1px solid var(--line);
            border-top: 3px solid var(--gold); border-radius: 4px;
            padding: 42px 44px; box-shadow: var(--shadow-sm);
          }}
          .aw-hero-grid {{ display: flex; gap: 36px; align-items: center; }}
          .aw-hero-text {{ flex: 1.5; min-width: 0; }}
          .aw-hero-media {{ flex: 1; min-width: 0; }}
          .aw-hero-media img, .aw-hero-media svg {{
            width: 100%; border-radius: 3px; object-fit: cover; max-height: 320px;
            border: 1px solid var(--ink); box-shadow: var(--shadow-md);
          }}
          .aw-hero h1 {{ color: var(--ink); font-size: 42px; margin: 0 0 16px; max-width: 18ch;
            line-height: 1.04; font-weight: 700; letter-spacing: -.03em; }}
          .aw-hero p  {{ color: var(--ink-soft); font-size: 16px; line-height: 1.68; margin: 0;
            max-width: 46ch; }}
          .aw-hero .eyebrow {{
            text-transform: uppercase; letter-spacing: .18em; font-size: 11px;
            color: var(--marine); font-weight: 500; margin-bottom: 16px; font-family: var(--mono);
          }}
          .aw-hero .eyebrow::before {{ content: "// "; color: var(--gold); }}

          /* --- Ledger signature: a strip of computed mini-stats --- */
          .aw-ledger {{ display: flex; gap: 0; margin: 22px 0 2px; border-top: 1px solid var(--line); }}
          .aw-ledger .cell {{ flex: 1; padding: 12px 16px 2px 0; border-right: 1px solid var(--line); }}
          .aw-ledger .cell:last-child {{ border-right: none; }}
          .aw-ledger .v {{ font-family: var(--mono); font-size: 22px; font-weight: 600;
            color: var(--ink); line-height: 1; }}
          .aw-ledger .k {{ font-family: var(--mono); font-size: 10.5px; color: var(--ink-soft);
            text-transform: uppercase; letter-spacing: .1em; margin-top: 6px; display: block; }}

          /* --- Trust strip --- */
          .aw-trust {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 16px 0 4px; }}
          .aw-trust .item {{
            flex: 1 1 0; min-width: 150px; display: flex; align-items: center; gap: 11px;
            background: var(--paper2); border: 1px solid var(--line); border-radius: 3px;
            padding: 13px 16px;
          }}
          .aw-trust .item svg {{ flex: none; color: var(--marine); }}
          .aw-trust .item b {{ display: block; font-size: 13px; color: var(--ink);
            font-weight: 600; font-family: var(--display); }}
          .aw-trust .item span {{ font-size: 11px; color: var(--ink-soft); font-family: var(--mono); }}

          /* --- Section label + heading --- */
          .aw-section-label {{
            text-transform: uppercase; letter-spacing: .16em; font-size: 11px;
            color: var(--marine); font-weight: 500; margin: 4px 0 3px; font-family: var(--mono);
          }}
          .aw-section-label::before {{ content: "// "; color: var(--gold); }}
          .aw-section-head {{ font-family: var(--display); font-size: 26px; color: var(--ink);
            font-weight: 600; margin: 2px 0 4px; letter-spacing: -.025em; }}
          .aw-section-sub {{ color: var(--ink-soft); font-size: 14.5px; margin: 0 0 8px; max-width: 62ch; }}

          /* --- Sub-section header (ledger tick) --- */
          .aw-subhead {{ display: flex; align-items: baseline; gap: 10px; margin: 8px 0 10px;
            border-left: 3px solid var(--gold); padding-left: 11px; }}
          .aw-subhead b {{ font-family: var(--display); font-size: 18px; font-weight: 600;
            color: var(--ink); letter-spacing: -.02em; }}
          .aw-subhead span {{ font-size: 12px; color: var(--ink-soft); font-family: var(--mono); }}

          div[data-testid="stExpander"] details {{ background: var(--paper2); }}

          /* --- Provenance badges (AI / rule-based / compliance-flagged) --- */
          .aw-badge {{
            display: inline-flex; align-items: center; gap: 5px; font-family: var(--mono);
            font-size: 10.5px; font-weight: 500; letter-spacing: .06em; text-transform: uppercase;
            padding: 3px 9px; border-radius: 2px; border: 1px solid var(--line);
            background: var(--paper2); color: var(--ink-soft); margin: 0 6px 6px 0;
          }}
          .aw-badge.ai {{ background: var(--marine); color: var(--paper); border-color: var(--marine-dark); }}
          .aw-badge.flag {{ background: rgba(180,71,46,.1); color: var(--neg); border-color: rgba(180,71,46,.35); }}

          /* --- Survey section banners --- */
          .aw-survey-section {{
            background: var(--marine); color: var(--paper); border-radius: 3px;
            padding: 12px 18px; margin: 26px 0 4px; font-weight: 600; font-size: 16px;
            font-family: var(--display); letter-spacing: -.01em;
          }}
          .aw-survey-section span {{ opacity: .85; font-weight: 400; font-size: 12px;
            font-family: var(--mono); }}
          .aw-survey-body {{
            border: 1px solid var(--line); border-top: none;
            border-radius: 0 0 3px 3px; padding: 18px 20px 8px; margin-bottom: 8px;
            background: var(--paper2);
          }}

          /* --- Cards --- */
          .aw-card {{
            background: var(--paper2); border: 1px solid var(--line); border-radius: 3px;
            padding: 24px; height: 100%;
            transition: transform .18s ease, border-color .18s ease;
          }}
          .aw-card:hover {{ transform: translateY(-2px); border-color: var(--marine); }}
          .aw-card h3 {{ margin: 14px 0 7px; font-size: 18px; font-family: var(--display);
            font-weight: 600; letter-spacing: -.02em; }}
          .aw-card p  {{ color: var(--ink-soft); font-size: 14px; line-height: 1.62; margin: 0; }}
          .aw-card .ico {{
            width: 44px; height: 44px; border-radius: 3px; background: var(--soft);
            display: flex; align-items: center; justify-content: center;
            border: 1px solid var(--line); color: var(--marine);
          }}

          /* --- Process timeline (a real sequence → numbered ledger entries) --- */
          .aw-steps {{ display: flex; gap: 0; margin: 8px 0 4px; }}
          .aw-step {{ flex: 1; position: relative; padding: 4px 18px 4px 0; }}
          .aw-step .n {{
            width: 40px; height: 40px; border-radius: 3px; font-family: var(--mono);
            background: var(--paper2); border: 1px solid var(--marine); color: var(--marine);
            display: flex; align-items: center; justify-content: center; font-weight: 600;
            font-size: 15px; position: relative; z-index: 2;
          }}
          .aw-step:not(:last-child)::after {{
            content: ""; position: absolute; top: 20px; left: 34px; right: 6px; height: 1px;
            background: var(--line); z-index: 1;
          }}
          .aw-step h4 {{ font-size: 16px; margin: 12px 0 5px; font-family: var(--display);
            font-weight: 600; letter-spacing: -.02em; }}
          .aw-step p {{ font-size: 13px; color: var(--ink-soft); line-height: 1.55; margin: 0;
            padding-right: 12px; }}

          /* --- Service / fee tiers --- */
          .aw-tier {{
            background: var(--paper2); border: 1px solid var(--line); border-radius: 3px;
            padding: 26px 24px; height: 100%;
            transition: transform .18s ease, border-color .18s ease;
            display: flex; flex-direction: column;
          }}
          .aw-tier:hover {{ transform: translateY(-2px); border-color: var(--marine); }}
          .aw-tier.feat {{ border: 1px solid var(--marine); border-top: 3px solid var(--gold); }}
          .aw-tier .badge {{ align-self: flex-start; background: var(--marine); color: var(--paper);
            font-size: 10px; font-weight: 500; letter-spacing: .1em; text-transform: uppercase;
            padding: 4px 10px; border-radius: 2px; margin-bottom: 10px; font-family: var(--mono); }}
          .aw-tier h3 {{ font-family: var(--display); font-size: 20px; margin: 0 0 3px;
            font-weight: 600; color: var(--ink); letter-spacing: -.02em; }}
          .aw-tier .price {{ font-size: 15px; color: var(--marine); font-weight: 600; margin: 0 0 12px;
            font-family: var(--mono); }}
          .aw-tier ul {{ list-style: none; padding: 0; margin: 0; }}
          .aw-tier li {{ font-size: 13.5px; color: var(--ink-soft); padding: 6px 0 6px 22px;
            position: relative; line-height: 1.45; }}
          .aw-tier li::before {{ content: "+"; position: absolute; left: 0; top: 6px;
            color: var(--gold); font-weight: 700; font-family: var(--mono); }}

          /* --- Team / advisor --- */
          .aw-team {{ display: flex; gap: 22px; align-items: center; }}
          .aw-team .photo {{
            width: 150px; height: 150px; border-radius: 3px; flex: none;
            background: var(--marine); border: 1px solid var(--ink);
            display: flex; align-items: center; justify-content: center;
            color: var(--paper); font-family: var(--display); font-size: 44px; font-weight: 600;
            overflow: hidden;
          }}
          .aw-team .photo img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
          .aw-team h3 {{ margin: 0 0 2px; font-size: 21px; font-family: var(--display);
            letter-spacing: -.02em; }}
          .aw-team .role {{ color: var(--marine); font-size: 12.5px; font-weight: 500; margin: 0 0 8px;
            font-family: var(--mono); }}
          .aw-team .creds {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }}
          .aw-team .creds span {{ font-size: 11px; background: var(--soft);
            border: 1px solid var(--line); color: var(--ink); padding: 3px 9px;
            border-radius: 2px; font-weight: 500; font-family: var(--mono); }}
          .aw-team p {{ font-size: 14px; color: var(--ink-soft); line-height: 1.62; margin: 4px 0 0; }}

          /* --- Testimonials --- */
          .aw-quote {{
            background: var(--paper2); border: 1px solid var(--line); border-radius: 3px;
            padding: 24px; height: 100%; position: relative;
          }}
          .aw-quote .mark {{ font-family: var(--display); font-size: 46px; color: var(--gold);
            line-height: .5; display: block; height: 22px; }}
          .aw-quote p {{ font-size: 14.5px; color: var(--ink); line-height: 1.6; margin: 6px 0 14px; }}
          .aw-quote .who {{ display: flex; align-items: center; gap: 10px; }}
          .aw-quote .av {{ width: 34px; height: 34px; border-radius: 2px; flex: none;
            background: var(--marine); color: var(--paper);
            display: flex; align-items: center; justify-content: center; font-size: 13px;
            font-weight: 600; font-family: var(--mono); }}
          .aw-quote .who b {{ font-size: 13px; color: var(--ink); display: block;
            font-family: var(--display); font-weight: 600; }}
          .aw-quote .who span {{ font-size: 11px; color: var(--ink-soft); font-family: var(--mono); }}

          /* --- Insights --- */
          .aw-insight {{
            background: var(--paper2); border: 1px solid var(--line); border-radius: 3px;
            overflow: hidden; height: 100%;
            transition: transform .18s ease, border-color .18s ease;
          }}
          .aw-insight:hover {{ transform: translateY(-2px); border-color: var(--marine); }}
          .aw-insight .top {{ height: 64px; background: var(--marine);
            display: flex; align-items: center; justify-content: flex-start; padding: 0 20px; }}
          .aw-insight .top span {{ color: var(--paper); font-size: 10.5px;
            text-transform: uppercase; letter-spacing: .14em; font-weight: 500; font-family: var(--mono); }}
          .aw-insight .top span::before {{ content: "// "; color: var(--gold); }}
          .aw-insight .body {{ padding: 16px 20px 20px; }}
          .aw-insight h4 {{ font-size: 16px; margin: 0 0 6px; font-family: var(--display);
            font-weight: 600; line-height: 1.28; letter-spacing: -.02em; }}
          .aw-insight p {{ font-size: 13px; color: var(--ink-soft); line-height: 1.55; margin: 0; }}
          .aw-insight .meta {{ font-size: 11px; color: var(--marine); font-weight: 500; margin-top: 10px;
            font-family: var(--mono); }}

          /* --- Disclosures footer --- */
          .aw-foot {{
            margin-top: 30px; border-top: 1px solid var(--line); padding-top: 22px;
            color: var(--ink-soft); font-size: 12px; line-height: 1.65;
          }}
          .aw-foot .cols {{ display: flex; gap: 40px; flex-wrap: wrap; margin-bottom: 16px; }}
          .aw-foot .cols b {{ color: var(--ink); font-family: var(--display);
            font-size: 13px; display: block; margin-bottom: 6px; font-weight: 600; }}
          .aw-foot .cols div {{ font-size: 12px; font-family: var(--mono); line-height: 1.7; }}
          .aw-foot .fine {{ font-size: 11px; color: var(--ink-soft); border-top: 1px dashed var(--line);
            padding-top: 12px; }}

          /* --- Metrics: the signature — mono values on a ledger underline --- */
          [data-testid="stMetric"] {{
            background: var(--paper2); border: 1px solid var(--line);
            border-bottom: 2px solid var(--marine); border-radius: 3px; padding: 14px 18px;
          }}
          [data-testid="stMetricValue"] {{ font-size: 24px; color: var(--ink);
            font-family: var(--mono); font-weight: 600; letter-spacing: -.02em; }}
          [data-testid="stMetricLabel"] {{ color: var(--ink-soft); font-family: var(--mono);
            letter-spacing: 0; font-size: 11px; }}
          [data-testid="stMetricLabel"] * {{ white-space: normal; overflow: visible;
            text-overflow: clip; }}
          [data-testid="stMetricDelta"] {{ font-family: var(--mono); font-size: 12px; }}

          /* --- Buttons --- */
          .stButton button, .stFormSubmitButton button {{
            border-radius: 3px; font-weight: 600; font-family: var(--sans);
            transition: transform .15s ease, background .15s ease, border-color .15s ease;
          }}
          .stButton button[kind="primary"], .stButton button[kind="primaryFormSubmit"],
          .stFormSubmitButton button[kind="primaryFormSubmit"] {{
            background: var(--marine); border-color: var(--marine); color: #ffffff;
          }}
          .stButton button[kind="primary"] *, .stButton button[kind="primaryFormSubmit"] *,
          .stFormSubmitButton button[kind="primaryFormSubmit"] * {{ color: #ffffff !important; }}
          .stButton button[kind="primary"]:hover, .stButton button[kind="primaryFormSubmit"]:hover,
          .stFormSubmitButton button[kind="primaryFormSubmit"]:hover {{
            background: var(--marine-dark); border-color: var(--marine-dark); color: #ffffff;
            transform: translateY(-1px);
          }}
          .stButton button[kind="secondary"] {{ color: var(--ink); border-color: var(--line);
            background: var(--paper2); }}
          .stButton button[kind="secondary"]:hover {{
            color: var(--ink); border-color: var(--marine);
            background: var(--soft); transform: translateY(-1px);
          }}

          /* --- Top navigation: mono ledger tabs in a bordered bar --- */
          div[data-testid="stHorizontalBlock"]:has(> div [class*="st-key-nav_"]) {{
            background: var(--paper2); border: 1px solid var(--line);
            border-radius: 3px; padding: 7px 9px; gap: 6px;
          }}
          [class*="st-key-nav_"] button {{
            border: none !important; background: transparent !important;
            color: var(--ink-soft) !important; font-weight: 500 !important;
            border-radius: 2px !important; font-family: var(--mono) !important;
            font-size: 12.5px !important; letter-spacing: .02em;
            box-shadow: none !important; transition: background .16s ease, color .16s ease !important;
          }}
          [class*="st-key-nav_"] button:hover {{
            background: var(--soft) !important; color: var(--ink) !important;
            transform: none !important; box-shadow: none !important;
          }}
          [class*="st-key-nav_"] button[kind="primary"] {{
            background: var(--marine) !important; color: #ffffff !important; box-shadow: none !important;
          }}
          [class*="st-key-nav_"] button[kind="primary"] * {{ color: #ffffff !important; }}
          [class*="st-key-nav_"] button[kind="primary"]:hover {{
            background: var(--marine-dark) !important; transform: none !important;
          }}
          [class*="st-key-gearbtn"] button {{
            border: 1px solid var(--line) !important; background: var(--paper2) !important;
            color: var(--marine) !important; border-radius: 2px !important; box-shadow: none !important;
          }}
          [class*="st-key-gearbtn"] button:hover {{
            border-color: var(--marine) !important; background: var(--soft) !important;
          }}

          hr {{ opacity: .4; border-color: var(--line); }}
          [data-testid="stExpander"] {{ border-radius: 3px; border-color: var(--line); }}

          @media (prefers-reduced-motion: reduce) {{
            * {{ transition: none !important; animation: none !important; }}
          }}
          @media (max-width: 820px) {{
            .aw-hero {{ padding: 30px 24px; }}
            .aw-hero h1 {{ font-size: 31px; }}
            .aw-hero-grid {{ flex-direction: column; }}
            .aw-ledger {{ flex-wrap: wrap; }}
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
              <div class="mark">{brand_mark_html(42)}</div>
              <div>
                <div class="name">{FIRM_NAME}</div>
                <div class="tag">{FIRM_TAGLINE}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c_adv:
        st.markdown('<div class="aw-advisor">👤 Advisor Workspace</div>', unsafe_allow_html=True)
    with c_gear:
        if st.button("⚙", key="gearbtn", help="Settings"):
            go_to("Settings")

    cols = st.columns(len(NAV_ITEMS))
    for col, (label, key) in zip(cols, NAV_ITEMS):
        active = st.session_state["page"] == key
        if col.button(label, key=f"nav_{key}",
                      type="primary" if active else "secondary", width="stretch"):
            st.session_state["page"] = key
            st.rerun()

    st.write("")
    return st.session_state["page"]


def brand_mark_html(size: int = 42) -> str:
    """The logo mark: reads assets/logo-mark.svg, the single source of truth.

    Same asset backs the nav badge, the brand guideline page, and (via a
    rasterized favicon-only variant) the browser tab icon — see
    assets/logo-mark-favicon.svg and assets/README.md.
    """
    svg = (Path(__file__).parent / "assets" / "logo-mark.svg").read_text(encoding="utf-8")
    return svg.replace("<svg ", f'<svg width="{size}" height="{size}" ', 1)


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
