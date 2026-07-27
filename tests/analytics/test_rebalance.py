"""Known-value tests for pra.analytics.rebalance.

Fixture: a portfolio 30 points overweight equity vs. the "moderate" model,
with four VOO lots engineered to exercise the full lot-sale priority order --
sheltered first, then losses, then long-term gains, then short-term gains --
including a partial-lot sale. Every number below was cross-checked against the
real implementation while writing this suite.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from pra.analytics.allocation import value_portfolio
from pra.analytics.rebalance import build_rebalance_plan, compute_drift
from pra.models import get_model
from pra.portfolio import Holding, Portfolio

from ..conftest import make_market_data


@pytest.fixture
def rebalance_plan():
    holdings = [
        # VOO: 4 lots, $1,000/share, $70,000 total -- 70% of the portfolio.
        Holding("VOO", 10, 800.0, date(2020, 1, 1), "traditional"),  # sheltered, +$2,000 gain
        Holding("VOO", 10, 1200.0, date(2020, 1, 1), "taxable"),      # taxable loss, -$2,000
        Holding("VOO", 30, 300.0, date(2019, 1, 1), "taxable"),       # taxable LT gain, +$21,000
        Holding("VOO", 20, 500.0, date(2024, 6, 1), "taxable"),       # taxable ST gain, +$10,000
        Holding("BND", 250, 100.0, date(2021, 1, 1), "traditional"),  # no gain, 25% of portfolio
        Holding("CASH", 5000, 1.0, date(2022, 1, 1), "taxable"),      # 5% of portfolio
    ]
    portfolio = Portfolio(holdings=holdings, client_name="Rebalance Test")

    index = pd.date_range("2024-01-01", periods=2, freq="D")
    prices = pd.DataFrame({"VOO": [995.0, 1000.0], "BND": [100.0, 100.0]}, index=index)
    metadata = {"VOO": {"name": "Vanguard S&P 500 ETF"}, "BND": {"name": "Vanguard Total Bond Market ETF"}}
    market = make_market_data(prices, {"VOO": 1000.0, "BND": 100.0}, metadata=metadata)

    allocation = value_portfolio(portfolio, market)
    model = get_model("moderate")  # targets: Equity 40%, Fixed Income 55%, Cash 5%
    plan = build_rebalance_plan(allocation, model, as_of=date(2025, 6, 1))
    return allocation, model, plan


def test_allocation_is_seventy_thirty_before_rebalancing(rebalance_plan):
    allocation, _, _ = rebalance_plan
    assert allocation.total_value == pytest.approx(100_000.0)
    assert allocation.by_asset_class == {
        "Equity": pytest.approx(70_000.0),
        "Fixed Income": pytest.approx(25_000.0),
        "Cash": pytest.approx(5_000.0),
    }
    assert allocation.total_unrealized_gain == pytest.approx(31_000.0)


def test_compute_drift_by_asset_class(rebalance_plan):
    allocation, model, _ = rebalance_plan
    drifts = {d.asset_class: d for d in compute_drift(allocation, model)}

    assert drifts["Equity"].current_weight == pytest.approx(0.70)
    assert drifts["Equity"].target_weight == pytest.approx(0.40)
    assert drifts["Equity"].drift == pytest.approx(0.30)
    assert drifts["Equity"].dollar_gap == pytest.approx(30_000.0)
    assert drifts["Equity"].is_material
    assert drifts["Equity"].direction == "overweight"

    assert drifts["Fixed Income"].drift == pytest.approx(-0.30)
    assert drifts["Fixed Income"].direction == "underweight"

    assert drifts["Cash"].drift == pytest.approx(0.0)
    assert not drifts["Cash"].is_material
    assert drifts["Cash"].direction == "on target"


def test_plan_needs_rebalancing_and_buys_fixed_income(rebalance_plan):
    _, _, plan = rebalance_plan
    assert plan.needs_rebalancing
    assert plan.buys == {"Fixed Income": pytest.approx(30_000.0)}
    assert plan.total_turnover == pytest.approx(30_000.0)


def test_sell_legs_follow_sheltered_then_loss_then_long_term_priority(rebalance_plan):
    _, _, plan = rebalance_plan
    assert len(plan.sells) == 3  # the short-term lot is never touched

    sheltered_leg, loss_leg, gain_leg = plan.sells

    assert sheltered_leg.account_type == "traditional"
    assert sheltered_leg.dollars == pytest.approx(10_000.0)
    assert sheltered_leg.realized_gain == pytest.approx(2_000.0)
    assert sheltered_leg.estimated_tax == pytest.approx(0.0)  # sheltered: no tax regardless of gain

    assert loss_leg.account_type == "taxable"
    assert loss_leg.dollars == pytest.approx(10_000.0)
    assert loss_leg.realized_gain == pytest.approx(-2_000.0)
    assert loss_leg.estimated_tax == pytest.approx(0.0)  # a loss creates no liability

    # Only $10,000 of the $30,000 long-term lot is needed -- a partial sale.
    assert gain_leg.account_type == "taxable"
    assert gain_leg.dollars == pytest.approx(10_000.0)
    assert gain_leg.shares == pytest.approx(10.0)  # 1/3 of the 30-share lot
    assert gain_leg.realized_gain == pytest.approx(7_000.0)  # 1/3 of the $21,000 gain
    assert gain_leg.is_long_term
    assert gain_leg.estimated_tax == pytest.approx(7_000.0 * 0.15)


def test_plan_tax_and_deferral_totals(rebalance_plan):
    _, _, plan = rebalance_plan
    assert plan.total_tax_cost == pytest.approx(1_050.0)
    assert plan.tax_free_proceeds == pytest.approx(10_000.0)
    assert plan.taxable_proceeds == pytest.approx(20_000.0)
    assert plan.tax_cost_pct_of_turnover == pytest.approx(1_050.0 / 30_000.0)
    # $31,000 total gain minus $7,000 realized ($2,000 + -$2,000 + $7,000 net).
    assert plan.unrealized_gain_deferred == pytest.approx(24_000.0)


def test_plan_notes_mention_mixed_sheltered_and_taxable_sourcing(rebalance_plan):
    _, _, plan = rebalance_plan
    assert any(
        "$10,000" in n and "sheltered" in n and "$20,000" in n and "taxable" in n
        for n in plan.notes
    )
    # No short-term gain was realized, so no short-term tax note should appear.
    assert not any("short-term" in n for n in plan.notes)


def test_no_material_drift_produces_empty_plan():
    index = pd.date_range("2024-01-01", periods=2, freq="D")
    prices = pd.DataFrame({"VOO": [400.0, 400.0], "BND": [75.0, 75.0]}, index=index)
    market = make_market_data(prices, {"VOO": 400.0, "BND": 75.0})
    holdings = [
        Holding("VOO", 100, 300.0, date(2020, 1, 1), "taxable"),   # 40,000 -> 40%
        Holding("BND", 733.3333333333334, 75.0, date(2020, 1, 1), "traditional"),  # ~55,000 -> 55%
        Holding("CASH", 5_000, 1.0, date(2020, 1, 1), "taxable"),  # 5,000 -> 5%
    ]
    portfolio = Portfolio(holdings=holdings, client_name="On Target Test")
    allocation = value_portfolio(portfolio, market)
    model = get_model("moderate")

    plan = build_rebalance_plan(allocation, model, as_of=date(2025, 1, 1))

    assert not plan.needs_rebalancing
    assert plan.sells == []
    assert plan.buys == {}
    assert plan.total_tax_cost == 0.0
