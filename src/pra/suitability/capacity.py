"""Capacity — the equity ceiling.

The heart of the capacity-first design. The risk score says how much risk the
client *wants*; this module says how much they can *bear*. Capacity is expressed
as a single number — the maximum equity fraction — computed as the minimum of
several independent constraints. Whichever constraint binds is the one that
matters, and the recommendation says which.

Each constraint maps a situational fact to an equity ceiling:

  drawdown tolerance   T / (assumed severe-bear equity loss)
  time horizon         short horizons cap equity (no time to recover)
  withdrawal rate      an unsustainable drawdown plan caps equity hard
  emergency reserve    no buffer -> forced selling risk -> cap equity
  objective            capital preservation caps equity
  age                  late-retirement sequence risk caps equity

All thresholds are named constants for review.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .profile import ClientProfile, Objective
from .retirement import RetirementReadiness

# Assumed equity decline in a severe bear market, used to translate a stated
# drawdown tolerance into an equity ceiling. A portfolio that is `e` in equities
# falls roughly `e * this` at the bottom, so keeping that <= tolerance T gives
# e <= T / this.
SEVERE_BEAR_EQUITY_LOSS = 0.50

# Equity ceilings for the hard situational constraints.
NO_RESERVE_EQUITY_CAP = 0.30
PRESERVATION_EQUITY_CAP = 0.40
LATE_RETIREMENT_AGE = 72
LATE_RETIREMENT_EQUITY_CAP = 0.55

# Horizon -> equity ceiling. First matching row wins; longer horizons uncapped.
HORIZON_EQUITY_CAPS = [
    (3, 0.20),
    (5, 0.40),
    (10, 0.65),
]

# Never let a computed ceiling round to literally zero equity — even the most
# constrained plan holds some growth sleeve once reserves are set aside.
MIN_EQUITY_FLOOR = 0.05


@dataclass
class Constraint:
    label: str
    ceiling: float
    binding: bool = False


@dataclass
class CapacityCeiling:
    max_equity: float
    constraints: list[Constraint] = field(default_factory=list)

    @property
    def binding(self) -> list[Constraint]:
        return [c for c in self.constraints if c.binding]

    @property
    def binding_reason(self) -> str:
        b = self.binding
        return b[0].label if b else "no binding capacity constraint"


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def equity_ceiling(
    profile: ClientProfile, readiness: RetirementReadiness
) -> CapacityCeiling:
    """Compute the maximum suitable equity fraction and what drives it."""
    constraints: list[Constraint] = []

    # Drawdown tolerance — always present.
    dd_cap = _clamp(profile.drawdown_tolerance / SEVERE_BEAR_EQUITY_LOSS, MIN_EQUITY_FLOOR, 1.0)
    constraints.append(Constraint(
        f"{profile.drawdown_tolerance:.0%} drawdown tolerance implies a ceiling near "
        f"{dd_cap:.0%} equity (equities can fall ~{SEVERE_BEAR_EQUITY_LOSS:.0%} in a "
        f"severe bear)",
        dd_cap,
    ))

    # Time horizon.
    for years, cap in HORIZON_EQUITY_CAPS:
        if profile.time_horizon_years <= years:
            constraints.append(Constraint(
                f"{profile.time_horizon_years}-year horizon caps equity at {cap:.0%} "
                f"(limited time to recover from a decline)",
                cap,
            ))
            break

    # Withdrawal-rate readiness (decumulation).
    if readiness.applicable:
        constraints.append(Constraint(
            f"{readiness.withdrawal_rate:.1%} withdrawal rate ({readiness.status}) caps "
            f"equity at {readiness.suggested_equity_fraction:.0%}",
            readiness.suggested_equity_fraction,
        ))

    # Emergency reserve.
    if not profile.has_emergency_reserve:
        constraints.append(Constraint(
            f"no emergency reserve caps equity at {NO_RESERVE_EQUITY_CAP:.0%} until a "
            f"buffer is funded (avoids forced selling into a downturn)",
            NO_RESERVE_EQUITY_CAP,
        ))

    # Objective.
    if profile.objective == Objective.PRESERVATION:
        constraints.append(Constraint(
            f"capital-preservation objective caps equity at {PRESERVATION_EQUITY_CAP:.0%}",
            PRESERVATION_EQUITY_CAP,
        ))

    # Age / sequence risk.
    if profile.age >= LATE_RETIREMENT_AGE:
        constraints.append(Constraint(
            f"age {profile.age} (sequence-of-returns risk) caps equity at "
            f"{LATE_RETIREMENT_EQUITY_CAP:.0%}",
            LATE_RETIREMENT_EQUITY_CAP,
        ))

    max_equity = min(c.ceiling for c in constraints)
    for c in constraints:
        if abs(c.ceiling - max_equity) < 1e-9:
            c.binding = True

    return CapacityCeiling(max_equity=max_equity, constraints=constraints)
