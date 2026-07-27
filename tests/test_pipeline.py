"""Integration test for pra.pipeline.run_analysis, fully offline.

Uses the `patch_prices` fixture (see conftest.py) to replace every pra.prices
network entry point with fixed, in-memory data -- run_analysis must never
reach yfinance. This is a wiring/determinism check, not a known-value test:
the risk-metric formulas themselves are covered exactly in
tests/analytics/test_risk.py.
"""

from __future__ import annotations

from datetime import date

import pytest

from pra.pipeline import run_analysis
from pra.portfolio import Holding, Portfolio


@pytest.fixture
def sample_portfolio() -> Portfolio:
    holdings = [
        Holding("VOO", 100, 300.0, date(2020, 1, 1), "taxable"),
        Holding("BND", 200, 90.0, date(2021, 1, 1), "traditional"),
        Holding("CASH", 5_000, 1.0, date(2022, 1, 1), "taxable"),
    ]
    return Portfolio(holdings=holdings, client_name="Pipeline Test")


def test_run_analysis_never_touches_the_network(patch_prices, monkeypatch, sample_portfolio):
    def _boom(*args, **kwargs):
        raise AssertionError("yfinance must never be called from a test")

    monkeypatch.setattr("yfinance.download", _boom, raising=False)
    monkeypatch.setattr("yfinance.Ticker", _boom, raising=False)

    result = run_analysis(sample_portfolio, "moderate", use_cache=False, use_ai=False)

    last_row = patch_prices.iloc[-1]
    expected_total = 100 * last_row["VOO"] + 200 * last_row["BND"] + 5_000
    assert result.allocation.total_value == pytest.approx(expected_total)
    assert result.market.risk_free_rate == 0.03
    assert result.market.risk_free_is_live is True


def test_run_analysis_is_deterministic_across_repeated_runs(patch_prices, sample_portfolio):
    first = run_analysis(sample_portfolio, "moderate", use_cache=False, use_ai=False)
    second = run_analysis(sample_portfolio, "moderate", use_cache=False, use_ai=False)

    assert first.allocation.total_value == second.allocation.total_value
    assert first.risk.sharpe_ratio == second.risk.sharpe_ratio
    assert first.risk.annualized_volatility == second.risk.annualized_volatility
    assert first.risk.max_drawdown == second.risk.max_drawdown
    assert first.risk.beta == second.risk.beta
    assert first.concentration.effective_holdings == second.concentration.effective_holdings
    assert first.plan.total_tax_cost == second.plan.total_tax_cost


def test_run_analysis_produces_a_complete_result(patch_prices, sample_portfolio):
    result = run_analysis(sample_portfolio, "moderate", use_cache=False, use_ai=False)

    assert result.portfolio is sample_portfolio
    assert result.model.key == "moderate"
    assert result.allocation.total_value > 0
    assert result.risk.trading_days > 0
    assert result.narrative is not None
    assert isinstance(result.warnings, list)
