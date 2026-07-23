# Phase 2 spec — suitability engine + structured products

Locked in the interview on 2026-07-22. This is the contract for Phase 2. If we
deviate, we change this file first.

Phase 2 turns the tool into a two-mode suite and closes the loop that Phase 1
left open:

    suitability -> allocation -> analysis -> client document

## Mode selector (top of page)

The Streamlit app opens with a choice between two modes:

1. **Analyze an existing portfolio** — the Phase 1 flow (holdings in, risk
   report out), moved behind a web UI.
2. **Build a plan for a new client** — the Phase 2 flow below.

Working name for the suite: **Advisor Workbench** (final name TBD).

## Decisions

| Question | Decision |
|---|---|
| Delivery | Streamlit web app, deployable to Streamlit Community Cloud for a live link |
| Audience | An advisor's tool — fiduciary / best-interest framing |
| Risk profiling | Scored questionnaire, with hard capacity rules that override the score |
| Allocation | Pick nearest of the four models, then apply documented tilts |
| Product families | Income/autocallable notes, buffered growth notes, defined-outcome/buffered ETFs, principal-protected notes |
| Income-note trigger | **All four** gates required (conjunctive) |
| Buffer approach | Prefer buffered ETFs; buffered notes only when specifically warranted |
| Payoff modeling | Model illustrative payoffs in Python; show a payoff diagram |
| Sleeve cap | Hard ceiling ~15% of portfolio, scaled down for smaller/less-liquid portfolios |
| Non-fit handling | Report states products were considered and explains why declined |
| IPS contents | Objectives/horizon/risk; allocation + rebalancing policy; constraints/liquidity/taxes; structured-product policy statement |
| Build order | Suitability engine first, structured products after |

## Suitability intake

Captures the factors a Series 66 / Reg BI suitability analysis actually turns on
— not just a risk slider. At minimum:

- Age, dependents
- Time horizon (years until funds are needed)
- Employment / income source, annual income
- Net worth, **liquid** net worth
- Marginal tax bracket
- Existing holdings / concentrations to unwind
- Liquidity needs and any near-term planned withdrawals
- Emergency-reserve adequacy
- Investment experience / sophistication
- Investment objective (growth / income / preservation)
- Stated risk tolerance
- Drawdown tolerance

## Risk profiling — score with capacity overrides

The questionnaire produces a numeric **risk score** mapped to a profile, but
hard rules can override it downward. **Capacity constrains tolerance** — a
client's situation can veto a risk level their stated tolerance would allow.

Override examples (final rule set to be built with the client's Series 66 input):

- Time horizon ≤ 5 years caps equity regardless of a high tolerance answer.
- A stated income need with imminent withdrawals pushes the profile toward income/preservation.
- Inadequate emergency reserve or thin liquid net worth caps risk until that's addressed.

The report shows the score, the mapped profile, **and any override that fired**,
with its reason — so the reasoning is visible, not a black box.

## Allocation — nearest model, then tilt

1. Map the profile to the nearest of the four existing models
   (Conservative / Moderate / Balanced Growth / Aggressive).
2. Apply documented tilts for client specifics (e.g. a high income need tilts
   toward income-producing fixed income; a large embedded-gain concentration
   tilts the unwind pace).
3. Feed the result into the Phase 1 analysis as its target allocation, so drift,
   risk, and rebalancing all run against the *recommended* allocation.

## Structured products

### The core principle

The tool models what these products actually are — capped upside, a downside
buffer or barrier, issuer credit risk, illiquidity, a defined term — and never
presents them as free protection or guaranteed income. It recommends them only
when the profile genuinely warrants it, and **documents the decision either way.**

### Product families in scope

| Family | What it is | Primary use |
|---|---|---|
| Income / autocallable notes | Contingent coupons while an underlying holds above a barrier; may auto-redeem early | Supplemental income |
| Buffered growth notes | Capped upside participation + downside buffer, single-issuer | Growth with downside cushion, defined term |
| Defined-outcome / buffered ETFs | Exchange-traded buffer: capped upside + buffer, liquid, no single-issuer credit risk | **Default** for a buffer need |
| Principal-protected notes | Near-full principal at maturity + limited upside | Very low market-risk tolerance, accepts opportunity cost |

### Income-note trigger — all four gates required

An income note is recommended only when **every** condition holds:

1. Stated income need (pre-retiree / retiree drawing down).
2. Adequate liquid net worth to lock up a sleeve for the term (hard gate).
3. Moderate risk tolerance — not conservative (can accept barrier risk).
4. Investment experience / sophistication (understands the product).

Any one failing → no income note, and the report names the failing gate.

### Buffer need — prefer the ETF

For a client who wants growth but can't stomach a large drawdown, default to a
**defined-outcome / buffered ETF** (liquid, no single-issuer credit risk). Reach
for a buffered *note* only when there's a specific reason the note structure
serves better (e.g. a defined term the client wants to lock).

### Payoff modeling — deterministic, illustrative

Payoff scenarios are computed in Python from **clearly-stated assumed terms**
(e.g. 10% buffer, 9% cap, 8% contingent coupon at a 70% barrier), with a payoff
diagram. Terms are illustrative and labeled as such — the tool is not quoting a
real issued note. This preserves the project's governing rule: the LLM never
produces a number; it explains the scenarios Python computed.

### Sleeve sizing

Structured products are a satellite sleeve, never the core. Hard ceiling around
**15%** of the portfolio, scaled down further for smaller or less-liquid
portfolios. The tool never exceeds it.

### When the profile doesn't fit

The report explicitly states that structured products were **evaluated and
declined**, naming the failing factor. The "when not to" logic is visible —
that is the strongest signal of judgment in this whole feature.

## The IPS document

A draft Investment Policy Statement containing:

- Objectives, time horizon, and the documented risk profile (with reasoning)
- Target allocation and rebalancing policy (drift tolerances, when/how to rebalance)
- Constraints, liquidity needs, and tax considerations
- A **structured-product policy statement** — whether and how they fit this
  client, including an explicit decision to exclude them

## Architecture — unchanged governing rules

- **The LLM never produces a number.** Risk scoring, allocation tilts, and all
  payoff modeling are deterministic Python. The AI drafts prose (IPS narrative,
  recommendation rationale) constrained to those computed outputs.
- **Compliance-review agent** reviews every recommendation. Structured-product
  language gets extra scrutiny given the regulatory weight of the category.
- **Educational disclaimer** on every document. All data synthetic. No trades,
  no brokerage, no money movement.

## Build order

1. **Suitability engine** — intake → risk scoring with overrides → allocation
   recommendation → IPS draft → wire into Phase 1 so the full loop runs.
2. **Streamlit shell** — mode selector + forms around the working logic.
3. **Structured-product layer** — suitability gates, ETF-first buffer logic,
   Python payoff modeling + diagram, sleeve sizing, decline-with-reason output.
4. **Deploy** to Streamlit Community Cloud for the live link.

## Open items to resolve with the client's Series 66 input

- The exact questionnaire items and their scoring weights.
- The precise capacity-override rule set (the thresholds).
- The tilt rules that adjust a base model for client specifics.
- Illustrative default terms for each product family in the payoff model.
