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
from .config import has_api_key
from .models import DEFAULT_MODEL, MODEL_PORTFOLIOS, get_model
from .pipeline import run_analysis
from .portfolio import PortfolioError, load_portfolio
from .prices import PriceDataError
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

    use_ai = has_api_key() and not args.no_ai
    try:
        result = run_analysis(
            portfolio,
            args.model,
            lookback=args.lookback,
            use_cache=not args.no_cache,
            use_ai=use_ai,
        )
    except PriceDataError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3

    output = args.output or f"reports/{Path(args.portfolio).stem}.html"
    path = render_report(
        portfolio=result.portfolio,
        allocation=result.allocation,
        risk=result.risk,
        concentration=result.concentration,
        plan=result.plan,
        model=result.model,
        narrative=result.narrative,
        market=result.market,
        output_path=output,
    )

    risk, plan = result.risk, result.plan
    print()
    print(f"Value        : ${result.allocation.total_value:,.0f}")
    print(f"Volatility   : {risk.annualized_volatility:.1%}   Max DD: {risk.max_drawdown:.1%}")
    print(f"Flags        : {len(result.concentration.flags)} concentration")
    if plan.needs_rebalancing:
        print(
            f"Rebalance    : ${plan.total_turnover:,.0f} turnover, "
            f"${plan.total_tax_cost:,.0f} est. tax"
        )
    print(f"Commentary   : {result.narrative.source}")
    print()
    print(f"Report written to {path.resolve()}")

    if args.open:
        webbrowser.open(path.resolve().as_uri())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
