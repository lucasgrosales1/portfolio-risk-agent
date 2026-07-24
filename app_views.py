"""Page views for the Advisor Workbench web app.

Every page reads from the real `pra` engine — no mock data. Portfolio-driven
pages (Dashboard, Portfolio Analysis, Rebalancing, Reports) share one computed
analysis held in session_state, so the advisor selects a portfolio once and
every tab reflects it, the way real software behaves.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

import app_ui as ui
from pra.config import has_api_key
from pra.models import MODEL_PORTFOLIOS
from pra.pipeline import AnalysisResult, run_analysis
from pra.portfolio import PortfolioError, load_portfolio, parse_portfolio
from pra.prices import BENCHMARK_NAME, PriceDataError
from pra.report import render_html
from pra.suitability import (
    ClientProfile,
    Employment,
    Experience,
    Objective,
    RiskTolerance,
    build_recommendation,
)

DATA_DIR = Path(__file__).parent / "data"
SAMPLE_PORTFOLIOS = {
    "Concentrated employer stock (Jordan Reyes)": "sample_concentrated.csv",
    "Pre-retiree, over-allocated (Margaret Chen)": "sample_preretiree.csv",
}


# ==========================================================================
# Shared active-portfolio helpers
# ==========================================================================
def _active() -> AnalysisResult | None:
    return st.session_state.get("active")


def _compute_active(label: str, model_key: str, upload_text: str | None) -> bool:
    """Run the pipeline for the chosen portfolio; store it. Returns success."""
    try:
        if upload_text is not None:
            portfolio = parse_portfolio(upload_text, default_name="Uploaded Portfolio")
        else:
            portfolio = load_portfolio(DATA_DIR / SAMPLE_PORTFOLIOS[label])
    except PortfolioError as exc:
        st.error(f"Could not read that portfolio: {exc}")
        return False

    with st.spinner(f"Fetching market data for {len(portfolio.tickers)} tickers…"):
        try:
            result = run_analysis(portfolio, model_key)
        except PriceDataError as exc:
            st.error(f"Market data error: {exc}")
            return False

    st.session_state["active"] = result
    st.session_state["active_meta"] = {"label": label, "model": model_key}
    return True


def _portfolio_picker(context: str) -> None:
    """A compact select-and-load control shared by Dashboard and Settings."""
    c1, c2 = st.columns([2, 1])
    with c1:
        source = st.radio(
            "Portfolio source", ["Sample portfolio", "Upload a CSV"],
            horizontal=True, key=f"src_{context}",
        )
        upload_text = None
        if source == "Sample portfolio":
            label = st.selectbox("Select a portfolio", list(SAMPLE_PORTFOLIOS),
                                 key=f"sample_{context}")
        else:
            up = st.file_uploader("Portfolio CSV", type=["csv"], key=f"up_{context}")
            label = "Uploaded Portfolio"
            if up is not None:
                upload_text = up.getvalue().decode("utf-8")
    with c2:
        model_key = st.selectbox(
            "Target model", list(MODEL_PORTFOLIOS),
            format_func=lambda k: MODEL_PORTFOLIOS[k].name,
            index=list(MODEL_PORTFOLIOS).index("balanced_growth"),
            key=f"model_{context}",
        )

    disabled = source == "Upload a CSV" and upload_text is None
    if st.button("Load portfolio", type="primary", disabled=disabled, key=f"load_{context}"):
        if _compute_active(label, model_key, upload_text):
            st.session_state["page"] = "Dashboard"
            st.rerun()


def _needs_portfolio_notice() -> None:
    st.info("No portfolio loaded yet. Load one below to populate this page.", icon="📂")
    _portfolio_picker("inline")


# ==========================================================================
# Home
# ==========================================================================
def home() -> None:
    st.markdown(
        f"""
        <div class="aw-hero">
          <div class="eyebrow">{ui.FIRM_NAME}</div>
          <h1>Institutional-grade portfolio intelligence, in one workspace.</h1>
          <p>Analyze a client's holdings, quantify concentration and risk, plan
             tax-aware rebalancing, and build suitability-driven allocations —
             every figure computed from real market data, never estimated.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")

    b1, b2, _ = st.columns([1, 1, 3])
    if b1.button("Open Dashboard", type="primary", width="stretch"):
        ui.go_to("Dashboard")
    if b2.button("Build a client plan", width="stretch"):
        ui.go_to("Planning")

    st.write("")
    st.markdown('<div class="aw-section-label">What it does</div>', unsafe_allow_html=True)
    r1 = st.columns(3)
    with r1[0]:
        ui.card("📊", "Portfolio Analysis",
                "Live valuation, allocation by asset class and sector, volatility, "
                "max drawdown, Sharpe, and beta against the S&P 500.")
    with r1[1]:
        ui.card("⚖️", "Tax-Aware Rebalancing",
                "Drift from target with a trade plan that sources sales from "
                "sheltered accounts first and prices the tax cost of the rest.")
    with r1[2]:
        ui.card("🧭", "Suitability Planning",
                "Capacity-first recommendations, retirement-income readiness, and a "
                "sequence-of-returns stress test — reconciled into one allocation.")

    st.write("")
    st.markdown('<div class="aw-section-label">Why it is different</div>', unsafe_allow_html=True)
    st.markdown(
        "- **Every number is computed, never guessed.** The analytics run in Python "
        "from real prices; the AI layer only explains figures it is handed.\n"
        "- **Suitability discipline built in.** Capacity constraints cap the "
        "recommendation, and the tool documents *why* — including when it declines a "
        "product.\n"
        "- **Client-ready output.** One command produces a report you could hand to a "
        "client."
    )
    st.caption("Educational portfolio project — not investment advice. All sample data is synthetic.")


# ==========================================================================
# Dashboard
# ==========================================================================
def dashboard() -> None:
    ui.page_title("Dashboard", "Overview of the loaded portfolio.")
    result = _active()
    if result is None:
        _needs_portfolio_notice()
        return

    a, r = result.allocation, result.risk
    meta = st.session_state.get("active_meta", {})
    st.caption(f"**{result.portfolio.client_name}** · target {result.model.name} · "
               f"benchmark {BENCHMARK_NAME}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Portfolio value", f"${a.total_value:,.0f}", f"{len(a.positions)} positions")
    c2.metric("Unrealized gain", f"${a.total_unrealized_gain:,.0f}",
              f"{a.total_unrealized_gain / a.total_cost_basis:+.1%} on cost")
    c3.metric("Volatility (ann.)", f"{r.annualized_volatility:.1%}",
              f"S&P {r.benchmark_volatility:.1%}", delta_color="off")
    c4.metric("Max drawdown", f"{r.max_drawdown:.1%}",
              f"S&P {r.benchmark_max_drawdown:.1%}", delta_color="off")

    st.write("")
    left, right = st.columns([1, 1])
    with left:
        st.markdown("**Allocation by asset class**")
        alloc = pd.Series(a.by_asset_class).sort_values(ascending=False)
        st.bar_chart(alloc, height=260, horizontal=True)
    with right:
        st.markdown("**Largest holdings**")
        top = sorted(a.positions, key=lambda p: p.market_value, reverse=True)[:6]
        df = pd.DataFrame(
            {"Ticker": p.ticker,
             "Weight": p.market_value / a.total_value,
             "Value": p.market_value} for p in top
        )
        st.dataframe(
            df, hide_index=True, width="stretch",
            column_config={
                "Weight": st.column_config.ProgressColumn(
                    "Weight", format="%.1f%%", min_value=0, max_value=float(df["Weight"].max())),
                "Value": st.column_config.NumberColumn("Value", format="$%,.0f"),
            },
        )

    if result.concentration.flags:
        high = sum(1 for f in result.concentration.flags if f.severity == "high")
        st.warning(f"{len(result.concentration.flags)} concentration flag(s), {high} high "
                   f"severity — see Portfolio Analysis.", icon="⚠️")


# ==========================================================================
# Portfolio Analysis
# ==========================================================================
def portfolio_analysis() -> None:
    ui.page_title("Portfolio Analysis", "Holdings, allocation, and risk metrics.")
    result = _active()
    if result is None:
        _needs_portfolio_notice()
        return

    a, r = result.allocation, result.risk

    st.markdown("**Holdings**")
    rows = []
    for p in a.positions:
        rows.append({
            "Ticker": p.ticker, "Name": p.name, "Class": p.asset_class,
            "Value": p.market_value, "Weight": p.market_value / a.total_value,
            "Cost basis": p.cost_basis, "Unrealized": p.unrealized_gain,
            "Return": p.gain_pct,
        })
    df = pd.DataFrame(rows)
    st.dataframe(
        df, hide_index=True, width="stretch",
        column_config={
            "Value": st.column_config.NumberColumn(format="$%,.0f"),
            "Cost basis": st.column_config.NumberColumn(format="$%,.0f"),
            "Unrealized": st.column_config.NumberColumn(format="$%,.0f"),
            "Weight": st.column_config.NumberColumn(format="%.1f%%"),
            "Return": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )

    st.write("")
    left, right = st.columns([1, 1])
    with left:
        st.markdown("**Risk & return** — 3-year, current weights")
        risk_df = pd.DataFrame({
            "Measure": ["Volatility (ann.)", "Max drawdown", "Annualized return",
                        "Sharpe ratio", "Beta vs S&P 500", "Correlation"],
            "Portfolio": [f"{r.annualized_volatility:.1%}", f"{r.max_drawdown:.1%}",
                          f"{r.annualized_return:.1%}", f"{r.sharpe_ratio:.2f}",
                          f"{r.beta:.2f}", f"{r.correlation:.2f}"],
            BENCHMARK_NAME: [f"{r.benchmark_volatility:.1%}", f"{r.benchmark_max_drawdown:.1%}",
                             f"{r.benchmark_annualized_return:.1%}", "—", "1.00", "1.00"],
        })
        st.dataframe(risk_df, hide_index=True, width="stretch")
    with right:
        st.markdown("**Concentration**")
        if not result.concentration.flags:
            st.success("No concentration guidelines exceeded.", icon="✅")
        for f in result.concentration.flags:
            color = {"high": "🔴", "moderate": "🟠", "low": "🟡"}.get(f.severity, "⚪")
            st.markdown(f"{color} **{f.subject}** ({f.weight:.0%}) — {f.message}")


# ==========================================================================
# Rebalancing
# ==========================================================================
def rebalancing() -> None:
    ui.page_title("Rebalancing", "Drift from target and a tax-aware trade plan.")
    result = _active()
    if result is None:
        _needs_portfolio_notice()
        return

    plan = result.plan
    st.markdown(f"**Allocation vs. {result.model.name} target**")
    drift_df = pd.DataFrame({
        "Asset class": [d.asset_class for d in plan.drifts],
        "Current": [d.current_weight for d in plan.drifts],
        "Target": [d.target_weight for d in plan.drifts],
        "Drift": [d.drift for d in plan.drifts],
        "Dollar gap": [d.dollar_gap for d in plan.drifts],
    })
    st.dataframe(
        drift_df, hide_index=True, width="stretch",
        column_config={
            "Current": st.column_config.NumberColumn(format="%.1f%%"),
            "Target": st.column_config.NumberColumn(format="%.1f%%"),
            "Drift": st.column_config.NumberColumn(format="%+.1f%%"),
            "Dollar gap": st.column_config.NumberColumn(format="$%,.0f"),
        },
    )

    if not plan.needs_rebalancing:
        st.success("Every asset class is within tolerance of the target. No trades indicated.",
                   icon="✅")
        return

    st.write("")
    st.markdown("**Proposed trades** — sourced sheltered-first, tax priced")
    trade_df = pd.DataFrame({
        "Reduce": [leg.ticker for leg in plan.sells],
        "Account": [leg.account_type.title() for leg in plan.sells],
        "Amount": [leg.dollars for leg in plan.sells],
        "Gain realized": [leg.realized_gain for leg in plan.sells],
        "Term": ["Long-term" if leg.is_long_term else "Short-term" for leg in plan.sells],
        "Est. tax": [leg.estimated_tax for leg in plan.sells],
    })
    st.dataframe(
        trade_df, hide_index=True, width="stretch",
        column_config={
            "Amount": st.column_config.NumberColumn(format="$%,.0f"),
            "Gain realized": st.column_config.NumberColumn(format="$%,.0f"),
            "Est. tax": st.column_config.NumberColumn(format="$%,.0f"),
        },
    )
    m1, m2, m3 = st.columns(3)
    m1.metric("Turnover", f"${plan.total_turnover:,.0f}")
    m2.metric("Est. tax cost", f"${plan.total_tax_cost:,.0f}",
              f"{plan.tax_cost_pct_of_turnover:.1%} of turnover", delta_color="off")
    m3.metric("Sourced tax-free", f"${plan.tax_free_proceeds:,.0f}")
    for n in plan.notes:
        st.caption(f"• {n}")


# ==========================================================================
# Reports
# ==========================================================================
def reports() -> None:
    ui.page_title("Reports", "Generate a client-ready report from the loaded portfolio.")
    result = _active()
    if result is None:
        _needs_portfolio_notice()
        return

    html = render_html(
        result.portfolio, result.allocation, result.risk, result.concentration,
        result.plan, result.model, result.narrative, result.market,
    )
    st.download_button(
        "Download report (HTML)", data=html,
        file_name=f"{result.portfolio.client_name.replace(' ', '_').lower()}_report.html",
        mime="text/html", type="primary",
    )
    st.caption("Opens in any browser; print to PDF for a client-quality one-pager.")
    st.write("")
    st.components.v1.html(html, height=820, scrolling=True)


# ==========================================================================
# Settings
# ==========================================================================
def settings() -> None:
    ui.page_title("Settings", "Portfolio selection and configuration.")
    st.markdown("**Active portfolio**")
    _portfolio_picker("settings")

    st.write("")
    st.markdown("**Configuration**")
    st.write(f"- Commentary engine: {'AI (Anthropic key detected)' if has_api_key() else 'Rule-based (no API key)'}")
    st.write(f"- Benchmark: {BENCHMARK_NAME}")
    st.write(f"- Firm name: {ui.FIRM_NAME}  \n"
             f"  *(change `FIRM_NAME` in app_ui.py to rebrand)*")
    st.caption("Educational project — not investment advice. All sample data is synthetic.")


# ==========================================================================
# Planning  (the suitability flow)
# ==========================================================================
def planning() -> None:
    ui.page_title(
        "Planning",
        "Capacity-first suitability: risk profile, allocation, retirement-income "
        "readiness, and a sequence-of-returns stress test.",
    )

    with st.form("intake"):
        st.markdown("##### Personal")
        p1, p2, p3 = st.columns(3)
        name = p1.text_input("Client name", "New Client")
        age = p2.number_input("Age", 18, 100, 45)
        dependents = p3.number_input("Dependents", 0, 15, 0)

        st.markdown("##### Time horizon & employment")
        h1, h2, h3 = st.columns(3)
        horizon = h1.number_input("Time horizon (years)", 1, 50, 15,
                                  help="Years until the funds are needed.")
        employment = h2.selectbox("Employment", list(Employment),
                                  format_func=lambda e: e.value.replace("_", " ").title())
        income = h3.number_input("Annual income ($)", 0, value=100_000, step=5_000)

        st.markdown("##### Balance sheet")
        b1, b2, b3 = st.columns(3)
        net_worth = b1.number_input("Net worth ($)", 0, value=500_000, step=10_000)
        liquid = b2.number_input("Liquid net worth ($)", 0, value=250_000, step=10_000)
        tax = b3.slider("Marginal tax bracket", 0.0, 0.5, 0.24, 0.01, format="%.0f%%")

        st.markdown("##### Retirement income")
        st.caption("Leave spending at 0 if the client is still accumulating.")
        ri1, ri2 = st.columns(2)
        investable = ri1.number_input("Investable assets ($)", 0, value=500_000, step=10_000)
        spending = ri2.number_input("Annual spending need ($)", 0, value=0, step=5_000)
        ri3, ri4 = st.columns(2)
        ss_income = ri3.number_input("Social Security ($/yr)", 0, value=0, step=1_000)
        pension_income = ri4.number_input("Pension / other income ($/yr)", 0, value=0, step=1_000)

        st.markdown("##### Liquidity & reserves")
        l1, l2 = st.columns(2)
        withdrawal = l1.number_input("Near-term withdrawal need ($)", 0, value=0, step=5_000)
        reserve = l2.checkbox("Emergency reserve in place (3–6 months)", value=True)

        st.markdown("##### Objectives & risk")
        o1, o2 = st.columns(2)
        objective = o1.selectbox("Primary objective", list(Objective), index=2,
                                 format_func=lambda o: o.value.title())
        risk_tol = o2.selectbox("Stated risk tolerance", list(RiskTolerance), index=2,
                                format_func=lambda r: r.value.replace("_", " ").title())
        d1, d2 = st.columns(2)
        drawdown = d1.slider("Drawdown tolerance", 0.0, 0.6, 0.20, 0.05, format="%.0f%%")
        experience = d2.selectbox("Investment experience", list(Experience), index=1,
                                  format_func=lambda e: e.value.title())
        constraints = st.text_area("Constraints / existing concentrations (optional)", "")

        submitted = st.form_submit_button("Generate recommendation", type="primary")

    if submitted:
        profile = ClientProfile(
            client_name=name, age=int(age), dependents=int(dependents),
            time_horizon_years=int(horizon), employment=employment,
            annual_income=float(income), net_worth=float(net_worth),
            liquid_net_worth=float(liquid), marginal_tax_bracket=float(tax),
            near_term_withdrawal=float(withdrawal), has_emergency_reserve=bool(reserve),
            objective=objective, risk_tolerance=risk_tol,
            drawdown_tolerance=float(drawdown), experience=experience,
            constraints=constraints, investable_assets=float(investable),
            annual_spending=float(spending), social_security_income=float(ss_income),
            pension_income=float(pension_income),
        )
        st.session_state["plan"] = build_recommendation(profile)

    rec = st.session_state.get("plan")
    if rec is None:
        return

    profile, assessment, readiness = rec.profile, rec.assessment, rec.readiness
    st.success(f"Profile captured — {profile.summary_line()}")

    if readiness.applicable:
        st.markdown("#### Retirement income readiness")
        icon = {"Safe": "✅", "Caution": "⚠️", "Unsafe": "🛑"}[readiness.status]
        w1, w2, w3 = st.columns(3)
        w1.metric("Withdrawal rate", f"{readiness.withdrawal_rate:.1%}",
                  f"benchmark {readiness.benchmark_rate:.0%}", delta_color="off")
        w2.metric("Status", f"{icon} {readiness.status}")
        w3.metric("Suggested split", readiness.suggested_split_label)
        for f in readiness.findings:
            st.markdown(f"- {f}")
        for rf in readiness.red_flags:
            st.error(rf, icon="🚩")
        st.divider()

    st.markdown("#### Recommendation")
    rc1, rc2, rc3, rc4 = st.columns(4)
    rc1.metric("Recommended model", rec.recommended_label)
    rc2.metric("Desired (score alone)", rec.desired_label,
               "capped by capacity" if rec.capped else "capacity supports it",
               delta_color="off")
    rc3.metric("Risk score", f"{assessment.raw_score:.0f}/100")
    rc4.metric("Equity ceiling", f"{rec.capacity.max_equity:.0%}")

    if rec.capped:
        st.warning(f"Stated profile supports **{rec.desired_label}**, but capacity caps the "
                   f"recommendation at **{rec.recommended_label}** — situation overriding "
                   f"attitude.", icon="🛡️")
    for line in rec.rationale:
        st.markdown(line if line.strip().startswith("•") else f"- {line}")

    with st.expander("Capacity ceiling — every constraint"):
        for c in rec.capacity.constraints:
            st.markdown(f"{'▶' if c.binding else '•'} **{c.ceiling:.0%}** — {c.label}")

    stress = rec.stress
    if stress.applicable:
        st.divider()
        st.markdown("#### Sequence-of-returns stress test")
        st.caption(f"{stress.equity_fraction:.0%} equity, ${stress.base_withdrawal:,.0f}/yr "
                   f"withdrawal over {stress.horizon_years} years.")
        chart_df = pd.DataFrame(
            {sc.name: sc.values for sc in stress.scenarios},
            index=range(1, stress.horizon_years + 1),
        )
        chart_df.index.name = "Year"
        st.line_chart(chart_df, height=320)
        cols = st.columns(3)
        for col, sc in zip(cols, stress.scenarios):
            status = "Survived" if sc.survived else f"Depleted yr {sc.depletion_year}"
            col.metric(sc.name, f"${sc.terminal_value:,.0f}", status, delta_color="off")
        for f in stress.findings:
            st.info(f, icon="📉")
        st.caption("Early bear and Late bear use the identical annual returns in reverse "
                   "order — any gap is pure sequence-of-returns risk. Illustrative, not a forecast.")


# Router table.
PAGES = {
    "Home": home,
    "Dashboard": dashboard,
    "Portfolio Analysis": portfolio_analysis,
    "Rebalancing": rebalancing,
    "Planning": planning,
    "Reports": reports,
    "Settings": settings,
}
