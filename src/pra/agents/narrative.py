"""Client-facing commentary.

Two paths produce the same `Narrative` object:

  rule_based_narrative()  Deterministic prose assembled from the computed
                          metrics. Always available, no API key, no cost.
  ai_narrative()          The Sonnet agent (added in the agent layer).

Both are constrained to figures computed elsewhere. Neither invents a number.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html import escape

from ..analytics import AllocationResult, ConcentrationResult, RebalanceResult, RiskMetrics
from ..models import EQUITY, FIXED_INCOME, ModelPortfolio
from ..portfolio import Portfolio


@dataclass
class Narrative:
    """Commentary plus its provenance."""

    paragraphs: list[str]
    source: str = "rule_based"          # "rule_based" | "ai"
    compliance_flags: list[str] = field(default_factory=list)
    model_used: str | None = None

    @property
    def html(self) -> str:
        """Render to HTML. Escaped — narrative text is never trusted as markup."""
        out = []
        for para in self.paragraphs:
            text = para.strip()
            if not text:
                continue
            if text.startswith("## "):
                out.append(f"<h3>{escape(text[3:].strip())}</h3>")
            else:
                out.append(f"<p>{escape(text)}</p>")
        return "\n".join(out)

    @property
    def plain_text(self) -> str:
        return "\n\n".join(p for p in self.paragraphs if p.strip())


def _usd(value: float) -> str:
    return f"${value:,.0f}"


def _pct(value: float, places: int = 1) -> str:
    return f"{value * 100:.{places}f}%"


def rule_based_narrative(
    portfolio: Portfolio,
    allocation: AllocationResult,
    risk: RiskMetrics,
    concentration: ConcentrationResult,
    plan: RebalanceResult,
    model: ModelPortfolio,
) -> Narrative:
    """Assemble commentary from the computed figures.

    Written to read like an advisor's summary rather than a metric dump: lead
    with the single biggest issue, quantify it, then explain the trade-off in
    acting on it.
    """
    paras: list[str] = []
    weights = allocation.asset_class_weights()
    equity_weight = weights.get(EQUITY, 0.0)
    equity_target = model.target_for(EQUITY)

    # --- Opening: what this portfolio is ---------------------------------
    opening = (
        f"This review covers a {_usd(allocation.total_value)} portfolio held across "
        f"{len(allocation.positions)} positions, measured against a "
        f"{model.name} target allocation."
    )
    if portfolio.client_age and portfolio.time_horizon_years:
        opening += (
            f" The stated time horizon is {portfolio.time_horizon_years} years."
        )
    paras.append(opening)

    # --- The headline issue ----------------------------------------------
    paras.append("## Primary observation")

    headline = concentration.headline
    equity_gap = equity_weight - equity_target

    # A short horizon paired with heavy equity outranks concentration, because
    # it is the issue with a deadline attached.
    short_horizon = (
        portfolio.time_horizon_years is not None
        and portfolio.time_horizon_years <= 5
        and equity_gap >= 0.10
    )

    if short_horizon:
        drawdown_dollars = abs(risk.max_drawdown) * allocation.total_value
        paras.append(
            f"The portfolio holds {_pct(equity_weight)} in equities against a "
            f"{_pct(equity_target)} target, a gap of "
            f"{_pct(abs(equity_gap))} with only {portfolio.time_horizon_years} years "
            f"before the funds are needed. Over the past "
            f"{risk.lookback_years:.1f} years this allocation experienced a maximum "
            f"decline of {_pct(abs(risk.max_drawdown))} from peak to trough — "
            f"approximately {_usd(drawdown_dollars)} at the current balance. A decline "
            f"of that size shortly before withdrawals begin leaves little time to "
            f"recover before assets must be sold."
        )
    elif headline is not None:
        paras.append(headline.message)
        if headline.category in ("employer_stock", "position", "overlap"):
            paras.append(
                f"For context, the five largest holdings account for "
                f"{_pct(concentration.top_five_weight)} of the portfolio, and the "
                f"effective number of holdings is "
                f"{concentration.effective_holdings:.1f} — meaning the portfolio "
                f"carries the diversification of roughly that many equally sized "
                f"positions, despite containing {concentration.position_count}."
            )
    else:
        paras.append(
            f"No individual position, sector, or look-through exposure exceeds the "
            f"concentration guidelines applied in this review. Asset class weights sit "
            f"within tolerance of the {model.name} target."
        )

    # --- Risk in plain language ------------------------------------------
    paras.append("## Risk profile")

    vol_ratio = (
        risk.annualized_volatility / risk.benchmark_volatility
        if risk.benchmark_volatility
        else 1.0
    )
    if vol_ratio >= 1.25:
        vol_phrase = (
            f"materially more volatile than the broad market — "
            f"{_pct(risk.annualized_volatility)} annualized against "
            f"{_pct(risk.benchmark_volatility)} for the S&P 500"
        )
    elif vol_ratio <= 0.8:
        vol_phrase = (
            f"less volatile than the broad market — "
            f"{_pct(risk.annualized_volatility)} annualized against "
            f"{_pct(risk.benchmark_volatility)} for the S&P 500"
        )
    else:
        vol_phrase = (
            f"broadly in line with the market at "
            f"{_pct(risk.annualized_volatility)} annualized volatility"
        )

    paras.append(
        f"The portfolio has been {vol_phrase}. Its beta of {risk.beta:.2f} indicates "
        f"it has historically moved about {risk.beta:.2f}% for each 1% move in the "
        f"index, with a correlation of {risk.correlation:.2f}. The Sharpe ratio over "
        f"the period was {risk.sharpe_ratio:.2f}, measuring return earned per unit of "
        f"volatility above the {_pct(risk.risk_free_rate, 2)} risk-free rate."
    )

    if risk.correlation >= 0.95 and equity_weight > 0.7:
        paras.append(
            f"A correlation of {risk.correlation:.2f} means the portfolio offers little "
            f"diversification benefit relative to simply holding the index. In a broad "
            f"market decline, nearly all positions would be expected to fall together."
        )

    # --- Fixed income gap -------------------------------------------------
    fi_weight = weights.get(FIXED_INCOME, 0.0)
    fi_target = model.target_for(FIXED_INCOME)
    if fi_target - fi_weight >= 0.10:
        paras.append(
            f"Fixed income represents {_pct(fi_weight)} of the portfolio against a "
            f"{_pct(fi_target)} target. Fixed income is the component of the "
            f"{model.name} allocation intended to cushion equity declines; at the "
            f"current weight that cushion is largely absent."
        )

    # --- What it would take to fix ---------------------------------------
    paras.append("## Closing the gap")

    if not plan.needs_rebalancing:
        paras.append(
            f"All asset classes are within three percentage points of the "
            f"{model.name} target. No rebalancing trades are indicated at this time."
        )
    else:
        cost_sentence = (
            f"Moving to the {model.name} target would involve reducing positions by "
            f"approximately {_usd(plan.total_turnover)}."
        )

        if plan.total_tax_cost <= 0:
            cost_sentence += (
                " The entire amount can be sourced from tax-sheltered accounts, so no "
                "capital gains would be realized and there would be no current tax cost."
            )
        elif plan.tax_free_proceeds > 0:
            cost_sentence += (
                f" Of that, {_usd(plan.tax_free_proceeds)} can be sourced from "
                f"tax-sheltered accounts at no tax cost. The remaining "
                f"{_usd(plan.taxable_proceeds)} would come from taxable accounts, with "
                f"an estimated tax cost of {_usd(plan.total_tax_cost)} — roughly "
                f"{_pct(plan.tax_cost_pct_of_turnover, 1)} of the total amount moved."
            )
        else:
            cost_sentence += (
                f" All of it would come from taxable accounts, with an estimated tax "
                f"cost of {_usd(plan.total_tax_cost)}, or roughly "
                f"{_pct(plan.tax_cost_pct_of_turnover, 1)} of the amount moved."
            )
        paras.append(cost_sentence)

        # The honest trade-off. This is the paragraph that separates an advisor's
        # framing from a dashboard's: the right move is not free, and saying so
        # is the point.
        if plan.total_tax_cost > 0:
            paras.append(
                f"That tax cost is real and worth weighing deliberately. It is also "
                f"the price of reducing an exposure that currently drives most of the "
                f"portfolio's risk. Approaches that spread the change over multiple "
                f"tax years, direct new contributions toward the underweight asset "
                f"classes, or pair sales with realized losses elsewhere can reduce "
                f"the cost of getting to the same destination."
            )
            if plan.unrealized_gain_deferred > 0:
                paras.append(
                    f"This plan would leave {_usd(plan.unrealized_gain_deferred)} of "
                    f"unrealized gain untouched, deferring tax on that portion."
                )

    return Narrative(paragraphs=paras, source="rule_based")
