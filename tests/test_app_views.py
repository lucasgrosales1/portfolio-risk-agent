"""Tests for app_views.py helpers that don't need a full Streamlit render."""

from __future__ import annotations

import app_views


def test_md_safe_escapes_every_dollar_sign():
    """Regression guard: a string with two or more bare '$' reaches
    st.markdown as a LaTeX math span (Streamlit pairs them up), rendering
    the text between as raw math source instead of a sentence -- this hit
    real findings text like "$72,000 is offset by $34,000...". _md_safe
    must escape every '$', not just the first."""
    text = "$72,000 is offset by $34,000, leaving $38,000 from a $980,000 portfolio."
    escaped = app_views._md_safe(text)

    assert "$" not in escaped.replace("\\$", "")
    assert escaped.count("\\$") == 4


def test_md_safe_leaves_dollar_free_text_untouched():
    text = "Balanced Growth caps the recommendation at 60% equity."
    assert app_views._md_safe(text) == text
