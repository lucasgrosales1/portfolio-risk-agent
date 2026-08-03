"""Tests for pra.agents.compliance — the review agent.

Offline: the Anthropic client is a scripted fake (tests/agents/conftest.py).
"""

from __future__ import annotations

import pytest

from pra.agents.compliance import compliance_review
from pra.config import COMPLIANCE_MODEL

DRAFT = ["This portfolio is worth $100,000.", "## Risk profile", "The Sharpe ratio is 1.42."]
FACT_SHEET = "PORTFOLIO\n- Total value: $100,000\n\nRISK\n- Sharpe ratio: 1.42"


def test_compliance_review_raises_without_api_key(monkeypatch):
    monkeypatch.setattr("pra.agents.compliance.anthropic_api_key", lambda: None)

    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        compliance_review(DRAFT, FACT_SHEET)


def test_compliance_review_returns_empty_list_when_approved(monkeypatch, fake_anthropic):
    monkeypatch.setattr("pra.agents.compliance.anthropic_api_key", lambda: "sk-ant-fake-key")
    fake_anthropic({"approved": True, "flags": []})

    assert compliance_review(DRAFT, FACT_SHEET) == []


def test_compliance_review_returns_flags_from_the_model(monkeypatch, fake_anthropic):
    monkeypatch.setattr("pra.agents.compliance.anthropic_api_key", lambda: "sk-ant-fake-key")
    fake_anthropic({
        "approved": False,
        "flags": ["'guaranteed 8% return' is a performance guarantee (rule 2)"],
    })

    flags = compliance_review(DRAFT, FACT_SHEET)

    assert flags == ["'guaranteed 8% return' is a performance guarantee (rule 2)"]


def test_compliance_review_sends_the_model_and_full_context(monkeypatch, fake_anthropic):
    monkeypatch.setattr("pra.agents.compliance.anthropic_api_key", lambda: "sk-ant-fake-key")
    client = fake_anthropic({"approved": True, "flags": []})

    compliance_review(DRAFT, FACT_SHEET)

    call = client.messages.calls[0]
    assert call["model"] == COMPLIANCE_MODEL
    sent_content = call["messages"][0]["content"]
    assert FACT_SHEET in sent_content
    for paragraph in DRAFT:
        assert paragraph in sent_content
