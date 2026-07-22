"""Valuation and allocation breakdown.

Turns tax lots plus prices into: what everything is worth, what the embedded
gain is, and how the money is split across asset classes and sectors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from ..models import CASH, OTHER, classify_asset_class
from ..portfolio import Holding, Portfolio
from ..prices import MarketData


@dataclass(frozen=True)
class ValuedLot:
    """A tax lot marked to market."""

    holding: Holding
    price: float
    asset_class: str

    @property
    def market_value(self) -> float:
        return self.holding.shares * self.price

    @property
    def unrealized_gain(self) -> float:
        return self.market_value - self.holding.cost_basis

    @property
    def gain_pct(self) -> float:
        basis = self.holding.cost_basis
        return (self.unrealized_gain / basis) if basis else 0.0

    def is_long_term(self, as_of: date) -> bool:
        return self.holding.is_long_term(as_of)


@dataclass
class Position:
    """All lots of one ticker, aggregated — how a client statement reads."""

    ticker: str
    name: str
    asset_class: str
    sector: str | None
    lots: list[ValuedLot]
    price: float
    expense_ratio: float | None = None

    @property
    def shares(self) -> float:
        return sum(lot.holding.shares for lot in self.lots)

    @property
    def market_value(self) -> float:
        return sum(lot.market_value for lot in self.lots)

    @property
    def cost_basis(self) -> float:
        return sum(lot.holding.cost_basis for lot in self.lots)

    @property
    def unrealized_gain(self) -> float:
        return self.market_value - self.cost_basis

    @property
    def gain_pct(self) -> float:
        return (self.unrealized_gain / self.cost_basis) if self.cost_basis else 0.0

    @property
    def is_employer_stock(self) -> bool:
        return any(lot.holding.is_employer_stock for lot in self.lots)

    @property
    def sheltered_value(self) -> float:
        """Market value sitting in accounts where a sale triggers no tax."""
        return sum(lot.market_value for lot in self.lots if lot.holding.is_sheltered)

    @property
    def taxable_value(self) -> float:
        return self.market_value - self.sheltered_value


@dataclass
class AllocationResult:
    total_value: float
    total_cost_basis: float
    positions: list[Position]
    by_asset_class: dict[str, float]        # asset class -> market value
    by_sector: dict[str, float]             # sector -> market value (equity only)
    by_account_type: dict[str, float]
    weighted_expense_ratio: float | None
    unclassified: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def total_unrealized_gain(self) -> float:
        return self.total_value - self.total_cost_basis

    def asset_class_weights(self) -> dict[str, float]:
        if not self.total_value:
            return {}
        return {k: v / self.total_value for k, v in self.by_asset_class.items()}

    def position_weights(self) -> dict[str, float]:
        if not self.total_value:
            return {}
        return {p.ticker: p.market_value / self.total_value for p in self.positions}


def value_portfolio(portfolio: Portfolio, market: MarketData) -> AllocationResult:
    """Mark every lot to market and roll it up into an allocation picture."""
    warnings: list[str] = []
    unclassified: list[str] = []

    # Group lots by ticker, valuing each against its current price.
    lots_by_ticker: dict[str, list[ValuedLot]] = {}
    for holding in portfolio.holdings:
        if holding.is_cash:
            # Cash is stated at face value: one "share" per dollar.
            price = 1.0
            asset_class = CASH
        else:
            if holding.ticker not in market.current_prices:
                warnings.append(f"No price for {holding.ticker}; position excluded.")
                continue
            price = market.current_prices[holding.ticker]
            meta = market.metadata.get(holding.ticker, {})
            asset_class = classify_asset_class(
                holding.ticker,
                quote_type=meta.get("quote_type"),
                category=meta.get("category"),
            )
            if asset_class == OTHER:
                unclassified.append(holding.ticker)

        lots_by_ticker.setdefault(holding.ticker, []).append(
            ValuedLot(holding=holding, price=price, asset_class=asset_class)
        )

    positions: list[Position] = []
    for ticker, lots in lots_by_ticker.items():
        meta = market.metadata.get(ticker, {})
        positions.append(
            Position(
                ticker=ticker,
                name=meta.get("name", "Cash" if ticker == "CASH" else ticker),
                asset_class=lots[0].asset_class,
                sector=meta.get("sector"),
                lots=lots,
                price=lots[0].price,
                expense_ratio=meta.get("expense_ratio"),
            )
        )

    positions.sort(key=lambda p: p.market_value, reverse=True)
    total_value = sum(p.market_value for p in positions)
    total_cost = sum(p.cost_basis for p in positions)

    by_asset_class: dict[str, float] = {}
    by_sector: dict[str, float] = {}
    by_account: dict[str, float] = {}

    for position in positions:
        by_asset_class[position.asset_class] = (
            by_asset_class.get(position.asset_class, 0.0) + position.market_value
        )
        for lot in position.lots:
            acct = lot.holding.account_type
            by_account[acct] = by_account.get(acct, 0.0) + lot.market_value

        # Sector attribution. An individual stock reports one sector; an ETF
        # reports a weight vector we can look through. Anything else is skipped
        # rather than lumped into a bucket it doesn't belong in.
        meta = market.metadata.get(position.ticker, {})
        sector_weights = meta.get("sector_weights")
        if sector_weights:
            for sector, weight in sector_weights.items():
                label = str(sector).replace("_", " ").title()
                by_sector[label] = (
                    by_sector.get(label, 0.0) + position.market_value * float(weight)
                )
        elif position.sector:
            by_sector[position.sector] = (
                by_sector.get(position.sector, 0.0) + position.market_value
            )

    # Expense ratio is weighted by the value of the positions we actually have
    # a ratio for — averaging over the whole portfolio would understate it.
    rated = [p for p in positions if p.expense_ratio is not None]
    rated_value = sum(p.market_value for p in rated)
    weighted_er = (
        sum(p.market_value * p.expense_ratio for p in rated) / rated_value
        if rated_value
        else None
    )

    if unclassified:
        warnings.append(
            f"Could not confirm asset class for: {', '.join(sorted(set(unclassified)))}. "
            "Treated as Other and excluded from target comparison."
        )

    return AllocationResult(
        total_value=total_value,
        total_cost_basis=total_cost,
        positions=positions,
        by_asset_class=by_asset_class,
        by_sector=by_sector,
        by_account_type=by_account,
        weighted_expense_ratio=weighted_er,
        unclassified=sorted(set(unclassified)),
        warnings=warnings,
    )
