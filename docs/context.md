# Project context — where WealthSync stands

A one-read catch-up for a fresh session (or a returning human). Written 2026-07-26.
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
- `app_ui.py` — design system: `inject_theme()` (all CSS), branding, `top_nav()`,
  and component helpers (`card`, `section_header`, `subhead`, `trust_strip`,
  `disclosures_footer`, `icon`, `coastal_svg`, `advisor_photo_html`).
- `app_views.py` — the 5 page views (`home`, `dashboard`, `portfolio_analysis`,
  `client_survey`, `settings`) + render helpers. ~1,380 lines (a monolith).
- `src/pra/` — the real engine, UI-independent:
  - `analytics/` (allocation, concentration, rebalance, risk),
  - `suitability/` (profile, scoring, capacity, recommend, retirement, stress,
    structured, strategy, montecarlo, ips),
  - `prices.py` (yfinance + on-disk pickle cache), `pipeline.py`, `report/render.py`,
    `agents/narrative.py`.
- `assets/` — `hero.jpg` (Miami Beach, Pexels/emma, licensed), `advisor.jpg`.
- `data/` — synthetic sample portfolios (client_*.csv, sample_concentrated.csv).

## Current visual identity — "The Ledger"
Warm printed-paper (`#F7F4EF`) + marine ink (`#0E6F73`) + one gold signal (`#C08A2D`).
Bricolage Grotesque display + Inter body + IBM Plex Mono for every number/label/eyebrow.
Signature = mono metrics on a marine ledger underline, `// ` gold-slash eyebrows, the
hero "100% computed / 0 guessed" strip. Full rules in `CLAUDE.md`.

## State: done vs. not
**Done:** all 5 pages build and render; The Ledger redesign applied app-wide;
licensed hero + real headshot; sample clients produce holdings analysis + suitability;
structured-note analysis replaces Monte Carlo in the recommendation view; an 80-test
`pytest` suite (`tests/`) with known-value coverage of `analytics/*` and
`suitability/*` plus AppTest smoke checks for all 5 pages — fully offline/deterministic,
see `tests/conftest.py`.

**Not done / unverified — read the critical backlog below before trusting anything.**

---

## Critical backlog (honest, prioritized)

### P0 — blocking a credible "finished" claim
1. ~~**Zero automated tests.**~~ **Done.** `tests/` now has known-value assertions for
   Sharpe, beta, volatility, max drawdown, allocation, concentration, rebalance,
   scoring, capacity reconciliation, retirement, stress (early-vs-late bear),
   structured-product gating, and the seeded Monte Carlo, plus an AppTest smoke check
   per page. Run with `.venv/Scripts/python.exe -m pytest` (needs `requirements-dev.txt`).
2. **Not pushed, not deployed.** 11 commits sit local-only; the app isn't live.
   A portfolio piece nobody can open is half-built. Action: push via GitHub Desktop,
   then deploy on share.streamlit.io (`streamlit_app.py`, branch `main`).
3. **yfinance is a live dependency with no guardrail on cold Cloud loads.** The cache
   is a local pickle in `.cache/` — ephemeral on Streamlit Cloud, so first load after
   any restart fetches live prices. There's fallback for a *corrupt* cache but no
   timeout/retry on the fetch itself. An employer's first click could hang or error.
   Action: add a fetch timeout + graceful degradation, and/or ship a static price
   snapshot for the demo so it never depends on a live call.

### P1 — quality gaps that undercut the redesign
4. **Two of five pages were never eyeballed after the redesign.** Portfolio Analysis
   and Client Survey were only checked for "renders without error." Unverified:
   the risk-triangle SVG colors, the survey section banners, and especially the
   **structured payoff line-charts** — `st.line_chart`/`st.bar_chart` use Streamlit's
   default look, which does **not** match The Ledger and likely clashes on paper.
5. **Downloadable Report + IPS don't match the site.** `report/render.py` and
   `suitability/ips.py` emit self-contained HTML with their *own* CSS/fonts — still the
   old look. The client-facing deliverables read as a different brand than the app.
6. **Streamlit dataframes/charts aren't themed.** Data-heavy views (holdings tables,
   drift tables, payoff charts) carry Streamlit defaults, so the mono/paper/marine
   identity partly breaks exactly where the "real numbers" story should be strongest.
7. **`requirements.txt` is unpinned (`>=`).** A future pandas/numpy/streamlit release
   can break the deploy with no warning. Pin known-good versions before/at deploy.

### P2 — polish / maintainability
8. **Mobile + accessibility unaudited.** Media queries exist but weren't tested at
   phone width; contrast of `ink-soft #5A6169` on paper and 11px mono labels isn't
   checked against WCAG AA.
9. **`app_views.py` is a 1,380-line monolith** — fine now, friction later; consider
   splitting per page.
10. **Emoji in dashboard subheads** (⏱️ 📋 📅) are the one off-note vs. the mono/ledger
    aesthetic; swap for the line-icon set or drop them.
11. **README for employers.** A `README.md` exists but should lead with the thesis and
    embed 2–3 screenshots — it's the first thing a reviewer opens.

## How to run / preview / deploy
- Run: `.venv/Scripts/streamlit run streamlit_app.py` → http://localhost:8501
- Restart after editing `app_ui.py`/`app_views.py` (imported modules don't hot-reload).
- Deploy: see `06-deploy.md`. Repo is public at
  `github.com/lucasgrosales1/portfolio-risk-agent`.

## Conventions
- Keep the "LLM never produces a number" rule: numbers come from `src/pra`, prose from
  `agents/narrative.py`. Don't let the UI invent figures.
- Reuse `app_ui.py` tokens/components; follow `CLAUDE.md`.
- Sample data and testimonials are synthetic and labeled as such — keep it that way.
