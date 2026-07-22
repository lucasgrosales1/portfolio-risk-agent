# portfolio-risk-agent

Generates a client-ready portfolio risk report from a holdings file: allocation
against a target model, concentration analysis with fund look-through,
volatility, maximum drawdown, Sharpe ratio, beta, and a **tax-aware** rebalancing
plan that accounts for lot-level holding periods and account registration.

```bash
python -m pra.cli --portfolio data/sample_concentrated.csv --model balanced_growth --open
```

Output is a single self-contained HTML file, print-styled so `Ctrl+P → Save as PDF`
produces a document you could hand to a client.

---

## The design decision this project is built around

**The language model never produces a number.**

Every figure in the report is computed in Python from real price data. The
narrative agent receives those computed figures as fact and its only job is to
explain them. It cannot invent a Sharpe ratio, round a drawdown in a flattering
direction, or reference a holding that isn't there. A second agent then reviews
the narrative against the same figures and flags any claim that doesn't trace
back to one.

This is not a stylistic preference. A tool that generates client-facing
investment commentary is a tool where a hallucinated number is a serious
problem, and "the model is usually accurate" is not an acceptable control. The
architecture removes the failure mode rather than mitigating it.

```
  price data ──▶ analytics/ ──▶ computed metrics ─┬──▶ narrative agent ──▶ compliance agent ──▶ report
                (pure Python)                     │       (explains)          (verifies)
                                                  └──────────────────────────────────────────▶ report
                                                       numbers pass through untouched
```

---

## What it actually catches

Two synthetic portfolios ship with the repo. Run both and the contrast is the point:

|                              | Concentrated employer stock | Pre-retiree, over-allocated |
| ---------------------------- | --------------------------: | --------------------------: |
| Portfolio value              |                  $1,388,867 |                  $1,787,503 |
| Equity weight vs. target     |             91.4% vs. 60.0% |             96.6% vs. 40.0% |
| Annualized volatility        |        27.3% (S&P: 15.0%)   |        15.6% (S&P: 15.0%)   |
| Rebalancing turnover         |                    $436,587 |                  $1,011,045 |
| **Estimated tax cost**       |     **$56,176 — 12.9%**     |      **$10,322 — 1.0%**     |

Margaret's rebalance is more than twice the size of Jordan's and costs a fifth
as much, because 84% of hers can be sourced from a traditional IRA where a sale
triggers no tax. That distinction is invisible to any tool that models a
portfolio as tickers and weights.

Other things the analytics surface that a spreadsheet typically misses:

- **Look-through concentration.** A client holding NVDA directly *and* holding
  VOO, VTI, and QQQ has ~50.0% true exposure, not the 47.0% their statement
  shows. Exposure is accumulated across every fund before being flagged.
- **Effective number of holdings.** The inverse Herfindahl index — a portfolio
  of 8 positions with one at 47% carries the diversification of about 3.3
  equally-weighted positions.
- **Short-term vs. long-term lots.** Sales are sourced cheapest-first: sheltered
  accounts, then losses, then long-term gains, then short-term.

---

## Quick start

```bash
git clone https://github.com/lucasgrosales1/portfolio-risk-agent.git
cd portfolio-risk-agent

python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows;  source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt

python -m pra.cli --portfolio data/sample_concentrated.csv --model balanced_growth --open
```

**No API key required.** Without one the report renders with rule-based
commentary and every number is identical — the key only changes who writes the
prose. To enable the AI narrative, copy `.env.example` to `.env` and add a key
from [console.anthropic.com](https://console.anthropic.com). Cost is roughly two
cents per report.

### Portfolio file format

One row per **tax lot**, not per ticker — the same holding bought on three dates
is three rows, which is how a cost-basis report actually arrives.

```csv
# client_name: Jordan Reyes
# client_age: 41
# time_horizon_years: 22
ticker,shares,cost_basis_per_share,acquisition_date,account_type,is_employer_stock
NVDA,1800,14.85,2019-04-15,taxable,true
VOO,410,398.00,2021-09-08,taxable,false
BND,850,85.20,2021-03-12,traditional,false
CASH,28000,1.00,2024-01-02,taxable,false
```

`account_type` is `taxable`, `traditional`, or `roth`. `acquisition_date` and
`account_type` are what make tax-aware rebalancing possible: the first
determines long- versus short-term treatment, the second determines whether a
sale is taxable at all.

### Target models

`conservative` · `moderate` · `balanced_growth` · `aggressive`

Illustrative teaching defaults with documented equity/fixed-income/cash splits,
not a house view. Phase 2 selects among them from a suitability questionnaire.

---

## How the metrics are computed

Written longhand rather than pulled from a library, because being able to
explain the arithmetic is part of the point.

| Metric | Method |
| --- | --- |
| Annualized volatility | Standard deviation of daily returns × √252 |
| Maximum drawdown | Worst peak-to-trough decline of the cumulative return series, with peak and trough dates |
| Sharpe ratio | Mean excess return ÷ standard deviation × √252, using the live 13-week T-bill as the risk-free rate |
| Beta | Covariance with the S&P 500 ÷ variance of the S&P 500 |
| Effective holdings | 1 ÷ Σ(wᵢ²) — the inverse Herfindahl index |
| Tax cost | Per-lot: long-term at 15%, short-term at 32%, zero in sheltered accounts |

**Return series assumption:** risk statistics apply the portfolio's *current*
weights across the full lookback window, rebalanced daily. This describes how
the present allocation would have behaved — not the account's realized
performance, which would require transaction history the tool doesn't have. The
report states this in its methodology footnote.

---

## Limitations

Stated plainly, because a tool that hides its assumptions is worse than one that
doesn't have many.

- **Mutual funds are out of scope.** yfinance exposes sector weights, top
  holdings, and expense ratios for ETFs; the equivalent data for mutual funds is
  largely absent. Rather than fake it, the tool covers stocks, ETFs, and cash.
- **Tax figures are planning estimates.** Assumed federal rates only — no state
  tax, no net investment income tax, no bracket detail, no wash-sale tracking.
- **Not a performance report.** See the return-series assumption above.
- **Free market data.** Yahoo Finance via yfinance is reliable for prices;
  metadata coverage is uneven. Missing fields are omitted from the report rather
  than guessed at.
- **Analysis only.** The tool never places a trade, connects to a brokerage, or
  moves money.

---

## Roadmap

- [x] Deterministic analytics core
- [x] HTML report with print styling
- [x] Rule-based narrative (no-API-key path)
- [ ] Narrative agent + compliance-review agent
- [ ] Phase 2 — Investment Policy Statement / suitability questionnaire, feeding
      its recommended allocation back in as this tool's target model, closing the
      loop: **suitability → allocation → analysis → client document**

---

## Disclaimer

This is a personal educational software project. It is not investment advice,
not a recommendation to buy or sell any security, and not a solicitation. It was
not prepared by a registered investment adviser or broker-dealer acting in that
capacity. All portfolio data in this repository is synthetic. Consult a
qualified adviser and tax professional before acting on any information produced
by this tool.
