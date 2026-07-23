"""The unified recommendation — desire reconciled against capacity.

This is the single entry point the app calls. It runs the three pieces and
reconciles them into one answer:

  1. score_profile          -> the model the client's risk profile DESIRES
  2. assess_retirement...   -> withdrawal-rate feasibility (decumulation)
  3. equity_ceiling         -> the maximum equity the situation can BEAR

The final recommendation is the desired model capped at the capacity ceiling.
"Capacity sets the boundaries; tolerance positions within them." When capacity
binds, the recommendation says so and names the constraint — which is exactly
the judgment a suitability reviewer looks for.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..models import EQUITY, MODEL_PORTFOLIOS
from .capacity import CapacityCeiling, equity_ceiling
from .profile import ClientProfile
from .retirement import RetirementReadiness, assess_retirement_readiness
from .scoring import RiskAssessment, score_profile

# Models ordered least to most equity, with their equity fraction.
_MODELS_BY_EQUITY = sorted(
    MODEL_PORTFOLIOS.values(), key=lambda m: m.targets.get(EQUITY, 0.0)
)


def _model_equity(key: str) -> float:
    return MODEL_PORTFOLIOS[key].targets.get(EQUITY, 0.0)


def _highest_model_within(ceiling: float) -> str:
    """The most equity-heavy model whose equity fraction is at or below `ceiling`."""
    allowed = [m for m in _MODELS_BY_EQUITY if m.targets.get(EQUITY, 0.0) <= ceiling + 1e-9]
    # If even the most conservative model exceeds the ceiling, use it anyway —
    # it's the closest available, and the report flags the gap.
    return (allowed[-1] if allowed else _MODELS_BY_EQUITY[0]).key


@dataclass
class Recommendation:
    profile: ClientProfile
    assessment: RiskAssessment
    readiness: RetirementReadiness
    capacity: CapacityCeiling

    desired_model: str          # what the risk score alone supports
    recommended_model: str      # after capacity reconciliation
    capped: bool
    branch: str                 # "accumulation" | "decumulation"
    rationale: list[str]

    @property
    def recommended_label(self) -> str:
        return MODEL_PORTFOLIOS[self.recommended_model].name

    @property
    def desired_label(self) -> str:
        return MODEL_PORTFOLIOS[self.desired_model].name

    @property
    def recommended_equity(self) -> float:
        return _model_equity(self.recommended_model)


def build_recommendation(profile: ClientProfile) -> Recommendation:
    """Run and reconcile the full suitability recommendation."""
    assessment = score_profile(profile)
    readiness = assess_retirement_readiness(profile)
    capacity = equity_ceiling(profile, readiness)

    desired = assessment.recommended_model
    desired_equity = _model_equity(desired)

    # Reconcile: cap desire at the capacity ceiling.
    final_equity = min(desired_equity, capacity.max_equity)
    recommended = _highest_model_within(final_equity)
    capped = recommended != desired

    branch = "decumulation" if readiness.applicable else "accumulation"

    rationale: list[str] = list(assessment.rationale)
    if capped:
        rationale.append(
            f"Capacity constraints reduce the recommendation from "
            f"{MODEL_PORTFOLIOS[desired].name} to "
            f"{MODEL_PORTFOLIOS[recommended].name}: the binding limit is that "
            f"{capacity.binding_reason}."
        )
    else:
        rationale.append(
            f"Capacity supports the desired allocation; the recommendation stands at "
            f"{MODEL_PORTFOLIOS[recommended].name} "
            f"(equity ceiling {capacity.max_equity:.0%}, "
            f"recommended equity {_model_equity(recommended):.0%})."
        )

    return Recommendation(
        profile=profile,
        assessment=assessment,
        readiness=readiness,
        capacity=capacity,
        desired_model=desired,
        recommended_model=recommended,
        capped=capped,
        branch=branch,
        rationale=rationale,
    )
