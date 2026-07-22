"""Drift from target, and what it would actually cost to close it.

Most portfolio tools stop at "you're 18% overweight equity, sell $150,000."
That answer is incomplete, because selling $150,000 of a position with a large
embedded gain in a taxable account is a very different act from selling the
same amount inside an IRA.

So this module does two things a naive rebalancer doesn't:

  1. Sources sales from sheltered accounts first, since those trigger no tax.
  2. Prices the tax cost of whatever must still come from taxable accounts,
     splitting long-term from short-term gains, because they are taxed at
     materially different rates.

The output is framed as drift from a stated target — never as a recommendation
to buy or sell a particular security.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from ..models import ASSET_CLASSES, CASH, ModelPortfolio
from .allocation import AllocationResult, Position, ValuedLot

# Illustrative federal rates used to size the tax drag. These are assumptions
# for planning discussion, not a tax calculation — no state tax, no NIIT,
# no bracket detail. The report says so.
ASSUMED_LONG_TERM_RATE = 0.15
ASSUMED_SHORT_TERM_RATE = 0.32

# Drift below this is noise, not a rebalancing trigger.
DRIFT_TOLERANCE = 0.03


@dataclass(frozen=True)
class ClassDrift:
    asset_class: str
    current_weight: float
    target_weight: float
    current_value: float
    target_value: float

    @property
    def drift(self) -> float:
        """Positive means overweight the target."""
        return self.current_weight - self.target_weight

    @property
    def dollar_gap(self) -> float:
        """Positive means this class needs to shrink by this many dollars."""
        return self.current_value - self.target_value

    @property
    def is_material(self) -> bool:
        return abs(self.drift) >= DRIFT_TOLERANCE

    @property
    def direction(self) -> str:
        if not self.is_material:
            return "on target"
        return "overweight" if self.drift > 0 else "underweight"


@dataclass
class TradeLeg:
    """A proposed reduction in one position, sourced lot by lot."""

    ticker: str
    asset_class: str
    dollars: float
    shares: float
    account_type: str
    realized_gain: float
    is_long_term: bool
    estimated_tax: float

    @property
    def is_sheltered(self) -> bool:
        return self.account_type in ("traditional", "roth")


@dataclass
class RebalanceResult:
    model: ModelPortfolio
    drifts: list[ClassDrift]
    sells: list[TradeLeg]
    buys: dict[str, float]           # asset class -> dollars to add
    total_tax_cost: float
    tax_free_proceeds: float
    taxable_proceeds: float
    unrealized_gain_deferred: float  # gain left untouched by this plan
    notes: list[str] = field(default_factory=list)

    @property
    def needs_rebalancing(self) -> bool:
        return any(d.is_material for d in self.drifts)

    @property
    def total_turnover(self) -> float:
        return sum(leg.dollars for leg in self.sells)

    @property
    def tax_cost_pct_of_turnover(self) -> float:
        return (self.total_tax_cost / self.total_turnover) if self.total_turnover else 0.0


def compute_drift(
    allocation: AllocationResult, model: ModelPortfolio
) -> list[ClassDrift]:
    """Compare current asset-class weights to the model's targets."""
    total = allocation.total_value
    weights = allocation.asset_class_weights()

    classes = [c for c in ASSET_CLASSES if c in weights or model.target_for(c) > 0]

    drifts = []
    for asset_class in classes:
        current_weight = weights.get(asset_class, 0.0)
        target_weight = model.target_for(asset_class)
        drifts.append(
            ClassDrift(
                asset_class=asset_class,
                current_weight=current_weight,
                target_weight=target_weight,
                current_value=allocation.by_asset_class.get(asset_class, 0.0),
                target_value=target_weight * total,
            )
        )

    drifts.sort(key=lambda d: abs(d.drift), reverse=True)
    return drifts


def _lot_sale_priority(lot: ValuedLot, as_of: date) -> tuple:
    """Order lots by how cheap they are to sell.

    Sheltered first (no tax at all), then losses (which offset gains), then
    long-term gains, then short-term. Within each tier, smallest gain first.
    """
    sheltered = 0 if lot.holding.is_sheltered else 1
    if lot.unrealized_gain <= 0:
        tier = 0
    elif lot.is_long_term(as_of):
        tier = 1
    else:
        tier = 2
    return (sheltered, tier, lot.unrealized_gain)


def _sell_from_position(
    position: Position,
    dollars_needed: float,
    as_of: date,
) -> list[TradeLeg]:
    """Source a dollar amount from one position, cheapest lots first."""
    legs: list[TradeLeg] = []
    remaining = dollars_needed

    for lot in sorted(position.lots, key=lambda l: _lot_sale_priority(l, as_of)):
        if remaining <= 0.01:
            break

        lot_value = lot.market_value
        if lot_value <= 0:
            continue

        take = min(remaining, lot_value)
        fraction = take / lot_value

        shares = lot.holding.shares * fraction
        realized_gain = lot.unrealized_gain * fraction
        long_term = lot.is_long_term(as_of)

        if lot.holding.is_sheltered:
            tax = 0.0
        elif realized_gain <= 0:
            tax = 0.0  # a loss creates no liability (and may offset other gains)
        else:
            rate = ASSUMED_LONG_TERM_RATE if long_term else ASSUMED_SHORT_TERM_RATE
            tax = realized_gain * rate

        legs.append(
            TradeLeg(
                ticker=position.ticker,
                asset_class=position.asset_class,
                dollars=take,
                shares=shares,
                account_type=lot.holding.account_type,
                realized_gain=realized_gain,
                is_long_term=long_term,
                estimated_tax=tax,
            )
        )
        remaining -= take

    return legs


def build_rebalance_plan(
    allocation: AllocationResult,
    model: ModelPortfolio,
    as_of: date | None = None,
) -> RebalanceResult:
    """Compute drift and a tax-aware plan to close it."""
    as_of = as_of or date.today()
    drifts = compute_drift(allocation, model)
    notes: list[str] = []

    sells: list[TradeLeg] = []
    buys: dict[str, float] = {}

    for drift in drifts:
        if not drift.is_material:
            continue

        if drift.dollar_gap > 0:
            # Overweight: raise this many dollars from this asset class.
            needed = drift.dollar_gap
            candidates = [
                p
                for p in allocation.positions
                if p.asset_class == drift.asset_class and p.asset_class != CASH
            ]
            # Trim the largest positions first — that's where the concentration is.
            candidates.sort(key=lambda p: p.market_value, reverse=True)

            for position in candidates:
                if needed <= 0.01:
                    break
                take = min(needed, position.market_value)
                legs = _sell_from_position(position, take, as_of)
                sells.extend(legs)
                needed -= sum(leg.dollars for leg in legs)

            if needed > 1.0:
                notes.append(
                    f"Could not fully source the {drift.asset_class} reduction; "
                    f"${needed:,.0f} remains unallocated."
                )
        else:
            buys[drift.asset_class] = -drift.dollar_gap

    total_tax = sum(leg.estimated_tax for leg in sells)
    sheltered_proceeds = sum(leg.dollars for leg in sells if leg.is_sheltered)
    taxable_proceeds = sum(leg.dollars for leg in sells if not leg.is_sheltered)

    # How much embedded gain the plan leaves alone — the deferral this approach buys.
    total_gain = allocation.total_unrealized_gain
    realized = sum(leg.realized_gain for leg in sells)
    deferred = total_gain - realized

    if sheltered_proceeds > 0 and taxable_proceeds == 0:
        notes.append(
            "The full rebalance can be sourced from tax-sheltered accounts, so no "
            "capital gains would be realized."
        )
    elif sheltered_proceeds > 0:
        notes.append(
            f"${sheltered_proceeds:,.0f} of the rebalance is sourced from sheltered "
            f"accounts at no tax cost; the remaining ${taxable_proceeds:,.0f} comes "
            f"from taxable accounts."
        )

    short_term_legs = [
        leg for leg in sells if not leg.is_long_term and not leg.is_sheltered
        and leg.realized_gain > 0
    ]
    if short_term_legs:
        st_total = sum(leg.realized_gain for leg in short_term_legs)
        notes.append(
            f"${st_total:,.0f} of the realized gain would be short-term and taxed as "
            f"ordinary income. Deferring those sales past the one-year mark would "
            f"reduce the tax cost."
        )

    return RebalanceResult(
        model=model,
        drifts=drifts,
        sells=sells,
        buys=buys,
        total_tax_cost=total_tax,
        tax_free_proceeds=sheltered_proceeds,
        taxable_proceeds=taxable_proceeds,
        unrealized_gain_deferred=deferred,
        notes=notes,
    )
