"""Render the HTML report.

Produces a single self-contained file — no external CSS, fonts, or scripts —
so it can be emailed, opened offline, or hosted on GitHub Pages unchanged.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .. import __version__
from ..agents.narrative import Narrative
from ..analytics import (
    AllocationResult,
    ConcentrationResult,
    RebalanceResult,
    RiskMetrics,
)
from ..config import DISCLAIMER, METHODOLOGY_NOTE, TAX_ASSUMPTION_NOTE
from ..analytics.rebalance import ASSUMED_LONG_TERM_RATE, ASSUMED_SHORT_TERM_RATE
from ..models import ModelPortfolio
from ..portfolio import Portfolio
from ..prices import BENCHMARK_NAME, MarketData

TEMPLATE_DIR = Path(__file__).parent


# --- Jinja filters --------------------------------------------------------
# Formatting lives here rather than in the template so the template stays
# readable and the number formatting is testable.

def _usd(value: float | None) -> str:
    if value is None:
        return "—"
    return f"-${abs(value):,.0f}" if value < 0 else f"${value:,.0f}"


def _usd_signed(value: float | None) -> str:
    if value is None:
        return "—"
    if value < 0:
        return f"-${abs(value):,.0f}"
    return f"+${value:,.0f}"


def _pct(value: float | None, places: int = 1) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.{places}f}%"


def _signed_pct(value: float | None, places: int = 1) -> str:
    if value is None:
        return "—"
    return f"{value * 100:+.{places}f}%"


def _fixed(value: float | None, places: int = 2) -> str:
    """Fixed decimal places. Jinja's round() drops trailing zeros, which makes
    a correlation of 0.80 render as '0.8' beside a benchmark '1.00'."""
    if value is None:
        return "—"
    return f"{value:.{places}f}"


def build_environment() -> Environment:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["usd"] = _usd
    env.filters["usd_signed"] = _usd_signed
    env.filters["pct"] = _pct
    env.filters["signed_pct"] = _signed_pct
    env.filters["fixed"] = _fixed
    return env


def render_report(
    portfolio: Portfolio,
    allocation: AllocationResult,
    risk: RiskMetrics,
    concentration: ConcentrationResult,
    plan: RebalanceResult,
    model: ModelPortfolio,
    narrative: Narrative,
    market: MarketData,
    output_path: str | Path,
) -> Path:
    """Render the report and write it to `output_path`."""
    env = build_environment()
    template = env.get_template("template.html")

    warnings = list(dict.fromkeys(allocation.warnings + market.warnings))

    html = template.render(
        client_name=portfolio.client_name,
        client_age=portfolio.client_age,
        time_horizon=portfolio.time_horizon_years,
        notes=portfolio.notes,
        report_date=date.today().strftime("%B %d, %Y"),
        model=model,
        benchmark_name=BENCHMARK_NAME,
        alloc=allocation,
        risk=risk,
        concentration=concentration,
        plan=plan,
        narrative=narrative,
        warnings=warnings,
        risk_free_is_live=market.risk_free_is_live,
        data_start=market.start_date.strftime("%b %Y"),
        data_end=market.end_date.strftime("%b %Y"),
        disclaimer=DISCLAIMER,
        tax_note=TAX_ASSUMPTION_NOTE.format(
            lt=ASSUMED_LONG_TERM_RATE, st=ASSUMED_SHORT_TERM_RATE
        ),
        methodology_note=METHODOLOGY_NOTE.format(
            days=risk.trading_days, years=risk.lookback_years
        ),
        version=__version__,
    )

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path
