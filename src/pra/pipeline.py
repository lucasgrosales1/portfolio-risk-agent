"""One place that runs the full Phase 1 analysis.

Both the CLI and the Streamlit app call this, so the sequence of steps lives in
exactly one spot. Returns everything needed to render a report or display
metrics; rendering itself stays in pra.report.
"""

from __future__ import annotations

from dataclasses import dataclass

from .agents.narrative import Narrative, rule_based_narrative
from .analytics import (
    AllocationResult,
    ConcentrationResult,
    RebalanceResult,
    RiskMetrics,
    analyze_concentration,
    build_rebalance_plan,
    compute_risk_metrics,
    value_portfolio,
)
from .config import has_api_key, risk_free_override
from .models import ModelPortfolio, get_model
from .portfolio import Portfolio
from .prices import MarketData, load_market_data


@dataclass
class AnalysisResult:
    """The complete output of a Phase 1 run."""

    portfolio: Portfolio
    model: ModelPortfolio
    market: MarketData
    allocation: AllocationResult
    risk: RiskMetrics
    concentration: ConcentrationResult
    plan: RebalanceResult
    narrative: Narrative

    @property
    def warnings(self) -> list[str]:
        return list(dict.fromkeys(self.allocation.warnings + self.market.warnings))


def _make_narrative(
    portfolio, allocation, risk, concentration, plan, model, use_ai: bool
) -> Narrative:
    """Choose the narrative path, falling back to rule-based on any AI failure."""
    if use_ai:
        try:
            from .agents.ai import ai_narrative

            return ai_narrative(portfolio, allocation, risk, concentration, plan, model)
        except ImportError:
            pass  # AI agent not built yet — rule-based is the intended fallback
        except Exception:
            pass  # a runtime AI failure must never break a report
    return rule_based_narrative(portfolio, allocation, risk, concentration, plan, model)


def run_analysis(
    portfolio: Portfolio,
    model_key: str,
    lookback: str = "3y",
    use_cache: bool = True,
    use_ai: bool | None = None,
) -> AnalysisResult:
    """Run the full analysis for one portfolio against one target model."""
    model = get_model(model_key)
    market = load_market_data(
        portfolio.tickers,
        lookback=lookback,
        risk_free_override=risk_free_override(),
        use_cache=use_cache,
    )

    allocation = value_portfolio(portfolio, market)
    risk = compute_risk_metrics(allocation, market)
    concentration = analyze_concentration(allocation, market)
    plan = build_rebalance_plan(allocation, model)

    if use_ai is None:
        use_ai = has_api_key()
    narrative = _make_narrative(
        portfolio, allocation, risk, concentration, plan, model, use_ai
    )

    return AnalysisResult(
        portfolio=portfolio,
        model=model,
        market=market,
        allocation=allocation,
        risk=risk,
        concentration=concentration,
        plan=plan,
        narrative=narrative,
    )
