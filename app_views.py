"""Page views for the Advisor Workbench web app.

Data flow the pages implement:

  Client Survey  ──submit──▶  session_state["surveys"]  ──▶  Dashboard
       │                                                     "Review client surveys"
       │                                                          │
       └── goals (risk triangle) + family balance sheet           ▼
                                                        Portfolio Analysis
                                                        (survey subject → quick
                                                         answers + full suitability
                                                         analysis)

Analytics are real (`pra` engine). The advisor CRM pipeline, survey-send, and
connect-a-rep actions are simulated and labeled as such.
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

ASSET_LABELS = ["Cash & savings", "Taxable investments", "Retirement accounts",
                "Home value", "Other assets"]
LIABILITY_LABELS = ["Mortgage", "Auto & student loans", "Credit cards", "Other debt"]


# ==========================================================================
# Shared portfolio helpers
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
    return True


def _portfolio_picker(context: str, navigate: bool = False) -> None:
    c1, c2 = st.columns([2, 1])
    with c1:
        source = st.radio("Portfolio source", ["Sample portfolio", "Upload a CSV"],
                          horizontal=True, key=f"src_{context}")
        upload_text = None
        if source == "Sample portfolio":
            label = st.selectbox("Select a portfolio", list(SAMPLE_PORTFOLIOS), key=f"sample_{context}")
        else:
            up = st.file_uploader("Portfolio CSV", type=["csv"], key=f"up_{context}")
            label = "Uploaded Portfolio"
            upload_text = up.getvalue().decode("utf-8") if up is not None else None
    with c2:
        model_key = st.selectbox("Target model", list(MODEL_PORTFOLIOS),
                                 format_func=lambda k: MODEL_PORTFOLIOS[k].name,
                                 index=list(MODEL_PORTFOLIOS).index("balanced_growth"),
                                 key=f"model_{context}")
    disabled = source == "Upload a CSV" and upload_text is None
    if st.button("Load portfolio", type="primary", disabled=disabled, key=f"load_{context}"):
        if _compute_active(label, model_key, upload_text) and navigate:
            ui.go_to("Portfolio Analysis")
        elif _active() is not None:
            st.rerun()


# ==========================================================================
# Risk triangle (Growth / Income / Safety)
# ==========================================================================
def _risk_triangle_svg(wg: float, wi: float, ws: float) -> str:
    total = wg + wi + ws or 1.0
    wg, wi, ws = wg / total, wi / total, ws / total
    G, I, S = (150, 26), (30, 250), (270, 250)
    px = wg * G[0] + wi * I[0] + ws * S[0]
    py = wg * G[1] + wi * I[1] + ws * S[1]
    return f"""
    <svg viewBox="0 0 300 290" width="300" height="278" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="tri" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#e8f3f6"/>
          <stop offset="100%" stop-color="#dbe9f2"/>
        </linearGradient>
      </defs>
      <polygon points="{G[0]},{G[1]} {I[0]},{I[1]} {S[0]},{S[1]}"
               fill="url(#tri)" stroke="{ui.NAVY}" stroke-width="2"/>
      <text x="{G[0]}" y="16" text-anchor="middle" font-size="13" font-weight="700" fill="{ui.NAVY_DARK}">Growth</text>
      <text x="{I[0]-4}" y="268" text-anchor="middle" font-size="13" font-weight="700" fill="{ui.NAVY_DARK}">Income</text>
      <text x="{S[0]+4}" y="268" text-anchor="middle" font-size="13" font-weight="700" fill="{ui.NAVY_DARK}">Safety</text>
      <circle cx="{px:.1f}" cy="{py:.1f}" r="10" fill="{ui.TEAL}" stroke="#fff" stroke-width="3"/>
    </svg>
    """


def _triangle_to_objective(wg: float, wi: float, ws: float) -> Objective:
    total = wg + wi + ws or 1.0
    wg, wi, ws = wg / total, wi / total, ws / total
    top = max(wg, wi, ws)
    if top < 0.45:
        return Objective.BALANCED
    if wg == top:
        return Objective.GROWTH
    if wi == top:
        return Objective.INCOME
    return Objective.PRESERVATION


def _triangle_to_risk_tolerance(wg: float, ws: float, total: float) -> RiskTolerance:
    total = total or 1.0
    tilt = (wg - ws) / total  # +1 all growth, -1 all safety
    if tilt > 0.4:
        return RiskTolerance.AGGRESSIVE
    if tilt > 0.15:
        return RiskTolerance.MODERATE_AGGRESSIVE
    if tilt > -0.15:
        return RiskTolerance.MODERATE
    if tilt > -0.4:
        return RiskTolerance.MODERATE_CONSERVATIVE
    return RiskTolerance.CONSERVATIVE


# ==========================================================================
# Home
# ==========================================================================
def home() -> None:
    st.markdown(
        f"""
        <div class="aw-hero">
          <div class="eyebrow">{ui.FIRM_NAME}</div>
          <h1>Thoughtful planning for your whole family's future.</h1>
          <p>From a first conversation to a complete portfolio review — clear,
             personal guidance backed by real analysis, so every decision fits
             your family's goals.</p>
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
    st.markdown('<div class="aw-section-label">How we help</div>', unsafe_allow_html=True)
    r1 = st.columns(3)
    with r1[0]:
        ui.card("👪", "Get to know your family",
                "A short survey captures your goals, your comfort with risk, and your "
                "family balance sheet — so your first meeting starts with understanding.")
    with r1[1]:
        ui.card("🧭", "A plan that fits you",
                "Capacity-first recommendations, retirement-income readiness, and "
                "stress testing — reconciled into one suitable allocation.")
    with r1[2]:
        ui.card("📊", "Clarity on your portfolio",
                "Live valuation, concentration and risk, tax-aware rebalancing, and a "
                "report you can keep — every figure computed, never guessed.")

    st.write("")
    st.markdown('<div class="aw-section-label">Talk to an advisor</div>', unsafe_allow_html=True)
    with st.container(border=True):
        cc1, cc2 = st.columns([3, 1])
        cc1.markdown(f"**Ready to start?** Complete a short survey and a {ui.FIRM_NAME} "
                     "advisor will follow up to build your plan.")
        if cc2.button("Connect now", type="primary", width="stretch", key="connect_rep"):
            ui.go_to("Client Survey")

    st.caption("Educational portfolio project — not investment advice. All sample data is synthetic.")


# ==========================================================================
# Dashboard — advisor CRM + review client surveys
# ==========================================================================
def _sim_clients() -> list[dict]:
    today = dt.date.today()
    d = lambda n: today + dt.timedelta(days=n)
    return [
        {"name": "Robert & Susan Hale", "meeting": d(1), "time": "9:00 AM",
         "complete": True, "aum": 2_450_000, "reason": "Annual review"},
        {"name": "Priya Nadella", "meeting": d(1), "time": "1:30 PM",
         "complete": False, "aum": 780_000, "reason": "New client onboarding"},
        {"name": "James Okoro", "meeting": d(2), "time": "11:00 AM",
         "complete": True, "aum": 1_120_000, "reason": "Rebalancing discussion"},
        {"name": "The Delgado Family Trust", "meeting": d(3), "time": "3:00 PM",
         "complete": False, "aum": 4_300_000, "reason": "Estate & concentration review"},
        {"name": "Helen Yoshida", "meeting": d(9), "time": "2:00 PM",
         "complete": True, "aum": 1_875_000, "reason": "Retirement income planning"},
    ]


def dashboard() -> None:
    ui.page_title("Advisor Dashboard",
                  "Your client pipeline for the week. (Simulated workflow data.)")
    clients = _sim_clients()
    surveys = st.session_state.get("surveys", [])
    today = dt.date.today()
    incomplete = [c for c in clients if not c["complete"]]
    week = [c for c in clients if 0 <= (c["meeting"] - today).days <= 7]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Active clients", len(clients))
    m2.metric("Profiles incomplete", len(incomplete))
    m3.metric("Meetings this week", len(week))
    m4.metric("New surveys to review", len(surveys))

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
    rows = [{"Client": c["name"], "Date": c["meeting"].strftime("%a %b %d"), "Time": c["time"],
             "Profile": "Complete" if c["complete"] else "Incomplete", "Purpose": c["reason"]}
            for c in sorted(clients, key=lambda c: c["meeting"])]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

    # --- Review client surveys (real submissions) ------------------------
    st.write("")
    st.markdown("**📝 Review client surveys** — new intake from prospective clients")
    if not surveys:
        st.info("No surveys submitted yet. Completed client surveys appear here for review.",
                icon="🗂️")
    for rec_wrap in reversed(surveys):
        rec = rec_wrap["rec"]
        with st.container(border=True):
            a, b = st.columns([3, 1])
            a.markdown(
                f"**{rec_wrap['name']}** · submitted {rec_wrap['submitted_at']:%b %d, %I:%M %p}  \n"
                f"<span style='color:#6b7280;font-size:13px'>"
                f"Goal: {rec.profile.objective.value.title()} · "
                f"Recommended: {rec.recommended_label} · "
                f"Net worth ${rec_wrap['net_worth']:,.0f}</span>",
                unsafe_allow_html=True)
            if b.button("Review", key=f"review_{rec_wrap['id']}", type="primary", width="stretch"):
                st.session_state["review_survey_id"] = rec_wrap["id"]
                ui.go_to("Portfolio Analysis")

    st.caption("Priority pipeline and meetings are a demo. Submitted surveys above are real "
               "engine analyses of what clients entered.")


# ==========================================================================
# Portfolio Analysis — portfolio OR client-survey analysis
# ==========================================================================
def _render_recommendation(rec) -> None:
    """Advisor-facing suitability detail for a submitted survey."""
    a, readiness = rec.assessment, rec.readiness
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

    st.markdown("#### Recommendation")
    rc1, rc2, rc3, rc4 = st.columns(4)
    rc1.metric("Recommended model", rec.recommended_label)
    rc2.metric("Desired (score alone)", rec.desired_label,
               "capped by capacity" if rec.capped else "capacity supports it", delta_color="off")
    rc3.metric("Risk score", f"{a.raw_score:.0f}/100")
    rc4.metric("Equity ceiling", f"{rec.capacity.max_equity:.0%}")
    if rec.capped:
        st.warning(f"Stated profile supports **{rec.desired_label}**, but capacity caps the "
                   f"recommendation at **{rec.recommended_label}**.", icon="🛡️")
    for line in rec.rationale:
        st.markdown(line if line.strip().startswith("•") else f"- {line}")
    with st.expander("Capacity ceiling — every constraint"):
        for c in rec.capacity.constraints:
            st.markdown(f"{'▶' if c.binding else '•'} **{c.ceiling:.0%}** — {c.label}")

    stress = rec.stress
    if stress.applicable:
        st.markdown("#### Sequence-of-returns stress test")
        chart_df = pd.DataFrame({sc.name: sc.values for sc in stress.scenarios},
                                index=range(1, stress.horizon_years + 1))
        chart_df.index.name = "Year"
        st.line_chart(chart_df, height=300)
        cols = st.columns(3)
        for col, sc in zip(cols, stress.scenarios):
            status = "Survived" if sc.survived else f"Depleted yr {sc.depletion_year}"
            col.metric(sc.name, f"${sc.terminal_value:,.0f}", status, delta_color="off")
        for f in stress.findings:
            st.info(f, icon="📉")


def _render_survey_subject(rec_wrap: dict) -> None:
    rec = rec_wrap["rec"]
    st.success(f"Reviewing survey — **{rec_wrap['name']}**, submitted "
               f"{rec_wrap['submitted_at']:%b %d, %Y %I:%M %p}", icon="📝")

    st.markdown("#### Client answers at a glance")
    p = rec.profile
    q1, q2, q3, q4 = st.columns(4)
    q1.metric("Age", p.age)
    q2.metric("Horizon", f"{p.time_horizon_years} yrs")
    q3.metric("Primary goal", p.objective.value.title())
    q4.metric("Risk tolerance", p.risk_tolerance.value.replace("_", " ").title())

    # Family balance sheet summary.
    assets, liabs = rec_wrap["assets"], rec_wrap["liabilities"]
    ta, tl = sum(assets.values()), sum(liabs.values())
    st.markdown("#### Family balance sheet")
    bs1, bs2, bs3 = st.columns(3)
    bs1.metric("Total assets", f"${ta:,.0f}")
    bs2.metric("Total liabilities", f"${tl:,.0f}")
    bs3.metric("Net worth", f"${ta - tl:,.0f}")
    left, right = st.columns(2)
    with left:
        st.caption("Assets")
        st.dataframe(pd.DataFrame({"Asset": list(assets), "Value": list(assets.values())}),
                     hide_index=True, width="stretch",
                     column_config={"Value": st.column_config.NumberColumn(format="$%,.0f")})
    with right:
        st.caption("Liabilities")
        st.dataframe(pd.DataFrame({"Liability": list(liabs), "Balance": list(liabs.values())}),
                     hide_index=True, width="stretch",
                     column_config={"Balance": st.column_config.NumberColumn(format="$%,.0f")})

    st.divider()
    _render_recommendation(rec)


def _render_portfolio_subject(result: AnalysisResult) -> None:
    a, r, plan = result.allocation, result.risk, result.plan
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Portfolio value", f"${a.total_value:,.0f}", f"{len(a.positions)} positions")
    c2.metric("Unrealized gain", f"${a.total_unrealized_gain:,.0f}",
              f"{a.total_unrealized_gain / a.total_cost_basis:+.1%} on cost")
    c3.metric("Volatility (ann.)", f"{r.annualized_volatility:.1%}",
              f"S&P {r.benchmark_volatility:.1%}", delta_color="off")
    c4.metric("Max drawdown", f"{r.max_drawdown:.1%}", f"S&P {r.benchmark_max_drawdown:.1%}",
              delta_color="off")

    st.markdown("#### Holdings")
    df = pd.DataFrame([{
        "Ticker": p.ticker, "Name": p.name, "Class": p.asset_class,
        "Value": p.market_value, "Weight": p.market_value / a.total_value,
        "Cost basis": p.cost_basis, "Unrealized": p.unrealized_gain, "Return": p.gain_pct,
    } for p in a.positions])
    st.dataframe(df, hide_index=True, width="stretch", column_config={
        "Value": st.column_config.NumberColumn(format="$%,.0f"),
        "Cost basis": st.column_config.NumberColumn(format="$%,.0f"),
        "Unrealized": st.column_config.NumberColumn(format="$%,.0f"),
        "Weight": st.column_config.NumberColumn(format="%.1f%%"),
        "Return": st.column_config.NumberColumn(format="%.1f%%")})

    left, right = st.columns(2)
    with left:
        st.markdown("#### Risk & return")
        st.caption("3-year, current weights")
        st.dataframe(pd.DataFrame({
            "Measure": ["Volatility (ann.)", "Max drawdown", "Annualized return",
                        "Sharpe ratio", "Beta vs S&P 500", "Correlation"],
            "Portfolio": [f"{r.annualized_volatility:.1%}", f"{r.max_drawdown:.1%}",
                          f"{r.annualized_return:.1%}", f"{r.sharpe_ratio:.2f}",
                          f"{r.beta:.2f}", f"{r.correlation:.2f}"],
            BENCHMARK_NAME: [f"{r.benchmark_volatility:.1%}", f"{r.benchmark_max_drawdown:.1%}",
                             f"{r.benchmark_annualized_return:.1%}", "—", "1.00", "1.00"]}),
            hide_index=True, width="stretch")
    with right:
        st.markdown("#### Concentration")
        if not result.concentration.flags:
            st.success("No concentration guidelines exceeded.", icon="✅")
        for f in result.concentration.flags:
            color = {"high": "🔴", "moderate": "🟠", "low": "🟡"}.get(f.severity, "⚪")
            st.markdown(f"{color} **{f.subject}** ({f.weight:.0%}) — {f.message}")

    st.markdown("#### Rebalancing")
    st.dataframe(pd.DataFrame({
        "Asset class": [d.asset_class for d in plan.drifts],
        "Current": [d.current_weight for d in plan.drifts],
        "Target": [d.target_weight for d in plan.drifts],
        "Drift": [d.drift for d in plan.drifts],
        "Dollar gap": [d.dollar_gap for d in plan.drifts]}),
        hide_index=True, width="stretch", column_config={
            "Current": st.column_config.NumberColumn(format="%.1f%%"),
            "Target": st.column_config.NumberColumn(format="%.1f%%"),
            "Drift": st.column_config.NumberColumn(format="%+.1f%%"),
            "Dollar gap": st.column_config.NumberColumn(format="$%,.0f")})
    if plan.needs_rebalancing:
        st.dataframe(pd.DataFrame({
            "Reduce": [l.ticker for l in plan.sells],
            "Account": [l.account_type.title() for l in plan.sells],
            "Amount": [l.dollars for l in plan.sells],
            "Gain realized": [l.realized_gain for l in plan.sells],
            "Term": ["Long-term" if l.is_long_term else "Short-term" for l in plan.sells],
            "Est. tax": [l.estimated_tax for l in plan.sells]}),
            hide_index=True, width="stretch", column_config={
                "Amount": st.column_config.NumberColumn(format="$%,.0f"),
                "Gain realized": st.column_config.NumberColumn(format="$%,.0f"),
                "Est. tax": st.column_config.NumberColumn(format="$%,.0f")})
        t1, t2, t3 = st.columns(3)
        t1.metric("Turnover", f"${plan.total_turnover:,.0f}")
        t2.metric("Est. tax cost", f"${plan.total_tax_cost:,.0f}",
                  f"{plan.tax_cost_pct_of_turnover:.1%} of turnover", delta_color="off")
        t3.metric("Sourced tax-free", f"${plan.tax_free_proceeds:,.0f}")
    else:
        st.success("Within tolerance of target. No trades indicated.", icon="✅")

    st.markdown("#### Client report")
    html = render_html(result.portfolio, a, r, result.concentration, plan,
                       result.model, result.narrative, result.market)
    st.download_button("Download report (HTML)", data=html,
                       file_name=f"{result.portfolio.client_name.replace(' ', '_').lower()}_report.html",
                       mime="text/html", type="primary")
    with st.expander("Preview report"):
        st.components.v1.html(html, height=760, scrolling=True)


def portfolio_analysis() -> None:
    ui.page_title("Portfolio Analysis",
                  "Analyze a holdings portfolio, or review a recently filed client survey.")
    surveys = st.session_state.get("surveys", [])
    active = _active()

    # Build the subject options: filed surveys first, then a loaded portfolio.
    options: list[tuple[str, str]] = []
    for w in reversed(surveys):
        options.append((f"survey:{w['id']}", f"📝 Survey — {w['name']} ({w['submitted_at']:%b %d})"))
    if active is not None:
        options.append(("active", f"📊 Portfolio — {active.portfolio.client_name}"))
    options.append(("load", "➕ Load a new portfolio…"))

    # Default selection: a survey we were sent to review, else first option.
    default_idx = 0
    review_id = st.session_state.pop("review_survey_id", None)
    if review_id is not None:
        for i, (val, _) in enumerate(options):
            if val == f"survey:{review_id}":
                default_idx = i
                break

    choice = st.selectbox("Select a portfolio or survey", options,
                          format_func=lambda o: o[1], index=default_idx, key="subject_sel")
    st.divider()

    kind = choice[0]
    if kind == "load":
        _portfolio_picker("inline", navigate=False)
    elif kind == "active" and active is not None:
        _render_portfolio_subject(active)
    elif kind.startswith("survey:"):
        sid = int(kind.split(":")[1])
        wrap = next((w for w in surveys if w["id"] == sid), None)
        if wrap:
            _render_survey_subject(wrap)


# ==========================================================================
# Client Survey
# ==========================================================================
def client_survey() -> None:
    if st.session_state.get("survey_done"):
        _survey_thank_you()
        return

    st.markdown(
        f"""
        <div class="aw-hero" style="padding:34px 40px">
          <div class="eyebrow">{ui.FIRM_NAME}</div>
          <h1 style="font-size:28px">Tell us about your family's goals.</h1>
          <p>A few minutes now helps your advisor arrive already understanding your
             situation — so your first meeting is about you, not paperwork.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")

    tabs = st.tabs(["🧭 Your Goals", "🏠 Family Balance Sheet", "👤 About You"])

    # --- Goals: the risk triangle (live) ---------------------------------
    with tabs[0]:
        st.markdown("**Where does your family sit between growth, income, and safety?**")
        st.caption("Adjust the sliders — the marker moves inside the triangle to show your balance.")
        tri_col, ctrl_col = st.columns([1, 1])
        with ctrl_col:
            wg = st.slider("Growth — build wealth over time", 0, 100, 50, key="tri_g")
            wi = st.slider("Income — steady cash flow", 0, 100, 25, key="tri_i")
            ws = st.slider("Safety — protect what I have", 0, 100, 25, key="tri_s")
            horizon = st.number_input("Years until you need this money", 1, 50, 15, key="sv_h")
            drawdown = st.slider("Largest drop you could sit through", 0.0, 0.6, 0.20, 0.05,
                                 format="%.0f%%", key="sv_dd")
            experience = st.selectbox("Investing experience", list(Experience), index=1,
                                      format_func=lambda e: e.value.title(), key="sv_exp")
        with tri_col:
            st.markdown(_risk_triangle_svg(wg, wi, ws), unsafe_allow_html=True)
            obj = _triangle_to_objective(wg, wi, ws)
            st.caption(f"Your balance reads as a **{obj.value.title()}** orientation.")

    # --- Family balance sheet --------------------------------------------
    with tabs[1]:
        st.markdown("**Your family's assets and liabilities**")
        st.caption("Approximate values are fine — this helps size your plan.")
        ac, lc = st.columns(2)
        assets: dict[str, float] = {}
        with ac:
            st.markdown("Assets")
            defaults = [50_000, 200_000, 250_000, 400_000, 0]
            for lab, dv in zip(ASSET_LABELS, defaults):
                assets[lab] = float(st.number_input(lab, 0, value=dv, step=5_000, key=f"as_{lab}"))
        liabs: dict[str, float] = {}
        with lc:
            st.markdown("Liabilities")
            ldef = [280_000, 20_000, 0, 0]
            for lab, dv in zip(LIABILITY_LABELS, ldef):
                liabs[lab] = float(st.number_input(lab, 0, value=dv, step=5_000, key=f"li_{lab}"))
        ta, tl = sum(assets.values()), sum(liabs.values())
        s1, s2, s3 = st.columns(3)
        s1.metric("Total assets", f"${ta:,.0f}")
        s2.metric("Total liabilities", f"${tl:,.0f}")
        s3.metric("Net worth", f"${ta - tl:,.0f}")

    # --- About you --------------------------------------------------------
    with tabs[2]:
        a1, a2, a3 = st.columns(3)
        name = a1.text_input("Your name", "", key="sv_name")
        age = a2.number_input("Age", 18, 100, 45, key="sv_age")
        dependents = a3.number_input("Dependents", 0, 15, 0, key="sv_dep")
        e1, e2 = st.columns(2)
        employment = e1.selectbox("Employment", list(Employment),
                                  format_func=lambda e: e.value.replace("_", " ").title(), key="sv_emp")
        income = e2.number_input("Annual income ($)", 0, value=100_000, step=5_000, key="sv_inc")
        st.caption("If you're retired or nearing it:")
        r1, r2, r3 = st.columns(3)
        spending = r1.number_input("Annual spending need ($)", 0, value=0, step=5_000, key="sv_sp")
        ss_income = r2.number_input("Social Security ($/yr)", 0, value=0, step=1_000, key="sv_ss")
        pension = r3.number_input("Pension / other ($/yr)", 0, value=0, step=1_000, key="sv_pen")
        reserve = st.checkbox("We have an emergency reserve (3–6 months)", value=True, key="sv_res")

    st.write("")
    share = st.checkbox(f"Share my responses with a {ui.FIRM_NAME} advisor to prepare for our "
                        "meeting", value=True, key="sv_share")
    if st.button("Submit survey", type="primary", key="sv_submit"):
        # Derive engine inputs from the survey.
        investable = assets["Taxable investments"] + assets["Retirement accounts"]
        liquid = assets["Cash & savings"]
        net_worth = sum(assets.values()) - sum(liabs.values())
        profile = ClientProfile(
            client_name=name or "Prospective Client", age=int(age), dependents=int(dependents),
            time_horizon_years=int(horizon), employment=employment, annual_income=float(income),
            net_worth=float(net_worth), liquid_net_worth=float(liquid),
            has_emergency_reserve=bool(reserve),
            objective=_triangle_to_objective(wg, wi, ws),
            risk_tolerance=_triangle_to_risk_tolerance(wg, ws, wg + wi + ws),
            drawdown_tolerance=float(drawdown), experience=experience,
            investable_assets=float(investable), annual_spending=float(spending),
            social_security_income=float(ss_income), pension_income=float(pension))

        st.session_state.setdefault("surveys", [])
        st.session_state.setdefault("survey_seq", 0)
        st.session_state["survey_seq"] += 1
        st.session_state["surveys"].append({
            "id": st.session_state["survey_seq"],
            "name": profile.client_name,
            "submitted_at": dt.datetime.now(),
            "rec": build_recommendation(profile),
            "assets": assets, "liabilities": liabs, "net_worth": net_worth,
        })
        st.session_state["survey_shared"] = bool(share)
        st.session_state["survey_done"] = True
        st.rerun()


def _survey_thank_you() -> None:
    surveys = st.session_state.get("surveys", [])
    rec_wrap = surveys[-1] if surveys else None
    name = rec_wrap["name"] if rec_wrap else "there"
    shared = st.session_state.get("survey_shared", False)

    st.markdown(
        f"""
        <div class="aw-hero" style="text-align:center; padding:56px 40px">
          <div style="font-size:52px; margin-bottom:8px">✓</div>
          <h1 style="font-size:30px; max-width:none">Thank you, {name}.</h1>
          <p style="margin:0 auto">Your responses have been received. An advisor will be
             with you shortly to review your goals and build a plan tailored to your family.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if shared:
            st.success(f"✓ Your responses were shared with the {ui.FIRM_NAME} advisory team and "
                       "now appear on their dashboard for review. "
                       "*(Simulated — no real data is transmitted.)*")
        else:
            st.info("Your responses were saved but not shared.")
        if rec_wrap:
            with st.container(border=True):
                p = rec_wrap["rec"].profile
                st.markdown("**What we heard**")
                st.markdown(f"- Time horizon: **{p.time_horizon_years} years**\n"
                            f"- Orientation: **{p.objective.value.title()}**\n"
                            f"- Net worth: **${rec_wrap['net_worth']:,.0f}**")
                st.caption("Your advisor will translate this into a specific, suitable plan.")
        if st.button("Start a new survey", width="stretch"):
            for k in ("survey_done", "survey_shared"):
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


PAGES = {
    "Home": home,
    "Dashboard": dashboard,
    "Portfolio Analysis": portfolio_analysis,
    "Client Survey": client_survey,
    "Settings": settings,
}
