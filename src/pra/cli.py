"""Command-line entry point.

    python -m pra.cli --portfolio data/sample_concentrated.csv --model balanced_growth
"""

from __future__ import annotations

import argparse
import sys
import warnings
import webbrowser
from pathlib import Path

from . import __version__
from .agents.narrative import rule_based_narrative
from .analytics import (
    analyze_concentration,
    build_rebalance_plan,
    compute_risk_metrics,
    value_portfolio,
)
from .config import has_api_key, risk_free_override
from .models import DEFAULT_MODEL, MODEL_PORTFOLIOS, get_model
from .portfolio import PortfolioError, load_portfolio
from .prices import PriceDataError, load_market_data
from .report import render_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pra",
        description="Generate a client-ready portfolio risk report.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  python -m pra.cli --portfolio data/sample_concentrated.csv "
            "--model balanced_growth\n"
            "  python -m pra.cli --portfolio data/sample_preretiree.csv "
            "--model moderate --open\n"
        ),
    )
    parser.add_argument(
        "--portfolio", "-p", required=True, help="Path to the portfolio CSV."
    )
    parser.add_argument(
        "--model",
        "-m",
        default=DEFAULT_MODEL,
        choices=sorted(MODEL_PORTFOLIOS),
        help=f"Target model portfolio (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--output", "-o", default=None, help="Output HTML path (default: reports/<name>.html)."
    )
    parser.add_argument(
        "--lookback",
        default="3y",
        help="Price history window for risk metrics (default: 3y).",
    )
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Force rule-based commentary even if an API key is present.",
    )
    parser.add_argument(
        "--no-cache", action="store_true", help="Bypass the local price cache."
    )
    parser.add_argument(
        "--open", action="store_true", help="Open the report in a browser when done."
    )
    parser.add_argument("--version", action="version", version=f"pra {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    warnings.filterwarnings("ignore")
    args = build_parser().parse_args(argv)

    try:
        portfolio = load_portfolio(args.portfolio)
    except PortfolioError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    model = get_model(args.model)
    print(f"Portfolio : {portfolio.client_name} ({len(portfolio.holdings)} lots)")
    print(f"Target    : {model.name}")
    print(f"Fetching market data for {len(portfolio.tickers)} tickers...")

    try:
        market = load_market_data(
            portfolio.tickers,
            lookback=args.lookback,
            risk_free_override=risk_free_override(),
            use_cache=not args.no_cache,
        )
    except PriceDataError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3

    allocation = value_portfolio(portfolio, market)
    risk = compute_risk_metrics(allocation, market)
    concentration = analyze_concentration(allocation, market)
    plan = build_rebalance_plan(allocation, model)

    # Commentary. The AI path is wired in the agent layer; until then, and
    # whenever no key is configured, the rule-based path runs.
    use_ai = has_api_key() and not args.no_ai
    if use_ai:
        try:
            from .agents.ai import ai_narrative  # noqa: F401

            narrative = ai_narrative(
                portfolio, allocation, risk, concentration, plan, model
            )
        except ImportError:
            narrative = rule_based_narrative(
                portfolio, allocation, risk, concentration, plan, model
            )
        except Exception as exc:
            print(f"note: AI commentary failed ({exc}); using rule-based.", file=sys.stderr)
            narrative = rule_based_narrative(
                portfolio, allocation, risk, concentration, plan, model
            )
    else:
        narrative = rule_based_narrative(
            portfolio, allocation, risk, concentration, plan, model
        )

    output = args.output or f"reports/{Path(args.portfolio).stem}.html"
    path = render_report(
        portfolio=portfolio,
        allocation=allocation,
        risk=risk,
        concentration=concentration,
        plan=plan,
        model=model,
        narrative=narrative,
        market=market,
        output_path=output,
    )

    print()
    print(f"Value        : ${allocation.total_value:,.0f}")
    print(f"Volatility   : {risk.annualized_volatility:.1%}   Max DD: {risk.max_drawdown:.1%}")
    print(f"Flags        : {len(concentration.flags)} concentration")
    if plan.needs_rebalancing:
        print(
            f"Rebalance    : ${plan.total_turnover:,.0f} turnover, "
            f"${plan.total_tax_cost:,.0f} est. tax"
        )
    print(f"Commentary   : {narrative.source}")
    print()
    print(f"Report written to {path.resolve()}")

    if args.open:
        webbrowser.open(path.resolve().as_uri())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
