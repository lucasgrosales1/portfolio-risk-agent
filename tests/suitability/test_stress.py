"""Known-value tests for pra.suitability.stress.run_stress_test.

The core scenario below demonstrates the module's whole point: the same
sequence of returns, reversed, produces a very different outcome once
withdrawals are involved. Age 90 pins the horizon at the 10-year floor
(95 - 90 = 5, but MIN_HORIZON_YEARS = 10 wins), which keeps the simulation
short enough to fully hand-verify. Expected terminal values were derived by
independently reimplementing the documented simulation loop (not by calling
the source) and cross-checked against the real implementation while writing
this suite.
"""

from __future__ import annotations

import pytest

from pra.suitability.stress import run_stress_test


@pytest.fixture
def demonstration_stress_test():
    return run_stress_test(
        age=90, equity_fraction=0.60, starting_value=1_000_000.0, base_withdrawal=110_000.0
    )


def test_horizon_is_pinned_at_the_ten_year_floor(demonstration_stress_test):
    assert demonstration_stress_test.applicable is True
    assert demonstration_stress_test.horizon_years == 10


def test_early_bear_depletes_the_portfolio(demonstration_stress_test):
    early = demonstration_stress_test.scenario("Early bear")
    assert early.survived is False
    assert early.depletion_year == 9
    assert early.terminal_value == 0.0


def test_late_bear_survives_with_the_same_returns_reversed(demonstration_stress_test):
    late = demonstration_stress_test.scenario("Late bear")
    assert late.survived is True
    assert late.depletion_year is None
    assert late.terminal_value == pytest.approx(123_489.77225584298)


def test_steady_scenario_survives(demonstration_stress_test):
    steady = demonstration_stress_test.scenario("Steady")
    assert steady.survived is True
    assert steady.terminal_value == pytest.approx(104_700.37116057082)


def test_findings_name_the_sequence_of_returns_gap(demonstration_stress_test):
    findings = " ".join(demonstration_stress_test.findings)
    assert "sequence-of-returns risk" in findings
    assert "year 9" in findings
    assert "10-year horizon" in findings


def test_not_applicable_with_no_withdrawal():
    result = run_stress_test(age=70, equity_fraction=0.60, starting_value=1_000_000.0, base_withdrawal=0.0)
    assert result.applicable is False
    assert result.scenarios == []
    assert "withdrawals" in result.findings[0]


def test_comfortable_withdrawal_survives_all_scenarios_with_margin():
    result = run_stress_test(
        age=90, equity_fraction=0.60, starting_value=1_000_000.0, base_withdrawal=20_000.0
    )
    assert all(s.survived for s in result.scenarios)
    assert "comfortable margin" in result.findings[0]
