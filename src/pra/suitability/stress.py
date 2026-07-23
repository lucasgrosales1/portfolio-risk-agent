"""Sequence-of-returns stress test.

The single most important risk in decumulation, and the one a simple average
return hides completely. Two portfolios can earn the *identical* set of annual
returns and end up worlds apart — because a retiree taking withdrawals during an
early downturn sells shares into the decline and never recovers, while the same
downturn late in retirement barely matters.

This module demonstrates exactly that. It runs three scenarios over a longevity
horizon:

  Steady      every year earns the expected return
  Early bear  a severe decline in the first years, then recovery
  Late bear   the *same annual returns as Early bear, reversed* — crash at the end

Because Early and Late use the same returns in a different order, a version with
no withdrawals would end identically. With withdrawals, Early can deplete the
portfolio while Late survives. That gap is sequence-of-returns risk, made visible.

Deterministic and reproducible — no randomness, no Monte Carlo (that's a later
stage). Every assumption is a named constant.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Nominal expected returns and inflation. Illustrative planning assumptions,
# stated in the output rather than presented as forecasts.
EQUITY_EXPECTED = 0.08
BOND_EXPECTED = 0.035
INFLATION = 0.025

# The stress path, expressed at the asset-class level so a portfolio's equity
# fraction determines how hard the crash hits it. First years are a severe bear
# with a flight to quality in bonds, then a recovery, then trend returns.
EQUITY_STRESS_PATH = [-0.35, -0.08, 0.30, 0.20]
BOND_STRESS_PATH = [0.06, 0.05, 0.01, 0.02]

# Plan to this age; the horizon is years from the client's age to here.
PLANNING_AGE = 95
MIN_HORIZON_YEARS = 10
MAX_HORIZON_YEARS = 35


@dataclass
class YearPoint:
    year: int
    start_value: float
    withdrawal: float
    return_pct: float
    end_value: float


@dataclass
class Scenario:
    name: str
    description: str
    path: list[YearPoint]
    survived: bool
    depletion_year: int | None
    terminal_value: float

    @property
    def values(self) -> list[float]:
        """End-of-year values, for charting."""
        return [p.end_value for p in self.path]


@dataclass
class StressTest:
    applicable: bool
    horizon_years: int
    equity_fraction: float
    starting_value: float
    base_withdrawal: float
    scenarios: list[Scenario] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)

    def scenario(self, name: str) -> Scenario | None:
        return next((s for s in self.scenarios if s.name == name), None)


def _portfolio_returns(equity_seq: list[float], bond_seq: list[float], equity: float) -> list[float]:
    return [equity * e + (1 - equity) * b for e, b in zip(equity_seq, bond_seq)]


def _build_sequences(horizon: int) -> tuple[list[float], list[float], list[float], list[float], list[float], list[float]]:
    """Return (steady_eq, steady_bd, early_eq, early_bd, late_eq, late_bd)."""
    steady_eq = [EQUITY_EXPECTED] * horizon
    steady_bd = [BOND_EXPECTED] * horizon

    fill = max(0, horizon - len(EQUITY_STRESS_PATH))
    early_eq = (EQUITY_STRESS_PATH + [EQUITY_EXPECTED] * fill)[:horizon]
    early_bd = (BOND_STRESS_PATH + [BOND_EXPECTED] * fill)[:horizon]

    # Late bear is the exact reverse — same returns, crash at the end.
    late_eq = list(reversed(early_eq))
    late_bd = list(reversed(early_bd))

    return steady_eq, steady_bd, early_eq, early_bd, late_eq, late_bd


def _simulate(
    name: str,
    description: str,
    returns: list[float],
    starting_value: float,
    base_withdrawal: float,
) -> Scenario:
    """Run one return path with inflation-growing withdrawals taken at year start."""
    value = starting_value
    path: list[YearPoint] = []
    depletion_year: int | None = None

    for i, r in enumerate(returns):
        year = i + 1
        withdrawal = base_withdrawal * (1 + INFLATION) ** i
        start = value

        after_withdrawal = value - withdrawal
        if after_withdrawal <= 0 and depletion_year is None:
            depletion_year = year
            after_withdrawal = 0.0

        value = max(0.0, after_withdrawal * (1 + r))
        path.append(YearPoint(year, start, withdrawal, r, value))

        if value <= 0 and depletion_year is None:
            depletion_year = year

    return Scenario(
        name=name,
        description=description,
        path=path,
        survived=depletion_year is None,
        depletion_year=depletion_year,
        terminal_value=value,
    )


def run_stress_test(
    age: int,
    equity_fraction: float,
    starting_value: float,
    base_withdrawal: float,
) -> StressTest:
    """Run the three-scenario sequence-of-returns stress test.

    Only meaningful when the portfolio funds withdrawals — without them, the
    order of returns doesn't change the ending value, so the test doesn't apply.
    """
    if base_withdrawal <= 0 or starting_value <= 0:
        return StressTest(
            applicable=False,
            horizon_years=0,
            equity_fraction=equity_fraction,
            starting_value=starting_value,
            base_withdrawal=base_withdrawal,
            findings=["Sequence-of-returns risk applies to portfolios funding "
                      "withdrawals. With no withdrawals, the order of returns does "
                      "not change the ending value."],
        )

    horizon = max(MIN_HORIZON_YEARS, min(MAX_HORIZON_YEARS, PLANNING_AGE - age))
    s_eq, s_bd, e_eq, e_bd, l_eq, l_bd = _build_sequences(horizon)

    steady = _simulate(
        "Steady", "Every year earns the expected return.",
        _portfolio_returns(s_eq, s_bd, equity_fraction), starting_value, base_withdrawal)
    early = _simulate(
        "Early bear", "A severe decline in the first years, then recovery.",
        _portfolio_returns(e_eq, e_bd, equity_fraction), starting_value, base_withdrawal)
    late = _simulate(
        "Late bear", "The same annual returns as Early bear, reversed — crash at the end.",
        _portfolio_returns(l_eq, l_bd, equity_fraction), starting_value, base_withdrawal)

    findings: list[str] = []
    if not early.survived and late.survived:
        findings.append(
            f"The same returns in a different order change the outcome entirely: with "
            f"the downturn early, the portfolio depletes in year {early.depletion_year}; "
            f"with the identical returns late, it survives the full "
            f"{horizon}-year horizon. That gap is sequence-of-returns risk."
        )
    elif not early.survived:
        findings.append(
            f"Under an early downturn the portfolio depletes in year "
            f"{early.depletion_year} of {horizon}. The withdrawal load leaves no room "
            f"to recover from a poor start."
        )
    elif early.terminal_value < late.terminal_value * 0.6:
        findings.append(
            f"The portfolio survives all three scenarios, but an early downturn leaves "
            f"roughly ${early.terminal_value:,.0f} versus ${late.terminal_value:,.0f} "
            f"if the same returns arrive late — the cost of a bad start while withdrawing."
        )
    else:
        findings.append(
            f"The portfolio survives all three scenarios with a comfortable margin, "
            f"indicating limited sequence-of-returns exposure at this withdrawal level "
            f"and allocation."
        )

    return StressTest(
        applicable=True,
        horizon_years=horizon,
        equity_fraction=equity_fraction,
        starting_value=starting_value,
        base_withdrawal=base_withdrawal,
        scenarios=[steady, early, late],
        findings=findings,
    )
