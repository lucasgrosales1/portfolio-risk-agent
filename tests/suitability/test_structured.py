"""Known-value tests for pra.suitability.structured.

Covers both layers: the pure payoff formulas (exact known-value math, no
ClientProfile needed) and the gating logic (which products get recommended or
declined, and why). Every scenario was cross-checked against the real
implementation while writing this suite.
"""

from __future__ import annotations

import pytest

from pra.suitability.profile import ClientProfile, Experience, Objective, RiskTolerance
from pra.suitability.structured import (
    BUFFERED_ETF_TERMS,
    INCOME_NOTE_TERMS,
    PRINCIPAL_PROTECTED_TERMS,
    _buffered_payoff,
    _income_note_payoff,
    _principal_protected_payoff,
    evaluate_structured_products,
    size_sleeve,
)


# ---------------------------------------------------------------------------
# Payoff formulas -- pure functions, exact known values.
# ---------------------------------------------------------------------------
def test_income_note_payoff_caps_at_total_coupon_above_the_barrier():
    t = INCOME_NOTE_TERMS  # 8% coupon * 2 years = 16% total; barrier at -40%
    assert _income_note_payoff(0.10, t) == pytest.approx(0.16)
    assert _income_note_payoff(-0.40, t) == pytest.approx(0.16)  # exactly at the barrier


def test_income_note_payoff_below_barrier_loses_1_for_1_plus_coupon():
    t = INCOME_NOTE_TERMS
    assert _income_note_payoff(-0.41, t) == pytest.approx(0.16 - 0.41)
    assert _income_note_payoff(-0.60, t) == pytest.approx(0.16 - 0.60)


def test_buffered_payoff_caps_upside_and_absorbs_the_buffer():
    t = BUFFERED_ETF_TERMS  # 15% buffer, 16% cap
    assert _buffered_payoff(0.10, t) == pytest.approx(0.10)
    assert _buffered_payoff(0.20, t) == pytest.approx(0.16)  # capped
    assert _buffered_payoff(-0.10, t) == pytest.approx(0.0)  # absorbed by the buffer
    assert _buffered_payoff(-0.15, t) == pytest.approx(0.0)  # exactly at the buffer edge
    assert _buffered_payoff(-0.30, t) == pytest.approx(-0.15)  # loss beyond the buffer


def test_principal_protected_payoff_never_loses_principal():
    t = PRINCIPAL_PROTECTED_TERMS  # 100% participation, 30% cap
    assert _principal_protected_payoff(0.20, t) == pytest.approx(0.20)
    assert _principal_protected_payoff(0.50, t) == pytest.approx(0.30)  # capped
    assert _principal_protected_payoff(-0.30, t) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Sleeve sizing.
# ---------------------------------------------------------------------------
def test_sleeve_sizing_full_for_a_large_liquid_portfolio():
    profile = ClientProfile(investable_assets=500_000.0, net_worth=600_000.0, liquid_net_worth=400_000.0)
    cap, note = size_sleeve(profile)
    assert cap == pytest.approx(0.15)


def test_sleeve_sizing_reduced_for_small_or_illiquid_portfolio():
    profile = ClientProfile(investable_assets=150_000.0, net_worth=600_000.0, liquid_net_worth=100_000.0)
    cap, note = size_sleeve(profile)
    assert cap == pytest.approx(0.10)
    assert "reduced" in note


def test_sleeve_sizing_zero_below_minimum_portfolio_size():
    profile = ClientProfile(investable_assets=50_000.0)
    cap, note = size_sleeve(profile)
    assert cap == 0.0


# ---------------------------------------------------------------------------
# Gating logic.
# ---------------------------------------------------------------------------
def _considered(assessment, key):
    return next(p for p in assessment.considered if p.key == key)


def test_all_four_income_note_gates_passing_recommends_it():
    profile = ClientProfile(
        objective=Objective.INCOME, annual_spending=60_000.0, social_security_income=10_000.0,
        investable_assets=500_000.0, net_worth=600_000.0, liquid_net_worth=200_000.0,
        risk_tolerance=RiskTolerance.MODERATE, experience=Experience.GOOD, drawdown_tolerance=0.20,
    )
    result = evaluate_structured_products(profile)
    income_note = _considered(result, "income_note")
    assert income_note.recommended is True
    assert income_note.failed_gates == []


def test_income_note_declined_when_experience_insufficient():
    profile = ClientProfile(
        objective=Objective.INCOME, annual_spending=60_000.0, social_security_income=10_000.0,
        investable_assets=500_000.0, net_worth=600_000.0, liquid_net_worth=200_000.0,
        risk_tolerance=RiskTolerance.MODERATE, experience=Experience.LIMITED, drawdown_tolerance=0.20,
    )
    result = evaluate_structured_products(profile)
    income_note = _considered(result, "income_note")
    assert income_note.recommended is False
    assert income_note.failed_gates == ["limited investment experience"]
    # A buffer is still independently evaluated -- unaffected by the income-note gates.
    assert _considered(result, "buffered_etf").recommended is True


def test_buffered_note_warranted_when_sophisticated_and_liquid():
    profile = ClientProfile(
        objective=Objective.GROWTH, risk_tolerance=RiskTolerance.MODERATE_AGGRESSIVE,
        drawdown_tolerance=0.20, experience=Experience.EXTENSIVE,
        investable_assets=500_000.0, net_worth=600_000.0, liquid_net_worth=200_000.0,
    )
    result = evaluate_structured_products(profile)
    assert _considered(result, "buffered_etf").recommended is True
    assert _considered(result, "buffered_note").recommended is True


def test_buffered_note_not_warranted_for_a_less_experienced_client():
    profile = ClientProfile(
        objective=Objective.GROWTH, risk_tolerance=RiskTolerance.MODERATE_AGGRESSIVE,
        drawdown_tolerance=0.20, experience=Experience.LIMITED,
        investable_assets=500_000.0, net_worth=600_000.0, liquid_net_worth=200_000.0,
    )
    result = evaluate_structured_products(profile)
    assert _considered(result, "buffered_etf").recommended is True  # ETF still fits
    note = _considered(result, "buffered_note")
    assert note.recommended is False
    assert note.failed_gates == ["ETF preferred over a note here"]


def test_portfolio_too_small_declines_everything_on_size_alone():
    profile = ClientProfile(investable_assets=50_000.0)
    result = evaluate_structured_products(profile)

    assert result.sleeve_max_pct == 0.0
    assert result.any_recommended is False
    assert all(p.failed_gates == ["portfolio size"] for p in result.considered)
    assert len(result.considered) == 4


def test_high_drawdown_tolerance_declines_principal_protection():
    profile = ClientProfile(
        objective=Objective.GROWTH, drawdown_tolerance=0.40, experience=Experience.GOOD,
        investable_assets=500_000.0, net_worth=600_000.0, liquid_net_worth=200_000.0,
    )
    result = evaluate_structured_products(profile)
    pp = _considered(result, "principal_protected")
    assert pp.recommended is False
    assert "opportunity cost" in pp.failed_gates[0]
