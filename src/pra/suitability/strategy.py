"""Implementation-strategy recommender: barbell, laddering, dollar-cost averaging.

Two clients with the same target allocation can *get there* differently, and the
right implementation depends on the client's situation:

  Dollar-cost averaging (DCA)  entering the market over time rather than all at
                               once — right when deploying a lump sum, or when
                               the client is anxious about timing.
  Barbell                      pairing very safe assets with a smaller aggressive
                               sleeve, skipping the middle — stability with a
                               shot at upside; suits moderate tolerance with a
                               defined need.
  Laddering                    staggering bond maturities — steady, predictable
                               income and reinvestment; suits an income need.

This module maps the profile to which strategies fit and why. It does not model
returns — that's the Monte Carlo's job, which tests these head to head.
"""

from __future__ import annotations

from dataclasses import dataclass

from .profile import ClientProfile, GoalType, Objective, RiskTolerance

STRATEGIES = ["dollar_cost_averaging", "barbell", "laddering", "lump_sum"]

STRATEGY_NAMES = {
    "dollar_cost_averaging": "Dollar-cost averaging",
    "barbell": "Barbell",
    "laddering": "Bond laddering",
    "lump_sum": "Lump-sum investment",
}


@dataclass
class StrategyFit:
    key: str
    name: str
    recommended: bool
    rationale: str


@dataclass
class StrategyAssessment:
    fits: list[StrategyFit]
    headline: str

    @property
    def recommended(self) -> list[StrategyFit]:
        return [f for f in self.fits if f.recommended]


def recommend_strategies(profile: ClientProfile) -> StrategyAssessment:
    """Which implementation strategies fit this client, with reasons."""
    fits: list[StrategyFit] = []
    has_income_need = profile.has_income_need
    conservative = profile.risk_tolerance in (
        RiskTolerance.CONSERVATIVE, RiskTolerance.MODERATE_CONSERVATIVE)
    low_experience = not profile.is_sophisticated
    goal_types = {g.goal_type for g in profile.goals}

    # --- Dollar-cost averaging -------------------------------------------
    dca = low_experience or conservative or GoalType.COLLEGE in goal_types
    fits.append(StrategyFit(
        "dollar_cost_averaging", STRATEGY_NAMES["dollar_cost_averaging"], dca,
        ("Phasing money in over several months reduces the risk of committing at a "
         "market peak and eases the client into volatility — a good fit here given "
         + ("their limited experience with market swings" if low_experience else
            "a cautious risk posture" if conservative else
            "a dated funding goal like college") + ".")
        if dca else
        "Less necessary — the client is comfortable with market risk and has no "
        "specific timing concern, so a phased entry mainly gives up expected return."))

    # --- Barbell ---------------------------------------------------------
    barbell = (
        profile.risk_tolerance in (RiskTolerance.MODERATE, RiskTolerance.MODERATE_AGGRESSIVE)
        and profile.drawdown_tolerance <= 0.30
        and (has_income_need or profile.objective == Objective.BALANCED)
    )
    fits.append(StrategyFit(
        "barbell", STRATEGY_NAMES["barbell"], barbell,
        ("Pairing a large safe sleeve with a smaller aggressive one gives downside "
         "stability while keeping meaningful upside — well suited to a client who "
         "wants growth but has a firm limit on how much they can lose, and a defined "
         "need to protect.")
        if barbell else
        "Not the best fit — a barbell shines for moderate tolerance with a firm "
        "drawdown limit; this client's profile points elsewhere."))

    # --- Laddering -------------------------------------------------------
    laddering = has_income_need or profile.objective == Objective.INCOME
    fits.append(StrategyFit(
        "laddering", STRATEGY_NAMES["laddering"], laddering,
        ("Staggering bond maturities produces steady, predictable income and "
         "reinvests at prevailing rates as each rung matures — a natural fit given "
         "the client's income need, and it dampens interest-rate timing risk.")
        if laddering else
        "Not indicated — laddering is built for a bond-income need this client does "
        "not have; their money is oriented toward growth."))

    # --- Lump sum --------------------------------------------------------
    lump = not (dca or has_income_need) and not conservative
    fits.append(StrategyFit(
        "lump_sum", STRATEGY_NAMES["lump_sum"], lump,
        ("Investing the full amount at once maximizes time in the market, which "
         "wins on average over a long horizon — appropriate here given the client's "
         "comfort with volatility and long timeframe.")
        if lump else
        "Weigh against phasing in — investing everything at once maximizes expected "
        "return but exposes the full balance to a poorly-timed entry."))

    rec = [f.name for f in fits if f.recommended]
    headline = (f"Recommended implementation: {', '.join(rec)}."
                if rec else "No single implementation strategy stands out; a straightforward "
                            "lump-sum or phased entry both work.")
    return StrategyAssessment(fits, headline)
