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
import secrets
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

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
    FinancialGoal,
    GoalType,
    Objective,
    RiskTolerance,
    build_recommendation,
    render_ips_html,
)
from pra.suitability.profile import GOAL_LABELS
from pra.suitability.structured import (
    BUFFERED_ETF_TERMS,
    INCOME_NOTE_TERMS,
    PRINCIPAL_PROTECTED_TERMS,
    _buffered_payoff,
    _income_note_payoff,
    _payoff_curve,
    _principal_protected_payoff,
)

DATA_DIR = Path(__file__).parent / "data"
SAMPLE_PORTFOLIOS = {
    "Concentrated employer stock (Jordan Reyes)": "sample_concentrated.csv",
    "Pre-retiree, over-allocated (Margaret Chen)": "sample_preretiree.csv",
}

ASSET_LABELS = ["Cash & savings", "Brokerage & investment accounts",
                "Retirement accounts (401k, IRA)", "Home value", "Other assets"]
LIABILITY_LABELS = ["Mortgage", "Auto & student loans", "Credit cards", "Other debt"]


# ==========================================================================
# Shared (cross-session) store
# ==========================================================================
@st.cache_resource
def _shared_store() -> dict:
    """Process-wide state, shared across every visitor -- unlike
    st.session_state, which is isolated per browser tab/connection and can
    never see what a different session submitted. This is what actually lets
    a client fill out a survey on their own device and have it show up on
    the advisor's dashboard in a different session.

    Trade-off, stated plainly: this resets whenever the app process restarts
    (a redeploy, or a Streamlit Community Cloud sleep/wake cycle). That's a
    real limitation for a demo, not a system of record -- surviving restarts
    permanently would need an external database, which this project doesn't
    have. @st.cache_resource guarantees the same dict is returned to every
    caller for the life of the process, which is the only property needed
    here.
    """
    return {"surveys": [], "survey_seq": 0, "invites": {}, "demo_seeded": False,
            "consult_leads": []}


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
        if _compute_active(label, model_key, upload_text):
            # Point Portfolio Analysis at the just-loaded portfolio so it shows
            # immediately, rather than staying on a stale selection.
            st.session_state["pa_subject"] = "active"
            if navigate:
                ui.go_to("Portfolio Analysis")
            else:
                st.rerun()


def _ensure_demo_survey() -> None:
    """Seed one realistic demo client so the full analysis and IPS can be shown
    without filling out the survey first. Seeded once per process (via the
    shared store's own flag, not session_state) so every visitor sees the
    same single demo entry rather than each session growing its own copy."""
    store = _shared_store()
    if store["demo_seeded"]:
        return
    store["demo_seeded"] = True
    p = ClientProfile(
        client_name="The Rivera Family", age=52, dependents=2, time_horizon_years=13,
        employment=Employment.EMPLOYED, annual_income=220_000, net_worth=1_400_000,
        liquid_net_worth=350_000, marginal_tax_bracket=0.32, has_emergency_reserve=True,
        objective=Objective.GROWTH, risk_tolerance=RiskTolerance.MODERATE_AGGRESSIVE,
        drawdown_tolerance=0.25, experience=Experience.GOOD, investable_assets=900_000,
        goals=[FinancialGoal(GoalType.RETIREMENT, 2_500_000, 13, "high"),
               FinancialGoal(GoalType.COLLEGE, 200_000, 9, "medium")])
    store["survey_seq"] += 1
    store["surveys"].append({
        "id": store["survey_seq"], "name": p.client_name,
        "phone": "(305) 555-0148", "email": "rivera.family@example.com",
        "submitted_at": dt.datetime.now() - dt.timedelta(hours=3),
        "rec": build_recommendation(p),
        "assets": {"Cash & savings": 60_000, "Brokerage & investment accounts": 500_000,
                   "Retirement accounts (401k, IRA)": 400_000, "Home value": 620_000,
                   "Other assets": 0},
        "liabilities": {"Mortgage": 240_000, "Auto & student loans": 18_000,
                        "Credit cards": 0, "Other debt": 0},
        "net_worth": 1_322_000, "demo": True,
    })


def _sample_clients() -> dict:
    """Pre-built simulated client profiles for the choose-and-generate flow.

    Cheap to construct (no recommendation is run until the advisor clicks
    Generate). Each entry carries a full profile plus a family balance sheet
    and contact details, so the generated analysis renders like a real survey.
    """
    return {
        "Devon & Ana Carter — 34, young family building wealth": dict(
            phone="(813) 555-0121", email="carter.family@example.com", net_worth=420_000,
            portfolio="client_carter.csv",
            profile=ClientProfile(
                client_name="Devon & Ana Carter", age=34, dependents=2, time_horizon_years=28,
                employment=Employment.EMPLOYED, annual_income=185_000, net_worth=420_000,
                liquid_net_worth=140_000, marginal_tax_bracket=0.24, has_emergency_reserve=True,
                objective=Objective.GROWTH, risk_tolerance=RiskTolerance.AGGRESSIVE,
                drawdown_tolerance=0.40, experience=Experience.GOOD, investable_assets=260_000,
                goals=[FinancialGoal(GoalType.WEALTH, 2_000_000, 25, "high"),
                       FinancialGoal(GoalType.COLLEGE, 250_000, 14, "medium")]),
            assets={"Cash & savings": 40_000, "Brokerage & investment accounts": 120_000,
                    "Retirement accounts (401k, IRA)": 140_000, "Home value": 380_000, "Other assets": 0},
            liabilities={"Mortgage": 300_000, "Auto & student loans": 40_000, "Credit cards": 0, "Other debt": 0}),

        "The Okafor Family — 47, college and retirement": dict(
            phone="(305) 555-0164", email="okafor.household@example.com", net_worth=980_000,
            portfolio="client_okafor.csv",
            profile=ClientProfile(
                client_name="The Okafor Family", age=47, dependents=3, time_horizon_years=18,
                employment=Employment.EMPLOYED, annual_income=240_000, net_worth=980_000,
                liquid_net_worth=280_000, marginal_tax_bracket=0.32, has_emergency_reserve=True,
                objective=Objective.BALANCED, risk_tolerance=RiskTolerance.MODERATE,
                drawdown_tolerance=0.22, experience=Experience.LIMITED, investable_assets=620_000,
                goals=[FinancialGoal(GoalType.COLLEGE, 300_000, 8, "high"),
                       FinancialGoal(GoalType.RETIREMENT, 2_500_000, 18, "medium")]),
            assets={"Cash & savings": 55_000, "Brokerage & investment accounts": 320_000,
                    "Retirement accounts (401k, IRA)": 300_000, "Home value": 560_000, "Other assets": 0},
            liabilities={"Mortgage": 255_000, "Auto & student loans": 0, "Credit cards": 0, "Other debt": 0}),

        "Margaret Ellis — 68, retiree, income focus": dict(
            phone="(727) 555-0139", email="m.ellis@example.com", net_worth=1_150_000,
            portfolio="client_ellis.csv",
            profile=ClientProfile(
                client_name="Margaret Ellis", age=68, dependents=0, time_horizon_years=8,
                employment=Employment.RETIRED, annual_income=0, net_worth=1_150_000,
                liquid_net_worth=340_000, marginal_tax_bracket=0.22, has_emergency_reserve=True,
                objective=Objective.INCOME, risk_tolerance=RiskTolerance.MODERATE_CONSERVATIVE,
                drawdown_tolerance=0.15, experience=Experience.GOOD, investable_assets=980_000,
                annual_spending=72_000, social_security_income=34_000,
                goals=[FinancialGoal(GoalType.WEALTH, 700_000, 20, "medium")]),
            assets={"Cash & savings": 90_000, "Brokerage & investment accounts": 520_000,
                    "Retirement accounts (401k, IRA)": 370_000, "Home value": 480_000, "Other assets": 0},
            liabilities={"Mortgage": 0, "Auto & student loans": 0, "Credit cards": 0, "Other debt": 0}),

        "Raj Patel — 45, concentrated tech position": dict(
            phone="(408) 555-0175", email="raj.patel@example.com", net_worth=2_100_000,
            portfolio="sample_concentrated.csv",
            profile=ClientProfile(
                client_name="Raj Patel", age=45, dependents=1, time_horizon_years=20,
                employment=Employment.EMPLOYED, annual_income=310_000, net_worth=2_100_000,
                liquid_net_worth=520_000, marginal_tax_bracket=0.35, has_emergency_reserve=True,
                objective=Objective.GROWTH, risk_tolerance=RiskTolerance.MODERATE_AGGRESSIVE,
                drawdown_tolerance=0.30, experience=Experience.EXTENSIVE, investable_assets=1_500_000,
                goals=[FinancialGoal(GoalType.WEALTH, 3_000_000, 15, "high"),
                       FinancialGoal(GoalType.MORTGAGE, 400_000, 10, "low")]),
            assets={"Cash & savings": 120_000, "Brokerage & investment accounts": 980_000,
                    "Retirement accounts (401k, IRA)": 520_000, "Home value": 900_000, "Other assets": 0},
            liabilities={"Mortgage": 420_000, "Auto & student loans": 0, "Credit cards": 0, "Other debt": 0}),
    }


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
          <div class="aw-hero-grid">
            <div class="aw-hero-text">
              <div class="eyebrow">Florida &middot; fee-only fiduciary</div>
              <h1>Thoughtful planning for your whole family's future.</h1>
              <p>From a first conversation to a complete portfolio review — clear,
                 personal guidance backed by real analysis, so every decision fits
                 your family's goals.</p>
              <div class="aw-ledger">
                <div class="cell"><div class="v">100%</div>
                  <span class="k">figures computed</span></div>
                <div class="cell"><div class="v">0</div>
                  <span class="k">numbers guessed</span></div>
                <div class="cell"><div class="v">3-yr</div>
                  <span class="k">risk &amp; return window</span></div>
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    b1, b2, _ = st.columns([1, 1, 2])
    if b1.button("Open Dashboard", type="primary", width="stretch"):
        ui.go_to("Dashboard")
    if b2.button("Portfolio Analysis", width="stretch"):
        ui.go_to("Portfolio Analysis")
    st.markdown(
        '<div style="margin:2px 0 6px;">'
        '<span class="aw-section-label" style="margin:0;">or</span> '
        '<span style="color:var(--ink-soft); font-size:14px;">take the client survey from '
        "the top nav to get a suitability recommendation first.</span></div>",
        unsafe_allow_html=True,
    )

    # --- Floating product screenshot ---------------------------------------
    shot = ui.product_shot_html()
    if shot:
        st.write("")
        st.write("")
        st.markdown(f'<div class="pw-shot">{shot}</div>', unsafe_allow_html=True)

    # --- Trust strip --------------------------------------------------------
    st.write("")
    st.write("")
    ui.trust_strip()

    # --- How we help (sticky-pinned heading + scrolling card column —
    # the reference's signature scroll mechanic, pure CSS position:sticky) ----
    st.write("")
    st.write("")
    help_cards = [
        (ui.icon("family"), "Get to know your family",
         "A short survey captures your goals, your comfort with risk, and your "
         "family balance sheet — so your first meeting starts with understanding."),
        (ui.icon("compass"), "A plan that fits you",
         "Capacity-first recommendations, retirement-income readiness, and "
         "stress testing — reconciled into one suitable allocation."),
        (ui.icon("chart"), "Clarity on your portfolio",
         "Live valuation, concentration and risk, tax-aware rebalancing, and a "
         "report you can keep — every figure computed, never guessed."),
    ]
    cards_html = "".join(
        f'<div class="pw-scroll-card"><div class="aw-card">'
        f'<div class="ico">{icon}</div><h3>{title}</h3><p>{body}</p></div></div>'
        for icon, title, body in help_cards
    )
    st.markdown(
        f"""
        <div class="pw-sticky-row">
          <div class="pw-sticky-col">
            <div class="aw-section-label">Features</div>
            <div class="aw-section-head">Real numbers, not a black box.</div>
            <div class="aw-section-sub">Three ways we turn your goals into a plan you
              can actually follow.</div>
          </div>
          <div class="pw-scroll-col">{cards_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --- Our process (numbered spotlight) ------------------------------------
    st.write("")
    st.write("")
    st.markdown(
        '<div class="aw-center"><div class="aw-section-head">A clear path from first '
        'call to ongoing care</div></div>',
        unsafe_allow_html=True,
    )
    st.write("")
    steps = [
        ("01", "Discovery", "We listen first — your goals, timeline, and what financial "
         "security means to your family.", "discovery"),
        ("02", "Plan", "We build a written plan: suitable allocation, retirement readiness, "
         "and the trade-offs behind each choice.", "plan"),
        ("03", "Implement", "We put the plan to work — tax-aware, account by account, with "
         "everything documented in your IPS.", "implement"),
        ("04", "Review", "We meet on a set cadence to rebalance, stress-test, and adjust as "
         "your life changes.", "review"),
    ]
    for i, (n, title, body, photo) in enumerate(steps):
        rev = " rev" if i % 2 else ""
        st.markdown(
            f"""
            <div class="pw-spot{rev}">
              <div class="media">{ui.step_photo_html(photo, n, title)}</div>
              <div class="text">
                <div class="eyebrow">Step {n}</div>
                <h3>{title}</h3>
                <p>{body}</p>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # --- Services & fees --------------------------------------------------
    st.write("")
    ui.section_header("Services & fees", "Transparent, fee-only engagements",
                      "Fee-only means we're paid by you, for advice — never by commissions on "
                      "products. Choose the level of support that fits your family.")
    t1, t2, t3 = st.columns(3)
    with t1:
        st.markdown(
            """
            <div class="aw-tier">
              <h3>Financial Planning</h3>
              <div class="price">From $2,500 / plan</div>
              <ul>
                <li>Goal &amp; cash-flow analysis</li>
                <li>Retirement-income readiness</li>
                <li>Written financial plan</li>
                <li>Two review meetings</li>
              </ul>
            </div>
            """, unsafe_allow_html=True)
    with t2:
        st.markdown(
            """
            <div class="aw-tier feat">
              <div class="badge">Most popular</div>
              <h3>Investment Management</h3>
              <div class="price">0.85% of assets / year</div>
              <ul>
                <li>Everything in Planning</li>
                <li>Capacity-first portfolio design</li>
                <li>Tax-aware rebalancing</li>
                <li>Investment Policy Statement</li>
                <li>Quarterly reviews</li>
              </ul>
            </div>
            """, unsafe_allow_html=True)
    with t3:
        st.markdown(
            """
            <div class="aw-tier">
              <h3>Comprehensive Wealth</h3>
              <div class="price">Custom · households $2M+</div>
              <ul>
                <li>Everything in Management</li>
                <li>Estate &amp; legacy coordination</li>
                <li>Structured-product suitability</li>
                <li>Concentrated-stock strategies</li>
                <li>Family-office style service</li>
              </ul>
            </div>
            """, unsafe_allow_html=True)
    st.caption("Illustrative fee schedule for this demo — not an offer of services.")

    # --- Our team ---------------------------------------------------------
    st.write("")
    ui.section_header("Our team", "The advisor behind your plan")
    with st.container(border=True):
        st.markdown(
            f"""
            <div class="aw-team">
              <div class="photo">{ui.advisor_photo_html('LR')}</div>
              <div>
                <h3>Lucas Rosales</h3>
                <div class="role">Founder &amp; Financial Advisor · {ui.FIRM_NAME}</div>
                <p>Lucas founded {ui.FIRM_NAME} to bring institutional-grade analysis to
                   everyday Florida families — honest numbers, visible reasoning, and a plan
                   you keep. He works with a limited number of households so every relationship
                   gets real attention.</p>
                <div class="creds">
                  <span>Series 66</span><span>Fiduciary</span>
                  <span>Fee-Only</span><span>Retirement Income</span>
                  <span>Florida-based</span>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # --- Testimonials -----------------------------------------------------
    st.write("")
    ui.section_header("What clients say", "Trusted by families across Florida")
    quotes = [
        ("They showed us the math behind every recommendation. For the first time we "
         "understood not just what to do, but why.", "The Carter Family", "Tampa, FL", "C"),
        ("We came in worried about a big tech position. They had a real, tax-aware plan "
         "for it — not a sales pitch.", "R. Patel", "Miami, FL", "P"),
        ("Approaching retirement, I wanted to know I'd be okay. The stress testing gave me "
         "genuine peace of mind.", "M. Ellis", "Naples, FL", "E"),
    ]
    qc = st.columns(3)
    for col, (text, who, city, initial) in zip(qc, quotes):
        col.markdown(
            f"""
            <div class="aw-quote">
              <span class="mark">&ldquo;</span>
              <p>{text}</p>
              <div class="who"><div class="av">{initial}</div>
                <div><b>{who}</b><span>{city}</span></div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.caption("Illustrative testimonials for this demo — not statements from real clients.")

    # --- Insights ---------------------------------------------------------
    st.write("")
    ui.section_header("Insights", "Perspective, not noise")
    articles = [
        ("Planning", "What sequence-of-returns risk means for your retirement",
         "Two portfolios with identical average returns can end very differently. Here's why "
         "the order matters most in your first retirement years.", "5 min read"),
        ("Portfolios", "Why we start with capacity, not your risk quiz",
         "Your ability to take risk sets the ceiling; your comfort positions you beneath it. "
         "How we reconcile the two into one allocation.", "4 min read"),
        ("Taxes", "Rebalancing without a surprise tax bill",
         "Where a trade happens matters as much as the trade itself. A look at sourcing "
         "rebalances from the right accounts.", "6 min read"),
    ]
    ic = st.columns(3)
    for col, (tag, title, body, meta) in zip(ic, articles):
        col.markdown(
            f"""
            <div class="aw-insight">
              <div class="top"><span>{tag}</span></div>
              <div class="body"><h4>{title}</h4><p>{body}</p>
                <div class="meta">{meta} →</div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.caption("Sample article previews for this demo.")

    # --- About us ---------------------------------------------------------
    st.write("")
    ui.section_header("About us", "A Florida firm built around families, not products")
    with st.container(border=True):
        st.markdown(
            f"""
{ui.FIRM_NAME} was founded on a simple idea: good financial advice starts with
truly understanding a family — their goals, their worries, and what *enough*
looks like to them. We're an independent, fiduciary practice based on Florida's
Gulf Coast, and we work with a limited number of households so every plan gets
real attention.

We believe the numbers should be honest and the reasoning should be visible. Every
recommendation we make is backed by analysis you can see — risk you can quantify,
trade-offs we'll name out loud, and a written plan you keep. We don't sell products
off a shelf; we build a strategy around your life and adjust it as your life changes.

Whether you're raising children, nearing retirement, or somewhere in between, our
job is the same: help your family make confident decisions and stay on track for
the things that matter most.
            """
        )

    # --- Schedule a consultation -----------------------------------------
    st.write("")
    ui.section_header("Get started", "Schedule a complimentary consultation",
                      "Tell us a little about you and pick a time that works — your advisor "
                      "will confirm by email. No cost, no obligation.")
    _schedule_consultation()

    # --- Contact us + FAQ -------------------------------------------------
    st.write("")
    contact_col, faq_col = st.columns(2)
    with contact_col:
        st.markdown('<div class="aw-section-label">Contact us</div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(
                f"""
**{ui.FIRM_NAME}**
📍 1200 Harborview Blvd, Suite 300 · Sarasota, FL 34236
📞 (941) 555-0192
✉️ hello@wealthsyncadvisors.com
🕘 Mon–Fri, 9:00 AM – 5:00 PM ET
                """
            )
            st.caption("Sample contact details for this demo.")
    with faq_col:
        st.markdown('<div class="aw-section-label">FAQ</div>', unsafe_allow_html=True)
        with st.container(border=True):
            with st.expander("How much does a first meeting cost?"):
                st.write("Your first conversation is complimentary. We'll review your "
                         "survey together and outline how we can help before you commit "
                         "to anything.")
            with st.expander("Do I need a minimum amount to invest?"):
                st.write("We work with families at many stages. What matters most is that "
                         "we're a good fit for your goals and how you like to work.")
            with st.expander("Are you a fiduciary?"):
                st.write("Yes. We're an independent, fiduciary practice — we're obligated "
                         "to act in your best interest, and we're paid for advice, not for "
                         "selling products.")
            with st.expander("What happens after I submit the survey?"):
                st.write("Your responses go straight to your advisor, who reviews your "
                         "goals and balance sheet and prepares a tailored plan before your "
                         "first meeting — so your time together is spent on advice.")

    # --- Disclosures footer ----------------------------------------------
    ui.disclosures_footer()


def _schedule_consultation() -> None:
    """A simulated 'book a consultation' form that flows into the CRM view.

    No real message is sent — submissions are stored in session_state and
    surfaced on the Dashboard, so the demo shows an end-to-end lead flow.
    """
    if st.session_state.get("consult_booked"):
        c = st.session_state["consult_booked"]
        st.success(
            f"Thanks, **{c['name']}** — your consultation request for "
            f"**{c['date']:%A, %b %d}** ({c['slot']}) is in. Your advisor will confirm at "
            f"**{c['email']}**.", icon="✅")
        if st.button("Book another time", key="consult_reset"):
            st.session_state.pop("consult_booked", None)
            st.rerun()
        return

    with st.form("consult_form", border=True):
        f1, f2 = st.columns(2)
        name = f1.text_input("Full name", placeholder="Jordan Rivera")
        email = f2.text_input("Email", placeholder="you@email.com")
        f3, f4 = st.columns(2)
        phone = f3.text_input("Phone (optional)", placeholder="(941) 555-0123")
        focus = f4.selectbox("What's on your mind?",
                             ["Retirement planning", "Investment management",
                              "A concentrated stock position", "College savings",
                              "A full financial plan", "Something else"])
        d1, d2 = st.columns(2)
        min_day = dt.date.today() + dt.timedelta(days=1)
        date = d1.date_input("Preferred date", value=min_day, min_value=min_day)
        slot = d2.selectbox("Preferred time",
                            ["9:00 AM", "11:00 AM", "1:00 PM", "3:00 PM", "4:30 PM"])
        submitted = st.form_submit_button("Request consultation", type="primary")
        if submitted:
            if not name.strip() or "@" not in email:
                st.error("Please enter your name and a valid email so we can confirm.")
            else:
                st.session_state["consult_booked"] = {
                    "name": name.strip(), "email": email.strip(), "phone": phone.strip(),
                    "focus": focus, "date": date, "slot": slot,
                    "requested_at": dt.datetime.now()}
                _shared_store()["consult_leads"].append(st.session_state["consult_booked"])
                st.rerun()


# ==========================================================================
# Dashboard — advisor CRM + review client surveys
# ==========================================================================
def _sim_clients() -> list[dict]:
    today = dt.date.today()
    d = lambda n: today + dt.timedelta(days=n)
    return [
        {"name": "Robert & Susan Hale", "meeting": d(1), "time": "9:00 AM",
         "complete": True, "aum": 2_450_000, "reason": "Annual review",
         "phone": "(941) 555-0114", "email": "r.hale@example.com"},
        {"name": "Priya Nadella", "meeting": d(1), "time": "1:30 PM",
         "complete": False, "aum": 780_000, "reason": "New client onboarding",
         "phone": "(813) 555-0176", "email": "priya.n@example.com"},
        {"name": "James Okoro", "meeting": d(2), "time": "11:00 AM",
         "complete": True, "aum": 1_120_000, "reason": "Rebalancing discussion",
         "phone": "(305) 555-0133", "email": "j.okoro@example.com"},
        {"name": "The Delgado Family Trust", "meeting": d(3), "time": "3:00 PM",
         "complete": False, "aum": 4_300_000, "reason": "Estate & concentration review",
         "phone": "(561) 555-0188", "email": "delgado.trust@example.com"},
        {"name": "Helen Yoshida", "meeting": d(9), "time": "2:00 PM",
         "complete": True, "aum": 1_875_000, "reason": "Retirement income planning",
         "phone": "(727) 555-0159", "email": "h.yoshida@example.com"},
    ]


def dashboard() -> None:
    head_l, head_r = st.columns([3, 1])
    with head_l:
        ui.section_header("Advisor workspace", "Advisor Dashboard",
                          "Your client pipeline for the week. (Simulated workflow data.)")
    with head_r:
        st.write("")
        st.write("")
        with st.popover("👤 Lucas Rosales", key="avatarbtn", width="stretch"):
            st.markdown(
                '<div class="pw-dropdown-item"><b>Lucas Rosales</b>'
                '<span>Founder &amp; Financial Advisor</span></div>'
                '<div class="pw-dropdown-item">View profile</div>'
                '<div class="pw-dropdown-item">Preferences</div>'
                '<div class="pw-dropdown-item">Sign out</div>',
                unsafe_allow_html=True,
            )
            st.caption("Demo menu — not wired to real account actions.")

    st.write("")
    _ensure_demo_survey()
    store = _shared_store()
    clients = _sim_clients()
    surveys = store["surveys"]
    pending_invites = [(tok, inv) for tok, inv in store["invites"].items()
                       if inv["status"] == "pending"]
    today = dt.date.today()
    incomplete = [c for c in clients if not c["complete"]]
    week = [c for c in clients if 0 <= (c["meeting"] - today).days <= 7]

    leads = store["consult_leads"]
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Active clients", len(clients))
    m2.metric("Profiles incomplete", len(incomplete))
    m3.metric("Meetings this week", len(week))
    m4.metric("New surveys to review", len(surveys))
    m5.metric("New consult requests", len(leads))

    # --- Assets under management by client (real figures already on this
    # page, charted — no charting library needed for a handful of bars) ------
    st.divider()
    ui.subhead("Assets under management", "by priority client this week")
    max_aum = max(c["aum"] for c in clients)
    bar_rows = "".join(
        f'<div class="pw-bar-row"><div class="name">{c["name"]}</div>'
        f'<div class="pw-bar-track"><div class="pw-bar-fill" '
        f'style="width:{c["aum"] / max_aum * 100:.0f}%"></div></div>'
        f'<div class="val">${c["aum"]:,.0f}</div></div>'
        for c in sorted(clients, key=lambda c: -c["aum"])
    )
    st.markdown(f'<div class="pw-bar-chart">{bar_rows}</div>', unsafe_allow_html=True)

    # --- Inbound consultation requests (from the Home page form) ---------
    if leads:
        st.divider()
        ui.subhead("📨 New consultation requests", "submitted from the website")
        for ld in reversed(leads):
            with st.container(border=True):
                st.markdown(
                    f"🟢 **{ld['name']}** — {ld['focus']}  \n"
                    f"<span style='color:#6b7280;font-size:13px'>Requested "
                    f"{ld['date']:%a %b %d} at {ld['slot']} · 📞 {ld['phone'] or '—'} · "
                    f"✉️ {ld['email']}</span>", unsafe_allow_html=True)

    st.divider()
    left, right = st.columns([1, 1])
    with left:
        ui.subhead("⏱️ Priority clients", "by next meeting")
        for c in sorted(clients, key=lambda c: c["meeting"])[:4]:
            days = (c["meeting"] - today).days
            when = "Today" if days == 0 else ("Tomorrow" if days == 1 else f"in {days} days")
            flag = "🔴" if days <= 1 else ("🟠" if days <= 3 else "🟢")
            with st.container(border=True):
                st.markdown(f"{flag} **{c['name']}** — {when}, {c['time']}  \n"
                            f"<span style='color:#6b7280;font-size:13px'>{c['reason']} · "
                            f"${c['aum']:,.0f}</span>", unsafe_allow_html=True)
    with right:
        ui.subhead("📋 Profiles awaiting completion")
        if not incomplete:
            st.success("All client profiles are complete.", icon="✅")
        for c in incomplete:
            with st.container(border=True):
                st.markdown(f"**{c['name']}**  \n"
                            f"<span style='color:#6b7280;font-size:13px'>{c['reason']}</span>",
                            unsafe_allow_html=True)

    st.divider()
    with st.expander("📅 Upcoming meetings", expanded=True):
        rows = [{"Client": c["name"], "Date": c["meeting"].strftime("%a %b %d"), "Time": c["time"],
                 "Phone": c["phone"], "Email": c["email"],
                 "Profile": "Complete" if c["complete"] else "Incomplete", "Purpose": c["reason"]}
                for c in sorted(clients, key=lambda c: c["meeting"])]
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

    # --- Pending survey invites (sent, awaiting the client's response) ---
    if pending_invites:
        st.divider()
        with st.expander(f"✉️ Awaiting response — {len(pending_invites)} survey invite"
                          f"{'s' if len(pending_invites) != 1 else ''} sent", expanded=True):
            for tok, inv in sorted(pending_invites, key=lambda pair: pair[1]["created_at"],
                                   reverse=True):
                with st.container(border=True):
                    st.markdown(
                        f"**{inv['name']}** — sent {inv['created_at']:%b %d, %I:%M %p}  \n"
                        f"<span style='color:#6b7280;font-size:13px'>"
                        f"✉️ {inv['email']}"
                        + (f" · 📞 {inv['phone']}" if inv.get("phone") else "")
                        + "</span>",
                        unsafe_allow_html=True)
                    # Lets the advisor recover the link if they've navigated away
                    # from Client Survey since creating it -- otherwise it only
                    # ever existed in that one page render.
                    ui.invite_link_html(tok)

    # --- Review client surveys (real submissions) ------------------------
    st.divider()
    with st.expander("📝 Review client surveys — new intake from prospective clients",
                      expanded=bool(surveys)):
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
                    f"📞 {rec_wrap.get('phone', '—')} · ✉️ {rec_wrap.get('email', '—')} · "
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
def _payoff_df(curve, product_label: str) -> pd.DataFrame:
    df = pd.DataFrame(
        {product_label: [r * 100 for _, r in curve],
         "Underlying (1:1) %": [u * 100 for u, _ in curve]},
        index=[round(u * 100, 1) for u, _ in curve])
    df.index.name = "Underlying return %"
    return df


def _render_structured_gallery() -> None:
    """Three illustrative structured-product payoff shapes with detail on each."""
    g1, g2, g3 = st.columns(3)

    with g1:
        t = INCOME_NOTE_TERMS
        with st.container(border=True):
            st.markdown("**Income / autocallable note**")
            st.line_chart(_payoff_df(_payoff_curve(_income_note_payoff, t), "Note return %"),
                          height=190, color=[ui.GOLD, ui.TEAL])
            st.markdown(
                f"**In the portfolio.** Held as a small satellite sleeve, an income note can "
                f"raise a portfolio's cash flow beyond what bonds yield today — an illustrative "
                f"**{t['contingent_coupon']:.0%} contingent coupon** while the index holds above "
                f"**{t['coupon_barrier']:.0%}** — without adding pure equity risk. It trades away "
                f"market upside (flat payoff) for that income, so it complements a core "
                f"allocation rather than replacing it.")
            st.markdown(
                "**Account placement.** Its coupons are taxed as ordinary income, so it usually "
                "belongs in a **traditional IRA or other tax-deferred account**, where the "
                "income isn't taxed yearly. Best for a client who wants supplemental income and "
                "accepts that principal is at risk in a severe decline.")

    with g2:
        t = PRINCIPAL_PROTECTED_TERMS
        with st.container(border=True):
            st.markdown("**Principal-protected note**")
            st.line_chart(_payoff_df(_payoff_curve(_principal_protected_payoff, t), "PPN return %"),
                          height=190, color=[ui.GOLD, ui.TEAL])
            st.markdown(
                f"**In the portfolio.** For a nervous client sitting in cash, a PPN can be the "
                f"bridge back into the market: principal is returned at maturity while capturing "
                f"**{t['participation']:.0%} of the index's gain** up to ~**{t['cap']:.0%}**. It "
                f"lets money that would otherwise earn nothing participate in an upside, which "
                f"can be the difference between a plan that keeps pace with inflation and one "
                f"that doesn't.")
            st.markdown(
                "**Account placement.** Because the payoff is a single lump at maturity, it fits "
                "money with a matching multi-year horizon — often a **Roth or taxable account** "
                "earmarked for a dated goal. Weigh the lockup, capped upside, and the issuer's "
                "credit risk against simply holding a conservative allocation.")

    with g3:
        t = BUFFERED_ETF_TERMS
        with st.container(border=True):
            st.markdown("**Buffer with a cap**")
            st.line_chart(_payoff_df(_payoff_curve(_buffered_payoff, t), "Buffered return %"),
                          height=190, color=[ui.GOLD, ui.TEAL])
            st.markdown(
                f"**In the portfolio.** A buffer lets a cautious client hold more growth exposure "
                f"than they otherwise could: it absorbs the **first {t['buffer']:.0%} of losses**, "
                f"so the equity sleeve can be larger without breaching the client's drawdown "
                f"limit — often improving the odds of reaching a goal versus an all-bond "
                f"defensive position. Upside is **capped near {t['cap']:.0%}** in exchange.")
            st.markdown(
                "**Account placement.** The **defined-outcome ETF** version is liquid, "
                "exchange-traded, and carries no single-issuer credit risk, so it drops cleanly "
                "into **any account — taxable, IRA, or Roth**. A buffered *note* only adds value "
                "when a longer defined term is specifically wanted.")


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
        # Column order is fixed (Steady, Early bear, Late bear) -- see stress.py.
        scenario_colors = [ui.POS, ui.NEG, ui.GOLD][:len(chart_df.columns)]
        st.line_chart(chart_df, height=300, color=scenario_colors)
        cols = st.columns(3)
        for col, sc in zip(cols, stress.scenarios):
            status = "Survived" if sc.survived else f"Depleted yr {sc.depletion_year}"
            col.metric(sc.name, f"${sc.terminal_value:,.0f}", status, delta_color="off")
        for f in stress.findings:
            st.info(f, icon="📉")

    # --- Structured products ---------------------------------------------
    sp = rec.structured
    st.markdown("#### Structured products")
    st.caption(sp.sleeve_note)
    if sp.any_recommended:
        st.success(sp.headline, icon="✅")
    else:
        st.info(sp.headline, icon="🚫")

    for p in sp.considered:
        if p.recommended:
            with st.container(border=True):
                st.markdown(f"**✅ {p.name}**")
                st.markdown(p.rationale)
                if p.payoff:
                    df = pd.DataFrame(
                        {"Product return %": [r * 100 for _, r in p.payoff],
                         "Underlying (1:1) %": [u * 100 for u, _ in p.payoff]},
                        index=[round(u * 100, 1) for u, _ in p.payoff])
                    df.index.name = "Underlying return %"
                    st.line_chart(df, height=230, color=[ui.GOLD, ui.TEAL])
        else:
            st.markdown(f"**✗ {p.name}** — {p.rationale}")
    st.caption("Payoff diagrams use illustrative, clearly-stated assumed terms at maturity — "
               "not a quote for any real issued product. Structured products carry issuer "
               "credit risk, limited liquidity, and defined terms.")

    # --- Financial goals --------------------------------------------------
    if rec.profile.goals:
        st.divider()
        st.markdown("#### Financial goals")
        gdf = pd.DataFrame([{
            "Goal": g.label, "Target": g.target_amount, "Timeframe": f"{g.years} yrs",
            "Priority": g.priority.title(),
        } for g in rec.profile.goals])
        st.dataframe(gdf, hide_index=True, width="stretch",
                     column_config={"Target": st.column_config.NumberColumn(format="$%,.0f")})

    # --- Implementation strategy -----------------------------------------
    sa = rec.strategies
    st.divider()
    st.markdown("#### Implementation strategy")
    st.caption("How to get to the target allocation — matched to this client.")
    st.success(sa.headline, icon="🧩")
    for f in sa.fits:
        if f.recommended:
            st.markdown(f"**✅ {f.name}** — {f.rationale}")
        else:
            st.markdown(f"<span style='color:#6b7280'>◦ {f.name} — {f.rationale}</span>",
                        unsafe_allow_html=True)

    # --- Structured note analysis ----------------------------------------
    st.divider()
    st.markdown("#### Structured note analysis — fitting each note to the portfolio")
    st.caption("How each structured note can work inside this client's plan — the portfolio "
               "role it plays and the account it's best held in. Illustrative assumed terms at "
               "maturity, not a quote for any real issued product.")
    _render_structured_gallery()

    # --- Investment Policy Statement -------------------------------------
    st.divider()
    st.markdown("#### Investment Policy Statement")
    st.caption("A draft IPS assembled from the analysis above — objectives, allocation, "
               "rebalancing, constraints, retirement-income and structured-product policy.")
    ips_html = render_ips_html(rec)
    st.download_button(
        "Download IPS (HTML)", data=ips_html,
        file_name=f"{rec.profile.client_name.replace(' ', '_').lower()}_ips.html",
        mime="text/html", type="primary", key="ips_dl")
    with st.expander("Preview IPS"):
        st.components.v1.html(ips_html, height=760, scrolling=True)


def _render_client_header(rec_wrap: dict) -> None:
    rec = rec_wrap["rec"]
    st.success(f"**{rec_wrap['name']}** — submitted "
               f"{rec_wrap['submitted_at']:%b %d, %Y %I:%M %p}", icon="📝")
    st.caption(f"📞 {rec_wrap.get('phone', '—')}  ·  ✉️ {rec_wrap.get('email', '—')}")

    st.markdown("#### Client answers at a glance")
    p = rec.profile
    q1, q2, q3, q4 = st.columns(4)
    q1.metric("Age", p.age)
    q2.metric("Horizon", f"{p.time_horizon_years} yrs")
    q3.metric("Primary goal", p.objective.value.title())
    q4.metric("Risk tolerance", p.risk_tolerance.value.replace("_", " ").title())

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


def _render_survey_subject(rec_wrap: dict) -> None:
    _render_client_header(rec_wrap)
    st.divider()
    _render_recommendation(rec_wrap["rec"])


def _render_sample_client(rec_wrap: dict) -> None:
    """A complete client view: intake, current portfolio holdings analysis
    (equity, concentration, risk indicators, rebalancing), then the suitability
    plan (capacity, stress test, strategy, structured note analysis, IPS)."""
    _render_client_header(rec_wrap)
    analysis = rec_wrap.get("analysis")
    if analysis is not None:
        st.divider()
        st.markdown("### Current portfolio holdings")
        _render_portfolio_subject(analysis, show_gallery=False)
    st.divider()
    st.markdown("### Suitability & planning")
    _render_recommendation(rec_wrap["rec"])


def _protection_score(concentration) -> int:
    """100 minus a deduction per concentration flag, scaled by severity.

    Every input here is a real ConcentrationFlag already computed by
    analytics/concentration.py — this only maps flags to a 0-100 display
    score, it doesn't invent risk assessment of its own.
    """
    deductions = {"high": 22, "moderate": 12, "low": 5}
    score = 100 - sum(deductions.get(f.severity, 5) for f in concentration.flags)
    return max(0, min(100, round(score)))


def _investment_score(plan) -> int:
    """100 minus scaled average absolute drift from the target allocation.

    Drift comes straight from analytics/rebalance.py's ClassDrift.drift —
    the same number already shown in the Rebalancing table below.
    """
    if not plan.drifts:
        return 100
    avg_abs_drift = sum(abs(d.drift) for d in plan.drifts) / len(plan.drifts)
    score = 100 - avg_abs_drift * 100 * 2.2
    return max(0, min(100, round(score)))


def _market_snapshot_rows(positions, market) -> list[dict]:
    """Per-holding price, day change, and 52-week range from the same cached
    price history the analytics already run on (market.prices / current_prices)
    — not a separate data source, so it can never disagree with the rest of
    the page. Tickers with no price series (e.g. CASH) show an em-dash.

    Pre-formatted to plain strings rather than left as NaN + a NumberColumn
    format: Streamlit's glide-data-grid renders a NaN cell under a custom
    printf-style format as the literal text "None", not blank — formatting
    here sidesteps that rather than fighting it.
    """
    rows = []
    for p in positions:
        # Cash has no real market series — "CASH" also happens to be Pathward
        # Financial's real ticker, so market.prices["CASH"] is that unrelated
        # stock's history, not a cash proxy. Never show it here.
        series = market.prices.get(p.ticker) if p.asset_class != "Cash" else None
        if series is not None:
            series = series.dropna()
        if series is not None and len(series) >= 2:
            prev_close = float(series.iloc[-2])
            last = float(series.iloc[-1])
            change = last - prev_close
            change_pct = (last - prev_close) / prev_close * 100 if prev_close else 0.0
            window = series.tail(252)
            day_change = f"{change:+.2f}"
            day_change_pct = f"{change_pct:+.2f}%"
            low_52w = f"${float(window.min()):.2f}"
            high_52w = f"${float(window.max()):.2f}"
        else:
            day_change = day_change_pct = low_52w = high_52w = "—"
        rows.append({
            "Ticker": p.ticker, "Name": p.name, "Price": p.price,
            "Day change": day_change, "Day change %": day_change_pct,
            "52w low": low_52w, "52w high": high_52w,
        })
    return rows


def _render_portfolio_subject(result: AnalysisResult, show_gallery: bool = True) -> None:
    a, r, plan = result.allocation, result.risk, result.plan
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Portfolio value", f"${a.total_value:,.0f}", f"{len(a.positions)} positions")
    c2.metric("Unrealized gain", f"${a.total_unrealized_gain:,.0f}",
              f"{a.total_unrealized_gain / a.total_cost_basis:+.1%} on cost")
    c3.metric("Volatility (ann.)", f"{r.annualized_volatility:.1%}",
              f"S&P {r.benchmark_volatility:.1%}", delta_color="off")
    c4.metric("Max drawdown", f"{r.max_drawdown:.1%}", f"S&P {r.benchmark_max_drawdown:.1%}",
              delta_color="off")

    st.write("")
    s1, s2 = st.columns(2)
    with s1:
        st.markdown(
            ui.score_gauge_html(
                "Protection Score", _protection_score(result.concentration),
                "How well-diversified this portfolio is against a single position, "
                "sector, or employer-stock shock — derived from the concentration "
                "flags below. Higher means fewer, smaller risk-of-loss clusters.",
                learn_more_anchor="pra-concentration",
            ),
            unsafe_allow_html=True,
        )
    with s2:
        st.markdown(
            ui.score_gauge_html(
                "Investment Score", _investment_score(plan),
                "How closely current holdings track the target allocation — derived "
                "from the rebalancing drift below. Higher means less deviation from "
                "the suitable model.",
                learn_more_anchor="pra-rebalancing",
            ),
            unsafe_allow_html=True,
        )

    st.markdown("#### Holdings")
    df = pd.DataFrame([{
        "Ticker": p.ticker, "Name": p.name, "Class": p.asset_class,
        "Value": p.market_value, "Weight": p.market_value / a.total_value * 100,
        "Cost basis": p.cost_basis, "Unrealized": p.unrealized_gain, "Return": p.gain_pct * 100,
    } for p in a.positions])
    st.dataframe(df, hide_index=True, width="stretch", column_config={
        "Value": st.column_config.NumberColumn(format="$%,.0f"),
        "Cost basis": st.column_config.NumberColumn(format="$%,.0f"),
        "Unrealized": st.column_config.NumberColumn(format="$%,.0f"),
        "Weight": st.column_config.NumberColumn(format="%.1f%%"),
        "Return": st.column_config.NumberColumn(format="%.1f%%")})

    st.markdown("#### Market snapshot")
    st.caption("Price, day change, and 52-week range from the same cached market data "
               "the analytics above already use.")
    mdf = pd.DataFrame(_market_snapshot_rows(a.positions, result.market))
    st.dataframe(mdf, hide_index=True, width="stretch",
                 column_config={"Price": st.column_config.NumberColumn(format="$%.2f")})

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
        st.markdown('<div id="pra-concentration"></div>', unsafe_allow_html=True)
        st.markdown("#### Concentration")
        if not result.concentration.flags:
            st.success("No concentration guidelines exceeded.", icon="✅")
        for f in result.concentration.flags:
            color = {"high": "🔴", "moderate": "🟠", "low": "🟡"}.get(f.severity, "⚪")
            st.markdown(f"{color} **{f.subject}** ({f.weight:.0%}) — {f.message}")

    st.markdown('<div id="pra-rebalancing"></div>', unsafe_allow_html=True)
    st.markdown("#### Rebalancing")
    st.dataframe(pd.DataFrame({
        "Asset class": [d.asset_class for d in plan.drifts],
        "Current": [d.current_weight * 100 for d in plan.drifts],
        "Target": [d.target_weight * 100 for d in plan.drifts],
        "Drift": [d.drift * 100 for d in plan.drifts],
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

    st.markdown("#### Advisor commentary")
    narrative = result.narrative
    if narrative.source == "ai":
        badges = (
            f'<span class="aw-badge ai">AI-written &middot; {narrative.model_used}</span>'
            '<span class="aw-badge">Compliance-reviewed</span>'
        )
    else:
        badges = '<span class="aw-badge">Rule-based</span>'
    if narrative.compliance_flags:
        badges += '<span class="aw-badge flag">Flagged</span>'
    st.markdown(badges, unsafe_allow_html=True)

    if narrative.compliance_flags:
        st.warning(
            "Compliance review flagged this commentary — shown unedited so the issue is "
            "visible rather than silently suppressed.\n\n"
            + "\n".join(f"- {flag}" for flag in narrative.compliance_flags)
        )

    for paragraph in narrative.paragraphs:
        # Escape bare "$" so Streamlit's markdown renderer doesn't treat a pair
        # of dollar amounts (e.g. "$113,662 ... $6,561") as a LaTeX math span.
        st.markdown(paragraph.replace("$", "\\$"))

    st.markdown("#### Client report")
    html = render_html(result.portfolio, a, r, result.concentration, plan,
                       result.model, result.narrative, result.market)
    st.download_button("Download report (HTML)", data=html,
                       file_name=f"{result.portfolio.client_name.replace(' ', '_').lower()}_report.html",
                       mime="text/html", type="primary")
    with st.expander("Preview report"):
        st.components.v1.html(html, height=760, scrolling=True)

    if show_gallery:
        st.markdown("#### Structured-product possibilities")
        st.caption("Illustrative payoff shapes to discuss alongside this portfolio — assumed "
                   "terms at maturity, not a quote for any real product.")
        _render_structured_gallery()

        st.info("Goal-based analysis — the recommended allocation, suitability-gated **structured "
                "note analysis**, and the IPS — appears when you review a **client survey** "
                "(Dashboard → Review), which supplies the client's goals.",
                icon="📄")


def portfolio_analysis() -> None:
    ui.section_header("Analysis & planning", "Portfolio Analysis",
                      "Choose a sample client, review a filed survey, or load a portfolio.")
    st.write("")
    surveys = _shared_store()["surveys"]
    active = _active()
    samples = _sample_clients()
    generated = st.session_state.setdefault("generated", {})

    # Build the subject options (plain string keys + a label lookup).
    keys: list[str] = []
    labels: dict[str, str] = {}
    for nm in samples:
        k = f"sample:{nm}"
        keys.append(k)
        labels[k] = f"🧑‍🤝‍🧑 Sample client — {nm}"
    for w in reversed(surveys):
        k = f"survey:{w['id']}"
        keys.append(k)
        labels[k] = f"📝 Filed survey — {w['name']} ({w['submitted_at']:%b %d})"
    if active is not None:
        keys.append("active")
        labels["active"] = f"📊 Portfolio — {active.portfolio.client_name}"
    keys.append("load")
    labels["load"] = "➕ Load a new portfolio…"

    # If we were sent here to review a specific survey, target it.
    review_id = st.session_state.pop("review_survey_id", None)
    if review_id is not None and f"survey:{review_id}" in keys:
        st.session_state["pa_subject"] = f"survey:{review_id}"

    # Index-driven from pa_subject (no persistent widget key) so it reflects the
    # intended subject on the first render.
    current = st.session_state.get("pa_subject")
    if current not in keys:
        current = keys[0]
    kind = st.selectbox("Choose who to analyze", keys,
                        format_func=lambda k: labels[k], index=keys.index(current))
    st.session_state["pa_subject"] = kind
    st.divider()

    if kind == "load":
        _portfolio_picker("inline", navigate=False)
    elif kind == "active" and active is not None:
        _render_portfolio_subject(active)
    elif kind.startswith("survey:"):
        sid = int(kind.split(":")[1])
        wrap = next((w for w in surveys if w["id"] == sid), None)
        if wrap:
            _render_survey_subject(wrap)
    elif kind.startswith("sample:"):
        nm = kind.split("sample:", 1)[1]
        if nm in generated:
            _render_sample_client(generated[nm])
            if st.button("Regenerate analysis", key="regen"):
                generated.pop(nm, None)
                st.rerun()
        else:
            s = samples[nm]
            p = s["profile"]
            g = p.primary_goal
            st.markdown(f"**{p.client_name}** — {p.summary_line()}")
            if g:
                st.caption(f"Primary goal: {g.label} — ${g.target_amount:,.0f} in {g.years} years.")
            if st.button("Generate analysis", type="primary", key="gen_sample"):
                with st.spinner("Running the portfolio and suitability analysis…"):
                    rec = build_recommendation(p)
                    analysis = None
                    csv = s.get("portfolio")
                    if csv:
                        try:
                            portfolio = load_portfolio(DATA_DIR / csv)
                            analysis = run_analysis(portfolio, rec.recommended_model)
                        except (PortfolioError, PriceDataError, FileNotFoundError,
                                ValueError, KeyError) as exc:
                            st.warning(f"Portfolio holdings analysis unavailable right now "
                                       f"({exc}) -- showing the suitability plan without it.",
                                       icon="⚠️")
                            analysis = None
                generated[nm] = {
                    "id": f"sample_{nm}", "name": p.client_name,
                    "phone": s["phone"], "email": s["email"],
                    "submitted_at": dt.datetime.now(), "rec": rec,
                    "analysis": analysis,
                    "assets": s["assets"], "liabilities": s["liabilities"],
                    "net_worth": s["net_worth"]}
                st.rerun()


# ==========================================================================
# Client Survey
# ==========================================================================
def client_survey() -> None:
    if st.session_state.get("survey_done"):
        _survey_thank_you()
        return
    _render_send_to_client_panel()
    _render_survey_form()


def render_client_invite(token: str) -> None:
    """The client's own view of a survey an advisor sent them — reached via
    a ?invite=<token> link, handled in streamlit_app.py before the normal
    welcome/nav/page dispatch. No nav bar, no advisor tools: just the form,
    scoped to this one invite.
    """
    st.markdown(
        f'<div class="aw-brand" style="margin-bottom:18px">'
        f'<div class="mark">{ui.brand_mark_html(40)}</div>'
        f'<div><div class="name">{ui.FIRM_NAME}</div></div></div>',
        unsafe_allow_html=True,
    )

    if st.session_state.get("survey_done"):
        _survey_thank_you()
        return

    store = _shared_store()
    invite = store["invites"].get(token)
    if invite is None:
        st.error("This link isn't valid, or has expired. Please contact your advisor "
                 "for a new one.")
        return
    if invite["status"] == "responded":
        st.success("This survey has already been submitted — thank you. If you need to "
                    "change anything, contact your advisor directly.")
        return

    st.info(f"**{invite['name']}** — your advisor at {ui.FIRM_NAME} sent you this survey "
            "to prepare for your meeting.", icon="✉️")
    _render_survey_form(prefill=invite, invite_token=token)


def _render_send_to_client_panel() -> None:
    """Advisor-only: create a shareable link that opens a stripped, client-only
    copy of this same form for one specific person — see render_client_invite.
    """
    store = _shared_store()
    with st.expander("✉️  Send this survey to a client", expanded=False):
        st.caption("Creates a link that opens this survey for one client only — their "
                   "response appears below and on the Dashboard when they submit it.")
        c1, c2, c3 = st.columns(3)
        name = c1.text_input("Client name", key="invite_name")
        email = c2.text_input("Email", key="invite_email", placeholder="client@email.com")
        phone = c3.text_input("Phone (optional)", key="invite_phone",
                              placeholder="(555) 123-4567")
        if st.button("Create client link", key="invite_create", type="primary"):
            if not name.strip() or "@" not in email:
                st.error("Enter the client's name and a valid email.")
            else:
                token = secrets.token_urlsafe(6)
                store["invites"][token] = {
                    "name": name.strip(), "email": email.strip(), "phone": phone.strip(),
                    "created_at": dt.datetime.now(), "status": "pending",
                }
                st.session_state["last_invite_token"] = token

        token = st.session_state.get("last_invite_token")
        if token and token in store["invites"]:
            inv = store["invites"][token]
            st.success(f"Link created for **{inv['name']}**.")
            ui.invite_link_html(token)
            st.caption("No email service is configured for this demo, so nothing sends "
                       "automatically — copy the link above and send it yourself. Add a "
                       "real email API key later and this can send it for you (see README).")

        pending = [inv for inv in store["invites"].values() if inv["status"] == "pending"]
        if pending:
            st.caption(f"{len(pending)} invite(s) currently awaiting a response.")


def _render_survey_form(prefill: dict | None = None, invite_token: str | None = None) -> None:
    """The actual intake form. Used both for the advisor's own Client Survey
    page and for a client filling it out remotely via an invite link —
    `prefill`/`invite_token` are only set in the latter case.
    """
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

    st.info("Please complete every section. Enter **0** for any dollar amount that "
            "doesn't apply to you (N/A).", icon="📝")

    # ===== 1) Your Goals — the risk triangle (live) ======================
    st.markdown('<div class="aw-survey-section">🧭 &nbsp;Your Goals '
                '<span>— your comfort with risk and what you\'re investing for</span></div>',
                unsafe_allow_html=True)
    st.markdown("**Where does your family sit between growth, income, and safety?**")
    st.caption("Adjust the sliders — the marker moves inside the triangle to show your balance.")
    tri_col, ctrl_col = st.columns([1, 1])
    with ctrl_col:
        wg = st.slider("Growth — build wealth over time", 0, 100, 50, key="tri_g")
        wi = st.slider("Income — steady cash flow", 0, 100, 25, key="tri_i")
        ws = st.slider("Safety — protect what I have", 0, 100, 25, key="tri_s")
        horizon = st.number_input("Years until you need this money", 1, 50, 15, key="sv_h")
        drawdown_pct = st.slider("Largest drop you could sit through", 0, 60, 20, 5,
                                 format="%d%%", key="sv_dd")
        drawdown = drawdown_pct / 100
        experience = st.selectbox("Investing experience", list(Experience), index=1,
                                  format_func=lambda e: e.value.title(), key="sv_exp")
    with tri_col:
        st.markdown(_risk_triangle_svg(wg, wi, ws), unsafe_allow_html=True)
        obj = _triangle_to_objective(wg, wi, ws)
        st.caption(f"Your balance reads as a **{obj.value.title()}** orientation.")

    st.markdown("**What are you investing for?** Select every goal that applies.")
    goal_choices = st.multiselect(
        "Financial goals", list(GoalType), default=[GoalType.RETIREMENT],
        format_func=lambda g: GOAL_LABELS[g], key="sv_goals")
    goal_defaults = {GoalType.RETIREMENT: (2_000_000, 25), GoalType.COLLEGE: (250_000, 12),
                     GoalType.MORTGAGE: (300_000, 10), GoalType.WEALTH: (1_000_000, 20)}
    goal_inputs: dict = {}
    for g in goal_choices:
        amt_d, yr_d = goal_defaults[g]
        gc1, gc2, gc3 = st.columns(3)
        amt = gc1.number_input(f"{GOAL_LABELS[g]} — target $", 0, value=amt_d, step=10_000,
                               key=f"goal_amt_{g.value}")
        yrs = gc2.number_input(f"{GOAL_LABELS[g]} — in how many years", 1, 50, yr_d,
                               key=f"goal_yrs_{g.value}")
        pri = gc3.selectbox(f"{GOAL_LABELS[g]} — priority", ["high", "medium", "low"],
                            key=f"goal_pri_{g.value}")
        goal_inputs[g] = (float(amt), int(yrs), pri)

    # ===== 2) Family Balance Sheet =======================================
    st.write("")
    st.markdown('<div class="aw-survey-section">🏠 &nbsp;Family Balance Sheet '
                '<span>— what you own and what you owe</span></div>', unsafe_allow_html=True)
    st.caption("Approximate values are fine. Enter 0 for anything you don't have (N/A).")
    ac, lc = st.columns(2)
    assets: dict[str, float] = {}
    with ac:
        st.markdown("**Assets**")
        defaults = [50_000, 200_000, 250_000, 400_000, 0]
        for lab, dv in zip(ASSET_LABELS, defaults):
            assets[lab] = float(st.number_input(lab, 0, value=dv, step=5_000, key=f"as_{lab}"))
    liabs: dict[str, float] = {}
    with lc:
        st.markdown("**Liabilities**")
        ldef = [280_000, 20_000, 0, 0]
        for lab, dv in zip(LIABILITY_LABELS, ldef):
            liabs[lab] = float(st.number_input(lab, 0, value=dv, step=5_000, key=f"li_{lab}"))
    ta, tl = sum(assets.values()), sum(liabs.values())
    s1, s2, s3 = st.columns(3)
    s1.metric("Total assets", f"${ta:,.0f}")
    s2.metric("Total liabilities", f"${tl:,.0f}")
    s3.metric("Net worth", f"${ta - tl:,.0f}")

    # ===== 3) About You ==================================================
    st.write("")
    st.markdown('<div class="aw-survey-section">👤 &nbsp;About You '
                '<span>— a few details to complete your profile</span></div>',
                unsafe_allow_html=True)
    a1, a2, a3 = st.columns(3)
    name = a1.text_input("Your name", prefill["name"] if prefill else "", key="sv_name")
    age = a2.number_input("Age", 18, 100, 45, key="sv_age")
    dependents = a3.number_input("Dependents", 0, 15, 0, key="sv_dep")
    ct1, ct2 = st.columns(2)
    phone = ct1.text_input("Phone number", prefill.get("phone", "") if prefill else "",
                           key="sv_phone", placeholder="(555) 123-4567")
    email = ct2.text_input("Email", prefill["email"] if prefill else "",
                           key="sv_email", placeholder="you@email.com")
    e1, e2 = st.columns(2)
    employment = e1.selectbox("Employment", list(Employment),
                              format_func=lambda e: e.value.replace("_", " ").title(), key="sv_emp")
    income = e2.number_input("Annual income ($) — enter 0 if retired/none", 0, value=100_000,
                             step=5_000, key="sv_inc")
    st.caption("If you're retired or nearing it (enter 0 for N/A):")
    r1, r2, r3 = st.columns(3)
    spending = r1.number_input("Annual spending need ($)", 0, value=0, step=5_000, key="sv_sp")
    ss_income = r2.number_input("Social Security ($/yr)", 0, value=0, step=1_000, key="sv_ss")
    pension = r3.number_input("Pension / other ($/yr)", 0, value=0, step=1_000, key="sv_pen")
    reserve = st.checkbox("We have an emergency reserve (3–6 months)", value=True, key="sv_res")

    # ===== Submit (single, at the bottom) ================================
    st.divider()
    share = st.checkbox(f"Share my responses with a {ui.FIRM_NAME} advisor to prepare for our "
                        "meeting", value=True, key="sv_share")

    if st.button("Submit survey", type="primary", key="sv_submit"):
        # Validate the important fields; 0 is an acceptable "N/A" for dollar amounts.
        missing = []
        if not name.strip():
            missing.append("your name")
        if (wg + wi + ws) == 0:
            missing.append("your goals balance (Growth / Income / Safety)")
        if sum(assets.values()) <= 0:
            missing.append("at least one asset on the balance sheet")
        if income <= 0 and spending <= 0:
            missing.append("annual income, or a spending need if retired")
        if missing:
            st.error("Please complete: " + "; ".join(missing) +
                     ". Enter 0 only for amounts that genuinely don't apply.")
            return

        investable = (assets["Brokerage & investment accounts"]
                      + assets["Retirement accounts (401k, IRA)"])
        liquid = assets["Cash & savings"]
        net_worth = sum(assets.values()) - sum(liabs.values())
        goals = [FinancialGoal(g, amt, yrs, pri)
                 for g, (amt, yrs, pri) in goal_inputs.items() if amt > 0]
        profile = ClientProfile(
            client_name=name.strip(), age=int(age), dependents=int(dependents),
            time_horizon_years=int(horizon), employment=employment, annual_income=float(income),
            net_worth=float(net_worth), liquid_net_worth=float(liquid),
            has_emergency_reserve=bool(reserve),
            objective=_triangle_to_objective(wg, wi, ws),
            risk_tolerance=_triangle_to_risk_tolerance(wg, ws, wg + wi + ws),
            drawdown_tolerance=float(drawdown), experience=experience,
            investable_assets=float(investable), annual_spending=float(spending),
            social_security_income=float(ss_income), pension_income=float(pension),
            goals=goals)

        store = _shared_store()
        store["survey_seq"] += 1
        record = {
            "id": store["survey_seq"],
            "name": profile.client_name,
            "phone": phone.strip() or "—", "email": email.strip() or "—",
            "submitted_at": dt.datetime.now(),
            "rec": build_recommendation(profile),
            "assets": assets, "liabilities": liabs, "net_worth": net_worth,
        }
        store["surveys"].append(record)
        if invite_token and invite_token in store["invites"]:
            store["invites"][invite_token]["status"] = "responded"
            store["invites"][invite_token]["survey_id"] = record["id"]
        # A local copy for this session's own thank-you page -- reading back
        # from the shared list by "last item" would be a race condition if
        # another session submits between this append and that page's render.
        st.session_state["my_survey_record"] = record
        st.session_state["survey_shared"] = bool(share)
        st.session_state["survey_done"] = True
        st.rerun()


def _survey_thank_you() -> None:
    rec_wrap = st.session_state.get("my_survey_record")
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
                       "now appear on their dashboard for review.")
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
        if "invite" not in st.query_params and st.button("Start a new survey", width="stretch"):
            for k in ("survey_done", "survey_shared", "my_survey_record"):
                st.session_state.pop(k, None)
            st.rerun()


# ==========================================================================
# Settings
# ==========================================================================
def settings() -> None:
    ui.section_header("Preferences", "Settings", "Portfolio selection and configuration.")
    st.write("")
    ui.subhead("Active portfolio")
    _portfolio_picker("settings", navigate=True)
    st.write("")
    ui.subhead("Configuration")
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
