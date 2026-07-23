"""Retirement-income readiness — the decumulation branch.

When a client draws income from the portfolio, the first question is not "what
risk do they want?" but "can this portfolio support this spending at all?" That
is a withdrawal-rate question, and it gates everything downstream: an allocation
recommendation is meaningless if the plan is spending itself into the ground.

This is Phase 1 of the retirement module (the client's scoping): withdrawal rate
vs. the 4% benchmark, a Safe / Caution / Unsafe flag, a starting allocation, and
the missing-emergency-reserve red flag. Deferred to later phases: essential vs.
discretionary spending, reserve sizing, Monte Carlo, RMDs, longevity glide paths.

Every threshold is a named constant for review. The 4% figure is a benchmark
with assumptions (roughly a 30-year horizon, a balanced allocation, US return
history) — the output states that rather than treating it as a guarantee.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .profile import ClientProfile

# The classic "safe withdrawal rate" benchmark and the caution band above it.
SAFE_WITHDRAWAL_RATE = 0.04
CAUTION_WITHDRAWAL_RATE = 0.05

# Starting allocation (equity fraction) for a plan that clears the safe rate.
# A 40/60 growth/defensive split — the client's stated default. The capacity
# band (next stage) can still lower the equity share for a low drawdown limit.
SAFE_EQUITY_FRACTION = 0.40
CAUTION_EQUITY_FRACTION = 0.30
UNSAFE_EQUITY_FRACTION = 0.20

STATUS_SAFE = "Safe"
STATUS_CAUTION = "Caution"
STATUS_UNSAFE = "Unsafe"


@dataclass
class RetirementReadiness:
    applicable: bool                 # False when there's no withdrawal need
    net_withdrawal_need: float       # annual $ the portfolio must provide
    withdrawal_rate: float           # as a fraction of investable assets
    benchmark_rate: float
    status: str                      # Safe | Caution | Unsafe
    suggested_equity_fraction: float
    emergency_reserve_ok: bool
    findings: list[str] = field(default_factory=list)
    red_flags: list[str] = field(default_factory=list)

    @property
    def suggested_split_label(self) -> str:
        eq = round(self.suggested_equity_fraction * 100)
        return f"{eq}/{100 - eq} equity/defensive"

    @property
    def headroom(self) -> float:
        """Percentage points of withdrawal-rate room below the safe benchmark."""
        return self.benchmark_rate - self.withdrawal_rate


def assess_retirement_readiness(profile: ClientProfile) -> RetirementReadiness:
    """Run the Phase 1 retirement-income readiness check."""
    need = profile.net_withdrawal_need
    rate = profile.withdrawal_rate

    if need <= 0:
        # No portfolio withdrawal required — this branch doesn't apply.
        return RetirementReadiness(
            applicable=False,
            net_withdrawal_need=0.0,
            withdrawal_rate=0.0,
            benchmark_rate=SAFE_WITHDRAWAL_RATE,
            status=STATUS_SAFE,
            suggested_equity_fraction=SAFE_EQUITY_FRACTION,
            emergency_reserve_ok=profile.has_emergency_reserve,
            findings=["No portfolio withdrawal is required; guaranteed income "
                      "covers stated spending."],
        )

    findings: list[str] = []
    red_flags: list[str] = []

    covered = profile.social_security_income + profile.pension_income
    findings.append(
        f"Annual spending of ${profile.annual_spending:,.0f} is offset by "
        f"${covered:,.0f} of guaranteed income (Social Security and pension), "
        f"leaving ${need:,.0f} to be drawn from a ${profile.investable_assets:,.0f} "
        f"portfolio — a {rate:.1%} withdrawal rate."
    )

    if rate <= SAFE_WITHDRAWAL_RATE:
        status = STATUS_SAFE
        equity = SAFE_EQUITY_FRACTION
        findings.append(
            f"That is at or below the {SAFE_WITHDRAWAL_RATE:.0%} benchmark, so the "
            f"spending is sustainable under historical assumptions."
        )
    elif rate <= CAUTION_WITHDRAWAL_RATE:
        status = STATUS_CAUTION
        equity = CAUTION_EQUITY_FRACTION
        findings.append(
            f"That is above the {SAFE_WITHDRAWAL_RATE:.0%} benchmark but within "
            f"{CAUTION_WITHDRAWAL_RATE:.0%}. The plan is workable but has little "
            f"margin; a poor first decade of returns could strain it."
        )
        red_flags.append(
            f"Withdrawal rate of {rate:.1%} exceeds the {SAFE_WITHDRAWAL_RATE:.0%} "
            f"safe benchmark — worth a spending conversation."
        )
    else:
        status = STATUS_UNSAFE
        equity = UNSAFE_EQUITY_FRACTION
        findings.append(
            f"That exceeds {CAUTION_WITHDRAWAL_RATE:.0%}, a rate historically "
            f"associated with a real risk of depleting the portfolio. No allocation "
            f"fixes an unsustainable withdrawal rate — spending, guaranteed income, "
            f"or the horizon has to change first."
        )
        red_flags.append(
            f"Withdrawal rate of {rate:.1%} is not sustainable. Reducing equity does "
            f"not solve this; it is a spending-vs-assets problem."
        )

    if not profile.has_emergency_reserve:
        red_flags.append(
            "No emergency reserve is in place. A drawdown-phase portfolio with no "
            "cash buffer may be forced to sell into a downturn to fund spending, "
            "which is the single largest avoidable risk in decumulation. Establish "
            "a reserve before committing to the equity allocation."
        )

    return RetirementReadiness(
        applicable=True,
        net_withdrawal_need=need,
        withdrawal_rate=rate,
        benchmark_rate=SAFE_WITHDRAWAL_RATE,
        status=status,
        suggested_equity_fraction=equity,
        emergency_reserve_ok=profile.has_emergency_reserve,
        findings=findings,
        red_flags=red_flags,
    )
