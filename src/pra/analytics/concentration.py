"""Concentration analysis.

Diversification failures are the risk an advisor is most often the first to
notice, and the one clients most often resist hearing about — usually because
the concentrated position is the one that made them money.

The look-through check is the piece a spreadsheet misses: a client holding
employer stock directly *and* holding an S&P 500 fund has more exposure to that
company than the position line shows.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..prices import MarketData
from .allocation import AllocationResult

# Thresholds. Conventional advisory rules of thumb, stated explicitly so a
# reader can disagree with the number rather than guess at it.
SINGLE_POSITION_THRESHOLD = 0.10      # any one holding above 10% of the portfolio
EMPLOYER_STOCK_THRESHOLD = 0.10       # employer stock warrants a lower bar
SECTOR_THRESHOLD = 0.25               # any one sector above 25%
TOP_FIVE_THRESHOLD = 0.50             # top five holdings above half the portfolio

SEVERITY_ORDER = {"high": 0, "moderate": 1, "low": 2}


@dataclass(frozen=True)
class ConcentrationFlag:
    category: str      # "position" | "employer_stock" | "sector" | "top_holdings" | "overlap"
    severity: str      # "high" | "moderate" | "low"
    subject: str       # what is concentrated
    weight: float      # its share of the portfolio
    threshold: float
    message: str


@dataclass
class ConcentrationResult:
    flags: list[ConcentrationFlag]
    top_five_weight: float
    largest_position: tuple[str, float] | None
    position_count: int
    effective_holdings: float  # 1 / sum(w^2) — the "how many bets is this really" number

    @property
    def has_high_severity(self) -> bool:
        return any(f.severity == "high" for f in self.flags)

    @property
    def headline(self) -> ConcentrationFlag | None:
        """The single flag most worth leading a client conversation with."""
        if not self.flags:
            return None
        return sorted(
            self.flags,
            key=lambda f: (SEVERITY_ORDER.get(f.severity, 9), -f.weight),
        )[0]


def _severity(weight: float, threshold: float) -> str:
    """Scale severity by how far past the threshold the position sits."""
    if weight >= threshold * 2:
        return "high"
    if weight >= threshold * 1.4:
        return "moderate"
    return "low"


def analyze_concentration(
    allocation: AllocationResult,
    market: MarketData,
) -> ConcentrationResult:
    flags: list[ConcentrationFlag] = []
    weights = allocation.position_weights()
    total = allocation.total_value

    # --- Single-position concentration -----------------------------------
    for position in allocation.positions:
        if position.asset_class == "Cash":
            continue  # a large cash balance is a different conversation
        weight = weights.get(position.ticker, 0.0)

        if position.is_employer_stock and weight >= EMPLOYER_STOCK_THRESHOLD:
            flags.append(
                ConcentrationFlag(
                    category="employer_stock",
                    severity="high" if weight >= 0.20 else "moderate",
                    subject=position.ticker,
                    weight=weight,
                    threshold=EMPLOYER_STOCK_THRESHOLD,
                    message=(
                        f"{position.ticker} represents {weight:.1%} of the portfolio "
                        f"and is employer stock. Salary, benefits, and this position "
                        f"all depend on the same company, so a downturn there affects "
                        f"income and net worth at the same time."
                    ),
                )
            )
        elif weight >= SINGLE_POSITION_THRESHOLD:
            flags.append(
                ConcentrationFlag(
                    category="position",
                    severity=_severity(weight, SINGLE_POSITION_THRESHOLD),
                    subject=position.ticker,
                    weight=weight,
                    threshold=SINGLE_POSITION_THRESHOLD,
                    message=(
                        f"{position.ticker} represents {weight:.1%} of the portfolio, "
                        f"above the {SINGLE_POSITION_THRESHOLD:.0%} single-position "
                        f"guideline."
                    ),
                )
            )

    # --- Sector concentration --------------------------------------------
    for sector, value in allocation.by_sector.items():
        weight = value / total if total else 0.0
        if weight >= SECTOR_THRESHOLD:
            flags.append(
                ConcentrationFlag(
                    category="sector",
                    severity=_severity(weight, SECTOR_THRESHOLD),
                    subject=sector,
                    weight=weight,
                    threshold=SECTOR_THRESHOLD,
                    message=(
                        f"{weight:.1%} of the portfolio sits in {sector}, above the "
                        f"{SECTOR_THRESHOLD:.0%} guideline. Sector-wide declines would "
                        f"affect a large share of the portfolio at once."
                    ),
                )
            )

    # --- Top-five concentration ------------------------------------------
    sorted_weights = sorted(weights.values(), reverse=True)
    top_five = sum(sorted_weights[:5])
    if top_five >= TOP_FIVE_THRESHOLD and len(sorted_weights) > 5:
        flags.append(
            ConcentrationFlag(
                category="top_holdings",
                severity=_severity(top_five, TOP_FIVE_THRESHOLD),
                subject="Top 5 holdings",
                weight=top_five,
                threshold=TOP_FIVE_THRESHOLD,
                message=(
                    f"The five largest holdings account for {top_five:.1%} of the "
                    f"portfolio. Diversification across the remaining positions has "
                    f"limited effect on overall risk at this level."
                ),
            )
        )

    # --- Look-through overlap --------------------------------------------
    # A directly held stock that also sits inside funds the client owns.
    # Exposure is accumulated across *every* fund before being flagged — a
    # stock held inside three different index funds is one exposure problem,
    # not three, and reporting it per-fund understates the total.
    direct_tickers = {
        p.ticker for p in allocation.positions if p.asset_class == "Equity" and p.sector
    }
    indirect_exposure: dict[str, float] = {}
    via_funds: dict[str, list[str]] = {}

    for position in allocation.positions:
        top_holdings = market.metadata.get(position.ticker, {}).get("top_holdings") or {}
        if not top_holdings:
            continue
        fund_weight = weights.get(position.ticker, 0.0)

        for held_ticker, held_weight in top_holdings.items():
            symbol = str(held_ticker).upper()
            if symbol not in direct_tickers or symbol == position.ticker:
                continue
            contribution = fund_weight * float(held_weight)
            if contribution <= 0:
                continue
            indirect_exposure[symbol] = indirect_exposure.get(symbol, 0.0) + contribution
            via_funds.setdefault(symbol, []).append(position.ticker)

    for symbol, indirect in indirect_exposure.items():
        direct = weights.get(symbol, 0.0)
        combined = direct + indirect
        # Only worth raising if the look-through changes the picture materially.
        if combined <= SINGLE_POSITION_THRESHOLD or indirect < 0.005:
            continue

        funds = via_funds[symbol]
        fund_list = ", ".join(sorted(set(funds)))
        flags.append(
            ConcentrationFlag(
                category="overlap",
                severity="high" if indirect >= 0.05 else "moderate",
                subject=symbol,
                weight=combined,
                threshold=SINGLE_POSITION_THRESHOLD,
                message=(
                    f"True exposure to {symbol} is approximately {combined:.1%} once "
                    f"fund holdings are counted: {direct:.1%} held directly plus about "
                    f"{indirect:.1%} held indirectly through {fund_list}. "
                    f"The position line alone understates it."
                ),
            )
        )

    flags.sort(key=lambda f: (SEVERITY_ORDER.get(f.severity, 9), -f.weight))

    # Effective number of holdings: the inverse Herfindahl index. A portfolio
    # of 20 positions where one is 60% behaves more like 3 holdings than 20.
    hhi = sum(w * w for w in weights.values())
    effective = (1 / hhi) if hhi else 0.0

    largest = max(weights.items(), key=lambda kv: kv[1]) if weights else None

    return ConcentrationResult(
        flags=flags,
        top_five_weight=top_five,
        largest_position=largest,
        position_count=len(allocation.positions),
        effective_holdings=effective,
    )
