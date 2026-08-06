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

# Palette — cloned from a dark "AI Finance" reference (client-supplied):
# near-black navy base, white type, glossy blue/cyan glow accents. Variable
# names kept from the prior "Ledger" system (NAVY, GOLD, ...) so every
# existing `var(--marine)` / `{NAVY}` reference below still resolves —
# only the values changed.
PAPER = "#05061C"         # near-black navy (page base)
PAPER2 = "#0B0C2E"        # elevated surface (cards) — one step lighter navy
NAVY = "#7DB2F5"          # sky-blue interactive accent (nav active, links, focus)
NAVY_DARK = "#5A93E0"     # accent, darker (hover)
TEAL = "#4C7FD6"          # deeper blue variant
TEAL_LIGHT = "#AAD4F6"    # pale blue — glow-orb highlight
SAND = "#FFE08C"          # warm gold signal accent
CORAL = "#FF7600"         # orange (rare signal)
GOLD = "#FFE08C"          # the single gold signal
BG_SOFT = "#FFFFFF0F"     # subtle white-on-navy wash (hover fills)
INK = "#FFFFFF"           # primary text — white on navy
INK_SOFT = "#FFFFFFB3"    # muted text — white at 70% alpha
BORDER = "#FFFFFF1F"      # hairline — white at ~12% alpha
POS = "#5FD98C"           # gain green, tuned for dark-navy contrast
NEG = "#FF7A6E"           # loss coral-red, tuned for dark-navy contrast
GLOW_BLUE = "#AAD4F6"     # decorative sphere/orb gradient — pale blue
GLOW_CYAN = "#A5EDEE"     # decorative sphere/orb gradient — cyan


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
    """Global CSS — cloned from a client-supplied dark "AI Finance" reference.

    Near-black navy base, white type, glossy blue/cyan glow accents standing
    in for the reference's 3D-rendered spheres (approximated here with layered
    radial gradients, since Streamlit can't host the original renders). Plus
    Jakarta Sans for display type (the reference's rounded, heavy headline
    voice) + Inter for body — no monospace signature, matching the reference,
    which doesn't use one.
    """
    st.markdown(
        f"""
        <style>
          @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

          :root {{
            --paper: {PAPER}; --paper2: {PAPER2}; --ink: {INK}; --ink-soft: {INK_SOFT};
            --marine: {NAVY}; --marine-dark: {NAVY_DARK}; --teal: {TEAL};
            --gold: {GOLD}; --line: {BORDER}; --pos: {POS}; --neg: {NEG}; --soft: {BG_SOFT};
            --glow-blue: {GLOW_BLUE}; --glow-cyan: {GLOW_CYAN};
            --display: 'Plus Jakarta Sans', -apple-system, system-ui, sans-serif;
            --mono: 'Plus Jakarta Sans', -apple-system, system-ui, sans-serif;
            --sans: 'Inter', -apple-system, system-ui, sans-serif;
            --shadow-sm: 0 1px 0 rgba(255,255,255,.04);
            --shadow-md: 0 30px 70px rgba(0,0,0,.55);
            --glow-ring: 0 0 0 1px rgba(125,178,245,.22), 0 20px 50px rgba(0,0,0,.45);
            --ease-settle: cubic-bezier(.16,1,.3,1);
            --glass: rgba(11,12,46,.58);
            --glass-border: rgba(255,255,255,.10);
            --glass-blur: blur(20px) saturate(140%);
          }}

          @keyframes aw-rise {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to   {{ opacity: 1; transform: translateY(0); }}
          }}

          #MainMenu {{ visibility: hidden; }}
          footer {{ visibility: hidden; }}
          [data-testid="stToolbar"] {{ visibility: hidden; }}
          header[data-testid="stHeader"] {{ background: transparent; }}

          /* Near-black navy base with soft glow blooms standing in for the
             reference's glossy 3D spheres. */
          [data-testid="stAppViewContainer"] {{
            background:
              radial-gradient(1100px 620px at 18% -8%, rgba(125,178,245,.20), transparent 60%),
              radial-gradient(900px 520px at 92% 4%, rgba(165,237,238,.13), transparent 55%),
              radial-gradient(700px 420px at 50% 30%, rgba(90,60,190,.10), transparent 60%),
              {PAPER};
          }}

          .block-container {{ padding-top: 1.1rem; padding-bottom: 3rem; max-width: 1180px; }}
          html, body, [class*="css"], .stMarkdown, p, li {{
            color: var(--ink); font-family: var(--sans);
          }}
          h1, h2, h3, h4, h5 {{
            font-family: var(--display); letter-spacing: -0.01em; color: var(--ink);
            font-weight: 700;
          }}

          :focus-visible {{ outline: 2px solid var(--gold); outline-offset: 2px; }}

          /* --- Top bar --- */
          .aw-brand {{ display: flex; align-items: center; gap: 12px; padding: 2px 2px 8px; }}
          .aw-brand .mark {{ width: 42px; height: 42px; flex: none; line-height: 0; }}
          .aw-brand .name {{ font-size: 20px; font-weight: 700; color: var(--ink);
            font-family: var(--display); letter-spacing: -.02em; }}
          .aw-brand .tag  {{ font-size: 11.5px; color: var(--ink-soft); margin-top: -1px;
            font-family: var(--sans); }}
          .aw-advisor {{ text-align: right; color: var(--ink-soft); font-size: 12px;
            padding-top: 8px; font-family: var(--sans); }}
          .aw-navsep {{ display: none; }}

          /* --- Shimmer: a diagonal light sweep on hover, for the wordmark at
             the top — transform/opacity only, per the motion rule. --- */
          .pw-shimmer {{
            position: relative; display: inline-block; overflow: hidden; cursor: default;
          }}
          .pw-shimmer::before {{
            content: ""; position: absolute; inset: -60% -20%; pointer-events: none;
            mix-blend-mode: screen; opacity: 0;
            background: linear-gradient(105deg,
              transparent 40%, rgba(255,255,255,.95) 47%, var(--glow-cyan) 50%,
              rgba(255,255,255,.95) 53%, transparent 60%);
            transform: translateX(-140%) skewX(-10deg);
            transition: transform 1.05s var(--ease-settle), opacity .25s var(--ease-settle);
          }}
          .pw-shimmer:hover::before {{ transform: translateX(140%) skewX(-10deg); opacity: 1; }}

          /* --- Hero: full-bleed dark panel, glow orbs, no card frame --- */
          .aw-hero {{
            background: transparent; border: none; position: relative;
            padding: 56px 6px 40px; overflow: hidden;
            animation: aw-rise .55s var(--ease-settle) both;
          }}
          .aw-hero::before {{
            content: ""; position: absolute; top: -220px; right: -160px;
            width: 520px; height: 520px; border-radius: 50%; z-index: 0;
            background: radial-gradient(circle at 35% 30%,
              rgba(255,255,255,.55), var(--glow-blue) 32%, var(--teal) 62%, transparent 75%);
            filter: blur(2px); opacity: .55;
          }}
          .aw-hero::after {{
            content: ""; position: absolute; bottom: -60px; right: 18%;
            width: 150px; height: 150px; border-radius: 50%; z-index: 0;
            background: radial-gradient(circle at 40% 30%,
              rgba(255,255,255,.5), var(--glow-cyan) 40%, transparent 78%);
            opacity: .4;
          }}
          .aw-hero > * {{ position: relative; z-index: 1; }}
          /* Single-column hero — the reference has no side image; the product
             screenshot appears in its own floating section further down. */
          .aw-hero-grid {{ display: block; max-width: 640px; }}
          .aw-hero-text {{ min-width: 0; }}
          .aw-hero-media {{ display: none; }}
          .aw-hero h1 {{ color: var(--ink); font-size: 60px; margin: 0 0 18px; max-width: 14ch;
            line-height: 1.02; font-weight: 800; letter-spacing: -.03em; }}
          .aw-hero p  {{ color: var(--ink-soft); font-size: 17px; line-height: 1.68; margin: 0;
            max-width: 46ch; }}
          .aw-hero .eyebrow {{
            text-transform: uppercase; letter-spacing: .14em; font-size: 12px;
            color: var(--marine); font-weight: 600; margin-bottom: 18px; font-family: var(--sans);
          }}

          /* --- Ledger signature: a strip of computed mini-stats --- */
          .aw-ledger {{ display: flex; gap: 0; margin: 26px 0 2px; border-top: 1px solid var(--line); }}
          .aw-ledger .cell {{ flex: 1; padding: 14px 16px 2px 0; border-right: 1px solid var(--line); }}
          .aw-ledger .cell:last-child {{ border-right: none; }}
          .aw-ledger .v {{ font-family: var(--display); font-size: 24px; font-weight: 800;
            color: var(--ink); line-height: 1; }}
          .aw-ledger .k {{ font-family: var(--sans); font-size: 11px; color: var(--ink-soft);
            text-transform: uppercase; letter-spacing: .08em; margin-top: 6px; display: block; }}

          /* --- Trust strip: minimal inline row (the reference's faded logo strip) --- */
          .aw-trust {{
            display: flex; flex-wrap: wrap; gap: 30px; margin: 8px 0 4px;
            align-items: center; justify-content: center;
          }}
          .aw-trust .item {{
            flex: 0 0 auto; display: flex; align-items: center; gap: 9px;
            background: transparent; border: none; padding: 4px 0; opacity: .78;
            animation: aw-rise .5s var(--ease-settle) both;
            transition: opacity .2s var(--ease-settle), transform .2s var(--ease-settle);
          }}
          .aw-trust .item:nth-child(1) {{ animation-delay: .08s; }}
          .aw-trust .item:nth-child(2) {{ animation-delay: .15s; }}
          .aw-trust .item:nth-child(3) {{ animation-delay: .22s; }}
          .aw-trust .item:nth-child(4) {{ animation-delay: .29s; }}
          .aw-trust .item:hover {{ opacity: 1; transform: translateY(-2px); }}
          .aw-trust .item svg {{ flex: none; color: var(--marine); width: 18px; height: 18px; }}
          .aw-trust .item b {{ display: block; font-size: 12.5px; color: var(--ink);
            font-weight: 600; font-family: var(--display); }}
          .aw-trust .item span {{ display: none; }}

          /* --- Section label + heading --- */
          .aw-section-label {{
            text-transform: uppercase; letter-spacing: .14em; font-size: 12px;
            color: var(--marine); font-weight: 600; margin: 4px 0 6px; font-family: var(--sans);
          }}
          .aw-section-head {{ font-family: var(--display); font-size: 34px; color: var(--ink);
            font-weight: 800; margin: 2px 0 8px; letter-spacing: -.02em; line-height: 1.12; }}
          .aw-section-sub {{ color: var(--ink-soft); font-size: 15px; margin: 0 0 8px; max-width: 62ch; }}

          /* Centered variant — the reference centers its dark feature sections. */
          .aw-center {{ text-align: center; }}
          .aw-center .aw-section-head, .aw-center .aw-section-sub {{ margin-left: auto; margin-right: auto; }}

          /* --- Sub-section header (ledger tick) --- */
          .aw-subhead {{ display: flex; align-items: baseline; gap: 10px; margin: 8px 0 10px;
            border-left: 3px solid var(--gold); padding-left: 11px; }}
          .aw-subhead b {{ font-family: var(--display); font-size: 18px; font-weight: 600;
            color: var(--ink); letter-spacing: -.02em; }}
          .aw-subhead span {{ font-size: 12px; color: var(--ink-soft); font-family: var(--mono); }}

          div[data-testid="stExpander"] details {{ background: var(--paper2); }}

          /* --- Provenance badges (AI / rule-based / compliance-flagged) --- */
          .aw-badge {{
            display: inline-flex; align-items: center; gap: 5px; font-family: var(--sans);
            font-size: 10.5px; font-weight: 600; letter-spacing: .06em; text-transform: uppercase;
            padding: 4px 11px; border-radius: 999px; border: 1px solid var(--line);
            background: var(--paper2); color: var(--ink-soft); margin: 0 6px 6px 0;
          }}
          .aw-badge.ai {{ background: var(--marine); color: #0B0C1F; border-color: var(--marine-dark); }}
          .aw-badge.flag {{ background: rgba(255,118,0,.14); color: var(--neg); border-color: rgba(255,118,0,.4); }}

          /* --- Survey section banners --- */
          .aw-survey-section {{
            background: var(--marine); color: #0B0C1F; border-radius: 14px;
            padding: 12px 18px; margin: 26px 0 4px; font-weight: 700; font-size: 16px;
            font-family: var(--display); letter-spacing: -.01em;
          }}
          .aw-survey-section span {{ opacity: .75; font-weight: 500; font-size: 12px;
            font-family: var(--sans); }}
          .aw-survey-body {{
            border: 1px solid var(--line); border-top: none;
            border-radius: 0 0 14px 14px; padding: 18px 20px 8px; margin-bottom: 8px;
            background: var(--paper2);
          }}

          /* --- Glow-orb graphic panel: stands in for the reference's 3D
             sphere renders inside feature/spotlight blocks. --- */
          .pw-orb-panel {{
            width: 100%; aspect-ratio: 16/10; border-radius: 16px; position: relative;
            background-color: #05061c; background-size: cover; background-repeat: no-repeat;
            box-shadow: inset 0 0 0 1px rgba(255,255,255,.08);
            display: flex; align-items: flex-start; padding: 16px 18px;
          }}
          .pw-orb-label {{ color: rgba(255,255,255,.55); font-family: var(--sans);
            font-size: 13px; font-weight: 600; }}

          /* --- Floating product screenshot --- */
          .pw-shot {{
            border-radius: 20px; border: 1px solid var(--line); overflow: hidden;
            box-shadow: var(--shadow-md); max-width: 900px; margin: 0 auto;
            background: var(--paper2);
          }}
          .pw-shot img {{ width: 100%; display: block; }}

          /* --- Sticky-pinned text + scrolling content column: the
             reference's signature scroll mechanic (pure CSS position:sticky,
             no JS/scroll-jacking needed — the right column is simply taller
             than the left, so it scrolls past while the left stays put). --- */
          .pw-sticky-row {{ display: flex; gap: 60px; align-items: flex-start; }}
          .pw-sticky-col {{
            flex: 1; min-width: 0; position: sticky; top: 90px; align-self: flex-start;
          }}
          .pw-scroll-col {{
            flex: 1.15; min-width: 0; display: flex; flex-direction: column;
            gap: 9vh; padding: 6vh 0;
          }}
          .pw-scroll-card {{ min-height: 42vh; display: flex; align-items: center; }}
          .pw-scroll-card .aw-card {{ width: 100%; }}

          /* --- Numbered spotlight (the reference's "Key Features" blocks) --- */
          .pw-spot {{
            display: flex; gap: 44px; align-items: center; margin: 46px 0;
            animation: aw-rise .6s var(--ease-settle) both;
          }}
          .pw-spot.rev {{ flex-direction: row-reverse; }}
          .pw-spot .media {{ flex: 1; min-width: 0; }}
          .pw-spot .media .pw-orb-panel {{ aspect-ratio: 4/3; }}
          .pw-spot .text {{ flex: 1; min-width: 0; }}
          .pw-spot .eyebrow {{
            text-transform: uppercase; letter-spacing: .14em; font-size: 12px;
            color: var(--marine); font-weight: 600; margin-bottom: 10px; font-family: var(--sans);
          }}
          .pw-spot h3 {{ font-size: 30px; font-family: var(--display); font-weight: 800;
            letter-spacing: -.02em; margin: 0 0 12px; line-height: 1.1; }}
          .pw-spot p {{ color: var(--ink-soft); font-size: 15.5px; line-height: 1.65; margin: 0;
            max-width: 42ch; }}

          /* --- Cards: frosted glass — translucent + blurred, so the page's
             glow orbs read through the surface instead of a flat panel. --- */
          .aw-card, .aw-tier, .aw-quote, .aw-insight {{
            backdrop-filter: var(--glass-blur); -webkit-backdrop-filter: var(--glass-blur);
          }}
          .aw-card {{
            background: var(--glass); border: 1px solid var(--glass-border); border-radius: 18px;
            padding: 26px; height: 100%;
            transition: transform .22s var(--ease-settle), border-color .22s var(--ease-settle),
                        box-shadow .22s var(--ease-settle);
          }}
          .aw-card:hover {{
            transform: translateY(-4px); border-color: var(--marine); box-shadow: var(--glow-ring);
          }}
          .aw-card h3 {{ margin: 16px 0 7px; font-size: 19px; font-family: var(--display);
            font-weight: 700; letter-spacing: -.01em; }}
          .aw-card p  {{ color: var(--ink-soft); font-size: 14px; line-height: 1.62; margin: 0; }}
          .aw-card .ico {{
            width: 68px; height: 68px; border-radius: 16px; position: relative; overflow: hidden;
            display: flex; align-items: center; justify-content: center; color: #ffffff;
            background:
              radial-gradient(circle at 32% 28%, rgba(255,255,255,.85), transparent 42%),
              radial-gradient(circle at 68% 72%, var(--glow-cyan), transparent 55%),
              radial-gradient(circle at 30% 75%, var(--glow-blue), var(--teal) 70%);
            box-shadow: inset 0 0 0 1px rgba(255,255,255,.14);
          }}

          /* --- Process timeline (a real sequence → numbered ledger entries) --- */
          .aw-steps {{ display: flex; gap: 0; margin: 8px 0 4px; }}
          .aw-step {{
            flex: 1; position: relative; padding: 4px 18px 4px 0;
            animation: aw-rise .5s var(--ease-settle) both;
          }}
          .aw-step:nth-child(1) {{ animation-delay: .05s; }}
          .aw-step:nth-child(2) {{ animation-delay: .13s; }}
          .aw-step:nth-child(3) {{ animation-delay: .21s; }}
          .aw-step:nth-child(4) {{ animation-delay: .29s; }}
          .aw-step .n {{
            width: 40px; height: 40px; border-radius: 12px; font-family: var(--display);
            background: var(--paper2); border: 1px solid var(--marine); color: var(--marine);
            display: flex; align-items: center; justify-content: center; font-weight: 700;
            font-size: 15px; position: relative; z-index: 2;
          }}
          .aw-step:not(:last-child)::after {{
            content: ""; position: absolute; top: 20px; left: 34px; right: 6px; height: 1px;
            background: var(--line); z-index: 1;
          }}
          .aw-step h4 {{ font-size: 16px; margin: 12px 0 5px; font-family: var(--display);
            font-weight: 700; letter-spacing: -.01em; }}
          .aw-step p {{ font-size: 13px; color: var(--ink-soft); line-height: 1.55; margin: 0;
            padding-right: 12px; }}

          /* --- Service / fee tiers --- */
          .aw-tier {{
            background: var(--glass); border: 1px solid var(--glass-border); border-radius: 18px;
            padding: 28px 26px; height: 100%;
            transition: transform .22s var(--ease-settle), border-color .22s var(--ease-settle),
                        box-shadow .22s var(--ease-settle);
            display: flex; flex-direction: column;
          }}
          .aw-tier:hover {{
            transform: translateY(-4px); border-color: var(--marine); box-shadow: var(--glow-ring);
          }}
          .aw-tier.feat {{ border: 1px solid var(--marine); border-top: 3px solid var(--gold); }}
          .aw-tier .badge {{ align-self: flex-start; background: var(--marine); color: var(--paper);
            font-size: 10px; font-weight: 600; letter-spacing: .1em; text-transform: uppercase;
            padding: 4px 10px; border-radius: 999px; margin-bottom: 10px; font-family: var(--sans); }}
          .aw-tier h3 {{ font-family: var(--display); font-size: 20px; margin: 0 0 3px;
            font-weight: 700; color: var(--ink); letter-spacing: -.01em; }}
          .aw-tier .price {{ font-size: 15px; color: var(--marine); font-weight: 600; margin: 0 0 12px;
            font-family: var(--sans); }}
          .aw-tier ul {{ list-style: none; padding: 0; margin: 0; }}
          .aw-tier li {{ font-size: 13.5px; color: var(--ink-soft); padding: 6px 0 6px 22px;
            position: relative; line-height: 1.45; }}
          .aw-tier li::before {{ content: "+"; position: absolute; left: 0; top: 6px;
            color: var(--gold); font-weight: 700; font-family: var(--sans); }}

          /* --- Team / advisor --- */
          .aw-team {{ display: flex; gap: 22px; align-items: center; }}
          .aw-team .photo {{
            width: 150px; height: 150px; border-radius: 18px; flex: none;
            background: var(--marine); border: 1px solid var(--line);
            display: flex; align-items: center; justify-content: center;
            color: var(--paper); font-family: var(--display); font-size: 44px; font-weight: 700;
            overflow: hidden;
          }}
          .aw-team .photo img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
          .aw-team h3 {{ margin: 0 0 2px; font-size: 21px; font-family: var(--display);
            letter-spacing: -.01em; }}
          .aw-team .role {{ color: var(--marine); font-size: 12.5px; font-weight: 600; margin: 0 0 8px;
            font-family: var(--sans); }}
          .aw-team .creds {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }}
          .aw-team .creds span {{ font-size: 11px; background: var(--soft);
            border: 1px solid var(--line); color: var(--ink); padding: 4px 11px;
            border-radius: 999px; font-weight: 500; font-family: var(--sans); }}
          .aw-team p {{ font-size: 14px; color: var(--ink-soft); line-height: 1.62; margin: 4px 0 0; }}

          /* --- Testimonials --- */
          .aw-quote {{
            background: var(--glass); border: 1px solid var(--glass-border); border-radius: 18px;
            padding: 26px; height: 100%; position: relative;
            transition: transform .22s var(--ease-settle), border-color .22s var(--ease-settle),
                        box-shadow .22s var(--ease-settle);
          }}
          .aw-quote:hover {{
            transform: translateY(-4px); border-color: var(--marine); box-shadow: var(--glow-ring);
          }}
          .aw-quote .mark {{ font-family: var(--display); font-size: 46px; color: var(--gold);
            line-height: .5; display: block; height: 22px; }}
          .aw-quote p {{ font-size: 14.5px; color: var(--ink); line-height: 1.6; margin: 6px 0 14px; }}
          .aw-quote .who {{ display: flex; align-items: center; gap: 10px; }}
          .aw-quote .av {{ width: 34px; height: 34px; border-radius: 10px; flex: none;
            background: var(--marine); color: var(--paper);
            display: flex; align-items: center; justify-content: center; font-size: 13px;
            font-weight: 700; font-family: var(--display); }}
          .aw-quote .who b {{ font-size: 13px; color: var(--ink); display: block;
            font-family: var(--display); font-weight: 600; }}
          .aw-quote .who span {{ font-size: 11px; color: var(--ink-soft); font-family: var(--sans); }}

          /* --- Insights --- */
          .aw-insight {{
            background: var(--glass); border: 1px solid var(--glass-border); border-radius: 18px;
            overflow: hidden; height: 100%;
            transition: transform .22s var(--ease-settle), border-color .22s var(--ease-settle),
                        box-shadow .22s var(--ease-settle);
          }}
          .aw-insight:hover {{
            transform: translateY(-4px); border-color: var(--marine); box-shadow: var(--glow-ring);
          }}
          .aw-insight .top {{
            height: 100px; display: flex; align-items: center; justify-content: flex-start;
            padding: 0 20px; position: relative; overflow: hidden;
            background:
              radial-gradient(circle at 75% 20%, rgba(255,255,255,.5), transparent 40%),
              radial-gradient(circle at 85% 90%, var(--glow-cyan), transparent 55%),
              radial-gradient(circle at 10% 60%, var(--glow-blue), var(--marine-dark) 70%);
          }}
          .aw-insight .top span {{ color: #ffffff; font-size: 10.5px; position: relative;
            text-transform: uppercase; letter-spacing: .14em; font-weight: 600; font-family: var(--sans); }}
          .aw-insight .body {{ padding: 16px 20px 20px; }}
          .aw-insight h4 {{ font-size: 16px; margin: 0 0 6px; font-family: var(--display);
            font-weight: 700; line-height: 1.28; letter-spacing: -.01em; }}
          .aw-insight p {{ font-size: 13px; color: var(--ink-soft); line-height: 1.55; margin: 0; }}
          .aw-insight .meta {{ font-size: 11px; color: var(--marine); font-weight: 600; margin-top: 10px;
            font-family: var(--sans); }}

          /* --- Card-grid entrance stagger: left-to-right by column position.
             Scoped by the card's own class, so this is safe to reuse across
             every st.columns(3) row on the page (How we help / Services /
             Testimonials / Insights) without a dedicated wrapper per row. --- */
          div[data-testid="stColumn"]:nth-child(1) .aw-card,
          div[data-testid="stColumn"]:nth-child(1) .aw-tier,
          div[data-testid="stColumn"]:nth-child(1) .aw-quote,
          div[data-testid="stColumn"]:nth-child(1) .aw-insight {{
            animation: aw-rise .5s var(--ease-settle) both; animation-delay: .05s;
          }}
          div[data-testid="stColumn"]:nth-child(2) .aw-card,
          div[data-testid="stColumn"]:nth-child(2) .aw-tier,
          div[data-testid="stColumn"]:nth-child(2) .aw-quote,
          div[data-testid="stColumn"]:nth-child(2) .aw-insight {{
            animation: aw-rise .5s var(--ease-settle) both; animation-delay: .13s;
          }}
          div[data-testid="stColumn"]:nth-child(3) .aw-card,
          div[data-testid="stColumn"]:nth-child(3) .aw-tier,
          div[data-testid="stColumn"]:nth-child(3) .aw-quote,
          div[data-testid="stColumn"]:nth-child(3) .aw-insight {{
            animation: aw-rise .5s var(--ease-settle) both; animation-delay: .21s;
          }}

          /* Scroll-driven reveal — additive progressive enhancement only;
             browsers without support simply keep the mount-triggered version
             above. Same keyframe, so it reads as one consistent system. */
          @supports (animation-timeline: view()) {{
            .aw-card, .aw-tier, .aw-quote, .aw-insight, .aw-step {{
              animation-delay: 0s;
              animation-timeline: view();
              animation-range: entry 0% cover 35%;
            }}
          }}

          /* --- Form inputs (text, select, date, textarea) — dark-themed to
             match; Streamlit's defaults are a plain white field. --- */
          [data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea,
          [data-testid="stDateInput"] input, [data-testid="stNumberInput"] input,
          [data-testid="stSelectbox"] input, [data-testid="stSelectbox"] [role="group"],
          [data-baseweb="select"] > div, [data-baseweb="input"] {{
            background: var(--paper2) !important; color: var(--ink) !important;
            border-color: var(--line) !important; border-radius: 10px !important;
          }}
          [data-testid="stTextInput"] input::placeholder, [data-testid="stTextArea"] textarea::placeholder,
          [data-testid="stSelectbox"] input::placeholder {{
            color: var(--ink-soft) !important; opacity: .7;
          }}
          [data-testid="stSelectbox"] button {{ background: transparent !important; }}
          [data-testid="stNumberInputContainer"] {{
            background: var(--paper2) !important; border-radius: 10px !important;
          }}
          [data-testid="stNumberInputContainer"] * {{ background-color: transparent !important; }}
          [data-testid="stNumberInputContainer"] input {{ color: var(--ink) !important; }}
          [data-testid="stNumberInputStepDown"] svg, [data-testid="stNumberInputStepUp"] svg {{
            fill: var(--ink-soft) !important;
          }}
          [data-testid="stSelectbox"] svg, [data-baseweb="select"] svg {{ fill: var(--ink-soft) !important; }}
          [data-testid="stWidgetLabel"] p {{ color: var(--ink) !important; font-weight: 500; }}
          [role="listbox"], div[data-baseweb="popover"] {{ background: var(--paper2) !important;
            border: 1px solid var(--line) !important; }}
          [role="option"], div[data-baseweb="popover"] li {{ color: var(--ink) !important;
            background: var(--paper2) !important; }}
          [role="option"]:hover, div[data-baseweb="popover"] li:hover {{ background: var(--soft) !important; }}
          div[data-baseweb="calendar"] {{ background: var(--paper2) !important; }}

          /* --- Disclosures footer --- */
          .aw-foot {{
            margin-top: 30px; border-top: 1px solid var(--line); padding-top: 22px;
            color: var(--ink-soft); font-size: 12px; line-height: 1.65;
          }}
          .aw-foot .cols {{ display: flex; gap: 40px; flex-wrap: wrap; margin-bottom: 16px; }}
          .aw-foot .cols b {{ color: var(--ink); font-family: var(--display);
            font-size: 13px; display: block; margin-bottom: 6px; font-weight: 700; }}
          .aw-foot .cols div {{ font-size: 12px; font-family: var(--sans); line-height: 1.7; }}
          .aw-foot .fine {{ font-size: 11px; color: var(--ink-soft); border-top: 1px dashed var(--line);
            padding-top: 12px; }}

          /* --- Metrics --- */
          [data-testid="stMetric"] {{
            background: var(--glass); border: 1px solid var(--glass-border);
            backdrop-filter: var(--glass-blur); -webkit-backdrop-filter: var(--glass-blur);
            border-bottom: 2px solid var(--marine); border-radius: 14px; padding: 14px 18px;
          }}
          [data-testid="stMetricValue"] {{ font-size: 24px; color: var(--ink);
            font-family: var(--display); font-weight: 700; letter-spacing: -.02em; }}
          [data-testid="stMetricLabel"] {{ color: var(--ink-soft); font-family: var(--sans);
            letter-spacing: 0; font-size: 11px; }}
          [data-testid="stMetricLabel"] * {{ white-space: normal; overflow: visible;
            text-overflow: clip; }}
          [data-testid="stMetricDelta"] {{ font-family: var(--sans); font-size: 12px; }}

          /* --- Buttons: solid pill + circular arrow badge, the reference's
             signature CTA shape. --- */
          .stButton button, .stFormSubmitButton button {{
            border-radius: 999px; font-weight: 600; font-family: var(--sans);
            padding: 12px 46px 12px 22px !important; position: relative; overflow: hidden;
            transition: transform .16s var(--ease-settle), background .16s var(--ease-settle),
                        border-color .16s var(--ease-settle), box-shadow .16s var(--ease-settle);
          }}
          /* Shine sweep on hover — a diagonal highlight bar, transform/opacity
             only (no background-position animation, per the motion rule). */
          .stButton button::before, .stFormSubmitButton button::before {{
            content: ""; position: absolute; inset: -30% -10%; z-index: 1;
            pointer-events: none; opacity: 0;
            background: linear-gradient(105deg,
              transparent 42%, rgba(125,178,245,.55) 48%, rgba(255,255,255,.85) 50%,
              rgba(125,178,245,.55) 52%, transparent 58%);
            transform: translateX(-130%) skewX(-10deg);
            transition: transform .9s var(--ease-settle), opacity .25s var(--ease-settle);
          }}
          .stButton button:hover::before, .stFormSubmitButton button:hover::before {{
            transform: translateX(130%) skewX(-10deg); opacity: 1;
          }}
          .stButton button::after, .stFormSubmitButton button::after {{
            content: "\\2192"; position: absolute; right: 7px; top: 50%; z-index: 2;
            transform: translateY(-50%); width: 27px; height: 27px; border-radius: 50%;
            display: flex; align-items: center; justify-content: center; font-size: 13px; line-height: 1;
          }}
          .stButton button > div, .stFormSubmitButton button > div {{ position: relative; z-index: 2; }}
          .stButton button:active, .stFormSubmitButton button:active {{
            transform: scale(.97); transition-duration: .08s;
          }}
          .stButton button[kind="primary"], .stButton button[kind="primaryFormSubmit"],
          .stFormSubmitButton button[kind="primaryFormSubmit"] {{
            background: #ffffff; border-color: #ffffff; color: #0B0C1F;
          }}
          .stButton button[kind="primary"] *, .stButton button[kind="primaryFormSubmit"] *,
          .stFormSubmitButton button[kind="primaryFormSubmit"] * {{ color: #0B0C1F !important; }}
          .stButton button[kind="primary"]::after, .stButton button[kind="primaryFormSubmit"]::after,
          .stFormSubmitButton button[kind="primaryFormSubmit"]::after {{
            background: #0B0C1F; color: #ffffff;
          }}
          .stButton button[kind="primary"]:hover, .stButton button[kind="primaryFormSubmit"]:hover,
          .stFormSubmitButton button[kind="primaryFormSubmit"]:hover {{
            background: #EDEFF6; border-color: #EDEFF6;
            transform: translateY(-1px); box-shadow: var(--shadow-md);
          }}
          .stButton button[kind="secondary"] {{
            color: var(--ink); border-color: var(--line); background: rgba(255,255,255,.05);
          }}
          .stButton button[kind="secondary"]::after {{ background: rgba(255,255,255,.92); color: #0B0C1F; }}
          .stButton button[kind="secondary"]:hover {{
            color: var(--ink); border-color: rgba(255,255,255,.32);
            background: rgba(255,255,255,.1); transform: translateY(-1px);
          }}

          /* --- Top navigation: rounded pill bar --- */
          div[data-testid="stHorizontalBlock"]:has(> div [class*="st-key-nav_"]) {{
            background: var(--paper2); border: 1px solid var(--line);
            border-radius: 999px; padding: 7px 9px; gap: 6px;
          }}
          [class*="st-key-nav_"] button {{
            border: none !important; background: transparent !important;
            color: var(--ink-soft) !important; font-weight: 500 !important;
            border-radius: 999px !important; font-family: var(--sans) !important;
            font-size: 12.5px !important; letter-spacing: .02em; padding: 8px 16px !important;
            box-shadow: none !important; transition: background .16s ease, color .16s ease !important;
          }}
          [class*="st-key-nav_"] button::after {{ display: none; }}
          [class*="st-key-nav_"] button:hover {{
            background: var(--soft) !important; color: var(--ink) !important;
            transform: none !important; box-shadow: none !important;
          }}
          [class*="st-key-nav_"] button[kind="primary"] {{
            background: #ffffff !important; color: #0B0C1F !important; box-shadow: none !important;
          }}
          [class*="st-key-nav_"] button[kind="primary"] * {{ color: #0B0C1F !important; }}
          [class*="st-key-nav_"] button[kind="primary"]:hover {{
            background: #EDEFF6 !important; transform: none !important;
          }}
          [class*="st-key-gearbtn"] button {{
            border: 1px solid var(--line) !important; background: var(--paper2) !important;
            color: var(--marine) !important; border-radius: 999px !important; box-shadow: none !important;
          }}
          [class*="st-key-gearbtn"] button::after {{ display: none; }}
          [class*="st-key-gearbtn"] button:hover {{
            border-color: var(--marine) !important; background: var(--soft) !important;
          }}

          hr {{ opacity: .4; border-color: var(--line); }}
          [data-testid="stExpander"] {{ border-radius: 14px; border-color: var(--line); }}
          [data-testid="stExpander"] summary {{
            background: var(--paper2) !important; color: var(--ink) !important;
            border-radius: 14px !important;
          }}
          [data-testid="stExpander"] summary:hover {{ background: var(--soft) !important; }}
          [data-testid="stExpander"] summary [data-testid="stIconMaterial"] {{
            color: var(--ink-soft) !important;
          }}
          [data-testid="stExpander"] details[open] summary {{
            border-radius: 14px 14px 0 0 !important;
          }}
          [data-testid="stExpanderDetails"] {{ background: var(--paper2) !important; }}

          /* --- Loading state: on-brand spinner instead of Streamlit's default --- */
          [data-testid="stSpinner"] {{ color: var(--marine); font-family: var(--sans); font-size: 13px; }}
          [data-testid="stSpinner"] > div {{ color: var(--marine); }}
          [data-testid="stSpinner"] svg {{ color: var(--marine) !important; }}

          /* --- Dashboard header: title block + avatar/dropdown control --- */
          .pw-dash-head {{ display: flex; align-items: flex-start; justify-content: space-between;
            gap: 16px; flex-wrap: wrap; }}
          [class*="st-key-avatarbtn"] button {{
            background: var(--paper2) !important; border: 1px solid var(--line) !important;
            border-radius: 999px !important; color: var(--ink) !important; box-shadow: none !important;
            font-family: var(--sans) !important; font-weight: 500 !important; padding: 6px 14px !important;
          }}
          [class*="st-key-avatarbtn"] button:hover {{
            border-color: var(--marine) !important; background: var(--soft) !important;
          }}
          [class*="st-key-avatarbtn"] button::after {{ display: none; }}
          [class*="st-key-avatarbtn"] [data-testid="stIconMaterial"] {{ color: var(--ink-soft) !important; }}
          [data-testid="stPopoverBody"] {{
            background: var(--paper2) !important; border: 1px solid var(--line) !important;
            border-radius: 14px !important; box-shadow: var(--shadow-md) !important;
          }}
          .pw-avatar-chip {{ display: flex; align-items: center; gap: 9px; }}
          .pw-avatar-chip .dot {{
            width: 26px; height: 26px; border-radius: 50%; background: var(--marine);
            color: #0B0C1F; display: flex; align-items: center; justify-content: center;
            font-family: var(--display); font-weight: 700; font-size: 11px; flex: none;
          }}
          .pw-dropdown-item {{ padding: 7px 4px; font-size: 13.5px; color: var(--ink);
            border-bottom: 1px solid var(--line); }}
          .pw-dropdown-item:last-child {{ border-bottom: none; }}
          .pw-dropdown-item span {{ color: var(--ink-soft); font-size: 12px; display: block; }}

          /* --- Bar chart (real AUM figures, no charting library needed) --- */
          .pw-bar-chart {{ display: flex; flex-direction: column; gap: 12px; }}
          .pw-bar-row {{ display: grid; grid-template-columns: 160px 1fr 90px; gap: 14px;
            align-items: center; }}
          .pw-bar-row .name {{ font-size: 13px; color: var(--ink); font-weight: 500;
            overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
          .pw-bar-track {{ background: var(--soft); border-radius: 999px; height: 10px;
            overflow: hidden; }}
          .pw-bar-fill {{ height: 100%; border-radius: 999px;
            background: linear-gradient(90deg, var(--marine-dark), var(--marine));
            animation: pw-bar-grow .8s var(--ease-settle) both; transform-origin: left; }}
          @keyframes pw-bar-grow {{ from {{ transform: scaleX(0); }} to {{ transform: scaleX(1); }} }}
          .pw-bar-row .val {{ font-size: 13px; color: var(--ink-soft); text-align: right;
            font-family: var(--display); font-weight: 600; }}

          @media (prefers-reduced-motion: reduce) {{
            * {{ transition: none !important; animation: none !important; }}
          }}
          @media (max-width: 820px) {{
            .aw-hero {{ padding: 40px 12px 28px; }}
            .aw-hero h1 {{ font-size: 38px; }}
            .aw-ledger {{ flex-wrap: wrap; }}
            .aw-steps {{ flex-direction: column; gap: 16px; }}
            .aw-step:not(:last-child)::after {{ display: none; }}
            .aw-team {{ flex-direction: column; text-align: center; align-items: center; }}
            .aw-team .creds {{ justify-content: center; }}
            .pw-spot, .pw-spot.rev {{ flex-direction: column; gap: 20px; margin: 32px 0; }}
            .pw-sticky-row {{ flex-direction: column; }}
            .pw-sticky-col {{ position: static; }}
            .pw-scroll-card {{ min-height: 0; }}
            .pw-scroll-col {{ gap: 20px; padding: 12px 0; }}
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
                <div class="name pw-shimmer">{FIRM_NAME}</div>
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


def product_shot_html() -> str:
    """The floating product screenshot from assets/product-shot.jpg, if present.

    A real screenshot of the app's own Dashboard, not a mockup.
    """
    f = Path(__file__).parent / "assets" / "product-shot.jpg"
    if f.exists():
        b64 = base64.b64encode(f.read_bytes()).decode()
        return f'<img src="data:image/jpeg;base64,{b64}" alt="WealthSync dashboard"/>'
    return ""


_ORB_VARIANTS = {
    1: "radial-gradient(circle at 30% 25%, rgba(255,255,255,.7), transparent 40%),"
       "radial-gradient(circle at 75% 70%, var(--glow-cyan), transparent 55%),"
       "radial-gradient(circle at 25% 80%, var(--glow-blue), var(--teal) 70%)",
    2: "radial-gradient(circle at 70% 20%, rgba(255,255,255,.6), transparent 40%),"
       "radial-gradient(circle at 20% 75%, var(--glow-blue), transparent 55%),"
       "radial-gradient(circle at 80% 85%, var(--gold), var(--marine-dark) 70%)",
    3: "radial-gradient(circle at 25% 70%, rgba(255,255,255,.6), transparent 40%),"
       "radial-gradient(circle at 80% 30%, var(--glow-cyan), transparent 50%),"
       "radial-gradient(circle at 60% 85%, var(--glow-blue), var(--marine-dark) 75%)",
}


def orb_panel_html(variant: int = 1, label: str = "") -> str:
    """A CSS-only glow-orb graphic panel — stands in for the reference's
    3D-rendered sphere images inside feature/spotlight blocks."""
    bg = _ORB_VARIANTS.get(variant, _ORB_VARIANTS[1])
    tag = f'<span class="pw-orb-label">{label}</span>' if label else ""
    return f'<div class="pw-orb-panel" style="background-image:{bg};">{tag}</div>'


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
    "bell": '<path d="M6 16v-5a6 6 0 0 1 12 0v5l1.5 2.5h-15z"/>'
            '<path d="M10 21a2 2 0 0 0 4 0"/>',
    "chevron-down": '<path d="M5 9l7 7 7-7"/>',
}


def icon(name: str, size: int = 22) -> str:
    """Return an inline SVG line-icon that inherits the surrounding color."""
    body = _ICON_PATHS.get(name, "")
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
            f'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" '
            f'stroke-linejoin="round">{body}</svg>')


def section_header(label: str, title: str, subtitle: str = "", centered: bool = False) -> None:
    """A consistent 'eyebrow + display heading + subtitle' section opener."""
    sub = f'<div class="aw-section-sub">{subtitle}</div>' if subtitle else ""
    wrap_open, wrap_close = ('<div class="aw-center">', "</div>") if centered else ("", "")
    st.markdown(
        f'{wrap_open}<div class="aw-section-label">{label}</div>'
        f'<div class="aw-section-head">{title}</div>{sub}{wrap_close}',
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
