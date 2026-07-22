# Step A — Aim

Per [AGENT-framework.md](AGENT-framework.md): define the outcome, not the steps. Nothing
gets built until the outcome fits in one sentence and the DoD is measurable.

## Why before how

I'm moving into a financial advisor role (Series 66 track). I want to demonstrate that I
can build AI software that does real advisory work — not that I can operate a chatbot.
The project has to survive two very different readers: a hiring manager who will skim it
in 90 seconds, and a compliance-minded advisor who will look for the places where an
AI-written client document could get a firm in trouble.

## Outcome (one sentence)

> Hand it a client's holdings and a target allocation, and it returns a client-ready risk
> report — the numbers computed deterministically, the explanation written in an
> advisor's voice, and every word checked against compliance language rules before it
> reaches the page.

## Definition of Done — Phase 1 (Portfolio Analyzer)

Done means: given a CSV of tickers and weights plus a target allocation, one command
produces a one-page HTML/PDF report containing allocation by asset class and sector,
concentration flags, annualized volatility, max drawdown, Sharpe ratio, beta and
correlation to the S&P 500, and drift vs. target with a rebalancing table — accompanied
by plain-English commentary that names the client's single biggest risk, contains no
prohibited language, and carries the required disclaimer.

## Definition of Done — Phase 2 (IPS / Suitability)

Done means: a questionnaire covering risk tolerance, time horizon, income needs, and tax
situation produces a documented risk profile, a recommended target allocation with the
reasoning shown, and a draft Investment Policy Statement — and that target allocation
feeds directly into Phase 1 as its input, so the two tools form one loop.

## The chain (why order matters)

Phase 2's output *is* Phase 1's input. Phase 1 asks "how far is this portfolio from
target?" — Phase 2 answers "what should target be, and why?" Building Phase 1 first means
Phase 2 has a real consumer waiting for it, and the seam between them is the story:
**suitability → allocation → analysis → client document.** That is the advisory workflow.

## The 3 R's check

| | Verdict |
|---|---|
| **Repetitive** | Yes — a portfolio review recurs per client, per quarter. |
| **Rules-based** | Yes for the math (fully deterministic); judgment-shaped for the narrative, which is exactly the part an LLM is good at. |
| **Return on time** | Yes — a review that takes an advisor 45 minutes of spreadsheet work becomes a 30-second command. |

Passes all three. Build it.

## The design decision that makes this project different

**The LLM never produces a number.**

Every figure in the report is computed in Python from price data and passed to the model
as fact. The model's only job is to explain figures it was handed. It cannot invent a
Sharpe ratio, round a drawdown in its favor, or hallucinate a holding.

This is the answer to the "lots of people build portfolio dashboards" weakness, and it is
also the honest answer to the compliance question an advisor will ask. It gets stated
plainly in the README, because the reasoning is the part worth hiring.

## Guardrails (Step T, decided up front)

- Generates **analysis and draft documents only** — it never places a trade, connects to
  a brokerage, or moves money.
- No performance predictions, no guarantees, no "will" about future returns.
- Rebalancing output is framed as *drift from a stated target*, never as a recommendation
  to buy or sell a security.
- Every generated document carries a disclaimer identifying it as educational output of a
  personal project, not investment advice from a registered representative.
- A separate compliance-review agent reads the narrative before it renders. If it flags,
  the report renders with the flag visible rather than silently passing.

## Non-goals

- Not a trading system. Not a robo-advisor. Not a live client tool.
- Not connected to real custodial or client data — ships with synthetic sample portfolios
  so anyone can clone and run it.
