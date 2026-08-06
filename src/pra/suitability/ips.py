"""Investment Policy Statement generation.

Turns a Recommendation into a draft IPS — the document that formalizes an
advisory relationship. Everything here is assembled from figures the engine
already computed; the IPS narrates them, it does not invent anything.

Sections follow the spec: objectives and risk profile with reasoning, target
allocation and rebalancing policy, constraints/liquidity/taxes, a
retirement-income policy where relevant, and a structured-product policy that
documents the decision either way — including an explicit choice to exclude.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from html import escape

from ..config import DISCLAIMER
from ..models import ASSET_CLASSES, MODEL_PORTFOLIOS


# `pra` exposes __version__ at the package root; import it lazily to avoid a
# circular import during package initialization.
def _pkg_version() -> str:
    from .. import __version__

    return __version__


@dataclass
class IPSSection:
    heading: str
    paragraphs: list[str] = field(default_factory=list)
    bullets: list[str] = field(default_factory=list)


@dataclass
class IPSDocument:
    client_name: str
    date: str
    model_name: str
    sections: list[IPSSection]

    def to_markdown(self) -> str:
        out = [f"# Investment Policy Statement\n\n**{self.client_name}** — {self.date}\n"]
        for s in self.sections:
            out.append(f"## {s.heading}\n")
            for p in s.paragraphs:
                out.append(p + "\n")
            for b in s.bullets:
                out.append(f"- {b}")
            out.append("")
        return "\n".join(out)


def _pct(x: float, places: int = 0) -> str:
    return f"{x * 100:.{places}f}%"


def build_ips(rec) -> IPSDocument:
    """Assemble the IPS sections from a Recommendation."""
    p = rec.profile
    model = MODEL_PORTFOLIOS[rec.recommended_model]
    sections: list[IPSSection] = []

    # --- Purpose ----------------------------------------------------------
    sections.append(IPSSection(
        "Purpose",
        [f"This Investment Policy Statement (IPS) sets out the investment "
         f"objectives, constraints, and management policies agreed for "
         f"{p.client_name}. It is the reference point against which the portfolio "
         f"is managed and reviewed."]))

    # --- Objectives & risk profile ---------------------------------------
    obj_paras = [
        f"The client's primary objective is **{p.objective.value.title()}**, over a "
        f"stated time horizon of **{p.time_horizon_years} years**. Stated risk "
        f"tolerance is **{p.risk_tolerance.value.replace('_', ' ')}**, with a "
        f"drawdown tolerance of **{_pct(p.drawdown_tolerance)}**.",
    ]
    obj_paras.extend(line.strip() for line in rec.rationale if not line.strip().startswith("•"))
    sections.append(IPSSection("Investment Objectives & Risk Profile", obj_paras))

    # --- Risk capacity ---------------------------------------------------
    cap_bullets = [c.label + (" (binding)" if c.binding else "") for c in rec.capacity.constraints]
    sections.append(IPSSection(
        "Risk Capacity",
        [f"Capacity analysis sets a maximum suitable equity exposure of "
         f"**{_pct(rec.capacity.max_equity)}**. The recommended allocation of "
         f"**{model.name}** ({_pct(model.target_for('Equity'))} equity) sits within "
         f"that ceiling. Capacity — not stated preference alone — governs the "
         f"allocation. The constraints considered:"],
        cap_bullets))

    # --- Target allocation -----------------------------------------------
    alloc_bullets = [f"{cls}: {_pct(model.target_for(cls))}"
                     for cls in ASSET_CLASSES if model.target_for(cls) > 0]
    sections.append(IPSSection(
        "Target Asset Allocation",
        [f"The strategic target is the **{model.name}** model:", model.description],
        alloc_bullets))

    # --- Rebalancing policy ----------------------------------------------
    sections.append(IPSSection(
        "Rebalancing Policy",
        ["The portfolio is reviewed at least semi-annually and rebalanced toward the "
         "target when any asset class drifts more than **3 percentage points** from "
         "its target weight.",
         "Rebalancing sales are sourced tax-efficiently: from tax-sheltered accounts "
         "first (no current tax), then from tax-lots carrying losses or long-term "
         "gains before short-term gains. The tax cost of any taxable rebalancing is "
         "estimated and weighed before acting."]))

    # --- Constraints, liquidity, taxes -----------------------------------
    liq = [
        f"Emergency reserve: {'in place' if p.has_emergency_reserve else 'NOT established — funding a reserve is a precondition to the equity allocation'}.",
        f"Liquid net worth: ${p.liquid_net_worth:,.0f} ({_pct(p.liquid_ratio)} of net worth).",
        f"Marginal tax bracket assumed at {_pct(p.marginal_tax_bracket)} for planning.",
    ]
    if p.constraints:
        liq.append(f"Client-specified constraints: {p.constraints}")
    sections.append(IPSSection(
        "Constraints, Liquidity & Taxes",
        ["The following constraints and considerations apply:"], liq))

    # --- Retirement income policy (if applicable) ------------------------
    r = rec.readiness
    if r.applicable:
        para = [
            f"The portfolio funds an annual withdrawal of **${r.net_withdrawal_need:,.0f}** "
            f"(net of guaranteed income), a **{_pct(r.withdrawal_rate, 1)}** withdrawal rate "
            f"against a {_pct(r.benchmark_rate)} sustainability benchmark — assessed as "
            f"**{r.status}**.",
        ]
        para.extend(r.findings)
        stress = rec.stress
        if stress.applicable:
            para.append(
                f"Sequence-of-returns stress testing over {stress.horizon_years} years "
                f"informs the allocation: an early market decline while withdrawing is the "
                f"primary risk, and the defensive allocation is sized with that in view.")
        sections.append(IPSSection("Retirement Income Policy", para, r.red_flags))

    # --- Structured-product policy ---------------------------------------
    sp = rec.structured
    sp_paras = [sp.sleeve_note]
    sp_bullets = []
    for prod in sp.considered:
        mark = "Approved" if prod.recommended else "Excluded"
        sp_bullets.append(f"**{prod.name} — {mark}.** {prod.rationale}")
    if sp.any_recommended:
        sp_paras.append("Approved structured products are held only as a satellite sleeve "
                        "within the cap above, never as core holdings. Each carries issuer "
                        "credit risk, limited liquidity, and a defined term.")
    else:
        sp_paras.append("Structured products were evaluated in full and **excluded** — none "
                        "suit this client's profile. Each exclusion and its reason is "
                        "documented below.")
    sections.append(IPSSection("Structured-Product Policy", sp_paras, sp_bullets))

    # --- Monitoring & review ---------------------------------------------
    sections.append(IPSSection(
        "Monitoring & Review",
        ["This IPS is reviewed at least annually, and sooner on a material change in the "
         "client's circumstances, goals, or risk capacity — a change in employment, "
         "health, family situation, time horizon, or a large change in net worth. "
         "Allocation drift, withdrawal sustainability, and concentration are monitored on "
         "the schedule above."]))

    # --- Disclaimer ------------------------------------------------------
    sections.append(IPSSection("Important Disclosures", [DISCLAIMER]))

    return IPSDocument(
        client_name=p.client_name,
        date=date.today().strftime("%B %d, %Y"),
        model_name=model.name,
        sections=sections,
    )


def render_ips_html(rec) -> str:
    """Render the IPS as a self-contained, print-styled HTML document."""
    doc = build_ips(rec)
    body = []
    for s in doc.sections:
        body.append(f"<h2>{escape(s.heading)}</h2>")
        for para in s.paragraphs:
            body.append(f"<p>{_md_inline(para)}</p>")
        if s.bullets:
            body.append("<ul>")
            for b in s.bullets:
                body.append(f"<li>{_md_inline(b)}</li>")
            body.append("</ul>")

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Investment Policy Statement — {escape(doc.client_name)}</title>
<style>
  html {{ background: #fff; color-scheme: light; }}
  body {{ font: 14px/1.6 "Segoe UI",-apple-system,Helvetica,Arial,sans-serif; color:#1f2937;
         background: #fff; max-width: 820px; margin: 0 auto; padding: 40px 28px 64px; }}
  h1 {{ font-size: 24px; color:#0d2b4a; margin:0 0 2px; }}
  .sub {{ color:#5c6370; margin-bottom: 18px; border-bottom: 2px solid #1a4d7a; padding-bottom: 12px; }}
  h2 {{ font-size: 13px; text-transform: uppercase; letter-spacing:.08em; color:#1a4d7a;
        margin: 26px 0 8px; border-bottom: 1px solid #e5e7eb; padding-bottom: 4px; }}
  p {{ margin: 0 0 10px; }}
  ul {{ margin: 0 0 12px; padding-left: 20px; }}
  li {{ margin-bottom: 5px; }}
  .foot {{ margin-top: 30px; padding-top: 12px; border-top: 1px solid #e5e7eb;
           font-size: 11px; color:#6b7280; }}
  @page {{ size: letter; margin: 0.7in; }}
</style></head><body>
<h1>Investment Policy Statement</h1>
<div class="sub"><strong>{escape(doc.client_name)}</strong> &middot; {escape(doc.date)}
 &middot; Strategic target: {escape(doc.model_name)}</div>
{''.join(body)}
<div class="foot">Draft prepared by Advisor Workbench v{_pkg_version()}. Figures are computed
 programmatically from the client's stated profile and current market data. For discussion;
 not a final advisory agreement.</div>
</body></html>"""


def _md_inline(text: str) -> str:
    """Minimal inline markdown (**bold**) → HTML, everything else escaped."""
    import re

    parts = re.split(r"(\*\*.+?\*\*)", text)
    out = []
    for part in parts:
        if part.startswith("**") and part.endswith("**"):
            out.append(f"<strong>{escape(part[2:-2])}</strong>")
        else:
            out.append(escape(part))
    return "".join(out)
