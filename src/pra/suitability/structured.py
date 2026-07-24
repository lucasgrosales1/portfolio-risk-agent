"""Structured-product suitability and illustrative payoff modeling.

The whole value of this module is restraint: it recommends structured products
only when the client's profile genuinely supports them, and when it declines it
says *why*, naming the failing factor. Structured products are the most-scrutinized
category in the business precisely because they get sold to people who shouldn't
hold them — so the "when not to" logic is the point.

Rules (from docs/05-phase2-spec.md):
  - Income / autocallable note: recommended only if ALL FOUR gates pass —
    income need, adequate liquidity, moderate-or-higher risk tolerance, and
    sophistication. Any one failing → declined, gate named.
  - Buffer need: prefer a defined-outcome / buffered ETF (liquid, no single-
    issuer credit risk); a buffered note only when specifically warranted.
  - Principal-protected note: only for very loss-averse clients who still want
    some upside, with the opportunity cost stated plainly.
  - Sleeve is a satellite, never the core: ≤15% of the portfolio, scaled down
    for smaller or less-liquid portfolios.

Payoffs are illustrative, computed in Python from clearly-stated assumed terms —
never quoted as a real issued product. As everywhere in this project, the numbers
are computed, not invented.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .profile import ClientProfile, Objective, RiskTolerance

# --------------------------------------------------------------------------
# Tunable thresholds — review these.
# --------------------------------------------------------------------------
# Below this investable size, a structured sleeve would over-concentrate.
MIN_PORTFOLIO_FOR_STRUCTURED = 100_000

# Income-note liquidity gate.
MIN_LIQUID_FOR_NOTES = 100_000
MIN_LIQUID_RATIO_FOR_NOTES = 0.25

# A client "needs a buffer" when they want growth participation but can only
# tolerate a modest drawdown.
BUFFER_NEED_MAX_DRAWDOWN = 0.25

# Principal-protection is only worth its opportunity cost for the very loss-averse.
PRINCIPAL_PROTECTION_MAX_DRAWDOWN = 0.10

# Sleeve sizing.
SLEEVE_BASE = 0.15
SLEEVE_SMALL = 0.10          # portfolios under SLEEVE_SMALL_THRESHOLD
SLEEVE_SMALL_THRESHOLD = 250_000

RISK_ORDER = [
    RiskTolerance.CONSERVATIVE,
    RiskTolerance.MODERATE_CONSERVATIVE,
    RiskTolerance.MODERATE,
    RiskTolerance.MODERATE_AGGRESSIVE,
    RiskTolerance.AGGRESSIVE,
]


def _risk_rank(t: RiskTolerance) -> int:
    return RISK_ORDER.index(t)


# --------------------------------------------------------------------------
# Illustrative terms (assumed, labeled as such in the report).
# --------------------------------------------------------------------------
INCOME_NOTE_TERMS = {
    "term_years": 2, "contingent_coupon": 0.08,
    "coupon_barrier": 0.70, "principal_barrier": 0.60,
}
BUFFERED_ETF_TERMS = {"term_years": 1, "buffer": 0.15, "cap": 0.16}
BUFFERED_NOTE_TERMS = {"term_years": 2, "buffer": 0.20, "cap": 0.28}
PRINCIPAL_PROTECTED_TERMS = {"term_years": 5, "participation": 1.0, "cap": 0.30}


@dataclass
class StructuredProduct:
    key: str
    name: str
    family: str
    recommended: bool
    rationale: str
    terms: dict = field(default_factory=dict)
    failed_gates: list[str] = field(default_factory=list)
    # (underlying_return, product_return) points for the payoff diagram.
    payoff: list[tuple[float, float]] | None = None


@dataclass
class StructuredAssessment:
    considered: list[StructuredProduct]
    sleeve_max_pct: float
    sleeve_note: str
    headline: str

    @property
    def recommended(self) -> list[StructuredProduct]:
        return [p for p in self.considered if p.recommended]

    @property
    def any_recommended(self) -> bool:
        return bool(self.recommended)


# --------------------------------------------------------------------------
# Payoff models — maturity return of the product vs. the underlying's return.
# --------------------------------------------------------------------------
def _underlying_grid(lo: float = -0.50, hi: float = 0.50, step: float = 0.02) -> list[float]:
    n = int(round((hi - lo) / step)) + 1
    return [round(lo + i * step, 4) for i in range(n)]


def _income_note_payoff(u: float, t: dict) -> float:
    """Coupons if the barrier holds; 1:1 downside below the principal barrier."""
    total_coupon = t["contingent_coupon"] * t["term_years"]
    barrier_drop = -(1 - t["principal_barrier"])  # e.g. 0.60 barrier -> -0.40
    if u >= barrier_drop:
        return total_coupon           # capped: coupons only, principal returned
    return total_coupon + u           # below barrier: full downside plus coupons


def _buffered_payoff(u: float, t: dict) -> float:
    buffer, cap = t["buffer"], t["cap"]
    if u >= 0:
        return min(u, cap)
    if u >= -buffer:
        return 0.0                    # buffer absorbs the first `buffer` of loss
    return u + buffer                 # loss beyond the buffer


def _principal_protected_payoff(u: float, t: dict) -> float:
    if u >= 0:
        return min(t["participation"] * u, t["cap"])
    return 0.0                        # principal protected at maturity


def _payoff_curve(fn, terms: dict) -> list[tuple[float, float]]:
    return [(u, fn(u, terms)) for u in _underlying_grid()]


# --------------------------------------------------------------------------
# Sleeve sizing
# --------------------------------------------------------------------------
def size_sleeve(profile: ClientProfile) -> tuple[float, str]:
    """Maximum structured-product sleeve as a fraction of the portfolio."""
    if profile.investable_assets < MIN_PORTFOLIO_FOR_STRUCTURED:
        return 0.0, (f"Portfolio is under ${MIN_PORTFOLIO_FOR_STRUCTURED:,.0f}; a "
                     "structured sleeve would over-concentrate the account.")

    cap = SLEEVE_BASE
    notes = []
    if profile.investable_assets < SLEEVE_SMALL_THRESHOLD:
        cap = min(cap, SLEEVE_SMALL)
        notes.append(f"reduced to {SLEEVE_SMALL:.0%} for a portfolio under "
                     f"${SLEEVE_SMALL_THRESHOLD:,.0f}")
    if profile.liquid_ratio < 0.30:
        cap = min(cap, 0.10)
        notes.append("reduced for limited liquidity")

    note = (f"Satellite sleeve capped at {cap:.0%} of the portfolio"
            + (" (" + "; ".join(notes) + ")." if notes else "."))
    return cap, note


# --------------------------------------------------------------------------
# The evaluation
# --------------------------------------------------------------------------
def evaluate_structured_products(profile: ClientProfile) -> StructuredAssessment:
    sleeve, sleeve_note = size_sleeve(profile)
    considered: list[StructuredProduct] = []

    # Global gate: portfolio too small → nothing is suitable.
    if sleeve <= 0:
        for key, name, fam in [
            ("income_note", "Income / autocallable note", "income_note"),
            ("buffered_etf", "Defined-outcome / buffered ETF", "buffered_etf"),
            ("buffered_note", "Buffered growth note", "buffered_note"),
            ("principal_protected", "Principal-protected note", "principal_protected"),
        ]:
            considered.append(StructuredProduct(
                key=key, name=name, family=fam, recommended=False,
                rationale=sleeve_note, failed_gates=["portfolio size"]))
        return StructuredAssessment(considered, 0.0, sleeve_note,
                                    "Portfolio is too small for a structured-product sleeve.")

    # --- Income / autocallable note: all four gates ----------------------
    gates_failed = []
    if not profile.has_income_need:
        gates_failed.append("no stated income need")
    if not (profile.liquid_net_worth >= MIN_LIQUID_FOR_NOTES
            and profile.liquid_ratio >= MIN_LIQUID_RATIO_FOR_NOTES):
        gates_failed.append("insufficient liquidity to lock up a sleeve")
    if _risk_rank(profile.risk_tolerance) < _risk_rank(RiskTolerance.MODERATE):
        gates_failed.append("risk tolerance below moderate")
    if not profile.is_sophisticated:
        gates_failed.append("limited investment experience")

    if not gates_failed:
        t = INCOME_NOTE_TERMS
        considered.append(StructuredProduct(
            key="income_note", name="Income / autocallable note", family="income_note",
            recommended=True,
            rationale=(f"All four suitability gates pass. An income note can supplement "
                       f"cash flow: an illustrative {t['contingent_coupon']:.0%} contingent "
                       f"coupon while the underlying stays above {t['coupon_barrier']:.0%} of "
                       f"its start, over {t['term_years']} years. The coupon is contingent, "
                       f"not guaranteed, and principal is at risk below the "
                       f"{t['principal_barrier']:.0%} barrier — this is not a bond."),
            terms=t, payoff=_payoff_curve(_income_note_payoff, t)))
    else:
        considered.append(StructuredProduct(
            key="income_note", name="Income / autocallable note", family="income_note",
            recommended=False,
            rationale="Evaluated and declined — an income note requires all of: an income "
                      "need, adequate liquidity, moderate-or-higher risk tolerance, and "
                      "sufficient sophistication.",
            failed_gates=gates_failed))

    # --- Buffer need: prefer the ETF -------------------------------------
    wants_growth = (
        profile.objective in (Objective.GROWTH, Objective.BALANCED)
        or _risk_rank(profile.risk_tolerance) >= _risk_rank(RiskTolerance.MODERATE)
    )
    buffer_need = wants_growth and profile.drawdown_tolerance <= BUFFER_NEED_MAX_DRAWDOWN

    if buffer_need:
        t = BUFFERED_ETF_TERMS
        considered.append(StructuredProduct(
            key="buffered_etf", name="Defined-outcome / buffered ETF", family="buffered_etf",
            recommended=True,
            rationale=(f"The client wants growth participation but has a "
                       f"{profile.drawdown_tolerance:.0%} drawdown tolerance. A buffered ETF "
                       f"fits: an illustrative {t['buffer']:.0%} downside buffer with upside "
                       f"capped near {t['cap']:.0%} over {t['term_years']} year. Exchange-"
                       f"traded and liquid, with no single-issuer credit risk — the preferred "
                       f"way to add a buffer."),
            terms=t, payoff=_payoff_curve(_buffered_payoff, t)))

        # A buffered NOTE only when specifically warranted (sophisticated + liquid,
        # e.g. wanting a longer defined term or larger buffer than ETFs offer).
        note_warranted = (
            profile.is_sophisticated
            and profile.liquid_net_worth >= MIN_LIQUID_FOR_NOTES
            and profile.liquid_ratio >= MIN_LIQUID_RATIO_FOR_NOTES
        )
        tn = BUFFERED_NOTE_TERMS
        if note_warranted:
            considered.append(StructuredProduct(
                key="buffered_note", name="Buffered growth note", family="buffered_note",
                recommended=True,
                rationale=(f"Optional: a buffered *note* offers a larger illustrative buffer "
                           f"({tn['buffer']:.0%}) and a longer {tn['term_years']}-year defined "
                           f"term than the ETF, suitable given the client's liquidity and "
                           f"sophistication. It carries single-issuer credit risk and is "
                           f"illiquid — the ETF is preferred unless the longer term is wanted."),
                terms=tn, payoff=_payoff_curve(_buffered_payoff, tn)))
        else:
            considered.append(StructuredProduct(
                key="buffered_note", name="Buffered growth note", family="buffered_note",
                recommended=False,
                rationale="Not warranted — the liquid buffered ETF achieves the same "
                          "protection without single-issuer credit risk or a lockup. A "
                          "buffered note would add risk the client's profile doesn't call for.",
                failed_gates=["ETF preferred over a note here"]))
    else:
        reason = ("the client's drawdown tolerance already supports their growth objective, "
                  "so a buffer isn't needed"
                  if wants_growth else
                  "the client is not seeking growth participation that a buffer would protect")
        for key, name, fam in [("buffered_etf", "Defined-outcome / buffered ETF", "buffered_etf"),
                               ("buffered_note", "Buffered growth note", "buffered_note")]:
            considered.append(StructuredProduct(
                key=key, name=name, family=fam, recommended=False,
                rationale=f"Evaluated and declined — {reason}.",
                failed_gates=["no buffer need"]))

    # --- Principal-protected note ----------------------------------------
    if profile.drawdown_tolerance <= PRINCIPAL_PROTECTION_MAX_DRAWDOWN:
        t = PRINCIPAL_PROTECTED_TERMS
        considered.append(StructuredProduct(
            key="principal_protected", name="Principal-protected note", family="principal_protected",
            recommended=True,
            rationale=(f"The client is highly loss-averse ({profile.drawdown_tolerance:.0%} "
                       f"drawdown tolerance) but wants more than cash. An illustrative "
                       f"principal-protected note returns principal at maturity with "
                       f"{t['participation']:.0%} of upside capped near {t['cap']:.0%} over "
                       f"{t['term_years']} years. Weigh the opportunity cost, the long lockup, "
                       f"and the issuer's credit risk before using it."),
            terms=t, payoff=_payoff_curve(_principal_protected_payoff, t)))
    else:
        considered.append(StructuredProduct(
            key="principal_protected", name="Principal-protected note", family="principal_protected",
            recommended=False,
            rationale="Evaluated and declined — the client's drawdown tolerance is high enough "
                      "that principal protection's opportunity cost and lockup aren't warranted.",
            failed_gates=["drawdown tolerance too high to justify the opportunity cost"]))

    recommended = [p for p in considered if p.recommended]
    if recommended:
        names = ", ".join(p.name for p in recommended)
        headline = f"{len(recommended)} structured product(s) may suit this client: {names}."
    else:
        headline = ("No structured products suit this client's profile; each was evaluated "
                    "and declined for the reason shown.")

    return StructuredAssessment(considered, sleeve, sleeve_note, headline)
