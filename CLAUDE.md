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
- The `frontend-design` skill is installed in this environment and should be
  invoked for aesthetic/layout decisions. Before writing UI code, also **read
  `app_ui.py inject_theme()`** and reuse the existing CSS variables and component
  classes rather than inventing new ones — the skill's general guidance defers
  to this project's established design system below.

## Design system — "The Ledger", already established, match it
- **Thesis:** precision as personality — every figure is computed, not guessed, and
  the design says so. Mono numerics are the signature voice.
- **Typography:** Bricolage Grotesque (display) for headings, Inter for body, and
  **IBM Plex Mono** for every number, label, eyebrow, price, and tag. Never one font
  for all. Tight tracking (`-0.02em`) on headings.
- **Palette (defined in `app_ui.py`):** paper `#F7F4EF`, paper2 `#FCFAF6`,
  ink `#14181F`, ink-soft `#5A6169`, marine `#0E6F73` (primary — the `NAVY` constant),
  marine-dark `#0A5155`, gold `#C08A2D` (the single signal accent), line `#E4DECF`
  (warm hairline). Derive new colors from these — never default Tailwind/generic hues.
- **Signatures:** mono metric values on a marine ledger underline; `// ` gold-slash
  mono eyebrows (`.aw-section-label`, `.eyebrow`); the hero ledger stat strip
  (`.aw-ledger`); gold left-tick subheads; numbered ledger steps.
- **Surfaces:** flat printed look — paper2 cards with 1px warm borders and small
  `border-radius: 3px`, minimal shadow. Hover lifts `translateY(-2px)` + marine border.
- **Spacing:** reuse the existing tokens; intentional and consistent, not random.

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
- **Colors:** the Ledger palette only (paper/ink/marine/gold) — never default Tailwind.
- **Typography:** Bricolage display + Inter body + IBM Plex Mono for all data/labels.
- **Signature first:** spend boldness on the mono/ledger signature; keep the rest quiet.
- **Animations:** `transform`/`opacity` only. Never `transition-all`.
- **Interactive states:** hover + focus-visible (gold ring) + active on every clickable.
- **Spacing:** intentional, consistent tokens.

## Hard rules
- Do not add sections, features, or content not requested or in the reference.
- Do not "improve" a reference design — match it.
- Do not stop after one screenshot pass.
- Do not use `transition-all`.
- Do not use default Tailwind blue/indigo as a primary color.
