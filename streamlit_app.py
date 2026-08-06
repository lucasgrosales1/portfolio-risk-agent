"""Advisor Workbench — Streamlit web app entry point.

A multi-page wealth-management workspace: a branded Home/landing page and a top
navigation bar routing to Dashboard, Portfolio Analysis, Rebalancing, Planning,
Reports, and Settings. This file is deliberately thin — theme and navigation
live in app_ui, the pages live in app_views, and all analytics live in the pra
package. Streamlit Community Cloud runs this file.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the `pra` package importable without installation. Locally the package is
# `pip install -e .`; on Streamlit Community Cloud (which installs only
# requirements.txt) `src/` must be added to the path explicitly. This must run
# before importing app_ui / app_views, which import pra.
_SRC = Path(__file__).parent / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import streamlit as st  # noqa: E402

import app_ui as ui  # noqa: E402
from app_views import PAGES, render_client_invite  # noqa: E402

_FAVICON = Path(__file__).parent / "assets" / "favicon.png"
st.set_page_config(
    page_title="WealthSync Advisors",
    page_icon=str(_FAVICON) if _FAVICON.exists() else "📊",
    layout="wide",
)

ui.inject_theme()

_invite_token = st.query_params.get("invite")

if _invite_token:
    # A client following a link an advisor sent them — takes priority over
    # everything else (the welcome splash, the nav bar): they get a stripped
    # view scoped to that one survey, never the advisor workspace.
    render_client_invite(_invite_token)
elif not st.session_state.get("welcomed", False):
    # First thing a fresh session sees — a one-time splash, not a page. Once
    # dismissed for this session, every subsequent rerun (including nav
    # clicks, which themselves trigger a rerun) skips straight past this.
    ui.welcome_screen()
else:
    active_page = ui.top_nav()

    # Dispatch to the selected page. Unknown keys fall back to Home.
    PAGES.get(active_page, PAGES["Home"])()
