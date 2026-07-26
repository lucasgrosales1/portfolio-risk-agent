# CLAUDE.md — WealthSync web design rules

Adapted for THIS project (a Streamlit app on this machine). The original template
targeted a static `index.html` + Tailwind site with a Node/puppeteer screenshot
workflow under another user's home folder — those parts have been rewritten to
match how design actually works here.

## Project shape
- This is a **Streamlit multi-page Python app** (the WealthSync Advisors demo).
  There is **no static HTML/Tailwind build** and no `index.html`.
- "Web design" here lives in:
  - `app_ui.py` → `inject_theme()` (all global CSS, tokens, component classes) and
    the shared helpers: `card`, `section_header`, `subhead`, `trust_strip`,
    `disclosures_footer`, `coastal_svg`, `icon`, `top_nav`, `advisor_photo_html`.
  - `app_views.py` → the page views (`home`, `dashboard`, `portfolio_analysis`,
    `client_survey`, `settings`).
- Entry point: `streamlit_app.py`. Run:
  `.venv/Scripts/streamlit run streamlit_app.py`

## Always do first
- The template's `frontend-design` skill is **not installed in this environment**,
  so it cannot be invoked. Instead, before writing UI code, **read
  `app_ui.py inject_theme()`** and reuse the existing CSS variables and component
  classes rather than inventing new ones.

## Design system — already established, match it
- **Typography:** Fraunces (display serif) for headings, Inter for body. Never the
  same font for both. Tight tracking (`-0.01em`) on large headings; body
  `line-height` 1.6–1.7.
- **Palette (Florida coastal, defined in `app_ui.py`):** navy `#12556e`,
  navy-dark `#0c3a4d`, teal `#1c9bb3`, sand `#e3c893`, coral `#e8785a`,
  gold `#d9a441`. Derive new colors from these — never default Tailwind/generic hues.
- **Shadows:** layered, low-opacity, navy-tinted (`--shadow-sm/md/lg`). No flat gray
  `box-shadow`.
- **Spacing:** reuse the existing scale/variables; intentional and consistent, not
  random values.
- **Depth:** surfaces layer (page bg → card → floating). Cards sit at `--shadow-sm`
  and lift to `--shadow-md` on hover.

## Interactive states
- Every clickable element needs **hover, focus-visible, and active** states.
- Animate **only `transform` and `opacity`**. Never `transition-all`.

## Reference images
- If a reference image is provided: match layout, spacing, typography, and color
  exactly; use placeholder content. Do not improve or add to the design.
- If no reference: design from scratch with high craft using the system above.
- Screenshot the output, compare against the reference, fix mismatches, re-screenshot.
  Do **at least 2 comparison rounds**. Be specific: "heading is 32px but reference
  shows ~24px", "card gap is 16px but should be 24px".

## Preview & screenshot workflow (this environment)
- Preview through the built-in **Browser pane**, not puppeteer. A launch config
  exists at `.claude/launch.json` (name: `wealthsync`, port 8760).
- Start / refresh: `preview_start {name:"wealthsync"}` → the app opens at
  `http://localhost:8760`. **Restart the server after editing `app_ui.py` /
  `app_views.py`** — Streamlit reruns the script but does not hot-reload imported
  modules, so changes there won't show until restart.
- Capture: if the pane isn't displayed and `computer{screenshot}` times out, verify
  visually by rasterizing an element via `javascript_tool` (canvas → dataURL, decode
  with Python) and read it back; check computed styles with `javascript_tool`; and
  inspect structure with `read_page`.
- If a Node/puppeteer workflow is ever added, put its scripts and cache under **your
  own home path** `C:/Users/buyer/...` — the template's `C:/Users/nateh/...` is a
  different user and will not resolve here.

## Brand assets
- `assets/` holds the real images — use them, never placeholders:
  - `hero.jpg` — aerial Miami Beach (Pexels, photo by emma; free license).
  - `advisor.jpg` — the advisor headshot.
  Both are swappable by dropping a new file with the same name; `app_ui.py` embeds
  whatever is present.

## Anti-generic guardrails
- **Colors:** custom coastal palette only — never default Tailwind indigo/blue.
- **Shadows:** layered, color-tinted, low opacity — never flat `shadow-md`.
- **Typography:** serif display + clean sans, tight heading tracking, roomy body.
- **Animations:** `transform`/`opacity` only, spring-style easing.
- **Interactive states:** hover + focus-visible + active on every clickable element.
- **Spacing:** intentional, consistent tokens.
- **Depth:** a real layering system (base → elevated → floating), not one z-plane.

## Hard rules
- Do not add sections, features, or content not requested or in the reference.
- Do not "improve" a reference design — match it.
- Do not stop after one screenshot pass.
- Do not use `transition-all`.
- Do not use default Tailwind blue/indigo as a primary color.
