"""Configuration and the disclaimer language that appears on every report."""

from __future__ import annotations

import os
from pathlib import Path

# Load .env if python-dotenv is installed. Absent file is fine — the tool runs
# without a key, using rule-based commentary instead of AI-written commentary.
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except ImportError:
    pass


# --- Models ---------------------------------------------------------------
# Sonnet writes the client-facing narrative; Haiku reviews it. Two different
# models for two different jobs, matched to the difficulty of each — the
# review task is narrow and rule-checkable, so it doesn't need the larger model.
NARRATIVE_MODEL = os.getenv("PRA_NARRATIVE_MODEL", "claude-sonnet-5")
COMPLIANCE_MODEL = os.getenv("PRA_COMPLIANCE_MODEL", "claude-haiku-4-5")


def anthropic_api_key() -> str | None:
    key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    return key or None


def has_api_key() -> bool:
    return anthropic_api_key() is not None


def risk_free_override() -> float | None:
    raw = os.getenv("PRA_RISK_FREE_RATE", "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


# --- Disclaimer -----------------------------------------------------------
# Appears on every generated document, without exception. This is a personal
# educational project, not the work product of a registered representative,
# and the report says so where a reader will actually see it.
DISCLAIMER = (
    "This report is the output of a personal educational software project. It is "
    "not investment advice, not a recommendation to buy or sell any security, and "
    "not a solicitation. It was not prepared by a registered investment adviser or "
    "broker-dealer acting in that capacity. Figures are derived from third-party "
    "market data believed to be reliable but not guaranteed, and are illustrative "
    "only. Past performance does not indicate future results. Tax figures are "
    "rough estimates using assumed federal rates; they exclude state taxes, the net "
    "investment income tax, and individual bracket detail. Consult a qualified "
    "adviser and tax professional before acting on any information here."
)

TAX_ASSUMPTION_NOTE = (
    "Tax estimates assume a {lt:.0%} long-term and {st:.0%} short-term federal "
    "rate. No state tax, net investment income tax, or bracket detail is modeled."
)

METHODOLOGY_NOTE = (
    "Risk statistics are computed from {days} daily observations ({years:.1f} years) "
    "by applying the portfolio's current weights across the full period, rebalanced "
    "daily. This describes how the current allocation would have behaved; it is not "
    "the account's realized performance, which would require transaction history."
)
