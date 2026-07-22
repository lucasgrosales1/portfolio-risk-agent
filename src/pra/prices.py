"""Market data via yfinance, with an on-disk cache.

Everything the analytics layer needs comes from here: a daily close price
history, current prices, the benchmark series, the risk-free rate, and whatever
security metadata yfinance will give us.

Caching matters more than it looks. Without it, every run during development
re-downloads several years of daily bars for every ticker, which is slow and
rude to a free data source. With it, the second run is instant.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

# The S&P 500. Beta and correlation are measured against this.
BENCHMARK_TICKER = "^GSPC"
BENCHMARK_NAME = "S&P 500"

# 13-week Treasury bill yield, used as the risk-free rate in the Sharpe ratio.
RISK_FREE_TICKER = "^IRX"

# Used only when the live risk-free lookup fails. Stated in the report so the
# reader knows a fallback assumption was used rather than a market rate.
FALLBACK_RISK_FREE_RATE = 0.042

CACHE_TTL_SECONDS = 60 * 60 * 12  # refresh prices at most twice a day
TRADING_DAYS_PER_YEAR = 252


class PriceDataError(RuntimeError):
    """Raised when market data can't be retrieved for a required ticker."""


@dataclass
class MarketData:
    """Everything the analytics layer needs from the outside world."""

    # Daily adjusted close, indexed by date, one column per ticker.
    prices: pd.DataFrame
    benchmark: pd.Series
    current_prices: dict[str, float]
    risk_free_rate: float
    risk_free_is_live: bool
    # ticker -> {quote_type, category, name, expense_ratio, sector}
    metadata: dict[str, dict] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def start_date(self) -> date:
        return self.prices.index[0].date()

    @property
    def end_date(self) -> date:
        return self.prices.index[-1].date()

    @property
    def trading_days(self) -> int:
        return len(self.prices)


def _cache_dir() -> Path:
    d = Path(__file__).resolve().parents[2] / ".cache"
    d.mkdir(exist_ok=True)
    return d


def _cache_path(key: str, suffix: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in key)
    return _cache_dir() / f"{safe}.{suffix}"


def _cache_is_fresh(path: Path) -> bool:
    return path.exists() and (time.time() - path.stat().st_mtime) < CACHE_TTL_SECONDS


def _download_history(tickers: list[str], period: str) -> pd.DataFrame:
    """Download daily closes. Returns a DataFrame with one column per ticker."""
    import yfinance as yf

    raw = yf.download(
        tickers=tickers,
        period=period,
        interval="1d",
        auto_adjust=True,   # adjust for splits and dividends
        progress=False,
        threads=True,
    )

    if raw is None or raw.empty:
        raise PriceDataError(
            f"yfinance returned no data for: {', '.join(tickers)}. "
            "Check the ticker symbols and your internet connection."
        )

    # Single ticker gives flat columns; multiple gives a MultiIndex.
    if isinstance(raw.columns, pd.MultiIndex):
        closes = raw["Close"]
    else:
        closes = raw[["Close"]].rename(columns={"Close": tickers[0]})

    return closes.dropna(how="all")


def fetch_prices(
    tickers: list[str],
    lookback: str = "3y",
    use_cache: bool = True,
) -> pd.DataFrame:
    """Daily close history for `tickers` plus the benchmark."""
    if not tickers:
        raise PriceDataError("No tickers to price.")

    all_tickers = sorted(set(tickers) | {BENCHMARK_TICKER})
    cache_key = f"prices_{lookback}_{'_'.join(all_tickers)}"
    # Pickle rather than parquet: parquet needs pyarrow, which is a large
    # dependency to add for a local cache nobody else reads.
    cache_file = _cache_path(cache_key, "pkl")

    if use_cache and _cache_is_fresh(cache_file):
        try:
            return pd.read_pickle(cache_file)
        except Exception:
            pass  # corrupt or unreadable cache — fall through and re-download

    closes = _download_history(all_tickers, lookback)

    missing = [t for t in all_tickers if t not in closes.columns]
    if missing:
        raise PriceDataError(
            f"No price history returned for: {', '.join(missing)}. "
            "Verify these are valid, currently-listed symbols."
        )

    if use_cache:
        try:
            closes.to_pickle(cache_file)
        except Exception:
            pass  # caching is an optimization, not a requirement

    return closes


def fetch_metadata(tickers: list[str], use_cache: bool = True) -> dict[str, dict]:
    """Security metadata: type, category, name, expense ratio, sector.

    Every field here is best-effort. yfinance's coverage is uneven, and a
    missing field must never break a report — the renderer omits the line
    instead of guessing.
    """
    import yfinance as yf

    cache_file = _cache_path(f"meta_{'_'.join(sorted(tickers))}", "json")
    if use_cache and _cache_is_fresh(cache_file):
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    out: dict[str, dict] = {}
    for ticker in tickers:
        record: dict = {"ticker": ticker}
        try:
            t = yf.Ticker(ticker)
            info = t.info or {}
            record["name"] = info.get("longName") or info.get("shortName") or ticker
            record["quote_type"] = info.get("quoteType")
            record["sector"] = info.get("sector")
            record["category"] = info.get("category")

            expense = info.get("netExpenseRatio") or info.get("annualReportExpenseRatio")
            if expense is not None:
                # yfinance reports this as a percent, not a decimal: VOO's
                # 0.03% expense ratio comes back as 0.03. Verified against
                # yfinance 1.5.1 — divide by 100 to get a decimal.
                record["expense_ratio"] = float(expense) / 100.0

            # ETF look-through: sector weights and top holdings, when available.
            try:
                funds = t.funds_data
                if funds is not None:
                    weights = getattr(funds, "sector_weightings", None)
                    if weights:
                        record["sector_weights"] = dict(weights)

                    # top_holdings is a DataFrame indexed by ticker symbol with
                    # columns ["Name", "Holding Percent"]. Select the percent
                    # column by name — positional access grabs the name string.
                    holdings = getattr(funds, "top_holdings", None)
                    if holdings is not None and not holdings.empty:
                        pct_col = next(
                            (c for c in holdings.columns if "percent" in str(c).lower()),
                            None,
                        )
                        if pct_col is not None:
                            record["top_holdings"] = {
                                str(idx): float(value)
                                for idx, value in holdings[pct_col].items()
                            }
            except Exception:
                pass  # funds_data is absent for stocks and unreliable for some ETFs

        except Exception as exc:
            record["error"] = str(exc)

        out[ticker] = record

    if use_cache:
        try:
            cache_file.write_text(json.dumps(out, indent=2), encoding="utf-8")
        except Exception:
            pass

    return out


def fetch_risk_free_rate() -> tuple[float, bool]:
    """Current 13-week T-bill yield as a decimal. Returns (rate, is_live)."""
    try:
        import yfinance as yf

        hist = yf.Ticker(RISK_FREE_TICKER).history(period="5d")
        if hist is not None and not hist.empty:
            # ^IRX quotes in percent — 4.25 means 4.25%.
            return float(hist["Close"].iloc[-1]) / 100.0, True
    except Exception:
        pass
    return FALLBACK_RISK_FREE_RATE, False


def load_market_data(
    tickers: list[str],
    lookback: str = "3y",
    risk_free_override: float | None = None,
    use_cache: bool = True,
) -> MarketData:
    """Fetch everything the analytics layer needs in one call."""
    warnings: list[str] = []

    closes = fetch_prices(tickers, lookback=lookback, use_cache=use_cache)
    benchmark = closes[BENCHMARK_TICKER].dropna()
    holding_prices = closes[[t for t in tickers if t in closes.columns]]

    current = {
        ticker: float(holding_prices[ticker].dropna().iloc[-1])
        for ticker in holding_prices.columns
    }

    if risk_free_override is not None:
        rate, is_live = risk_free_override, False
    else:
        rate, is_live = fetch_risk_free_rate()
        if not is_live:
            warnings.append(
                f"Live risk-free rate unavailable; assumed "
                f"{FALLBACK_RISK_FREE_RATE:.2%} for the Sharpe ratio."
            )

    metadata = fetch_metadata(tickers, use_cache=use_cache)
    for ticker, record in metadata.items():
        if "error" in record:
            warnings.append(f"Limited security data for {ticker}; some fields omitted.")

    return MarketData(
        prices=holding_prices,
        benchmark=benchmark,
        current_prices=current,
        risk_free_rate=rate,
        risk_free_is_live=is_live,
        metadata=metadata,
        warnings=warnings,
    )
