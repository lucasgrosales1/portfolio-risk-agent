"""Tests for pra.prices' network-failure handling.

Everything else about prices.py (successful fetches) is exercised indirectly
through the patch_prices fixture used across the rest of the suite, which
replaces these functions entirely. This file covers the one thing that
fixture can't: what happens when the underlying yfinance call itself fails
or times out, since that's the actual behavior being fixed here.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import pra.prices as prices_module
from pra.prices import FETCH_TIMEOUT_SECONDS, PriceDataError, fetch_risk_free_rate


def test_download_history_converts_network_exception_to_price_data_error(monkeypatch):
    """A raw exception from yf.download (timeout, DNS failure, connection
    reset -- whatever curl_cffi/requests raises) must never reach the caller
    as-is. The app's error handling only knows to catch PriceDataError."""

    def _boom(**kwargs):
        raise TimeoutError("simulated cold-start timeout")

    monkeypatch.setattr("yfinance.download", _boom)

    with pytest.raises(PriceDataError, match="Could not reach the market data service"):
        prices_module._download_history(["VOO"], "3y")


def test_download_history_passes_an_explicit_timeout(monkeypatch):
    """Regression guard: the whole point is a bounded, predictable wait --
    silently dropping the timeout kwarg would put this back to relying on
    yfinance's own internal default."""
    captured = {}

    def _fake_download(**kwargs):
        captured.update(kwargs)
        import pandas as pd

        return pd.DataFrame({"Close": [1.0, 2.0]})

    monkeypatch.setattr("yfinance.download", _fake_download)
    prices_module._download_history(["VOO"], "3y")

    assert captured.get("timeout") == FETCH_TIMEOUT_SECONDS


def test_fetch_prices_surfaces_price_data_error_not_a_raw_exception(monkeypatch):
    def _boom(**kwargs):
        raise ConnectionError("simulated network failure")

    monkeypatch.setattr("yfinance.download", _boom)

    with pytest.raises(PriceDataError):
        prices_module.fetch_prices(["VOO"], use_cache=False)


def test_fetch_prices_rejects_a_present_but_all_nan_column(monkeypatch):
    """Reproduces a live crash: yfinance recognized a ticker (its column
    exists) but a transient partial failure meant every price came back NaN.
    dropna(how="all") in _download_history only drops rows where *every*
    column is empty, so this column survives that step untouched and used to
    reach load_market_data's `.dropna().iloc[-1]`, which raised a raw,
    unhandled IndexError -- exactly the crash seen on Devon & Ana Carter's
    sample portfolio. fetch_prices must catch this itself and raise the same
    clean, retryable PriceDataError as a genuinely missing ticker."""
    index = pd.bdate_range("2024-01-02", periods=5)
    tickers = ["VOO", "BROKEN", prices_module.BENCHMARK_TICKER]
    columns = pd.MultiIndex.from_product([["Close"], tickers])
    raw = pd.DataFrame(
        {
            ("Close", "VOO"): [400.0, 401.0, 402.0, 403.0, 404.0],
            ("Close", "BROKEN"): [np.nan] * 5,
            ("Close", prices_module.BENCHMARK_TICKER): [4500.0, 4510.0, 4505.0, 4520.0, 4515.0],
        },
        index=index,
        columns=columns,
    )
    monkeypatch.setattr("yfinance.download", lambda **kwargs: raw)

    with pytest.raises(PriceDataError, match="BROKEN"):
        prices_module.fetch_prices(["VOO", "BROKEN"], use_cache=False)


def test_fetch_risk_free_rate_falls_back_when_history_raises(monkeypatch):
    """Already-existing graceful-fallback behavior -- this locks in that
    adding an explicit timeout kwarg didn't change it."""

    class _BoomTicker:
        def __init__(self, *_args, **_kwargs):
            pass

        def history(self, *_args, **_kwargs):
            raise TimeoutError("simulated timeout")

    monkeypatch.setattr("yfinance.Ticker", _BoomTicker)

    rate, is_live = fetch_risk_free_rate()

    assert is_live is False
    assert rate == prices_module.FALLBACK_RISK_FREE_RATE
