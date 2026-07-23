"""The client suitability profile.

This is the input contract for the whole Phase 2 flow: the intake form fills a
ClientProfile, and every downstream step — risk scoring, allocation, structured-
product gating, the IPS — reads from it. Defining it first means the form and the
(not-yet-built) engine agree on shape before either exists.

Nothing here scores or recommends. It is a container plus a few derived
conveniences. The judgment lives in the suitability engine, built next.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Employment(str, Enum):
    EMPLOYED = "employed"
    SELF_EMPLOYED = "self_employed"
    RETIRED = "retired"
    NOT_EMPLOYED = "not_employed"


class Objective(str, Enum):
    """Primary investment objective, preservation-to-growth."""

    PRESERVATION = "preservation"
    INCOME = "income"
    BALANCED = "balanced"
    GROWTH = "growth"


class RiskTolerance(str, Enum):
    """Stated willingness to accept volatility — distinct from capacity to bear it."""

    CONSERVATIVE = "conservative"
    MODERATE_CONSERVATIVE = "moderate_conservative"
    MODERATE = "moderate"
    MODERATE_AGGRESSIVE = "moderate_aggressive"
    AGGRESSIVE = "aggressive"


class Experience(str, Enum):
    """Investment sophistication. Gates access to complex products."""

    NONE = "none"
    LIMITED = "limited"
    GOOD = "good"
    EXTENSIVE = "extensive"


# Experience levels the tool treats as sophisticated enough for structured
# products. One of the four conjunctive income-note gates in the Phase 2 spec.
SOPHISTICATED_EXPERIENCE = (Experience.GOOD, Experience.EXTENSIVE)


@dataclass
class ClientProfile:
    """Everything the suitability analysis needs about one client.

    All figures are the client's stated values. Nothing is fetched or inferred
    here — this is pure intake.
    """

    # --- Identity / personal ---------------------------------------------
    client_name: str = "New Client"
    age: int = 45
    dependents: int = 0

    # --- Horizon ---------------------------------------------------------
    time_horizon_years: int = 15

    # --- Employment & income ---------------------------------------------
    employment: Employment = Employment.EMPLOYED
    annual_income: float = 100_000.0

    # --- Balance sheet ---------------------------------------------------
    net_worth: float = 500_000.0
    liquid_net_worth: float = 250_000.0
    marginal_tax_bracket: float = 0.24  # federal marginal rate as a decimal

    # --- Liquidity & reserves --------------------------------------------
    # Cash the client expects to withdraw within the next ~2 years.
    near_term_withdrawal: float = 0.0
    # Whether an emergency reserve (typically 3-6 months of expenses) is in place.
    has_emergency_reserve: bool = True

    # --- Objectives & risk -----------------------------------------------
    objective: Objective = Objective.BALANCED
    risk_tolerance: RiskTolerance = RiskTolerance.MODERATE
    # Largest peak-to-trough loss the client says they could tolerate, as a
    # positive decimal (0.20 = a 20% drawdown). Capacity, not just attitude.
    drawdown_tolerance: float = 0.20
    experience: Experience = Experience.LIMITED

    # --- Context ---------------------------------------------------------
    # Free-text: existing concentrations to unwind, restrictions, ESG wishes, etc.
    constraints: str = ""
    existing_holdings_note: str = ""
    meta: dict[str, str] = field(default_factory=dict)

    # --- Derived conveniences --------------------------------------------

    @property
    def has_income_need(self) -> bool:
        """A stated need for portfolio income.

        True when the objective is income, or when the client is retired and
        drawing down. The first of the four income-note gates.
        """
        return self.objective == Objective.INCOME or (
            self.employment == Employment.RETIRED and self.near_term_withdrawal > 0
        )

    @property
    def is_sophisticated(self) -> bool:
        """Experience sufficient for complex products. An income-note gate."""
        return self.experience in SOPHISTICATED_EXPERIENCE

    @property
    def liquid_ratio(self) -> float:
        """Liquid net worth as a share of total. Feeds the liquidity gate."""
        return self.liquid_net_worth / self.net_worth if self.net_worth else 0.0

    @property
    def short_horizon(self) -> bool:
        """A horizon short enough to cap equity regardless of stated tolerance."""
        return self.time_horizon_years <= 5

    def summary_line(self) -> str:
        return (
            f"{self.client_name}, age {self.age}, {self.time_horizon_years}-year "
            f"horizon, {self.risk_tolerance.value.replace('_', ' ')} risk tolerance"
        )
