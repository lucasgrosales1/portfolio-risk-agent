"""Known-value tests for pra.suitability.recommend.build_recommendation.

This is the capacity-reconciliation layer: the model the risk score DESIRES,
capped at the maximum equity the situation can BEAR. Both scenarios were
cross-checked against the real implementation while writing this suite.
"""

from __future__ import annotations

import pytest

from pra.suitability.profile import ClientProfile, Employment, Experience, Objective, RiskTolerance
from pra.suitability.recommend import build_recommendation


def test_capacity_caps_a_high_desire_when_there_is_no_emergency_reserve():
    profile = ClientProfile(
        risk_tolerance=RiskTolerance.AGGRESSIVE, objective=Objective.GROWTH,
        drawdown_tolerance=0.40, time_horizon_years=25,
        has_emergency_reserve=False, net_worth=500_000.0, liquid_net_worth=250_000.0,
        employment=Employment.EMPLOYED, investable_assets=500_000.0, annual_spending=0.0,
        experience=Experience.GOOD,
    )

    rec = build_recommendation(profile)

    assert rec.assessment.raw_score == pytest.approx(85.2)
    assert rec.desired_model == "aggressive"
    # No emergency reserve caps equity at 30%; the highest model at or below
    # that ceiling is "conservative" (20% equity) -- moderate (40%) is over.
    assert rec.recommended_model == "conservative"
    assert rec.capped is True
    assert rec.capacity.max_equity == pytest.approx(0.30)
    assert rec.branch == "accumulation"
    assert any("no emergency reserve" in r.lower() for r in rec.rationale)


def test_capacity_does_not_cap_when_the_ceiling_is_ample():
    profile = ClientProfile(
        risk_tolerance=RiskTolerance.MODERATE, objective=Objective.BALANCED,
        drawdown_tolerance=0.20, time_horizon_years=20,
        has_emergency_reserve=True, net_worth=500_000.0, liquid_net_worth=250_000.0,
        employment=Employment.EMPLOYED, investable_assets=500_000.0, annual_spending=0.0,
    )

    rec = build_recommendation(profile)

    # Same 68.8 raw score as the scoring known-value test -> desires balanced_growth,
    # but a 20% drawdown tolerance caps equity at 40%, one tier below.
    assert rec.assessment.raw_score == pytest.approx(68.8)
    assert rec.desired_model == "balanced_growth"
    assert rec.recommended_model == "moderate"
    assert rec.capped is True
    assert rec.capacity.max_equity == pytest.approx(0.40)


def test_decumulation_branch_when_readiness_is_applicable():
    profile = ClientProfile(
        employment=Employment.RETIRED, age=68, investable_assets=1_000_000.0,
        annual_spending=54_000.0, social_security_income=8_000.0,
        near_term_withdrawal=0.0, has_emergency_reserve=True,
    )
    rec = build_recommendation(profile)

    assert rec.branch == "decumulation"
    assert rec.readiness.applicable is True
    assert rec.readiness.status == "Caution"
