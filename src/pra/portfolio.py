"""Portfolio data types and CSV loading.

The shape of a Holding is the most important design decision in this project.
Two fields do the heavy lifting, and neither is obvious if you've only ever
seen a portfolio as "ticker + weight":

  acquisition_date  Cost basis alone tells you the size of a gain. It does not
                    tell you whether that gain is taxed at long-term rates
                    (held > 1 year) or short-term ordinary income rates.
                    Rebalancing advice that ignores the distinction is
                    incomplete advice.

  account_type      A position held in an IRA can be trimmed with no tax
                    consequence at all. The right rebalancing move is very
                    often "sell it in the sheltered account" rather than
                    "sell it." A tool that can't see account type can't say
                    that.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

# Positions held longer than this qualify for long-term capital gains treatment.
LONG_TERM_HOLDING_DAYS = 365

# A position with this ticker is treated as cash rather than looked up on an exchange.
CASH_TICKER = "CASH"

AccountType = str  # one of ACCOUNT_TYPES
ACCOUNT_TYPES = ("taxable", "traditional", "roth")

# Accounts where selling a position triggers no current-year tax.
SHELTERED_ACCOUNTS = ("traditional", "roth")


class PortfolioError(ValueError):
    """Raised when a portfolio file is malformed. Always names the offending row."""


@dataclass(frozen=True)
class Holding:
    """A single tax lot.

    One row per lot, not per ticker — the same ticker bought on three dates is
    three Holdings. That is how a real cost-basis report arrives, and it is what
    makes lot-level tax analysis possible.
    """

    ticker: str
    shares: float
    cost_basis_per_share: float
    acquisition_date: date
    account_type: AccountType
    is_employer_stock: bool = False

    @property
    def cost_basis(self) -> float:
        """Total dollars originally paid for this lot."""
        return self.shares * self.cost_basis_per_share

    @property
    def is_cash(self) -> bool:
        return self.ticker.upper() == CASH_TICKER

    @property
    def is_sheltered(self) -> bool:
        """True when selling this lot triggers no current-year tax."""
        return self.account_type in SHELTERED_ACCOUNTS

    def holding_period_days(self, as_of: date) -> int:
        return (as_of - self.acquisition_date).days

    def is_long_term(self, as_of: date) -> bool:
        """Long-term capital gains treatment requires a holding period over one year."""
        return self.holding_period_days(as_of) > LONG_TERM_HOLDING_DAYS


@dataclass
class Portfolio:
    """A named collection of tax lots, plus the client context a report needs."""

    holdings: list[Holding]
    client_name: str = "Sample Client"
    client_age: int | None = None
    time_horizon_years: int | None = None
    notes: str = ""
    # Free-form key/value pairs read from `# key: value` comment lines in the CSV.
    meta: dict[str, str] = field(default_factory=dict)

    @property
    def tickers(self) -> list[str]:
        """Unique non-cash tickers, in first-seen order — these get priced."""
        seen: list[str] = []
        for h in self.holdings:
            if not h.is_cash and h.ticker not in seen:
                seen.append(h.ticker)
        return seen

    @property
    def total_cost_basis(self) -> float:
        return sum(h.cost_basis for h in self.holdings)

    def lots_for(self, ticker: str) -> list[Holding]:
        return [h for h in self.holdings if h.ticker == ticker]


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in ("true", "yes", "y", "1")


def _parse_date(value: str, row_num: int) -> date:
    """Accept ISO dates and the US format people actually paste from spreadsheets."""
    text = value.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise PortfolioError(
        f"Row {row_num}: could not read acquisition_date {text!r}. "
        f"Use YYYY-MM-DD (e.g. 2019-03-14)."
    )


def _parse_float(value: str, column: str, row_num: int) -> float:
    """Tolerate the $ and , that survive a copy-paste out of a brokerage statement."""
    text = value.strip().replace("$", "").replace(",", "")
    try:
        return float(text)
    except ValueError:
        raise PortfolioError(
            f"Row {row_num}: {column} value {value!r} is not a number."
        ) from None


REQUIRED_COLUMNS = {"ticker", "shares", "cost_basis_per_share", "acquisition_date"}


def load_portfolio(path: str | Path) -> Portfolio:
    """Read a portfolio CSV.

    Expected columns (order doesn't matter):
        ticker, shares, cost_basis_per_share, acquisition_date,
        account_type (optional, defaults to taxable),
        is_employer_stock (optional, defaults to false)

    Lines beginning with `#` before the header are metadata:
        # client_name: Jordan Reyes
        # client_age: 41
    """
    path = Path(path)
    if not path.exists():
        raise PortfolioError(f"Portfolio file not found: {path}")

    meta: dict[str, str] = {}
    data_lines: list[str] = []

    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if stripped.startswith("#"):
            # Metadata comment; ignore anything that isn't `key: value`.
            body = stripped.lstrip("#").strip()
            if ":" in body:
                key, _, value = body.partition(":")
                meta[key.strip().lower()] = value.strip()
            continue
        if stripped:
            data_lines.append(raw)

    if not data_lines:
        raise PortfolioError(f"{path} contains no data rows.")

    reader = csv.DictReader(data_lines)
    if reader.fieldnames is None:
        raise PortfolioError(f"{path} has no header row.")

    columns = {name.strip().lower() for name in reader.fieldnames}
    missing = REQUIRED_COLUMNS - columns
    if missing:
        raise PortfolioError(
            f"{path} is missing required column(s): {', '.join(sorted(missing))}. "
            f"Found: {', '.join(sorted(columns))}"
        )

    holdings: list[Holding] = []
    for row_num, row in enumerate(reader, start=2):  # row 1 is the header
        clean = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}

        ticker = clean["ticker"].upper()
        if not ticker:
            continue  # tolerate stray blank rows

        account_type = (clean.get("account_type") or "taxable").lower()
        if account_type not in ACCOUNT_TYPES:
            raise PortfolioError(
                f"Row {row_num}: account_type {account_type!r} is not one of "
                f"{', '.join(ACCOUNT_TYPES)}."
            )

        holdings.append(
            Holding(
                ticker=ticker,
                shares=_parse_float(clean["shares"], "shares", row_num),
                cost_basis_per_share=_parse_float(
                    clean["cost_basis_per_share"], "cost_basis_per_share", row_num
                ),
                acquisition_date=_parse_date(clean["acquisition_date"], row_num),
                account_type=account_type,
                is_employer_stock=_parse_bool(clean.get("is_employer_stock", "")),
            )
        )

    if not holdings:
        raise PortfolioError(f"{path} produced no holdings.")

    def _int_meta(key: str) -> int | None:
        value = meta.get(key)
        if value is None:
            return None
        try:
            return int(value)
        except ValueError:
            return None

    return Portfolio(
        holdings=holdings,
        client_name=meta.get("client_name", path.stem.replace("_", " ").title()),
        client_age=_int_meta("client_age"),
        time_horizon_years=_int_meta("time_horizon_years"),
        notes=meta.get("notes", ""),
        meta=meta,
    )
