"""Risk metrics: volatility, drawdown, Sharpe, beta, correlation.

Every formula here is standard, and every one is written out longhand rather
than pulled from a library, because being able to explain the arithmetic is
part of the point of this project.

One assumption is worth stating plainly, because it appears in the report's
footnotes: the return series is built by applying the portfolio's *current*
weights across the full lookback window, rebalanced daily. It answers "how
would this allocation have behaved?" — not "how did this client's account
actually perform?", which would need a transaction history the tool doesn't have.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..prices import TRADING_DAYS_PER_YEAR, MarketData
from .allocation import AllocationResult


@dataclass
class RiskMetrics:
    annualized_volatility: float
    max_drawdown: float
    max_drawdown_start: pd.Timestamp | None
    max_drawdown_trough: pd.Timestamp | None
    sharpe_ratio: float
    beta: float
    correlation: float
    annualized_return: float
    cumulative_return: float
    benchmark_volatility: float
    benchmark_max_drawdown: float
    benchmark_annualized_return: float
    risk_free_rate: float
    trading_days: int
    lookback_years: float
    returns: pd.Series  # daily portfolio returns, kept for charting


def _daily_returns(prices: pd.DataFrame | pd.Series) -> pd.DataFrame | pd.Series:
    return prices.pct_change().dropna(how="all")


def build_portfolio_returns(
    allocation: AllocationResult,
    market: MarketData,
) -> pd.Series:
    """Daily return series for the portfolio at its current weights.

    Cash is included as a zero-return sleeve, which correctly dampens the
    portfolio's volatility rather than pretending the cash isn't there.
    """
    weights = allocation.position_weights()
    priced = {t: w for t, w in weights.items() if t in market.prices.columns}

    if not priced:
        raise ValueError("No priced positions available to build a return series.")

    returns = _daily_returns(market.prices[list(priced)])

    # Cash earns nothing here — a deliberate simplification, and a conservative
    # one, since it slightly understates the portfolio's return.
    cash_weight = sum(w for t, w in weights.items() if t not in priced)

    weight_vector = pd.Series(priced)
    portfolio_returns = (returns * weight_vector).sum(axis=1)

    # The priced sleeve's returns are already scaled by their true weights;
    # the cash sleeve contributes zero. No renormalization needed.
    _ = cash_weight

    return portfolio_returns.dropna()


def annualized_volatility(returns: pd.Series) -> float:
    """Standard deviation of daily returns, scaled to a year.

    The sqrt(252) factor comes from variance scaling linearly with time while
    standard deviation scales with its square root.
    """
    return float(returns.std(ddof=1) * math.sqrt(TRADING_DAYS_PER_YEAR))


def max_drawdown(returns: pd.Series) -> tuple[float, pd.Timestamp | None, pd.Timestamp | None]:
    """Largest peak-to-trough decline, as a negative decimal.

    Returns (drawdown, peak_date, trough_date). This is the number clients
    actually feel — the worst it got, not how bumpy the ride was on average.
    """
    if returns.empty:
        return 0.0, None, None

    cumulative = (1 + returns).cumprod()
    running_peak = cumulative.cummax()
    drawdowns = (cumulative - running_peak) / running_peak

    trough = drawdowns.idxmin()
    worst = float(drawdowns.min())
    # The peak is the last date at or above the running max before the trough.
    peak = cumulative.loc[:trough].idxmax() if trough is not None else None

    return worst, peak, trough


def annualized_return(returns: pd.Series) -> float:
    """Geometric (compound) annual growth rate over the sample."""
    if returns.empty:
        return 0.0
    total_growth = float((1 + returns).prod())
    years = len(returns) / TRADING_DAYS_PER_YEAR
    if years <= 0 or total_growth <= 0:
        return 0.0
    return total_growth ** (1 / years) - 1


def sharpe_ratio(returns: pd.Series, risk_free_rate: float) -> float:
    """Excess return per unit of volatility.

    The risk-free rate is annual, so it is de-annualized to a daily figure
    before being subtracted from the daily return series.
    """
    if returns.empty or returns.std(ddof=1) == 0:
        return 0.0
    daily_rf = (1 + risk_free_rate) ** (1 / TRADING_DAYS_PER_YEAR) - 1
    excess = returns - daily_rf
    return float(
        excess.mean() / excess.std(ddof=1) * math.sqrt(TRADING_DAYS_PER_YEAR)
    )


def beta_and_correlation(
    returns: pd.Series, benchmark_returns: pd.Series
) -> tuple[float, float]:
    """Sensitivity to, and co-movement with, the benchmark.

    Beta is covariance divided by benchmark variance: a beta of 1.2 means the
    portfolio has historically moved 1.2% for each 1% move in the index.
    Correlation is the same relationship stripped of magnitude.
    """
    aligned = pd.concat([returns, benchmark_returns], axis=1, join="inner").dropna()
    if len(aligned) < 2:
        return 0.0, 0.0

    port = aligned.iloc[:, 0]
    bench = aligned.iloc[:, 1]

    benchmark_variance = float(bench.var(ddof=1))
    if benchmark_variance == 0:
        return 0.0, 0.0

    covariance = float(np.cov(port, bench, ddof=1)[0][1])
    beta = covariance / benchmark_variance
    correlation = float(port.corr(bench))

    return beta, correlation


def compute_risk_metrics(
    allocation: AllocationResult,
    market: MarketData,
) -> RiskMetrics:
    """Run every risk calculation and package the results."""
    returns = build_portfolio_returns(allocation, market)
    benchmark_returns = _daily_returns(market.benchmark).dropna()

    dd, dd_start, dd_trough = max_drawdown(returns)
    bench_dd, _, _ = max_drawdown(benchmark_returns)
    beta, correlation = beta_and_correlation(returns, benchmark_returns)

    return RiskMetrics(
        annualized_volatility=annualized_volatility(returns),
        max_drawdown=dd,
        max_drawdown_start=dd_start,
        max_drawdown_trough=dd_trough,
        sharpe_ratio=sharpe_ratio(returns, market.risk_free_rate),
        beta=beta,
        correlation=correlation,
        annualized_return=annualized_return(returns),
        cumulative_return=float((1 + returns).prod() - 1),
        benchmark_volatility=annualized_volatility(benchmark_returns),
        benchmark_max_drawdown=bench_dd,
        benchmark_annualized_return=annualized_return(benchmark_returns),
        risk_free_rate=market.risk_free_rate,
        trading_days=len(returns),
        lookback_years=len(returns) / TRADING_DAYS_PER_YEAR,
        returns=returns,
    )
