"""Phase 2: suitability intake, risk profiling, and recommendations.

Only the intake data model exists so far. The risk-scoring engine, allocation
recommender, and structured-product logic land here next, per docs/05-phase2-spec.md.
"""

from .profile import (
    ClientProfile,
    Employment,
    Experience,
    Objective,
    RiskTolerance,
)
from .retirement import RetirementReadiness, assess_retirement_readiness
from .scoring import RiskAssessment, ScoreComponent, score_profile

__all__ = [
    "ClientProfile",
    "Employment",
    "Experience",
    "Objective",
    "RiskTolerance",
    "RiskAssessment",
    "ScoreComponent",
    "score_profile",
    "RetirementReadiness",
    "assess_retirement_readiness",
]
