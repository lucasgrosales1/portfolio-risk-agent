"""AI-written client commentary — the narrative-writing half of the agent pair.

Produces the same `Narrative` shape as `rule_based_narrative`, from the same
computed inputs, with one added step: every draft is reviewed by a second,
independent model (`agents.compliance`) before it comes back. The reviewer
gets nothing the writer didn't already have — the same fact sheet — so it can
catch a claim that doesn't trace back to a computed figure.

If anything here fails (missing key, API error, malformed output), the caller
(`pra.pipeline._make_narrative`) catches it and falls back to the deterministic
rule-based path. That fallback is why this is a separate module: an AI failure
must never be the reason a report doesn't render.
"""

from __future__ import annotations

import json

import anthropic

from ..analytics import AllocationResult, ConcentrationResult, RebalanceResult, RiskMetrics
from ..config import NARRATIVE_MODEL, anthropic_api_key
from ..models import EQUITY, FIXED_INCOME, ModelPortfolio
from ..portfolio import Portfolio
from .compliance import compliance_review
from .narrative import Narrative

_PARAGRAPHS_SCHEMA = {
    "type": "object",
    "properties": {
        "paragraphs": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Each element is one paragraph. A section heading is its own "
                "element, the heading text prefixed with '## ' (e.g. "
                "'## Risk profile')."
            ),
        }
    },
    "required": ["paragraphs"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """\
You are a client-communications writer for a fee-only fiduciary wealth \
advisory firm. You turn a portfolio review's computed figures into a short, \
plain-English narrative a client will actually read.

Hard rules, no exceptions:
- Every number you write must appear, verbatim or as a trivial reformat (e.g. \
0.273 written as "27.3%"), in the "Computed figures" block you are given. \
Never compute, estimate, round to a different precision than shown, or invent \
a figure that is not already there.
- Never predict future performance or state a return as certain ("will \
return", "is expected to grow"). Every figure describes the past or a \
current holding.
- Never recommend buying or selling a specific security. Frame rebalancing \
only as drift from the client's own stated target allocation.
- Never claim a strategy is "safe," "guaranteed," or risk-free.
- If a fact is not in the block, do not mention it — say nothing rather than \
guess.

Write like an advisor's written summary, not a metrics dump: lead with the \
single biggest issue, quantify it using only the given figures, then explain \
the trade-off in acting on it. Structure the output as: an opening paragraph \
describing the portfolio, a "## Primary observation" section, a "## Risk \
profile" section, and a "## Closing the gap" section. Plain text within each \
paragraph — no markdown besides the "## " section headings.
"""


def _fmt_pct(value: float, places: int = 1) -> str:
    return f"{value * 100:.{places}f}%"


def _fmt_usd(value: float) -> str:
    return f"${value:,.0f}"


def build_fact_sheet(
    portfolio: Portfolio,
    allocation: AllocationResult,
    risk: RiskMetrics,
    concentration: ConcentrationResult,
    plan: RebalanceResult,
    model: ModelPortfolio,
) -> str:
    """Every figure the narrative is allowed to reference, labeled and grouped.

    This is also what the compliance reviewer checks claims against — a number
    the writer invents has no matching line here for the reviewer to confirm.
    """
    weights = allocation.asset_class_weights()
    equity_weight = weights.get(EQUITY, 0.0)
    equity_target = model.target_for(EQUITY)
    fi_weight = weights.get(FIXED_INCOME, 0.0)
    fi_target = model.target_for(FIXED_INCOME)

    lines = [
        "PORTFOLIO",
        f"- Total value: {_fmt_usd(allocation.total_value)}",
        f"- Position count: {len(allocation.positions)}",
        f"- Target model: {model.name}",
    ]
    if portfolio.client_age is not None:
        lines.append(f"- Client age: {portfolio.client_age}")
    if portfolio.time_horizon_years is not None:
        lines.append(f"- Time horizon: {portfolio.time_horizon_years} years")

    lines += [
        "",
        "ALLOCATION",
        f"- Equity weight: {_fmt_pct(equity_weight)} (target {_fmt_pct(equity_target)})",
        f"- Fixed income weight: {_fmt_pct(fi_weight)} (target {_fmt_pct(fi_target)})",
    ]

    lines += [
        "",
        "CONCENTRATION",
        f"- Top five holdings: {_fmt_pct(concentration.top_five_weight)} of the portfolio",
        f"- Effective number of holdings: {concentration.effective_holdings:.1f}",
        f"- Position count: {concentration.position_count}",
    ]
    if concentration.headline is not None:
        h = concentration.headline
        lines.append(f"- Headline concentration flag ({h.category}, {h.severity}): {h.message}")
    else:
        lines.append("- No concentration flags triggered.")

    lines += [
        "",
        "RISK",
        f"- Annualized volatility: {_fmt_pct(risk.annualized_volatility)} "
        f"(benchmark {_fmt_pct(risk.benchmark_volatility)})",
        f"- Beta: {risk.beta:.2f}",
        f"- Correlation to benchmark: {risk.correlation:.2f}",
        f"- Sharpe ratio: {risk.sharpe_ratio:.2f}",
        f"- Risk-free rate used: {_fmt_pct(risk.risk_free_rate, 2)}",
        f"- Max drawdown: {_fmt_pct(risk.max_drawdown)}",
        f"- Lookback: {risk.trading_days} trading days ({risk.lookback_years:.1f} years)",
    ]

    lines += ["", "REBALANCING", f"- Needs rebalancing: {'yes' if plan.needs_rebalancing else 'no'}"]
    if plan.needs_rebalancing:
        lines += [
            f"- Total turnover: {_fmt_usd(plan.total_turnover)}",
            f"- Estimated tax cost: {_fmt_usd(plan.total_tax_cost)} "
            f"({_fmt_pct(plan.tax_cost_pct_of_turnover)} of turnover)",
            f"- Sourced tax-free (sheltered accounts): {_fmt_usd(plan.tax_free_proceeds)}",
            f"- Sourced from taxable accounts: {_fmt_usd(plan.taxable_proceeds)}",
            f"- Unrealized gain left deferred: {_fmt_usd(plan.unrealized_gain_deferred)}",
        ]

    return "\n".join(lines)


def ai_narrative(
    portfolio: Portfolio,
    allocation: AllocationResult,
    risk: RiskMetrics,
    concentration: ConcentrationResult,
    plan: RebalanceResult,
    model: ModelPortfolio,
) -> Narrative:
    """Write client commentary with Claude, then have a second model review it.

    Raises on any failure — the caller (`pra.pipeline._make_narrative`) catches
    every exception here and falls back to `rule_based_narrative`. This
    function does not swallow its own errors.
    """
    api_key = anthropic_api_key()
    if not api_key:
        raise RuntimeError("No ANTHROPIC_API_KEY configured.")

    fact_sheet = build_fact_sheet(portfolio, allocation, risk, concentration, plan, model)
    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model=NARRATIVE_MODEL,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        output_config={"format": {"type": "json_schema", "schema": _PARAGRAPHS_SCHEMA}},
        messages=[
            {
                "role": "user",
                "content": f"Computed figures:\n\n{fact_sheet}\n\nWrite the commentary.",
            }
        ],
    )
    text = next(b.text for b in response.content if b.type == "text")
    paragraphs = json.loads(text)["paragraphs"]
    if not paragraphs:
        raise ValueError("Narrative agent returned no paragraphs.")

    flags = compliance_review(paragraphs, fact_sheet)

    return Narrative(
        paragraphs=paragraphs,
        source="ai",
        compliance_flags=flags,
        model_used=NARRATIVE_MODEL,
    )
