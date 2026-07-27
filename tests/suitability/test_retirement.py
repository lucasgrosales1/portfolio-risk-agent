"""Known-value tests for pra.suitability.retirement.assess_retirement_readiness.

Every rate/status/equity combination below was cross-checked against the real
implementation while writing this suite.
"""

from __future__ import annotations

import pytest

from pra.suitability.profile import ClientProfile
from pra.suitability.retirement import assess_retirement_readiness


def test_no_withdrawal_need_is_not_applicable():
    profile = ClientProfile(investable_assets=1_000_000.0, annual_spending=0.0)
    result = assess_retirement_readiness(profile)

    assert result.applicable is False
    assert result.withdrawal_rate == 0.0
    assert result.status == "Safe"
    assert result.suggested_equity_fraction == pytest.approx(0.40)
    assert result.red_flags == []


def test_safe_withdrawal_rate():
    profile = ClientProfile(
        investable_assets=1_000_000.0, annual_spending=44_000.0, social_security_income=8_000.0
    )
    result = assess_retirement_readiness(profile)

    assert result.applicable is True
    assert result.net_withdrawal_need == pytest.approx(36_000.0)
    assert result.withdrawal_rate == pytest.approx(0.036)
    assert result.status == "Safe"
    assert result.suggested_equity_fraction == pytest.approx(0.40)
    assert result.suggested_split_label == "40/60 equity/defensive"
    assert result.headroom == pytest.approx(0.004)
    assert result.red_flags == []


def test_caution_withdrawal_rate():
    profile = ClientProfile(
        investable_assets=1_000_000.0, annual_spending=54_000.0, social_security_income=8_000.0
    )
    result = assess_retirement_readiness(profile)

    assert result.withdrawal_rate == pytest.approx(0.046)
    assert result.status == "Caution"
    assert result.suggested_equity_fraction == pytest.approx(0.30)
    assert result.suggested_split_label == "30/70 equity/defensive"
    assert any("4.6%" in f for f in result.red_flags)


def test_unsafe_withdrawal_rate():
    profile = ClientProfile(
        investable_assets=1_000_000.0,
        annual_spending=70_000.0,
        social_security_income=8_000.0,
        pension_income=2_000.0,
    )
    result = assess_retirement_readiness(profile)

    assert result.net_withdrawal_need == pytest.approx(60_000.0)
    assert result.withdrawal_rate == pytest.approx(0.06)
    assert result.status == "Unsafe"
    assert result.suggested_equity_fraction == pytest.approx(0.20)
    assert any("not sustainable" in f for f in result.red_flags)


def test_missing_emergency_reserve_adds_red_flag_even_when_safe():
    profile = ClientProfile(
        investable_assets=1_000_000.0,
        annual_spending=44_000.0,
        social_security_income=8_000.0,
        has_emergency_reserve=False,
    )
    result = assess_retirement_readiness(profile)

    assert result.status == "Safe"  # the rate itself is still fine
    assert result.emergency_reserve_ok is False
    assert any("No emergency reserve" in f for f in result.red_flags)
