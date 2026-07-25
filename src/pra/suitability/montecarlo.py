"""Monte Carlo simulation of routes to a financial goal.

A "route" is an allocation paired with an implementation strategy. For each
route this runs many simulated market paths and measures how often the portfolio
reaches the client's primary goal, then ranks the top routes by probability of
success — with the *why*: success rate, the typical (median) outcome, and the
downside (10th-percentile) result.

The randomness is seeded, so results are reproducible run to run — the same
discipline as the rest of the project: the numbers are computed, not conjured,
and they don't change under the advisor's feet.

Return assumptions are illustrative planning inputs, stated in the output, not
forecasts.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from .profile import ClientProfile

# Reproducible.
SEED = 20260724
N_PATHS = 5000

# Asset-class assumptions (nominal annual).
EQUITY_MEAN, EQUITY_STD = 0.08, 0.17
BOND_MEAN, BOND_STD = 0.035, 0.055
CASH_MEAN, CASH_STD = 0.02, 0.008

# Candidate allocations by equity fraction (the four models).
_ALLOCATIONS = {
    "Conservative (20/80)": 0.20,
    "Moderate (40/60)": 0.40,
    "Balanced Growth (60/40)": 0.60,
    "Aggressive (85/15)": 0.85,
}


@dataclass
class Route:
    name: str
    allocation: str
    strategy: str
    success_rate: float          # P(reach goal)
    median_end: float
    downside_end: float          # 10th percentile
    goal_amount: float
    reason: str = ""


@dataclass
class MonteCarloResult:
    applicable: bool
    goal_label: str
    goal_amount: float
    years: int
    starting_value: float
    annual_contribution: float
    top_routes: list[Route] = field(default_factory=list)
    note: str = ""


def _blended_moments(equity: float) -> tuple[float, float]:
    """Mean and std of a portfolio at a given equity fraction (bond is the rest)."""
    bond = 1 - equity
    mean = equity * EQUITY_MEAN + bond * BOND_MEAN
    # Variance assuming low equity/bond correlation (~0.15).
    var = (equity ** 2 * EQUITY_STD ** 2 + bond ** 2 * BOND_STD ** 2
           + 2 * equity * bond * 0.15 * EQUITY_STD * BOND_STD)
    return mean, math.sqrt(var)


def _strategy_variants(equity: float) -> list[tuple[str, float, float, str]]:
    """Return (strategy_name, mean, std, entry) variants for an allocation.

    `entry` = 'lump' invests immediately; 'phased' averages in over the first
    third of the horizon (modeled as reduced early volatility).
    """
    mean, std = _blended_moments(equity)
    variants = [("Lump-sum", mean, std, "lump")]
    # DCA: slightly lower mean (cash drag while entering), lower std.
    variants.append(("Dollar-cost averaging", mean * 0.97, std * 0.88, "phased"))
    # Barbell: safe core + aggressive sleeve — same average equity but fatter,
    # modeled here as a modest vol increase with a small return premium.
    b_mean, b_std = _blended_moments(equity)
    variants.append(("Barbell", b_mean * 1.02, b_std * 1.10, "lump"))
    # Laddering: bond-income tilt — lower mean and much lower vol.
    l_equity = max(0.0, equity - 0.15)
    l_mean, l_std = _blended_moments(l_equity)
    variants.append(("Bond laddering", l_mean, l_std * 0.85, "lump"))
    return variants


def _simulate(mean: float, std: float, entry: str, start: float,
              contribution: float, years: int, rng: random.Random) -> float:
    """One simulated path; returns the terminal value."""
    value = start
    for year in range(years):
        r = rng.gauss(mean, std)
        # Phased entry dampens volatility in the first third of the horizon.
        if entry == "phased" and year < max(1, years // 3):
            r = rng.gauss(mean, std * 0.5)
        value = value * (1 + r) + contribution
    return value


def run_monte_carlo(profile: ClientProfile) -> MonteCarloResult:
    """Rank routes to the client's primary goal by probability of success."""
    goal = profile.primary_goal
    if goal is None or goal.target_amount <= 0 or goal.years <= 0:
        return MonteCarloResult(
            applicable=False, goal_label="", goal_amount=0.0, years=0,
            starting_value=profile.investable_assets, annual_contribution=0.0,
            note="Add a financial goal (target amount and year) to simulate routes to it.")

    start = profile.investable_assets
    years = goal.years
    # A simple contribution assumption: for accumulation goals, assume the client
    # can save ~10% of income annually; for withdrawal-phase clients, zero.
    contribution = 0.0 if profile.net_withdrawal_need > 0 else round(profile.annual_income * 0.10)

    rng = random.Random(SEED)
    routes: list[Route] = []
    for alloc_name, equity in _ALLOCATIONS.items():
        for strat_name, mean, std, entry in _strategy_variants(equity):
            ends = [_simulate(mean, std, entry, start, contribution, years, rng)
                    for _ in range(N_PATHS)]
            ends.sort()
            success = sum(1 for e in ends if e >= goal.target_amount) / len(ends)
            median = ends[len(ends) // 2]
            downside = ends[int(len(ends) * 0.10)]
            routes.append(Route(
                name=f"{alloc_name} · {strat_name}",
                allocation=alloc_name, strategy=strat_name,
                success_rate=success, median_end=median, downside_end=downside,
                goal_amount=goal.target_amount))

    # Rank by success, then by downside protection, then median.
    routes.sort(key=lambda r: (r.success_rate, r.downside_end, r.median_end), reverse=True)
    top = routes[:5]
    for r in top:
        r.reason = _route_reason(r, goal.target_amount)

    return MonteCarloResult(
        applicable=True, goal_label=goal.label, goal_amount=goal.target_amount,
        years=years, starting_value=start, annual_contribution=contribution,
        top_routes=top,
        note=(f"{N_PATHS:,} simulated paths per route over {years} years, starting from "
              f"${start:,.0f}"
              + (f" plus ${contribution:,.0f}/yr in contributions" if contribution else "")
              + f", toward a ${goal.target_amount:,.0f} goal. Assumes ~8% equity / 3.5% "
              f"bond nominal returns; illustrative, not a forecast."))


def _route_reason(r: Route, target: float) -> str:
    if r.success_rate >= 0.85:
        conf = "a high probability of reaching the goal"
    elif r.success_rate >= 0.65:
        conf = "a solid but not certain chance of reaching the goal"
    else:
        conf = "a below-even chance of reaching the goal as stated"
    return (f"{r.strategy} on a {r.allocation.split(' (')[0]} allocation gives {conf} "
            f"({r.success_rate:.0%}); in a poor market it still lands near "
            f"${r.downside_end:,.0f}, versus a typical ${r.median_end:,.0f}.")
