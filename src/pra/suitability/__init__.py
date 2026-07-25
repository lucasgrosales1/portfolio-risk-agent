"""Phase 2: suitability intake, risk profiling, and recommendations.

Only the intake data model exists so far. The risk-scoring engine, allocation
recommender, and structured-product logic land here next, per docs/05-phase2-spec.md.
"""

from .montecarlo import MonteCarloResult, Route, run_monte_carlo
from .profile import (
    ClientProfile,
    Employment,
    Experience,
    FinancialGoal,
    GoalType,
    Objective,
    RiskTolerance,
)
from .strategy import StrategyAssessment, recommend_strategies
from .capacity import CapacityCeiling, Constraint, equity_ceiling
from .recommend import Recommendation, build_recommendation
from .retirement import RetirementReadiness, assess_retirement_readiness
from .scoring import RiskAssessment, ScoreComponent, score_profile
from .stress import Scenario, StressTest, run_stress_test
from .ips import IPSDocument, build_ips, render_ips_html
from .structured import (
    StructuredAssessment,
    StructuredProduct,
    evaluate_structured_products,
)

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
    "CapacityCeiling",
    "Constraint",
    "equity_ceiling",
    "Recommendation",
    "build_recommendation",
    "Scenario",
    "StressTest",
    "run_stress_test",
    "StructuredAssessment",
    "StructuredProduct",
    "evaluate_structured_products",
    "IPSDocument",
    "build_ips",
    "render_ips_html",
    "FinancialGoal",
    "GoalType",
    "StrategyAssessment",
    "recommend_strategies",
    "MonteCarloResult",
    "Route",
    "run_monte_carlo",
]
