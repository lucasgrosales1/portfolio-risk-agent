"""Smoke tests: every page renders with no exception.

Navigation is driven by st.session_state["page"] (see app_ui.top_nav), so each
page is reached by seeding that key before at.run(), rather than by clicking
through the nav bar. None of the 5 pages call run_analysis/build_recommendation
on initial render -- those only fire on an explicit button click -- but
patch_prices is still applied as a safety net so this suite stays offline even
if that ever changes.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = str(Path(__file__).resolve().parent.parent / "streamlit_app.py")

PAGES = ["Home", "Dashboard", "Portfolio Analysis", "Client Survey", "Settings"]


@pytest.mark.parametrize("page", PAGES)
def test_page_renders_without_exception(patch_prices, page):
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.session_state["page"] = page
    at.run()

    assert not at.exception
