# Project spec — portfolio-risk-agent

Locked in the interview on 2026-07-21. This is the contract; if we deviate later, we
change this file first.

## Context (the user file, in draft)

- Licensed, actively job hunting. The project is an interview differentiator.
- Targeting **RIA / fiduciary** firms — the tool may speak in best-interest terms and take
  a whole-portfolio view. No firm compliance department to clear yet.
- Series 66 mindset is the through-line: suitability, time horizon, concentration,
  diversification, fiduciary duty.
- Wants to understand the code well enough to defend it in an interview, not just run it.
- Resume-first: public repo, synthetic data, sharp demo. Real-portfolio use comes later.

## Decisions

| Question | Decision |
|---|---|
| Name | `portfolio-risk-agent` |
| Asset universe | Stocks, ETFs, cash positions — **no mutual funds** |
| Portfolio input | Ticker + shares + cost basis + acquisition date |
| Report output | Single HTML file, print-styled so it exports to a clean PDF |
| Target allocation | Four built-in model portfolios |
| No API key | Falls back to rule-based narrative; report still renders |
| Demo scenarios | Concentrated stock risk; pre-retiree too aggressive |
| Pace | Fast — long sessions, big chunks |

**Note on acquisition date:** cost basis alone can't tell you whether a gain is long- or
short-term, and that distinction is the whole point of tax-aware rebalancing. So the input
schema carries a purchase date per lot. This is a detail that will read as genuinely
advisor-brained to anyone who knows the business.

## Phase 1 — Portfolio Analyzer

### Input

`data/*.csv` — one row per position:

```
ticker,shares,cost_basis_per_share,acquisition_date,account_type
```

`account_type` (taxable / traditional / roth) matters because tax-aware rebalancing should
say "trim this in the IRA where it costs nothing" — which is the actual advisor move.

### Computed metrics — all deterministic Python, no LLM

**Allocation**
- By asset class (equity / fixed income / cash / other), derived from holding type
- By sector, look-through where available
- By geography (US / international) where derivable

**Concentration**
- Any single position > 10% of portfolio
- Top-5 positions as % of portfolio
- Any sector > 25%
- Employer-stock flag when a position is marked as such

**Risk**
- Annualized volatility — daily return stdev × √252
- Maximum drawdown over the lookback window
- Sharpe ratio — risk-free rate from the 13-week T-bill, with a configurable constant fallback
- Beta and correlation vs. the S&P 500

**Cost**
- Weighted-average expense ratio across ETF holdings
- Overlap detection — the same underlying held through multiple ETFs, or held directly
  *and* inside an ETF (the concentrated-stock case, where employer stock also sits in the
  S&P 500 fund)

**Data note:** mutual funds are deliberately out of scope. yfinance exposes `funds_data`
for ETFs — sector weightings, top holdings, expense ratio — which makes look-through and
overlap detection possible. The equivalent data for mutual funds is largely absent, and
faking it with a hand-maintained file would be a maintenance burden that adds nothing to
the demo. The README states the limitation rather than hiding it. Any ETF field that
comes back missing degrades gracefully: the report omits that line instead of guessing.

**Rebalancing**
- Drift per asset class vs. the selected model portfolio
- Trade list to close the gap
- **Tax impact per suggested trade**: embedded gain, long vs. short term based on
  acquisition date, and whether the position sits in a sheltered account

### Output

One self-contained HTML file: summary header, allocation vs. target, concentration flags,
risk metrics, rebalancing table with tax column, narrative commentary, disclaimer.

Print CSS so `Ctrl+P → Save as PDF` produces something you'd hand a client.

## Model portfolios

Illustrative and documented as such — equity / fixed income / cash:

| Model | Equity | Fixed income | Cash |
|---|---|---|---|
| Conservative | 20% | 70% | 10% |
| Moderate | 40% | 55% | 5% |
| Balanced Growth | 60% | 35% | 5% |
| Aggressive | 85% | 13% | 2% |

These are teaching defaults, not a house view. The README says so plainly.

## Demo scenarios

**1. Concentrated stock risk.** Software engineer, age 41, ~$850k portfolio with roughly
45% in employer stock carrying a large long-term embedded gain, held in a taxable account.
Target: Balanced Growth. Exercises concentration flags, beta distortion, and the central
tension of tax-aware rebalancing — the right move costs money, and the report has to say
that honestly rather than pretending trimming is free.

**2. Pre-retiree, too aggressive.** Age 62, ~$1.2M, roughly 90% equities, needs income in
three years, mixed taxable and IRA. Target: Moderate. Exercises drawdown risk against a
short horizon, sequence-of-returns concern, and the "trim inside the IRA where there's no
tax drag" insight.

## Architecture

**The LLM never produces a number.** Every figure is computed in Python and handed to the
model as fact. The model explains figures it was given and nothing else.

| Layer | Model | Job |
|---|---|---|
| `data/` | none | Fetch and validate prices via yfinance, cache to disk |
| `analytics/` | none | All math above — pure functions, unit tested |
| Narrative agent | Sonnet | Client-facing commentary from computed metrics only |
| Compliance agent | Haiku | Separate agent; reviews narrative for prohibited language |
| `report/` | none | Render HTML from metrics + approved narrative |

Narrative and compliance are **separate agents with separate system prompts** — the
video's "one agent writes, a different agent reviews" pattern. If compliance flags the
narrative, the report renders with the flag visible rather than silently passing.

### Compliance agent's rules

Rejects: performance guarantees, predictions phrased as certainty ("will return"),
anything resembling a personalized recommendation to buy or sell a specific security,
absolute claims about safety, and any figure not present in the computed metrics it was
given. That last check is the hallucination backstop.

## Repo layout

```
portfolio-risk-agent/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── docs/
├── data/
│   ├── sample_concentrated.csv
│   └── sample_preretiree.csv
├── src/pra/
│   ├── config.py
│   ├── portfolio.py          # Holding / Portfolio types, CSV loading
│   ├── prices.py             # yfinance + cache
│   ├── analytics/
│   │   ├── allocation.py
│   │   ├── risk.py
│   │   ├── concentration.py
│   │   └── rebalance.py
│   ├── models.py             # the four model portfolios
│   ├── agents/
│   │   ├── narrative.py
│   │   └── compliance.py
│   ├── report/
│   │   ├── render.py
│   │   └── template.html
│   └── cli.py
└── tests/
```

## Guardrails (Step T)

- Analysis and draft documents only. Never trades, never connects to a brokerage, never
  moves money.
- No performance predictions, no guarantees.
- Rebalancing framed as *drift from a stated target*, never as a recommendation on a
  specific security.
- Every report carries a disclaimer: educational output of a personal project, not
  investment advice.
- Synthetic data only in the repo. Real portfolios, if ever used, stay local and
  gitignored.

## Out of scope

Not a trading system. Not a robo-advisor. No live client data. No Monte Carlo retirement
projection in Phase 1 — that's a tempting scope creep and it waits.

## Phase 2 — IPS / Suitability (after Phase 1 ships)

Questionnaire covering risk tolerance, time horizon, income needs, and tax situation →
documented risk profile → recommended model portfolio with reasoning shown → draft
Investment Policy Statement. Its output feeds Phase 1's target allocation, closing the
loop: **suitability → allocation → analysis → client document.**

Streamlit front end, deployed to Streamlit Community Cloud for a live shareable link.
