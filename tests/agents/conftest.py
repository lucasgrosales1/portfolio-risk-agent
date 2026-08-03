"""Fixtures shared by the agents tests: a fully-computed analysis (real
allocation/risk/concentration/rebalance objects, from the offline synthetic
price fixture) plus a scriptable fake Anthropic client so no test ever makes
a real network call.
"""

from __future__ import annotations

import json
from datetime import date

import pytest

import pra.prices as prices_module
from pra.analytics import (
    analyze_concentration,
    build_rebalance_plan,
    compute_risk_metrics,
    value_portfolio,
)
from pra.models import get_model
from pra.portfolio import Holding, Portfolio

from ..conftest import make_market_data


@pytest.fixture
def computed_review(fixed_price_frame):
    """A real, fully-computed (portfolio, allocation, risk, concentration, plan, model) tuple."""
    holdings = [
        Holding("VOO", 100, 300.0, date(2020, 1, 1), "taxable"),
        Holding("BND", 200, 90.0, date(2021, 1, 1), "traditional"),
        Holding("CASH", 5000, 1.0, date(2022, 1, 1), "taxable"),
    ]
    portfolio = Portfolio(
        holdings=holdings, client_name="Fact Sheet Test", client_age=52, time_horizon_years=13
    )

    last = fixed_price_frame.iloc[-1]
    market = make_market_data(
        fixed_price_frame[["VOO", "BND"]],
        {"VOO": float(last["VOO"]), "BND": float(last["BND"])},
        benchmark=fixed_price_frame[prices_module.BENCHMARK_TICKER],
    )

    allocation = value_portfolio(portfolio, market)
    risk = compute_risk_metrics(allocation, market)
    concentration = analyze_concentration(allocation, market)
    model = get_model("moderate")
    plan = build_rebalance_plan(allocation, model, as_of=date(2024, 6, 1))
    return portfolio, allocation, risk, concentration, plan, model


class _FakeTextBlock:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class _FakeMessage:
    def __init__(self, payload: dict) -> None:
        self.content = [_FakeTextBlock(json.dumps(payload))]


class _FakeMessages:
    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeMessage(self._payload)


class FakeAnthropicClient:
    def __init__(self, payload: dict) -> None:
        self.messages = _FakeMessages(payload)


@pytest.fixture
def fake_anthropic(monkeypatch):
    """Patch anthropic.Anthropic to return a scripted client.

    fake_anthropic({"paragraphs": [...]}) installs the client and returns it;
    client.messages.calls records every messages.create(**kwargs) invocation
    so a test can assert on what was actually sent.
    """
    import anthropic

    def _install(payload: dict) -> FakeAnthropicClient:
        client = FakeAnthropicClient(payload)
        monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: client)
        return client

    return _install
