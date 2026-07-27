"""Known-value tests for pra.analytics.allocation.value_portfolio.

Fixture: a 3-position portfolio (VOO, BND, CASH) with hand-computed market
values, gains, and weights. All expected numbers below were derived
independently of the source (plain arithmetic on the fixture's own inputs) and
cross-checked against the real implementation while writing this suite.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from pra.analytics.allocation import value_portfolio
from pra.portfolio import Holding, Portfolio

from ..conftest import make_market_data


@pytest.fixture
def three_position_portfolio() -> Portfolio:
    holdings = [
        Holding("VOO", 100, 300.0, date(2020, 1, 1), "taxable"),
        Holding("BND", 200, 90.0, date(2021, 1, 1), "traditional"),
        Holding("CASH", 5000, 1.0, date(2022, 1, 1), "taxable"),
    ]
    return Portfolio(holdings=holdings, client_name="Allocation Test")


@pytest.fixture
def three_position_market():
    index = pd.date_range("2024-01-01", periods=2, freq="D")
    prices = pd.DataFrame({"VOO": [398.0, 400.0], "BND": [76.0, 75.0]}, index=index)
    benchmark = pd.Series([4500.0, 4510.0], index=index, name="^GSPC")
    metadata = {
        "VOO": {"name": "Vanguard S&P 500 ETF", "expense_ratio": 0.03},
        "BND": {"name": "Vanguard Total Bond Market ETF", "expense_ratio": 0.08},
    }
    return make_market_data(
        prices, {"VOO": 400.0, "BND": 75.0}, benchmark=benchmark, metadata=metadata
    )


def test_value_portfolio_known_totals(three_position_portfolio, three_position_market):
    result = value_portfolio(three_position_portfolio, three_position_market)

    assert result.total_value == pytest.approx(60_000.0)
    assert result.total_cost_basis == pytest.approx(53_000.0)
    assert result.total_unrealized_gain == pytest.approx(7_000.0)
    assert result.warnings == []
    assert result.unclassified == []


def test_value_portfolio_asset_class_breakdown(three_position_portfolio, three_position_market):
    result = value_portfolio(three_position_portfolio, three_position_market)

    assert result.by_asset_class == {
        "Equity": pytest.approx(40_000.0),
        "Fixed Income": pytest.approx(15_000.0),
        "Cash": pytest.approx(5_000.0),
    }
    weights = result.asset_class_weights()
    assert weights["Equity"] == pytest.approx(2 / 3)
    assert weights["Fixed Income"] == pytest.approx(0.25)
    assert weights["Cash"] == pytest.approx(1 / 12)


def test_value_portfolio_position_weights_and_gains(three_position_portfolio, three_position_market):
    result = value_portfolio(three_position_portfolio, three_position_market)
    weights = result.position_weights()

    assert weights["VOO"] == pytest.approx(2 / 3)
    assert weights["BND"] == pytest.approx(0.25)
    assert weights["CASH"] == pytest.approx(1 / 12)

    voo = next(p for p in result.positions if p.ticker == "VOO")
    bnd = next(p for p in result.positions if p.ticker == "BND")
    assert voo.market_value == pytest.approx(40_000.0)
    assert voo.cost_basis == pytest.approx(30_000.0)
    assert voo.gain_pct == pytest.approx(1 / 3)
    assert bnd.market_value == pytest.approx(15_000.0)
    assert bnd.cost_basis == pytest.approx(18_000.0)
    assert bnd.gain_pct == pytest.approx(-1 / 6)


def test_value_portfolio_weighted_expense_ratio(three_position_portfolio, three_position_market):
    result = value_portfolio(three_position_portfolio, three_position_market)
    # Weighted by market value: (40000*0.03 + 15000*0.08) / 55000
    assert result.weighted_expense_ratio == pytest.approx((40_000 * 0.03 + 15_000 * 0.08) / 55_000)


def test_value_portfolio_missing_price_excludes_position_and_warns(three_position_market):
    holdings = [
        Holding("VOO", 100, 300.0, date(2020, 1, 1), "taxable"),
        Holding("GHOST", 10, 50.0, date(2020, 1, 1), "taxable"),
    ]
    portfolio = Portfolio(holdings=holdings, client_name="Missing Price Test")

    result = value_portfolio(portfolio, three_position_market)

    tickers = {p.ticker for p in result.positions}
    assert "GHOST" not in tickers
    assert result.total_value == pytest.approx(40_000.0)
    assert any("GHOST" in w for w in result.warnings)


def test_value_portfolio_unclassified_ticker_is_flagged():
    index = pd.date_range("2024-01-01", periods=2, freq="D")
    prices = pd.DataFrame({"WEIRD": [10.0, 10.0]}, index=index)
    market = make_market_data(
        prices, {"WEIRD": 10.0}, metadata={"WEIRD": {"name": "Unknown Fund"}}
    )
    holdings = [Holding("WEIRD", 100, 5.0, date(2020, 1, 1), "taxable")]
    portfolio = Portfolio(holdings=holdings, client_name="Unclassified Test")

    result = value_portfolio(portfolio, market)

    assert result.unclassified == ["WEIRD"]
    assert any("WEIRD" in w for w in result.warnings)
