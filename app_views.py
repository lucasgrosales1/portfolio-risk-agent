"""Page views for the Advisor Workbench web app.

Analytics pages read from the real `pra` engine — no mock numbers. The advisor
Dashboard uses clearly-labeled *simulated* workflow data (a demo client pipeline
and meeting calendar), which is context, not investment figures. The Client
Survey and "connect a representative" actions are simulated too — nothing is
actually sent anywhere.
"""

from __future__ import annotations

import datetime as dt
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


def _portfolio_picker(context: str, navigate: bool = False) -> None:
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
        if _compute_active(label, model_key, upload_text) and navigate:
            st.session_state["page"] = "Portfolio Analysis"
            st.rerun()
        elif _active() is not None:
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

    b1, b2, b3, _ = st.columns([1, 1, 1, 2])
    if b1.button("Open Dashboard", type="primary", width="stretch"):
        ui.go_to("Dashboard")
    if b2.button("Portfolio Analysis", width="stretch"):
        ui.go_to("Portfolio Analysis")
    if b3.button("Take Client Survey", width="stretch"):
        ui.go_to("Client Survey")

    st.write("")
    st.markdown('<div class="aw-section-label">What it does</div>', unsafe_allow_html=True)
    r1 = st.columns(3)
    with r1[0]:
        ui.card("📊", "Portfolio Analysis",
                "Live valuation, allocation, volatility, max drawdown, Sharpe, and "
                "beta — plus tax-aware rebalancing and a client-ready report.")
    with r1[1]:
        ui.card("🧭", "Suitability Planning",
                "Capacity-first recommendations, retirement-income readiness, and a "
                "sequence-of-returns stress test — reconciled into one allocation.")
    with r1[2]:
        ui.card("📝", "Client Survey",
                "A short questionnaire clients complete before meeting — so their "
                "advisor arrives already understanding their needs.")

    st.write("")
    st.markdown('<div class="aw-section-label">Why it is different</div>', unsafe_allow_html=True)
    st.markdown(
        "- **Every number is computed, never guessed.** The analytics run in Python "
        "from real prices; the AI layer only explains figures it is handed.\n"
        "- **Suitability discipline built in.** Capacity constraints cap the "
        "recommendation, and the tool documents *why* — including when it declines a "
        "product.\n"
        "- **Client-ready output.** One click produces a report you could hand to a client."
    )

    # --- Connect with a representative (simulated) -------------------------
    st.write("")
    st.markdown('<div class="aw-section-label">Talk to an advisor</div>', unsafe_allow_html=True)
    with st.container(border=True):
        cc1, cc2 = st.columns([3, 1])
        with cc1:
            st.markdown(
                f"**Have questions? Connect with a {ui.FIRM_NAME} representative.** "
                "Request a callback and an advisor will reach out to walk through your "
                "situation."
            )
        with cc2:
            if st.button("Connect now", type="primary", width="stretch", key="connect_rep"):
                st.session_state["rep_requested"] = True
        if st.session_state.get("rep_requested"):
            st.success(
                "✓ Request received — a representative will reach out shortly. "
                "*(Simulated: this demo does not send a real message.)*"
            )

    st.caption("Educational portfolio project — not investment advice. All sample data is synthetic.")


# ==========================================================================
# Dashboard — advisor CRM view (simulated workflow data)
# ==========================================================================
def _sim_clients() -> list[dict]:
    """Clearly-simulated advisor pipeline. Meeting dates are relative to today."""
    today = dt.date.today()

    def d(days: int) -> dt.date:
        return today + dt.timedelta(days=days)

    return [
        {"name": "Robert & Susan Hale", "meeting": d(1), "time": "9:00 AM",
         "complete": True, "aum": 2_450_000, "reason": "Annual review"},
        {"name": "Priya Nadella", "meeting": d(1), "time": "1:30 PM",
         "complete": False, "aum": 780_000, "reason": "New client onboarding"},
        {"name": "James Okoro", "meeting": d(2), "time": "11:00 AM",
         "complete": True, "aum": 1_120_000, "reason": "Rebalancing discussion"},
        {"name": "The Delgado Family Trust", "meeting": d(3), "time": "3:00 PM",
         "complete": False, "aum": 4_300_000, "reason": "Estate & concentration review"},
        {"name": "Marcus Webb", "meeting": d(6), "time": "10:00 AM",
         "complete": False, "aum": 340_000, "reason": "Survey submitted — needs review"},
        {"name": "Helen Yoshida", "meeting": d(9), "time": "2:00 PM",
         "complete": True, "aum": 1_875_000, "reason": "Retirement income planning"},
    ]


def dashboard() -> None:
    ui.page_title("Advisor Dashboard",
                  "Your client pipeline for the week. (Simulated workflow data.)")
    clients = _sim_clients()
    today = dt.date.today()
    incomplete = [c for c in clients if not c["complete"]]
    week = [c for c in clients if 0 <= (c["meeting"] - today).days <= 7]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Active clients", len(clients))
    m2.metric("Profiles incomplete", len(incomplete))
    m3.metric("Meetings this week", len(week))
    m4.metric("Assets under advisement", f"${sum(c['aum'] for c in clients)/1e6:.1f}M")

    st.write("")
    left, right = st.columns([1, 1])

    with left:
        st.markdown("**⏱️ Priority clients** — by next meeting")
        for c in sorted(clients, key=lambda c: c["meeting"])[:4]:
            days = (c["meeting"] - today).days
            when = "Today" if days == 0 else ("Tomorrow" if days == 1 else f"in {days} days")
            flag = "🔴" if days <= 1 else ("🟠" if days <= 3 else "🟢")
            with st.container(border=True):
                st.markdown(f"{flag} **{c['name']}** — {when}, {c['time']}  \n"
                            f"<span style='color:#6b7280;font-size:13px'>{c['reason']} · "
                            f"${c['aum']:,.0f}</span>", unsafe_allow_html=True)

    with right:
        st.markdown("**📋 Profiles awaiting completion**")
        if not incomplete:
            st.success("All client profiles are complete.", icon="✅")
        for c in incomplete:
            with st.container(border=True):
                st.markdown(f"**{c['name']}**  \n"
                            f"<span style='color:#6b7280;font-size:13px'>{c['reason']}</span>",
                            unsafe_allow_html=True)

    st.write("")
    st.markdown("**📅 Upcoming meetings**")
    rows = [{"Client": c["name"], "Date": c["meeting"].strftime("%a %b %d"),
             "Time": c["time"], "Profile": "Complete" if c["complete"] else "Incomplete",
             "Purpose": c["reason"]}
            for c in sorted(clients, key=lambda c: c["meeting"])]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.caption("Demo pipeline for illustration. In production this would connect to the "
               "firm's CRM and calendar.")


# ==========================================================================
# Portfolio Analysis — merged workspace (holdings, risk, rebalancing, report)
# ==========================================================================
def portfolio_analysis() -> None:
    ui.page_title("Portfolio Analysis",
                  "Holdings, risk, concentration, rebalancing, and the client report.")
    result = _active()
    if result is None:
        _needs_portfolio_notice()
        return

    a, r, plan = result.allocation, result.risk, result.plan
    with st.container(border=True):
        cc = st.columns([3, 1])
        cc[0].markdown(f"**{result.portfolio.client_name}** · target {result.model.name} · "
                       f"benchmark {BENCHMARK_NAME}")
        if cc[1].button("Change portfolio", width="stretch", key="change_pf"):
            st.session_state.pop("active", None)
            st.rerun()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Portfolio value", f"${a.total_value:,.0f}", f"{len(a.positions)} positions")
    c2.metric("Unrealized gain", f"${a.total_unrealized_gain:,.0f}",
              f"{a.total_unrealized_gain / a.total_cost_basis:+.1%} on cost")
    c3.metric("Volatility (ann.)", f"{r.annualized_volatility:.1%}",
              f"S&P {r.benchmark_volatility:.1%}", delta_color="off")
    c4.metric("Max drawdown", f"{r.max_drawdown:.1%}",
              f"S&P {r.benchmark_max_drawdown:.1%}", delta_color="off")

    # --- Holdings ---------------------------------------------------------
    st.markdown("#### Holdings")
    df = pd.DataFrame([{
        "Ticker": p.ticker, "Name": p.name, "Class": p.asset_class,
        "Value": p.market_value, "Weight": p.market_value / a.total_value,
        "Cost basis": p.cost_basis, "Unrealized": p.unrealized_gain, "Return": p.gain_pct,
    } for p in a.positions])
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

    # --- Risk + concentration --------------------------------------------
    left, right = st.columns([1, 1])
    with left:
        st.markdown("#### Risk & return")
        st.caption("3-year, current weights")
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
        st.markdown("#### Concentration")
        if not result.concentration.flags:
            st.success("No concentration guidelines exceeded.", icon="✅")
        for f in result.concentration.flags:
            color = {"high": "🔴", "moderate": "🟠", "low": "🟡"}.get(f.severity, "⚪")
            st.markdown(f"{color} **{f.subject}** ({f.weight:.0%}) — {f.message}")

    # --- Rebalancing ------------------------------------------------------
    st.markdown("#### Rebalancing")
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
    if plan.needs_rebalancing:
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
        t1, t2, t3 = st.columns(3)
        t1.metric("Turnover", f"${plan.total_turnover:,.0f}")
        t2.metric("Est. tax cost", f"${plan.total_tax_cost:,.0f}",
                  f"{plan.tax_cost_pct_of_turnover:.1%} of turnover", delta_color="off")
        t3.metric("Sourced tax-free", f"${plan.tax_free_proceeds:,.0f}")
        for n in plan.notes:
            st.caption(f"• {n}")
    else:
        st.success("Within tolerance of target. No trades indicated.", icon="✅")

    # --- Report -----------------------------------------------------------
    st.markdown("#### Client report")
    html = render_html(result.portfolio, a, r, result.concentration, plan,
                       result.model, result.narrative, result.market)
    st.download_button(
        "Download report (HTML)", data=html,
        file_name=f"{result.portfolio.client_name.replace(' ', '_').lower()}_report.html",
        mime="text/html", type="primary",
    )
    with st.expander("Preview report"):
        st.components.v1.html(html, height=760, scrolling=True)


# ==========================================================================
# Client Survey — client-facing suitability intake
# ==========================================================================
def client_survey() -> None:
    # Completion screen takes over once submitted.
    if st.session_state.get("survey_done"):
        _survey_thank_you()
        return

    st.markdown(
        f"""
        <div class="aw-hero" style="padding:34px 40px">
          <div class="eyebrow">{ui.FIRM_NAME}</div>
          <h1 style="font-size:28px">Tell us about your goals.</h1>
          <p>A few minutes now helps your advisor arrive already understanding your
             situation — so your first meeting is spent on advice, not paperwork.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")

    with st.form("survey"):
        st.markdown("##### About you")
        p1, p2, p3 = st.columns(3)
        name = p1.text_input("Your name", "")
        age = p2.number_input("Age", 18, 100, 45)
        dependents = p3.number_input("Dependents", 0, 15, 0)

        st.markdown("##### Your timeline & work")
        h1, h2, h3 = st.columns(3)
        horizon = h1.number_input("Years until you need this money", 1, 50, 15)
        employment = h2.selectbox("Employment", list(Employment),
                                  format_func=lambda e: e.value.replace("_", " ").title())
        income = h3.number_input("Annual income ($)", 0, value=100_000, step=5_000)

        st.markdown("##### Your finances")
        b1, b2, b3 = st.columns(3)
        net_worth = b1.number_input("Net worth ($)", 0, value=500_000, step=10_000)
        liquid = b2.number_input("Cash & liquid savings ($)", 0, value=250_000, step=10_000)
        investable = b3.number_input("Investable assets ($)", 0, value=500_000, step=10_000)

        st.markdown("##### If you're retired or nearing retirement")
        st.caption("Leave spending at 0 if you're still saving.")
        ri1, ri2, ri3 = st.columns(3)
        spending = ri1.number_input("Annual spending need ($)", 0, value=0, step=5_000)
        ss_income = ri2.number_input("Social Security ($/yr)", 0, value=0, step=1_000)
        pension_income = ri3.number_input("Pension / other income ($/yr)", 0, value=0, step=1_000)

        st.markdown("##### Your comfort with risk")
        o1, o2 = st.columns(2)
        objective = o1.selectbox("What's your main goal?", list(Objective), index=2,
                                 format_func=lambda o: o.value.title())
        risk_tol = o2.selectbox("How would you describe your risk tolerance?",
                                list(RiskTolerance), index=2,
                                format_func=lambda r: r.value.replace("_", " ").title())
        d1, d2 = st.columns(2)
        drawdown = d1.slider("Largest drop you could sit through", 0.0, 0.6, 0.20, 0.05,
                             format="%.0f%%")
        experience = d2.selectbox("Investing experience", list(Experience), index=1,
                                  format_func=lambda e: e.value.title())
        reserve = st.checkbox("I have an emergency reserve (3–6 months of expenses)", value=True)

        share = st.checkbox(
            f"Share my responses with a {ui.FIRM_NAME} advisor so they can prepare for "
            f"our meeting", value=True)

        submitted = st.form_submit_button("Submit survey", type="primary")

    if submitted:
        profile = ClientProfile(
            client_name=name or "Prospective Client", age=int(age),
            dependents=int(dependents), time_horizon_years=int(horizon),
            employment=employment, annual_income=float(income),
            net_worth=float(net_worth), liquid_net_worth=float(liquid),
            near_term_withdrawal=0.0, has_emergency_reserve=bool(reserve),
            objective=objective, risk_tolerance=risk_tol,
            drawdown_tolerance=float(drawdown), experience=experience,
            investable_assets=float(investable), annual_spending=float(spending),
            social_security_income=float(ss_income), pension_income=float(pension_income),
        )
        st.session_state["survey_rec"] = build_recommendation(profile)
        st.session_state["survey_shared"] = bool(share)
        st.session_state["survey_done"] = True
        st.rerun()


def _survey_thank_you() -> None:
    rec = st.session_state.get("survey_rec")
    shared = st.session_state.get("survey_shared", False)
    name = rec.profile.client_name if rec else "there"

    st.markdown(
        f"""
        <div class="aw-hero" style="text-align:center; padding:56px 40px">
          <div style="font-size:52px; margin-bottom:10px">✓</div>
          <h1 style="font-size:30px; max-width:none">Thank you, {name}.</h1>
          <p style="margin:0 auto">Your responses have been received. An advisor will be
             with you shortly to review your goals and build a plan tailored to you.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if shared:
            st.success(
                f"✓ Your responses were shared with the {ui.FIRM_NAME} advisory team. "
                "*(Simulated — this demo does not transmit real data.)*"
            )
        else:
            st.info("Your responses were saved but not shared. You can share them with "
                    "your advisor at your meeting.")

        # A friendly, non-technical summary for the client.
        if rec is not None:
            with st.container(border=True):
                st.markdown("**What we heard**")
                st.markdown(
                    f"- Time horizon: **{rec.profile.time_horizon_years} years**\n"
                    f"- Comfort with risk: **{rec.profile.risk_tolerance.value.replace('_',' ')}**\n"
                    f"- Primary goal: **{rec.profile.objective.value.title()}**"
                )
                st.caption("Your advisor will translate this into a specific, suitable "
                           "allocation when you meet.")

        if st.button("Start a new survey", width="stretch"):
            for k in ("survey_done", "survey_rec", "survey_shared"):
                st.session_state.pop(k, None)
            st.rerun()


# ==========================================================================
# Settings
# ==========================================================================
def settings() -> None:
    ui.page_title("Settings", "Portfolio selection and configuration.")
    st.markdown("**Active portfolio**")
    _portfolio_picker("settings", navigate=True)

    st.write("")
    st.markdown("**Configuration**")
    st.write(f"- Commentary engine: "
             f"{'AI (Anthropic key detected)' if has_api_key() else 'Rule-based (no API key)'}")
    st.write(f"- Benchmark: {BENCHMARK_NAME}")
    st.write(f"- Firm name: **{ui.FIRM_NAME}** — *change `FIRM_NAME` in app_ui.py to rebrand*")
    st.caption("Educational project — not investment advice. All sample data is synthetic.")


# Router table.
PAGES = {
    "Home": home,
    "Dashboard": dashboard,
    "Portfolio Analysis": portfolio_analysis,
    "Client Survey": client_survey,
    "Settings": settings,
}
