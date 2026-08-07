# Project context — where WealthSync stands

A one-read catch-up for a fresh session (or a returning human). Written 2026-07-26,
last updated 2026-08-06. **Live:** [wealthsync-advisors.streamlit.app](https://wealthsync-advisors.streamlit.app/).
For design rules see [`CLAUDE.md`](../CLAUDE.md); for deploy steps see
[`06-deploy.md`](06-deploy.md).

## What this is
A Streamlit web app for a Florida fee-only fiduciary advisor (a résumé piece that
doubles as a real tool). Core principle: **the LLM never produces a number — every
figure is computed in Python; AI only narrates.** Two chained capabilities:
1. **Portfolio analysis** — holdings → valuation, concentration, volatility, Sharpe,
   beta, max drawdown, tax-aware rebalancing, downloadable report.
2. **Suitability & planning** — a client survey → capacity-first recommendation,
   retirement-income readiness, sequence-of-returns stress test, value strategy,
   structured-note analysis, and a downloadable Investment Policy Statement.

## Architecture (where things live)
- `streamlit_app.py` — thin entry point; adds `src/` to `sys.path` (needed on
  Streamlit Cloud, which installs `requirements.txt` not `pip install -e .`).
  Also owns routing priority: a `?invite=<token>` query param (a client
  following a link an advisor sent them) short-circuits straight to
  `render_client_invite()` before the welcome splash or nav bar ever run.
- `app_ui.py` — design system: `inject_theme()` (all CSS), branding, `top_nav()`,
  `welcome_screen()`, and component helpers (`card`, `section_header`, `subhead`,
  `score_gauge_html`, `step_photo_html`, `invite_link_html`, `advisor_photo_html`).
  ~1,440 lines. Two components.v1 iframes do real cross-frame JS work that
  `st.markdown()` can't (it never executes injected `<script>` tags): `_scroll_bridge()`
  drives scroll-linked parallax, `_fix_button_accessible_names()` patches Streamlit's
  buttons (which all render `aria-label=""` by default) so screen readers get a
  real label instead of silence.
- `app_views.py` — the 5 page views (`home`, `dashboard`, `portfolio_analysis`,
  `client_survey`, `settings`) plus `render_client_invite` (the stripped, nav-free
  view a client sees through an invite link) and render helpers. ~1,710 lines (a
  monolith — still true, still fine for now).
- `src/pra/` — the real engine, UI-independent:
  - `analytics/` (allocation, concentration, rebalance, risk),
  - `suitability/` (profile, scoring, capacity, recommend, retirement, stress,
    structured, strategy, montecarlo, ips),
  - `prices.py` (yfinance + on-disk pickle cache, explicit 15s fetch timeout),
    `pipeline.py`, `report/render.py`, `agents/narrative.py` (rule-based path),
    `agents/ai.py` + `agents/compliance.py` (the real Sonnet-writes/Haiku-reviews
    pair — see `docs/case-study.md`).
- `assets/` — `hero.jpg` (Miami Beach, Pexels/emma), `advisor.jpg`, four
  `step-*.jpg` process photos (Pexels), `logo-mark.svg`/`logo-mark-favicon.svg`/
  `logo-wordmark.svg`/`favicon.png` (brand mark).
- `data/` — synthetic sample portfolios (client_*.csv, sample_concentrated.csv).
- `brandfolder/brand-guidelines.html` — full brand guideline; source for the
  published Artifact. **Describes the original light "Ledger" identity — see
  the visual-identity note below before trusting it for color/type specifics.**

## Cross-session state: the architecture that makes "send to client" possible
`st.session_state` is scoped to one browser session/connection — it looks like
shared app state (you read and write it like a normal variable, it persists
across reruns) but a different visitor's browser can never see it. That's fine
until a feature is inherently cross-person: an advisor creates a client-survey
invite link on their own machine, and a completely different person on a
completely different device opens it later and submits it.

`app_views._shared_store()` is an `@st.cache_resource`-backed dict — the same
object for every visitor, for the life of the process — used for exactly the
state that has to be genuinely shared: filed surveys, pending/responded
invites, and consultation leads from the Home page form. Trade-off, stated
plainly: it resets on redeploy or a Streamlit Community Cloud sleep/wake
cycle. That's an acceptable limit for a demo; a system of record would need
an external database, which this project deliberately doesn't have. See
`docs/case-study.md` for the fuller "why," including the race-condition it
also fixed (the thank-you page used to read `surveys[-1]` from what's now a
multi-writer list — it stashes a session-local copy of just-submitted data
instead).

## Current visual identity — dark "AI Finance" redesign
**This superseded the original light "Ledger" identity** (`CLAUDE.md` still
documents that older system in detail; treat its palette/type specifics as
historical unless it's been updated since this note was written). The live
app now runs a near-black navy base (`#05061C`/`#0B0C2E`), white type, a
sky-blue interactive accent (`#7DB2F5`), a single gold signal (`#FFE08C`),
and glassy blue/cyan glow accents standing in for a reference design's
3D-rendered spheres. Plus Jakarta Sans for display type, Inter for body —
no monospace signature (a deliberate departure from the old Ledger voice).
`.streamlit/config.toml`'s `[theme]` block carries the same two fonts and
palette into native widgets CSS can't reach (dataframes, Vega-Lite charts,
`st.metric`) — it has to stay in sync with `app_ui.py` by hand, there's no
single source of truth shared between them.

Signature motion: an entrance stagger on arrival at a page (`@keyframes
aw-rise`), scroll-linked parallax on Home's hero blobs, a living animated
background (`.pw-bg-glow`), hover lift + shadow bloom + press-scale on every
interactive element. `transform`/`opacity` only, never `transition-all`,
respects `prefers-reduced-motion`.

## State: done vs. not
**Done:** all 5 pages plus the client-invite view build and render; the dark
redesign applied app-wide including a one-time welcome splash and scroll
parallax; licensed hero + real headshot + four process-step photos; sample
clients and filed surveys both produce holdings analysis + suitability;
structured-note analysis with themed payoff charts (explicit GOLD/TEAL/POS/NEG
colors, not Streamlit's auto-picked defaults); a 96-test `pytest` suite with
known-value coverage of `analytics/*` and `suitability/*`, a mocked-Anthropic
coverage of the AI agent pair, prices.py's network-failure handling, and
AppTest smoke checks for every page — fully offline/deterministic, see
`tests/conftest.py` (including an autouse fixture that resets the shared
`cache_resource` store between test cases); a refined logo mark + brand
guideline; the narrative + compliance-review agent pair wired end to end,
surfaced natively with a source/compliance badge; cross-session survey
delivery via a shareable invite link (advisor creates it, client's response
lands on the advisor's Dashboard, recoverable from there too if the advisor
navigates away before copying it); every button has a real screen-reader
label (Streamlit's own `aria-label=""` default silently strips this app-wide
otherwise); yfinance calls have an explicit 15s timeout and convert network
failures into the existing friendly-error UI instead of crashing the page;
`requirements.txt` pinned to known-good versions; mobile nav bar fixed (was
losing its button chrome when Streamlit's columns stack vertically below
~640px); pushed and **deployed live**.

**Not done / open** — genuinely short now; see the README roadmap for the
checklist view:
- **Downloadable Report + IPS carry their own CSS**, separate from the live
  app's dark theme (`report/render.py`, `suitability/ips.py`). This is
  arguably *correct* now rather than a gap — a printable/PDF-able client
  deliverable wants a light, ink-friendly, print-optimized look, not the
  app's dark navy. Revisit only if that judgment call changes.
- **`app_views.py` is a ~1,710-line monolith.** Fine at this size, real
  friction if it keeps growing — candidate for a per-page split.
- **Emoji in dashboard subheads** (⏱️ 📋 📅) are a minor off-note against the
  otherwise-considered visual system. Low priority.
- **`brandfolder/brand-guidelines.html` and `CLAUDE.md` describe the old
  light Ledger identity**, not the current dark redesign. Neither is
  user-facing (design instructions / an internal Artifact source, not
  something a visitor sees), so this is documentation debt, not a product
  gap — but worth knowing before trusting either for current color/type specifics.

### Fixed along the way (not previously tracked here)
- **Percentages displayed ~100x too small** in tables/sliders —
  `st.column_config.NumberColumn`/`st.slider` printf-style `%` formatting
  doesn't auto-scale a 0–1 fraction. Display-only; the computed numbers were
  always correct.
- **Dollar amounts rendering as mangled inline LaTeX** in native "Advisor
  commentary" — `st.markdown` treats a bare `$...$` pair as a math span.
  Fixed by escaping `$` before rendering.
- **Cash position mislabeled "Pathward Financial, Inc."** — the synthetic
  `CASH` ticker collided with a real Nasdaq symbol in yfinance metadata;
  `value_portfolio()` now special-cases the cash placeholder rather than
  trusting whatever metadata comes back for it.
- **Three of five structured-product charts would have crashed** the first
  time a real client profile reached them — `st.line_chart(..., color=[...])`
  needs one color per column, and the payoff dataframe always has two
  columns (product + underlying reference); found while adding explicit
  chart theming, not by inspection.

## How to run / preview / deploy
- Run: `.venv/Scripts/streamlit run streamlit_app.py` → http://localhost:8501
- Restart after editing `app_ui.py`/`app_views.py` (imported modules don't hot-reload).
- Deploy: see `06-deploy.md`. Repo is public at
  `github.com/lucasgrosales1/portfolio-risk-agent`, live at
  `wealthsync-advisors.streamlit.app`. Every push to `main` auto-redeploys —
  note the shared `cache_resource` store (surveys, invites, consult leads)
  resets on every redeploy and on a Streamlit Cloud sleep/wake cycle.

## Conventions
- Keep the "LLM never produces a number" rule: numbers come from `src/pra`, prose from
  `agents/narrative.py`. Don't let the UI invent figures.
- Reuse `app_ui.py` tokens/components; follow `CLAUDE.md` for CSS mechanics even
  though its literal palette/type is the superseded Ledger identity (see above).
- Sample data and testimonials are synthetic and labeled as such — keep it that way.
- Anything that must be visible to every visitor, not just the browser tab that
  wrote it, belongs in `app_views._shared_store()`, not `st.session_state`.
