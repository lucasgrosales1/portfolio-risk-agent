"""Shared fixtures for the pra test suite.

Every fixture here is synthetic and deterministic. Nothing in this suite is
allowed to touch the network: analytics/suitability tests build MarketData
objects by hand, and anything that goes through pra.pipeline.run_analysis uses
the `patch_prices` fixture below, which replaces pra.prices' three network
entry points (fetch_prices, fetch_metadata, fetch_risk_free_rate) with fixed,
in-memory data.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import pra.prices as prices_module
from pra.prices import MarketData


def make_market_data(
    prices: pd.DataFrame,
    current_prices: dict[str, float],
    benchmark: pd.Series | None = None,
    risk_free_rate: float = 0.03,
    risk_free_is_live: bool = True,
    metadata: dict[str, dict] | None = None,
    warnings: list[str] | None = None,
) -> MarketData:
    """Build a MarketData object from plain values -- no network, no cache."""
    if benchmark is None:
        benchmark = pd.Series([100.0] * len(prices), index=prices.index, name="^GSPC")
    return MarketData(
        prices=prices,
        benchmark=benchmark,
        current_prices=current_prices,
        risk_free_rate=risk_free_rate,
        risk_free_is_live=risk_free_is_live,
        metadata=metadata or {},
        warnings=list(warnings or []),
    )


_FIXED_LOOKBACK_DAYS = 300


def _synthetic_price_frame() -> pd.DataFrame:
    """A deterministic (seeded), realistic-looking daily-close history.

    Covers the tickers used by the sample portfolios plus the benchmark, so
    pipeline-level tests can price an arbitrary small portfolio without ever
    calling yfinance.
    """
    index = pd.bdate_range("2023-01-03", periods=_FIXED_LOOKBACK_DAYS)

    def path(start: float, mu: float, sigma: float, seed: int) -> np.ndarray:
        rng = np.random.RandomState(seed)
        daily = rng.normal(mu, sigma, _FIXED_LOOKBACK_DAYS)
        return start * np.cumprod(1 + daily)

    columns = {
        "VOO": path(400.0, 0.0004, 0.010, seed=1),
        "BND": path(90.0, 0.0001, 0.003, seed=2),
        "CASH": np.full(_FIXED_LOOKBACK_DAYS, 1.0),
        prices_module.BENCHMARK_TICKER: path(4500.0, 0.00035, 0.009, seed=3),
    }
    return pd.DataFrame(columns, index=index)


_FIXED_METADATA = {
    "VOO": {"name": "Vanguard S&P 500 ETF", "quote_type": "ETF", "expense_ratio": 0.0003},
    "BND": {"name": "Vanguard Total Bond Market ETF", "quote_type": "ETF", "expense_ratio": 0.0035},
}


@pytest.fixture
def fixed_price_frame() -> pd.DataFrame:
    return _synthetic_price_frame()


@pytest.fixture
def patch_prices(monkeypatch, fixed_price_frame):
    """Make every pra.prices network entry point deterministic and offline.

    Patches the module-level functions rather than load_market_data itself, so
    run_analysis/pipeline exercise their real wiring (caching decisions,
    warning collection, risk-free fallback plumbing) against fixed data.
    """
    monkeypatch.delenv("PRA_RISK_FREE_RATE", raising=False)

    def _fetch_prices(tickers, lookback="3y", use_cache=True):
        needed = sorted(set(tickers) | {prices_module.BENCHMARK_TICKER})
        missing = [t for t in needed if t not in fixed_price_frame.columns]
        if missing:
            raise prices_module.PriceDataError(
                f"No fixture price data for: {', '.join(missing)}."
            )
        return fixed_price_frame[needed].copy()

    def _fetch_metadata(tickers, use_cache=True):
        return {t: dict(_FIXED_METADATA.get(t, {"ticker": t})) for t in tickers}

    def _fetch_risk_free_rate():
        return 0.03, True

    monkeypatch.setattr(prices_module, "fetch_prices", _fetch_prices)
    monkeypatch.setattr(prices_module, "fetch_metadata", _fetch_metadata)
    monkeypatch.setattr(prices_module, "fetch_risk_free_rate", _fetch_risk_free_rate)
    return fixed_price_frame
