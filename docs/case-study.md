# Case study: the design decisions behind WealthSync Advisors

This is the "why," not the "what" — the code and the README cover what the
tool does. This is for a reader who wants to know why it works this way,
written the way I'd defend these choices in a design review.

## 1. The LLM never produces a number

The thesis on the homepage — "100% figures computed, 0 numbers guessed" —
isn't marketing copy, it's a constraint on the code. `src/pra/analytics/` and
`src/pra/suitability/` are pure Python: every metric is computed with
longhand arithmetic (no black-box library calls) from a portfolio's holdings
or a client's survey answers. Nothing downstream of that layer can produce a
number that doesn't already exist as a typed field on a dataclass.

The narrative agent (`agents/ai.py`) is handed a **fact sheet** —
`build_fact_sheet()` walks the same computed objects (`AllocationResult`,
`RiskMetrics`, `ConcentrationResult`, `RebalanceResult`) and renders every
figure it's allowed to reference as a labeled line: `"Beta: 0.99"`,
`"Sharpe ratio: 1.06"`, `"Estimated tax cost: $6,561 (5.8% of turnover)"`. The
system prompt is explicit that every number in the output must appear on that
sheet, verbatim or as a trivial reformat, and that the model should say
nothing rather than guess at a fact that isn't there. The model's job is
strictly framing and emphasis — which figure is the headline, how the
trade-off reads — never arithmetic.

This is enforced with **structured outputs**
(`output_config.format` → a JSON schema), not a hope that the model follows
instructions in free text. The narrative agent can only return `{paragraphs:
[...]}`; there's no code path where it returns something else that then gets
parsed loosely.

## 2. Why two separate model calls, not one

The obvious simpler design is one model call with a system prompt that says
"write this, and don't make anything up." I didn't build that, for the same
reason a compliance department doesn't let an advisor self-certify their own
client letters: **a model checking its own output shares the same blind
spots that produced the output.** If Sonnet's system prompt has a gap that
lets a hallucinated figure through, asking the same context to re-read its
own answer doesn't reliably catch it — it already believes the sentence.

So `agents/compliance.py` is a genuinely separate call: its own system
prompt, a cheaper model (Haiku — the task is narrow and rule-checkable, so it
doesn't need Sonnet's capability), and it receives the draft the same way an
outside reviewer would — the fact sheet plus the paragraphs, nothing else.
It checks four things: every number traces to the fact sheet, nothing is
phrased as a performance guarantee, nothing reads as a specific buy/sell
recommendation, nothing claims a strategy is risk-free. It returns
`{approved, flags}` — structured, so there's no ambiguity about whether a
partial pass counts as a pass.

The part I'd defend hardest: **when compliance flags something, the report
still ships — with the flag attached.** The alternative (silently discard
the AI draft and fall back to rule-based) is safer-looking but worse in
practice, because it hides the failure instead of surfacing it. A flagged
report tells the advisor exactly what to check before it goes to a client.
A silently-substituted report tells them nothing went wrong, which isn't
true.

Either agent failing at all — API error, malformed output, missing key —
falls back to `rule_based_narrative()`, the deterministic path, with no
retry logic and no partial output. `pra.pipeline._make_narrative()` wraps
the whole AI path in one `except Exception: pass`. An AI failure is not
allowed to be the reason a report doesn't render.

## 3. Capacity-first suitability: why the cap only moves one direction

`suitability/scoring.py` produces a **score** — a blended 0–100 number from
stated risk tolerance, objective, drawdown appetite, time horizon, and
financial cushion — that maps to one of four model portfolios. Read in
isolation, this is what most robo-advisor questionnaires stop at: an
attitude score.

`suitability/capacity.py` computes something different: the maximum equity
fraction the client's *situation* can bear, as the minimum across six
independent constraints — drawdown tolerance translated through an assumed
severe-bear equity loss, time horizon, withdrawal-rate sustainability,
whether an emergency reserve exists, objective, and age/sequence risk.

`suitability/recommend.py` reconciles them with one rule: **the final
recommendation is the desired model, capped at the capacity ceiling — never
raised by it.** A client who scores as aggressive but has no emergency
reserve gets capped to whatever equity fraction a 30% ceiling allows, full
stop. A client with generous capacity but a conservative stated score is
*not* pushed toward more risk than they said they wanted. Capacity is a
one-directional brake, not a second vote.

The reason this is the load-bearing design decision in the whole suitability
engine: a score-only system will recommend "aggressive" to someone who says
they can tolerate a 40% drawdown, even if they have a five-year horizon and
no cash reserve — technically following their stated preference straight
into a plan that can't survive contact with a bad year. Capacity is what a
human advisor is actually accountable for catching, and it's exactly the
kind of judgment that's easy to skip when a tool just averages a
questionnaire.

Every threshold this reconciliation depends on is a named constant at the
top of `capacity.py` (`SEVERE_BEAR_EQUITY_LOSS = 0.50`,
`NO_RESERVE_EQUITY_CAP = 0.30`, `LATE_RETIREMENT_AGE = 72`, ...) —
deliberately, because these are exactly the numbers a licensed reviewer
should be able to disagree with and adjust, not something buried in
conditional logic.

## 4. Tax-aware rebalancing: the trade-off a naive rebalancer can't see

`analytics/rebalance.py` doesn't just say "you're 18% overweight equity,
sell $150,000." It sources the sale lot-by-lot, cheapest first: sheltered
accounts (no tax at all), then lots at a loss (offset other gains), then
long-term gains, then short-term gains — because those four categories are
taxed completely differently, and a naive rebalancer that ignores the
distinction gives advice that's directionally right and dollar-wrong.

The two sample portfolios in the repo exist specifically to make this
visible: Margaret's rebalance is more than twice the dollar size of Jordan's
and costs a fifth as much, because 84% of hers can be sourced from a
traditional IRA. Run both and the tax-cost column tells the real story that
a percentage-drift number alone hides.

## 5. The stress test proves its point without Monte Carlo

`suitability/stress.py` runs three fixed return paths over a client's
retirement horizon — steady, an early bear market, and a late bear market —
where **Early and Late use the exact same annual returns, just reversed.** A
retiree who withdraws a fixed (inflation-adjusted) amount every year gets a
completely different outcome depending only on *when* the downturn lands,
even though the average return across the two paths is identical.

I picked this over a Monte Carlo simulation for the sequence-of-returns
concept specifically because it's deterministic and legible: with a real
example in the test suite (age 90, a 60/40 allocation, a $110,000 withdrawal
against a $1M start), the early-bear path depletes the portfolio in year 9
of 10, and the late-bear path — identical returns, reversed order — ends the
same horizon with $123,490 still standing. No randomness to explain away;
the entire point is legible in one side-by-side number. (Monte Carlo still
exists separately, in `suitability/montecarlo.py`, for ranking accumulation
strategies by probability of hitting a goal — a different question that
does need many paths.)

## 6. Structured products: the value is in what gets declined

`suitability/structured.py` evaluates four structured-product categories
against a client's profile, and the design goal was restraint, not coverage:
an income note is recommended only if **all four** gates pass — income need,
liquidity, risk tolerance, sophistication — and if any one fails, the report
says which one, by name, rather than a generic "not suitable."

This is the opposite of what most product-recommendation logic optimizes
for. The interesting behavior isn't "here's a product," it's "here's why
this client shouldn't get this product" — because structured products are
the most-scrutinized category in the industry precisely because they get
sold to people whose profile doesn't support them. A tool that only ever
says yes isn't doing suitability analysis; it's doing sales enablement.

---

## What I'd build next

The honest backlog is in [`docs/context.md`](context.md). The two I'd call
out: a fetch timeout on the live yfinance call (the cache is ephemeral on
Streamlit Cloud, so a cold load has no guardrail today), and finishing the
visual pass so the downloadable report/IPS match the app's own design system
instead of carrying their own older CSS.
