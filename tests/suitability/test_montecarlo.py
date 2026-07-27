"""Reproducibility tests for pra.suitability.montecarlo.run_monte_carlo.

run_monte_carlo seeds its own random.Random(SEED) on every call, so two calls
with the same profile must produce byte-identical results -- that determinism
is the entire point ("the numbers are computed, not conjured, and they don't
change under the advisor's feet"). The baseline values below were captured
from a real run against this exact profile while writing this suite, so a
future change to SEED, N_PATHS, or the simulation logic will be caught here
rather than discovered silently.
"""

from __future__ import annotations

import pytest

from pra.suitability.profile import ClientProfile, Employment, FinancialGoal, GoalType
from pra.suitability.montecarlo import run_monte_carlo


@pytest.fixture
def goal_profile():
    return ClientProfile(
        client_name="MC Test", age=40, time_horizon_years=20,
        employment=Employment.EMPLOYED, annual_income=200_000.0,
        investable_assets=300_000.0, annual_spending=0.0,
        goals=[FinancialGoal(GoalType.RETIREMENT, 1_500_000.0, 20, "high")],
    )


def test_repeated_calls_are_byte_identical(goal_profile):
    first = run_monte_carlo(goal_profile)
    second = run_monte_carlo(goal_profile)

    assert [r.name for r in first.top_routes] == [r.name for r in second.top_routes]
    for a, b in zip(first.top_routes, second.top_routes):
        assert a.success_rate == b.success_rate
        assert a.median_end == b.median_end
        assert a.downside_end == b.downside_end


def test_known_baseline_for_the_seeded_simulation(goal_profile):
    result = run_monte_carlo(goal_profile)

    assert result.applicable is True
    assert result.years == 20
    assert result.starting_value == 300_000.0
    assert result.annual_contribution == 20_000.0  # 10% of $200,000 income

    top = result.top_routes[0]
    assert top.allocation == "Aggressive (85/15)"
    assert top.strategy == "Dollar-cost averaging"
    assert top.success_rate == pytest.approx(0.6868)
    assert top.median_end == pytest.approx(1_840_676.274828822)
    assert top.downside_end == pytest.approx(1_071_398.4526201885)


def test_no_goal_is_not_applicable():
    profile = ClientProfile(goals=[])
    result = run_monte_carlo(profile)

    assert result.applicable is False
    assert result.top_routes == []
    assert "Add a financial goal" in result.note
