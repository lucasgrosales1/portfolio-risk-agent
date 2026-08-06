"""Smoke tests: every page renders with no exception.

Navigation is driven by st.session_state["page"] (see app_ui.top_nav), so each
page is reached by seeding that key before at.run(), rather than by clicking
through the nav bar. "welcomed" is also seeded so the run lands on the actual
page instead of the one-time welcome splash (see app_ui.welcome_screen) --
without it every case here would just render the splash and technically
still pass, without testing what it claims to. None of the 5 pages call
run_analysis/build_recommendation on initial render -- those only fire on an
explicit button click -- but patch_prices is still applied as a safety net
so this suite stays offline even if that ever changes.
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
    at.session_state["welcomed"] = True
    at.session_state["page"] = page
    at.run()

    assert not at.exception


def test_fresh_session_shows_welcome_screen_not_a_page(patch_prices):
    """A brand-new session (no "welcomed" key at all) must land on the splash,
    not silently skip it -- this is the actual default-state behavior a real
    first-time visitor hits, not just what the other tests seed around."""
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()

    assert not at.exception
    assert "welcomed" not in at.session_state or at.session_state["welcomed"] is not True
    assert any(b.key == "welcome_get_started" for b in at.button)


def test_get_started_button_dismisses_welcome_screen(patch_prices):
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()

    at.button(key="welcome_get_started").click().run()

    assert not at.exception
    assert at.session_state["welcomed"] is True
    assert at.session_state["page"] == "Home"
    assert not any(b.key == "welcome_get_started" for b in at.button)
