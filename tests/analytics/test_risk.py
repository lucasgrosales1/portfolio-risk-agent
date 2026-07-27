"""Known-value tests for pra.analytics.risk.

Expected numbers are computed independently of the module under test -- using
Python's stdlib `statistics` (a different implementation than pandas/numpy) or
exact algebraic identities (a perfectly linear series has beta == the slope and
correlation == 1.0 by construction) -- then compared with pytest.approx.
"""

from __future__ import annotations

import math
import statistics

import pandas as pd
import pytest

from pra.analytics.risk import (
    annualized_return,
    annualized_volatility,
    beta_and_correlation,
    max_drawdown,
    sharpe_ratio,
)
from pra.prices import TRADING_DAYS_PER_YEAR

RETURNS = [0.01, -0.02, 0.03, -0.01, 0.02]


def _series(values: list[float]) -> pd.Series:
    return pd.Series(values, index=pd.date_range("2024-01-01", periods=len(values), freq="D"))


def test_annualized_volatility_matches_independent_stdlib_calc():
    expected = statistics.stdev(RETURNS) * math.sqrt(TRADING_DAYS_PER_YEAR)
    assert annualized_volatility(_series(RETURNS)) == pytest.approx(expected)


def test_max_drawdown_known_value():
    # Cumulative wealth: 1.10, 0.88, 0.924, 1.0164 -- peak at day 1, trough at
    # day 2, drawdown = (0.88 - 1.10) / 1.10 = exactly -0.20.
    returns = _series([0.10, -0.20, 0.05, 0.10])
    worst, peak, trough = max_drawdown(returns)

    assert worst == pytest.approx(-0.20)
    assert peak == returns.index[0]
    assert trough == returns.index[1]


def test_max_drawdown_empty_series():
    assert max_drawdown(pd.Series([], dtype=float)) == (0.0, None, None)


def test_sharpe_ratio_matches_independent_stdlib_calc():
    rf = 0.05
    daily_rf = (1 + rf) ** (1 / TRADING_DAYS_PER_YEAR) - 1
    excess = [r - daily_rf for r in RETURNS]
    expected = statistics.mean(excess) / statistics.stdev(excess) * math.sqrt(TRADING_DAYS_PER_YEAR)

    assert sharpe_ratio(_series(RETURNS), rf) == pytest.approx(expected)


def test_sharpe_ratio_zero_volatility_returns_zero():
    constant_returns = _series([0.01] * 5)
    assert sharpe_ratio(constant_returns, 0.05) == 0.0


def test_beta_and_correlation_perfect_linear_relationship():
    benchmark = _series([0.02, -0.01, 0.03, -0.02, 0.01])
    portfolio = benchmark * 1.5  # exact linear relationship: beta == 1.5, corr == 1.0

    beta, correlation = beta_and_correlation(portfolio, benchmark)

    assert beta == pytest.approx(1.5)
    assert correlation == pytest.approx(1.0)


def test_beta_and_correlation_too_short_returns_zero():
    one_day = _series([0.01])
    assert beta_and_correlation(one_day, one_day) == (0.0, 0.0)


def test_annualized_return_known_value():
    # A full trading year (252 days) of constant daily return r: years == 1.0
    # exactly, so annualized_return reduces algebraically to (1+r)**252 - 1.
    r = 0.0003
    returns = _series([r] * TRADING_DAYS_PER_YEAR)
    expected = (1 + r) ** TRADING_DAYS_PER_YEAR - 1

    assert annualized_return(returns) == pytest.approx(expected)


def test_annualized_return_empty_series_is_zero():
    assert annualized_return(pd.Series([], dtype=float)) == 0.0
