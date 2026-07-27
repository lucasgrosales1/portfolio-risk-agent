"""Known-value tests for pra.analytics.concentration.analyze_concentration.

Fixture: a 6-position portfolio engineered to trip every flag category at
once -- employer stock, single-position, sector, top-5, and look-through
overlap -- so the severity/priority ordering and the headline-selection logic
(employer stock outranks a larger sector flag) are exercised together. Every
number below was cross-checked against the real implementation while writing
this suite.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from pra.analytics.allocation import value_portfolio
from pra.analytics.concentration import analyze_concentration
from pra.portfolio import Holding, Portfolio

from ..conftest import make_market_data


@pytest.fixture
def concentrated_result():
    holdings = [
        Holding("NVDA", 3000, 10.0, date(2019, 1, 1), "taxable", is_employer_stock=True),
        Holding("VOO", 500, 300.0, date(2020, 1, 1), "taxable"),
        Holding("AAPL", 250, 150.0, date(2020, 1, 1), "taxable"),
        Holding("MSFT", 100, 300.0, date(2020, 1, 1), "taxable"),
        Holding("BND", 2000, 80.0, date(2021, 1, 1), "traditional"),
        Holding("CASH", 50_000, 1.0, date(2022, 1, 1), "taxable"),
    ]
    portfolio = Portfolio(holdings=holdings, client_name="Concentration Test")

    index = pd.date_range("2024-01-01", periods=2, freq="D")
    current_prices = {"NVDA": 100.0, "VOO": 400.0, "AAPL": 200.0, "MSFT": 500.0, "BND": 75.0}
    prices = pd.DataFrame({t: [p, p] for t, p in current_prices.items()}, index=index)
    metadata = {
        "NVDA": {"name": "NVIDIA", "sector": "Technology", "quote_type": "EQUITY"},
        "AAPL": {"name": "Apple", "sector": "Technology", "quote_type": "EQUITY"},
        "MSFT": {"name": "Microsoft", "sector": "Technology", "quote_type": "EQUITY"},
        "VOO": {
            "name": "Vanguard S&P 500 ETF",
            "top_holdings": {"NVDA": 0.07, "MSFT": 0.06, "AAPL": 0.05},
        },
        "BND": {"name": "Vanguard Total Bond Market ETF"},
    }
    market = make_market_data(prices, current_prices, metadata=metadata)

    allocation = value_portfolio(portfolio, market)
    return analyze_concentration(allocation, market), allocation


def test_position_weights_and_effective_holdings(concentrated_result):
    result, allocation = concentrated_result

    assert allocation.total_value == pytest.approx(800_000.0)
    assert result.largest_position == ("NVDA", pytest.approx(0.375))
    assert result.top_five_weight == pytest.approx(0.9375)
    # 1 / sum(w^2): NVDA .375, VOO .25, BND .1875, AAPL/MSFT/CASH .0625 each.
    assert result.effective_holdings == pytest.approx(4.0)


def test_employer_stock_flag_is_high_severity(concentrated_result):
    result, _ = concentrated_result
    flag = next(f for f in result.flags if f.category == "employer_stock")

    assert flag.subject == "NVDA"
    assert flag.severity == "high"
    assert flag.weight == pytest.approx(0.375)


def test_single_position_flags_for_non_employer_holdings(concentrated_result):
    result, _ = concentrated_result
    by_subject = {f.subject: f for f in result.flags if f.category == "position"}

    assert by_subject["VOO"].severity == "high"  # 0.25 >= 2x the 10% threshold
    assert by_subject["VOO"].weight == pytest.approx(0.25)
    assert by_subject["BND"].severity == "moderate"  # 0.1875 >= 1.4x but < 2x
    assert by_subject["BND"].weight == pytest.approx(0.1875)


def test_sector_concentration_flag(concentrated_result):
    result, _ = concentrated_result
    flag = next(f for f in result.flags if f.category == "sector")

    assert flag.subject == "Technology"
    assert flag.weight == pytest.approx(0.50)  # NVDA + AAPL + MSFT, all direct
    assert flag.severity == "high"  # exactly 2x the 25% threshold


def test_top_five_holdings_flag(concentrated_result):
    result, _ = concentrated_result
    flag = next(f for f in result.flags if f.category == "top_holdings")

    assert flag.weight == pytest.approx(0.9375)
    assert flag.severity == "moderate"  # >= 1.4x but < 2x the 50% threshold


def test_look_through_overlap_flag_for_fund_held_employer_stock(concentrated_result):
    result, _ = concentrated_result
    flag = next(f for f in result.flags if f.category == "overlap")

    # Direct 0.375 + indirect (0.25 VOO weight * 0.07 top-holding weight) = 0.3925.
    assert flag.subject == "NVDA"
    assert flag.weight == pytest.approx(0.3925)
    assert flag.severity == "moderate"  # indirect (0.0175) < 0.05


def test_headline_prefers_employer_stock_over_larger_sector_flag(concentrated_result):
    result, _ = concentrated_result
    # Sector flag (0.50) is numerically larger than employer stock (0.375), but
    # both are "high" severity and employer_stock has category priority 0.
    assert result.headline.category == "employer_stock"
    assert result.headline.subject == "NVDA"


def test_no_flags_for_a_boring_diversified_portfolio():
    index = pd.date_range("2024-01-01", periods=2, freq="D")
    prices = pd.DataFrame({"VOO": [400.0, 400.0], "BND": [75.0, 75.0]}, index=index)
    metadata = {"VOO": {"name": "Vanguard S&P 500 ETF"}, "BND": {"name": "Vanguard Total Bond Market ETF"}}
    market = make_market_data(prices, {"VOO": 400.0, "BND": 75.0}, metadata=metadata)
    holdings = [
        # A large cash pile dilutes VOO/BND to ~6%/4% of the portfolio -- both
        # comfortably under the 10% single-position guideline.
        Holding("VOO", 100, 300.0, date(2020, 1, 1), "taxable"),
        Holding("BND", 400, 75.0, date(2020, 1, 1), "taxable"),
        Holding("CASH", 600_000, 1.0, date(2020, 1, 1), "taxable"),
    ]
    portfolio = Portfolio(holdings=holdings, client_name="Boring Test")

    allocation = value_portfolio(portfolio, market)
    result = analyze_concentration(allocation, market)

    assert result.flags == []
    assert result.headline is None
    assert result.has_high_severity is False
