"""Tests for pra.agents.ai — the narrative-writing agent.

Every test here is offline: the Anthropic client is replaced with a scripted
fake (see tests/agents/conftest.py), so nothing reaches the network and every
assertion is on deterministic, known input/output.
"""

from __future__ import annotations

import pytest

from pra.agents.ai import ai_narrative, build_fact_sheet
from pra.config import NARRATIVE_MODEL


def test_build_fact_sheet_transcribes_computed_figures(computed_review):
    portfolio, allocation, risk, concentration, plan, model = computed_review

    sheet = build_fact_sheet(portfolio, allocation, risk, concentration, plan, model)

    assert f"Total value: ${allocation.total_value:,.0f}" in sheet
    assert f"Position count: {len(allocation.positions)}" in sheet
    assert f"Target model: {model.name}" in sheet
    assert f"Client age: {portfolio.client_age}" in sheet
    assert f"Time horizon: {portfolio.time_horizon_years} years" in sheet
    assert f"Beta: {risk.beta:.2f}" in sheet
    assert f"Sharpe ratio: {risk.sharpe_ratio:.2f}" in sheet
    assert f"Effective number of holdings: {concentration.effective_holdings:.1f}" in sheet
    expected_rebalance_line = f"Needs rebalancing: {'yes' if plan.needs_rebalancing else 'no'}"
    assert expected_rebalance_line in sheet


def test_build_fact_sheet_omits_optional_client_fields_when_absent(computed_review):
    portfolio, allocation, risk, concentration, plan, model = computed_review
    portfolio.client_age = None
    portfolio.time_horizon_years = None

    sheet = build_fact_sheet(portfolio, allocation, risk, concentration, plan, model)

    assert "Client age" not in sheet
    assert "Time horizon" not in sheet


def test_ai_narrative_raises_without_api_key(monkeypatch, computed_review):
    monkeypatch.setattr("pra.agents.ai.anthropic_api_key", lambda: None)

    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        ai_narrative(*computed_review)


def test_ai_narrative_wires_writer_and_reviewer_together(monkeypatch, fake_anthropic, computed_review):
    monkeypatch.setattr("pra.agents.ai.anthropic_api_key", lambda: "sk-ant-fake-key")
    client = fake_anthropic({"paragraphs": ["Opening paragraph.", "## Risk profile", "Risk paragraph."]})

    captured_review_args = {}

    def _fake_compliance_review(paragraphs, fact_sheet):
        captured_review_args["paragraphs"] = paragraphs
        captured_review_args["fact_sheet"] = fact_sheet
        return ["flag: figure not found in computed figures"]

    monkeypatch.setattr("pra.agents.ai.compliance_review", _fake_compliance_review)

    result = ai_narrative(*computed_review)

    assert result.source == "ai"
    assert result.model_used == NARRATIVE_MODEL
    assert result.paragraphs == ["Opening paragraph.", "## Risk profile", "Risk paragraph."]
    assert result.compliance_flags == ["flag: figure not found in computed figures"]

    # The writer call used the configured narrative model.
    assert client.messages.calls[0]["model"] == NARRATIVE_MODEL
    # The reviewer received exactly what the writer produced.
    assert captured_review_args["paragraphs"] == result.paragraphs
    assert "PORTFOLIO" in captured_review_args["fact_sheet"]


def test_ai_narrative_raises_on_empty_paragraphs(monkeypatch, fake_anthropic, computed_review):
    monkeypatch.setattr("pra.agents.ai.anthropic_api_key", lambda: "sk-ant-fake-key")
    fake_anthropic({"paragraphs": []})

    with pytest.raises(ValueError, match="no paragraphs"):
        ai_narrative(*computed_review)
