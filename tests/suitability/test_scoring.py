"""Known-value tests for pra.suitability.scoring.score_profile.

Both profiles below were hand-scored against the documented weights/point
tables in scoring.py, then cross-checked against the real implementation
while writing this suite.
"""

from __future__ import annotations

import pytest

from pra.suitability.profile import ClientProfile, Employment, Objective, RiskTolerance
from pra.suitability.scoring import score_profile


def test_mid_tier_profile_scores_and_recommends_balanced_growth():
    profile = ClientProfile(
        risk_tolerance=RiskTolerance.MODERATE,       # 50 pts * 0.25 = 12.5
        objective=Objective.BALANCED,                # 60 pts * 0.15 = 9.0
        drawdown_tolerance=0.20,                     # 50 pts * 0.20 = 10.0 (0.20/0.40*100)
        time_horizon_years=20,                       # 100 pts * 0.22 = 22.0 (>= ceiling)
        has_emergency_reserve=True,                  # cushion: 50+20=70
        net_worth=500_000.0,
        liquid_net_worth=250_000.0,                  # liquid_ratio 0.5 -> +15 = 85
        near_term_withdrawal=0.0,
        employment=Employment.EMPLOYED,
    )

    result = score_profile(profile)

    assert result.raw_score == pytest.approx(68.8)
    assert result.recommended_model == "balanced_growth"
    assert result.profile_label == "Balanced Growth"

    by_name = {c.name: c for c in result.components}
    assert by_name["Stated risk tolerance"].contribution == pytest.approx(12.5)
    assert by_name["Investment objective"].contribution == pytest.approx(9.0)
    assert by_name["Drawdown tolerance"].contribution == pytest.approx(10.0)
    assert by_name["Time horizon"].contribution == pytest.approx(22.0)
    assert by_name["Financial cushion"].raw == pytest.approx(85.0)
    assert by_name["Financial cushion"].contribution == pytest.approx(15.3)


def test_worst_case_profile_clamps_to_conservative():
    profile = ClientProfile(
        risk_tolerance=RiskTolerance.CONSERVATIVE,   # 10 pts * 0.25 = 2.5
        objective=Objective.PRESERVATION,            # 10 pts * 0.15 = 1.5
        drawdown_tolerance=0.0,                      # 0 pts
        time_horizon_years=3,                        # 0 pts (at the floor)
        has_emergency_reserve=False,                 # cushion penalties clamp to 0
        net_worth=100_000.0,
        liquid_net_worth=10_000.0,                   # liquid_ratio 0.1 -> thin
        near_term_withdrawal=25_000.0,                # 25% of net worth -> large withdrawal
        employment=Employment.NOT_EMPLOYED,
    )

    result = score_profile(profile)

    assert result.raw_score == pytest.approx(4.0)
    assert result.recommended_model == "conservative"
    assert result.profile_label == "Conservative"

    cushion = next(c for c in result.components if c.name == "Financial cushion")
    assert cushion.raw == 0.0  # clamped at the floor, not negative
    assert "no emergency reserve" in cushion.note
    assert "thin liquid net worth" in cushion.note
    assert "large near-term withdrawal" in cushion.note
    assert "no earned income" in cushion.note


def test_score_model_property_is_unaffected_before_capacity_overrides():
    profile = ClientProfile(risk_tolerance=RiskTolerance.MODERATE, time_horizon_years=20)
    result = score_profile(profile)

    # score_profile never applies capacity overrides itself (that happens in
    # pra.suitability.recommend), so recommended_model always equals score_model.
    assert result.recommended_model == result.score_model
    assert result.was_capped is False
    assert result.overrides == []
