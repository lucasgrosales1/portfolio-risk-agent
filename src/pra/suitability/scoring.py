"""Risk scoring with capacity overrides.

The design the client chose: **capacity constrains tolerance.** A blended score
captures the nuanced, attitudinal part (stated tolerance, objective, drawdown
appetite) alongside the situational part (horizon, financial cushion). Then hard
capacity rules can *only cap the result downward* — a short horizon or a missing
emergency reserve vetoes an aggressive allocation no matter how the score came
out. Overrides never raise the recommendation.

Every tunable number lives at the top of this file as a named constant, because
the scoring judgment is exactly the part that should be reviewed and adjusted by
someone with the licensing to defend it. Nothing here is a market truth; it is a
documented, transparent starting point.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..models import MODEL_PORTFOLIOS
from .profile import ClientProfile, Employment, Experience, Objective, RiskTolerance

# --------------------------------------------------------------------------
# Tunable parameters — review these first.
# --------------------------------------------------------------------------

# The four models, ordered least to most risk. Overrides cap by index here.
MODEL_RISK_ORDER = ["conservative", "moderate", "balanced_growth", "aggressive"]

# Blend weights for the raw score (must sum to 1.0).
# Attitudinal factors (~60%) vs situational factors (~40%).
WEIGHTS = {
    "tolerance": 0.25,   # stated willingness to accept volatility
    "objective": 0.15,   # preservation -> growth
    "drawdown": 0.20,    # the loss the client says they could sit through
    "horizon": 0.22,     # years until the money is needed (capacity)
    "cushion": 0.18,     # financial ability to weather a decline (capacity)
}

# Score (0-100) each stated risk-tolerance level contributes. Deliberately not
# 0/100 at the extremes — stated attitude alone shouldn't peg the recommendation.
TOLERANCE_POINTS = {
    RiskTolerance.CONSERVATIVE: 10,
    RiskTolerance.MODERATE_CONSERVATIVE: 30,
    RiskTolerance.MODERATE: 50,
    RiskTolerance.MODERATE_AGGRESSIVE: 72,
    RiskTolerance.AGGRESSIVE: 90,
}

OBJECTIVE_POINTS = {
    Objective.PRESERVATION: 10,
    Objective.INCOME: 35,
    Objective.BALANCED: 60,
    Objective.GROWTH: 90,
}

# Horizon: <= this many years scores 0; >= this many scores 100; linear between.
HORIZON_FLOOR_YEARS = 3
HORIZON_CEILING_YEARS = 20

# Drawdown tolerance that earns a full 100 on that axis.
DRAWDOWN_FULL_MARKS = 0.40

# Raw-score cut points mapping to the four models.
SCORE_TO_MODEL = [
    (30, "conservative"),
    (55, "moderate"),
    (78, "balanced_growth"),
    (101, "aggressive"),  # 101 so a perfect 100 lands here
]

# Capacity-override thresholds.
SHORT_HORIZON_HARD = 3        # <= this caps at conservative
SHORT_HORIZON_SOFT = 5        # <= this caps at moderate
NEAR_TERM_WITHDRAWAL_FRAC = 0.20   # withdrawal > this fraction of net worth caps hard
LATE_RETIREMENT_AGE = 72      # at/after this age, cap at moderate


@dataclass
class ScoreComponent:
    name: str
    raw: float      # 0-100 on this axis
    weight: float
    note: str

    @property
    def contribution(self) -> float:
        return self.raw * self.weight


@dataclass
class Override:
    """A capacity rule that capped the recommendation downward."""

    reason: str
    capped_to: str  # model key


@dataclass
class RiskAssessment:
    raw_score: float
    recommended_model: str
    profile_label: str
    components: list[ScoreComponent]
    overrides: list[Override] = field(default_factory=list)
    rationale: list[str] = field(default_factory=list)

    @property
    def score_model(self) -> str:
        """The model the blended score alone would have chosen, before overrides."""
        for cutoff, key in SCORE_TO_MODEL:
            if self.raw_score < cutoff:
                return key
        return "aggressive"

    @property
    def was_capped(self) -> bool:
        return self.recommended_model != self.score_model


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _horizon_score(years: int) -> float:
    if years <= HORIZON_FLOOR_YEARS:
        return 0.0
    if years >= HORIZON_CEILING_YEARS:
        return 100.0
    span = HORIZON_CEILING_YEARS - HORIZON_FLOOR_YEARS
    return (years - HORIZON_FLOOR_YEARS) / span * 100.0


def _cushion_score(profile: ClientProfile) -> tuple[float, str]:
    """Financial ability to weather a decline. 50 is neutral."""
    score = 50.0
    notes: list[str] = []

    if profile.has_emergency_reserve:
        score += 20
    else:
        score -= 25
        notes.append("no emergency reserve")

    lr = profile.liquid_ratio
    if lr >= 0.5:
        score += 15
    elif lr < 0.2:
        score -= 15
        notes.append("thin liquid net worth")

    if profile.net_worth > 0:
        withdrawal_frac = profile.near_term_withdrawal / profile.net_worth
        if withdrawal_frac > NEAR_TERM_WITHDRAWAL_FRAC:
            score -= 25
            notes.append("large near-term withdrawal")
        elif withdrawal_frac > 0.10:
            score -= 10

    if profile.employment == Employment.NOT_EMPLOYED:
        score -= 10
        notes.append("no earned income")

    note = "; ".join(notes) if notes else "adequate cushion"
    return _clamp(score), note


def _model_index(key: str) -> int:
    return MODEL_RISK_ORDER.index(key)


def _cap(current: str, ceiling: str) -> str:
    """Return the lower-risk of two model keys."""
    return current if _model_index(current) <= _model_index(ceiling) else ceiling


def score_profile(profile: ClientProfile) -> RiskAssessment:
    """Turn a client profile into a documented, capped risk recommendation."""

    components = [
        ScoreComponent(
            "Stated risk tolerance",
            TOLERANCE_POINTS[profile.risk_tolerance],
            WEIGHTS["tolerance"],
            profile.risk_tolerance.value.replace("_", " "),
        ),
        ScoreComponent(
            "Investment objective",
            OBJECTIVE_POINTS[profile.objective],
            WEIGHTS["objective"],
            profile.objective.value,
        ),
        ScoreComponent(
            "Drawdown tolerance",
            _clamp(profile.drawdown_tolerance / DRAWDOWN_FULL_MARKS * 100),
            WEIGHTS["drawdown"],
            f"{profile.drawdown_tolerance:.0%} stated",
        ),
        ScoreComponent(
            "Time horizon",
            _horizon_score(profile.time_horizon_years),
            WEIGHTS["horizon"],
            f"{profile.time_horizon_years} years",
        ),
    ]
    cushion_raw, cushion_note = _cushion_score(profile)
    components.append(
        ScoreComponent("Financial cushion", cushion_raw, WEIGHTS["cushion"], cushion_note)
    )

    raw_score = sum(c.contribution for c in components)

    # The score expresses DESIRE — how much risk the client's blended profile
    # supports. It is not the final recommendation. Hard capacity constraints
    # (the equity ceiling in pra.suitability.capacity) cap this downward during
    # reconciliation. Keeping desire and capacity separate is the whole point of
    # the capacity-first design.
    model = next(key for cutoff, key in SCORE_TO_MODEL if raw_score < cutoff)
    label = MODEL_PORTFOLIOS[model].name

    top = max(components, key=lambda c: c.contribution)
    low = min(components, key=lambda c: c.contribution)
    rationale = [
        f"The blended risk score is {raw_score:.0f} of 100, driven most by "
        f"{top.name.lower()} and held back most by {low.name.lower()}. On its own "
        f"the score supports the {label} model, before capacity constraints."
    ]

    return RiskAssessment(
        raw_score=raw_score,
        recommended_model=model,
        profile_label=label,
        components=components,
        overrides=[],
        rationale=rationale,
    )
