"""Advisor Workbench — Streamlit front end.

Two modes, chosen at the top of the page:

  1. Analyze an existing portfolio   (Phase 1 — fully wired)
  2. Build a plan for a new client    (Phase 2 — intake form; recommendation
                                       engine lands in the next stage)

This file is the entry point Streamlit Community Cloud runs. Keep it thin: it
handles the UI and delegates every calculation to the pra package, preserving
the rule that the analytics library never depends on the web framework.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from pra import __version__
from pra.config import DISCLAIMER, has_api_key
from pra.models import MODEL_PORTFOLIOS
from pra.pipeline import run_analysis
from pra.portfolio import PortfolioError, load_portfolio, parse_portfolio
from pra.prices import PriceDataError
from pra.report import render_html
from pra.suitability import (
    ClientProfile,
    Employment,
    Experience,
    Objective,
    RiskTolerance,
    assess_retirement_readiness,
    score_profile,
)

DATA_DIR = Path(__file__).parent / "data"

SAMPLE_PORTFOLIOS = {
    "Concentrated employer stock (Jordan Reyes)": "sample_concentrated.csv",
    "Pre-retiree, over-allocated (Margaret Chen)": "sample_preretiree.csv",
}

st.set_page_config(
    page_title="Advisor Workbench",
    page_icon="📊",
    layout="wide",
)


# --------------------------------------------------------------------------
# Header + mode selector (the "option at the top of the page")
# --------------------------------------------------------------------------
st.title("Advisor Workbench")
st.caption(
    "Portfolio risk analysis and suitability-driven planning. "
    "Educational project — not investment advice. All sample data is synthetic."
)

mode = st.radio(
    "What would you like to do?",
    ["Analyze an existing portfolio", "Build a plan for a new client"],
    horizontal=True,
    label_visibility="collapsed",
)

if not has_api_key():
    st.info(
        "Running without an API key: commentary is rule-based. Every figure is "
        "identical either way — a key only changes who writes the prose.",
        icon="ℹ️",
    )

st.divider()


# ==========================================================================
# MODE 1 — Analyze an existing portfolio  (fully working)
# ==========================================================================
def render_analyze_mode() -> None:
    st.subheader("Analyze an existing portfolio")

    left, right = st.columns([1, 1])
    with left:
        source = st.radio(
            "Portfolio source",
            ["Use a sample portfolio", "Upload a CSV"],
            key="analyze_source",
        )
    with right:
        model_key = st.selectbox(
            "Target model portfolio",
            options=list(MODEL_PORTFOLIOS),
            format_func=lambda k: MODEL_PORTFOLIOS[k].name,
            index=list(MODEL_PORTFOLIOS).index("balanced_growth"),
        )
        st.caption(MODEL_PORTFOLIOS[model_key].description)

    portfolio = None
    upload_text = None

    if source == "Use a sample portfolio":
        label = st.selectbox("Sample", list(SAMPLE_PORTFOLIOS))
        portfolio_path = DATA_DIR / SAMPLE_PORTFOLIOS[label]
    else:
        uploaded = st.file_uploader(
            "Portfolio CSV",
            type=["csv"],
            help=(
                "Columns: ticker, shares, cost_basis_per_share, acquisition_date, "
                "account_type, is_employer_stock. One row per tax lot."
            ),
        )
        portfolio_path = None
        if uploaded is not None:
            upload_text = uploaded.getvalue().decode("utf-8")

    run = st.button("Generate report", type="primary", disabled=(
        source == "Upload a CSV" and upload_text is None
    ))

    # A Streamlit button returns True only on the run that the click triggers;
    # any later rerun resets it. So when clicked, compute the analysis and store
    # it in session_state, and always render from session_state below. That way
    # the report survives scrolling, reconnects, and changing other widgets.
    if run:
        try:
            if upload_text is not None:
                portfolio = parse_portfolio(upload_text, default_name="Uploaded Portfolio")
            else:
                portfolio = load_portfolio(portfolio_path)
        except PortfolioError as exc:
            st.session_state.pop("analysis", None)
            st.error(f"Could not read that portfolio: {exc}")
            return

        with st.spinner(f"Fetching market data for {len(portfolio.tickers)} tickers..."):
            try:
                result = run_analysis(portfolio, model_key)
            except PriceDataError as exc:
                st.session_state.pop("analysis", None)
                st.error(f"Market data error: {exc}")
                return

        st.session_state["analysis"] = {
            "client_name": result.portfolio.client_name,
            "html": render_html(
                result.portfolio, result.allocation, result.risk,
                result.concentration, result.plan, result.model,
                result.narrative, result.market,
            ),
            "value": result.allocation.total_value,
            "gain": result.allocation.total_unrealized_gain,
            "gain_pct": result.allocation.total_unrealized_gain / result.allocation.total_cost_basis,
            "vol": result.risk.annualized_volatility,
            "bench_vol": result.risk.benchmark_volatility,
            "dd": result.risk.max_drawdown,
            "bench_dd": result.risk.benchmark_max_drawdown,
            "flags": len(result.concentration.flags),
            "high_flags": sum(1 for f in result.concentration.flags if f.severity == "high"),
        }

    data = st.session_state.get("analysis")
    if not data:
        return

    a = data
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Portfolio value", f"${a['value']:,.0f}")
    c2.metric("Unrealized gain", f"${a['gain']:,.0f}", f"{a['gain_pct']:+.1%} on cost")
    c3.metric(
        "Volatility (ann.)", f"{a['vol']:.1%}",
        f"vs. {a['bench_vol']:.1%} S&P 500", delta_color="off",
    )
    c4.metric(
        "Max drawdown", f"{a['dd']:.1%}",
        f"vs. {a['bench_dd']:.1%} S&P 500", delta_color="off",
    )

    if a["flags"]:
        st.warning(
            f"{a['flags']} concentration flag(s), {a['high_flags']} high severity. "
            f"See the full report below.",
            icon="⚠️",
        )

    st.download_button(
        "Download report (HTML)",
        data=a["html"],
        file_name=f"{a['client_name'].replace(' ', '_').lower()}_report.html",
        mime="text/html",
    )
    st.components.v1.html(a["html"], height=900, scrolling=True)


# ==========================================================================
# MODE 2 — Build a plan for a new client  (intake shell)
# ==========================================================================
def render_plan_mode() -> None:
    st.subheader("Build a plan for a new client")
    st.caption(
        "Capture the client's suitability profile. The recommendation engine — "
        "risk scoring, allocation, structured-product analysis, and the IPS — is "
        "the next build stage; for now this confirms the intake."
    )

    with st.form("intake"):
        st.markdown("##### Personal")
        p1, p2, p3 = st.columns(3)
        name = p1.text_input("Client name", "New Client")
        age = p2.number_input("Age", min_value=18, max_value=100, value=45)
        dependents = p3.number_input("Dependents", min_value=0, max_value=15, value=0)

        st.markdown("##### Time horizon & employment")
        h1, h2, h3 = st.columns(3)
        horizon = h1.number_input(
            "Time horizon (years)", min_value=1, max_value=50, value=15,
            help="Years until the funds are needed. Short horizons cap equity "
                 "regardless of stated risk tolerance.",
        )
        employment = h2.selectbox(
            "Employment", list(Employment), format_func=lambda e: e.value.replace("_", " ").title()
        )
        income = h3.number_input("Annual income ($)", min_value=0, value=100_000, step=5_000)

        st.markdown("##### Balance sheet")
        b1, b2, b3 = st.columns(3)
        net_worth = b1.number_input("Net worth ($)", min_value=0, value=500_000, step=10_000)
        liquid = b2.number_input(
            "Liquid net worth ($)", min_value=0, value=250_000, step=10_000,
            help="Readily accessible assets. A hard gate for illiquid products.",
        )
        tax = b3.slider("Marginal tax bracket", 0.0, 0.5, 0.24, 0.01, format="%.0f%%")

        st.markdown("##### Retirement income")
        st.caption("Leave spending at 0 if the client is still accumulating.")
        ri1, ri2 = st.columns(2)
        investable = ri1.number_input(
            "Investable assets ($)", min_value=0, value=500_000, step=10_000,
            help="The portfolio that funds withdrawals — excludes home equity and "
                 "other illiquid assets.",
        )
        spending = ri2.number_input(
            "Annual spending need ($)", min_value=0, value=0, step=5_000,
            help="Total annual spending to fund. The withdrawal rate is measured "
                 "against this, net of guaranteed income.",
        )
        ri3, ri4 = st.columns(2)
        ss_income = ri3.number_input(
            "Social Security ($/yr)", min_value=0, value=0, step=1_000
        )
        pension_income = ri4.number_input(
            "Pension / other guaranteed income ($/yr)", min_value=0, value=0, step=1_000
        )

        st.markdown("##### Liquidity & reserves")
        l1, l2 = st.columns(2)
        withdrawal = l1.number_input(
            "Near-term withdrawal need ($)", min_value=0, value=0, step=5_000,
            help="Cash expected to be withdrawn within ~2 years.",
        )
        reserve = l2.checkbox("Emergency reserve in place (3–6 months)", value=True)

        st.markdown("##### Objectives & risk")
        o1, o2 = st.columns(2)
        objective = o1.selectbox(
            "Primary objective", list(Objective), index=2,
            format_func=lambda o: o.value.title(),
        )
        risk_tol = o2.selectbox(
            "Stated risk tolerance", list(RiskTolerance), index=2,
            format_func=lambda r: r.value.replace("_", " ").title(),
        )
        d1, d2 = st.columns(2)
        drawdown = d1.slider(
            "Drawdown tolerance", 0.0, 0.6, 0.20, 0.05, format="%.0f%%",
            help="The largest peak-to-trough loss the client says they could tolerate.",
        )
        experience = d2.selectbox(
            "Investment experience", list(Experience), index=1,
            format_func=lambda e: e.value.title(),
        )

        constraints = st.text_area(
            "Constraints, existing concentrations, restrictions (optional)", ""
        )

        submitted = st.form_submit_button("Generate recommendation", type="primary")

    if submitted:
        profile = ClientProfile(
            client_name=name,
            age=int(age),
            dependents=int(dependents),
            time_horizon_years=int(horizon),
            employment=employment,
            annual_income=float(income),
            net_worth=float(net_worth),
            liquid_net_worth=float(liquid),
            marginal_tax_bracket=float(tax),
            near_term_withdrawal=float(withdrawal),
            has_emergency_reserve=bool(reserve),
            objective=objective,
            risk_tolerance=risk_tol,
            drawdown_tolerance=float(drawdown),
            experience=experience,
            constraints=constraints,
            investable_assets=float(investable),
            annual_spending=float(spending),
            social_security_income=float(ss_income),
            pension_income=float(pension_income),
        )
        st.session_state["plan"] = {
            "profile": profile,
            "assessment": score_profile(profile),
            "readiness": assess_retirement_readiness(profile),
        }

    plan = st.session_state.get("plan")
    if not plan:
        return

    profile = plan["profile"]
    assessment = plan["assessment"]
    readiness = plan["readiness"]

    st.success(f"Profile captured — {profile.summary_line()}")

    # --- Retirement-income readiness (decumulation branch) -----------------
    # When the portfolio must fund withdrawals, feasibility comes before risk:
    # an allocation is meaningless if the withdrawal rate is unsustainable.
    if readiness.applicable:
        st.markdown("### Retirement income readiness")
        status_icon = {"Safe": "✅", "Caution": "⚠️", "Unsafe": "🛑"}[readiness.status]
        wc1, wc2, wc3 = st.columns(3)
        wc1.metric("Withdrawal rate", f"{readiness.withdrawal_rate:.1%}",
                   f"benchmark {readiness.benchmark_rate:.0%}", delta_color="off")
        wc2.metric("Status", f"{status_icon} {readiness.status}")
        wc3.metric("Suggested split", readiness.suggested_split_label)

        for f in readiness.findings:
            st.markdown(f"- {f}")
        for rf in readiness.red_flags:
            st.error(rf, icon="🚩")
        st.caption(
            "The 4% benchmark assumes roughly a 30-year horizon and historical US "
            "returns; it is a starting reference, not a guarantee. Reserve sizing, "
            "sequence-of-returns stress testing, and Monte Carlo come in later stages."
        )
        st.divider()

    # --- The recommendation ------------------------------------------------
    st.markdown("### Recommendation")
    rc1, rc2, rc3 = st.columns([2, 1, 1])
    rc1.metric("Recommended model", assessment.profile_label)
    rc2.metric("Risk score", f"{assessment.raw_score:.0f}/100")
    rc3.metric("Capacity capped", "Yes" if assessment.was_capped else "No")

    if assessment.was_capped:
        st.warning(
            "The client's stated risk profile was reduced by capacity constraints. "
            "This is the suitability discipline at work — situation overriding attitude.",
            icon="🛡️",
        )

    st.markdown("**Why:**")
    for line in assessment.rationale:
        st.markdown(line if line.strip().startswith("•") else f"- {line}")

    # --- Score breakdown ---------------------------------------------------
    with st.expander("Risk-score breakdown"):
        st.caption("Each factor scores 0–100; the weighted blend is the risk score.")
        for c in assessment.components:
            bar_c1, bar_c2 = st.columns([3, 2])
            bar_c1.markdown(f"**{c.name}** — {c.note}")
            bar_c1.progress(int(c.raw))
            bar_c2.caption(
                f"{c.raw:.0f}/100 × weight {c.weight:.0%} = "
                f"{c.contribution:.1f} pts"
            )

    # --- Derived structured-product signals (used by the next stage) -------
    with st.expander("Suitability signals for structured products"):
        s1, s2, s3 = st.columns(3)
        s1.metric("Income need", "Yes" if profile.has_income_need else "No")
        s2.metric("Liquid ratio", f"{profile.liquid_ratio:.0%}")
        s3.metric("Sophisticated", "Yes" if profile.is_sophisticated else "No")
        st.caption(
            "The structured-product layer (next stage) gates income notes behind "
            "all of: an income need, adequate liquidity, moderate-or-higher risk "
            "tolerance, and sufficient sophistication — and documents the decision "
            "either way."
        )

    with st.expander("Still to come"):
        st.markdown(
            "Next stages add: allocation **tilts** for client specifics, the "
            "**structured-product analysis** (income notes and buffers, or a "
            "documented decision to exclude them), a draft **Investment Policy "
            "Statement**, and a button to run the recommended allocation straight "
            "through the Phase 1 analysis — closing the loop."
        )


# --------------------------------------------------------------------------
if mode == "Analyze an existing portfolio":
    render_analyze_mode()
else:
    render_plan_mode()

st.divider()
st.caption(f"Advisor Workbench v{__version__} — {DISCLAIMER}")
