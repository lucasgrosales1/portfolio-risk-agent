"""Model portfolios and asset-class classification.

The four models below are illustrative teaching defaults, not a house view.
They exist so Phase 1 has something to measure drift against; Phase 2 (the
IPS / suitability tool) will select among them based on a client questionnaire,
which is what closes the loop:

    suitability -> allocation -> analysis -> client document
"""

from __future__ import annotations

from dataclasses import dataclass

# Asset classes. Deliberately coarse — a one-page client report that splits
# equity into eleven sub-sleeves is a report nobody reads.
EQUITY = "Equity"
FIXED_INCOME = "Fixed Income"
CASH = "Cash"
OTHER = "Other"

ASSET_CLASSES = (EQUITY, FIXED_INCOME, CASH, OTHER)


@dataclass(frozen=True)
class ModelPortfolio:
    key: str
    name: str
    description: str
    targets: dict[str, float]  # asset class -> target weight (sums to 1.0)
    typical_horizon: str

    def target_for(self, asset_class: str) -> float:
        return self.targets.get(asset_class, 0.0)


MODEL_PORTFOLIOS: dict[str, ModelPortfolio] = {
    "conservative": ModelPortfolio(
        key="conservative",
        name="Conservative",
        description=(
            "Capital preservation with modest growth. Suited to short horizons "
            "or a low tolerance for drawdown."
        ),
        targets={EQUITY: 0.20, FIXED_INCOME: 0.70, CASH: 0.10},
        typical_horizon="Under 5 years",
    ),
    "moderate": ModelPortfolio(
        key="moderate",
        name="Moderate",
        description=(
            "Balanced toward income and stability, with enough equity to keep "
            "pace with inflation over a full market cycle."
        ),
        targets={EQUITY: 0.40, FIXED_INCOME: 0.55, CASH: 0.05},
        typical_horizon="5 to 10 years",
    ),
    "balanced_growth": ModelPortfolio(
        key="balanced_growth",
        name="Balanced Growth",
        description=(
            "Growth-oriented with a meaningful fixed income allocation to "
            "dampen drawdowns. A common default for mid-career accumulation."
        ),
        targets={EQUITY: 0.60, FIXED_INCOME: 0.35, CASH: 0.05},
        typical_horizon="10 to 20 years",
    ),
    "aggressive": ModelPortfolio(
        key="aggressive",
        name="Aggressive",
        description=(
            "Maximum long-term growth, accepting substantial interim volatility. "
            "Appropriate only where the horizon is long and the drawdown "
            "tolerance is genuine."
        ),
        targets={EQUITY: 0.85, FIXED_INCOME: 0.13, CASH: 0.02},
        typical_horizon="20+ years",
    ),
}

DEFAULT_MODEL = "balanced_growth"


def get_model(key: str) -> ModelPortfolio:
    normalized = key.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized not in MODEL_PORTFOLIOS:
        available = ", ".join(MODEL_PORTFOLIOS)
        raise KeyError(f"Unknown model portfolio {key!r}. Available: {available}")
    return MODEL_PORTFOLIOS[normalized]


# ---------------------------------------------------------------------------
# Asset-class classification
# ---------------------------------------------------------------------------
#
# yfinance exposes a `quoteType` and, for ETFs, a fund category — but coverage
# is uneven and the category strings are not stable enough to parse blindly.
# So: a small explicit map for tickers we know, a keyword heuristic for the
# rest, and an honest "Other" bucket when we genuinely cannot tell. The report
# surfaces anything that lands in Other rather than silently folding it into
# equity, because a misclassified sleeve makes every allocation number wrong.

_KNOWN_FIXED_INCOME = {
    "AGG", "BND", "BNDX", "BIV", "BSV", "BLV", "VCIT", "VCSH", "VCLT",
    "LQD", "HYG", "JNK", "TLT", "IEF", "SHY", "GOVT", "TIP", "VTIP", "SCHP",
    "MUB", "VTEB", "TFI", "SUB", "EMB", "VWOB", "IGSB", "SPTL", "SPTI",
    "SCHZ", "SPAB", "FBND", "TOTL", "USIG", "SHV", "BIL", "SGOV",
}

_KNOWN_EQUITY = {
    "VOO", "SPY", "IVV", "VTI", "ITOT", "SCHB", "SCHX", "VUG", "VTV",
    "QQQ", "IWM", "IJH", "IJR", "VO", "VB", "MDY",
    "VEA", "VWO", "VXUS", "IEFA", "IEMG", "EFA", "EEM", "ACWI", "VT",
    "VNQ", "SCHD", "DVY", "VYM", "NOBL", "RSP", "MTUM", "QUAL", "USMV",
    "XLK", "XLF", "XLV", "XLE", "XLY", "XLP", "XLI", "XLU", "XLB", "XLRE",
}

# Money-market and ultra-short instruments people hold as cash equivalents.
_KNOWN_CASH = {"SPAXX", "SPRXX", "VMFXX", "SWVXX", "FDRXX"}

_FIXED_INCOME_KEYWORDS = ("bond", "treasury", "fixed income", "municipal", "credit")
_CASH_KEYWORDS = ("money market",)


def classify_asset_class(
    ticker: str,
    quote_type: str | None = None,
    category: str | None = None,
) -> str:
    """Map a ticker to an asset class.

    `quote_type` and `category` come from yfinance when available. They are
    optional so this stays a pure function that is trivial to unit test.
    """
    symbol = ticker.upper()

    if symbol == "CASH" or symbol in _KNOWN_CASH:
        return CASH
    if symbol in _KNOWN_FIXED_INCOME:
        return FIXED_INCOME
    if symbol in _KNOWN_EQUITY:
        return EQUITY

    haystack = " ".join(filter(None, [quote_type, category])).lower()
    if any(word in haystack for word in _CASH_KEYWORDS):
        return CASH
    if any(word in haystack for word in _FIXED_INCOME_KEYWORDS):
        return FIXED_INCOME

    # An individual stock is unambiguous; a fund we don't recognize is not.
    if (quote_type or "").upper() == "EQUITY":
        return EQUITY
    if (quote_type or "").upper() in ("ETF", "MUTUALFUND"):
        # A fund we can't categorize. Assume equity (the common case) but the
        # report flags it so the advisor can override rather than trust it.
        return EQUITY

    return OTHER
