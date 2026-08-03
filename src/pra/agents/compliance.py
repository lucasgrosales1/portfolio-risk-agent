"""The compliance-review agent — the reviewing half of the agent pair.

A second, independent model checks the narrative agent's draft against the
same computed figures it was given. Separate system prompt, separate (cheaper)
model, since the review task is narrow and rule-checkable: does this paragraph
make a claim the figures don't support?
"""

from __future__ import annotations

import json

import anthropic

from ..config import COMPLIANCE_MODEL, anthropic_api_key

_REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "approved": {"type": "boolean"},
        "flags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "One short, specific reason per violation found. Empty if approved.",
        },
    },
    "required": ["approved", "flags"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """\
You are a compliance reviewer at a fee-only fiduciary wealth advisory firm. \
You are given a draft client commentary and the exact computed figures it was \
allowed to use. Check the draft against these rules and flag any violation, \
quoting the offending phrase:

1. Every number in the draft must appear in the computed figures (verbatim or \
a trivial reformat, e.g. 0.273 written as "27.3%"). Flag any figure you cannot \
find in the computed figures — this is the most important check, since it \
catches a fabricated number.
2. No performance guarantees or predictions phrased as certainty ("will \
return", "is expected to grow").
3. No personalized recommendation to buy or sell a specific security — \
rebalancing may only be framed as drift from the stated target allocation.
4. No absolute claims about safety ("guaranteed," "risk-free," "can't lose \
money").

Set approved to true only if you find zero violations. List every violation \
you find in flags, each as one short, specific sentence naming the exact \
phrase and which rule it breaks. If approved, flags must be an empty list.
"""


def compliance_review(paragraphs: list[str], fact_sheet: str) -> list[str]:
    """Review a narrative draft. Returns a list of flags (empty means clean).

    Raises on any API failure — the caller (`agents.ai.ai_narrative`) lets that
    propagate, and `pra.pipeline` falls back to the rule-based narrative rather
    than ship an unreviewed AI draft.
    """
    api_key = anthropic_api_key()
    if not api_key:
        raise RuntimeError("No ANTHROPIC_API_KEY configured.")

    client = anthropic.Anthropic(api_key=api_key)
    draft = "\n\n".join(paragraphs)

    response = client.messages.create(
        model=COMPLIANCE_MODEL,
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        output_config={"format": {"type": "json_schema", "schema": _REVIEW_SCHEMA}},
        messages=[
            {
                "role": "user",
                "content": f"Computed figures:\n\n{fact_sheet}\n\nDraft commentary:\n\n{draft}",
            }
        ],
    )
    text = next(b.text for b in response.content if b.type == "text")
    result = json.loads(text)
    return list(result.get("flags") or [])
