"""Advisor Workbench — Streamlit web app entry point.

A multi-page wealth-management workspace: a branded Home/landing page and a top
navigation bar routing to Dashboard, Portfolio Analysis, Rebalancing, Planning,
Reports, and Settings. This file is deliberately thin — theme and navigation
live in app_ui, the pages live in app_views, and all analytics live in the pra
package. Streamlit Community Cloud runs this file.
"""

from __future__ import annotations

import streamlit as st

import app_ui as ui
from app_views import PAGES

st.set_page_config(page_title="WealthSync Advisors", page_icon="📊", layout="wide")

ui.inject_theme()
active_page = ui.top_nav()

# Dispatch to the selected page. Unknown keys fall back to Home.
PAGES.get(active_page, PAGES["Home"])()
