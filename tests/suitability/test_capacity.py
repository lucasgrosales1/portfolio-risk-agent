"""Known-value tests for pra.suitability.capacity.equity_ceiling.

Each test isolates one constraint by holding the others slack, so the binding
constraint and its ceiling can be asserted precisely. RetirementReadiness is
constructed directly (not via assess_retirement_readiness) to keep these tests
independent of the retirement module's own logic. Numbers were cross-checked
against the real implementation while writing this suite.
"""

from __future__ import annotations

import pytest

from pra.suitability.capacity import equity_ceiling
from pra.suitability.profile import ClientProfile, Objective
from pra.suitability.retirement import RetirementReadiness

NOT_APPLICABLE = RetirementReadiness(
    applicable=False,
    net_withdrawal_need=0.0,
    withdrawal_rate=0.0,
    benchmark_rate=0.04,
    status="Safe",
    suggested_equity_fraction=0.40,
    emergency_reserve_ok=True,
)

# A profile with every constraint slack except the ones a test overrides.
BASE_KWARGS = dict(
    drawdown_tolerance=0.50,       # dd_cap = 1.0, not binding
    time_horizon_years=25,         # no horizon row matches (> 10 years)
    age=50,                        # below the late-retirement age
    objective=Objective.GROWTH,    # not preservation
    has_emergency_reserve=True,
)


def _ceiling(readiness=NOT_APPLICABLE, **overrides):
    profile = ClientProfile(**{**BASE_KWARGS, **overrides})
    return equity_ceiling(profile, readiness)


def test_drawdown_tolerance_binds_when_it_is_the_tightest_constraint():
    result = _ceiling(drawdown_tolerance=0.10)  # dd_cap = 0.10 / 0.50 = 0.20
    assert result.max_equity == pytest.approx(0.20)
    assert len(result.binding) == 1
    assert "drawdown tolerance" in result.binding_reason


def test_drawdown_tolerance_clamps_to_the_min_equity_floor():
    result = _ceiling(drawdown_tolerance=0.01)  # 0.01/0.50 = 0.02, below the 5% floor
    assert result.max_equity == pytest.approx(0.05)


def test_short_horizon_binds():
    result = _ceiling(time_horizon_years=4)  # <= 5 -> 40% cap
    assert result.max_equity == pytest.approx(0.40)
    assert "horizon" in result.binding_reason


def test_no_emergency_reserve_binds():
    result = _ceiling(has_emergency_reserve=False)
    assert result.max_equity == pytest.approx(0.30)
    assert "emergency reserve" in result.binding_reason


def test_preservation_objective_binds():
    result = _ceiling(drawdown_tolerance=0.90, objective=Objective.PRESERVATION)
    assert result.max_equity == pytest.approx(0.40)
    assert "preservation" in result.binding_reason


def test_late_retirement_age_binds():
    result = _ceiling(drawdown_tolerance=0.90, age=75)
    assert result.max_equity == pytest.approx(0.55)
    assert "age 75" in result.binding_reason


def test_retirement_readiness_ceiling_binds_when_applicable():
    readiness = RetirementReadiness(
        applicable=True,
        net_withdrawal_need=40_000.0,
        withdrawal_rate=0.05,
        benchmark_rate=0.04,
        status="Caution",
        suggested_equity_fraction=0.30,
        emergency_reserve_ok=True,
    )
    result = _ceiling(readiness, drawdown_tolerance=0.90)
    assert result.max_equity == pytest.approx(0.30)
    assert "withdrawal rate" in result.binding_reason


def test_tied_constraints_are_all_marked_binding():
    # 20% drawdown tolerance -> 0.40 ceiling; a 4-year horizon -> 0.40 ceiling too.
    result = _ceiling(drawdown_tolerance=0.20, time_horizon_years=4)
    assert result.max_equity == pytest.approx(0.40)
    assert len(result.binding) == 2
    labels = {c.label for c in result.binding}
    assert any("drawdown tolerance" in label for label in labels)
    assert any("horizon" in label for label in labels)
