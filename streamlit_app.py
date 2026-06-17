"""
Horizon Catalog Description Management
Snowflake Streamlit entry point.
"""

import os
import sys

import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))

from app_bootstrap import ensure_connection, render_database_context_sidebar
from ui_components import apply_custom_styling

st.set_page_config(
    page_title="Horizon Catalog",
    page_icon="🌅",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_custom_styling()
ensure_connection()

with st.sidebar:
    render_database_context_sidebar()

pages = [
    st.Page("pages/1_Overview.py", title="Overview", icon="🏠", default=True),
    st.Page("pages/2_Tables_Browser.py", title="Tables Browser", icon="📊"),
    st.Page("pages/3_AI_Generator.py", title="AI Generator", icon="🤖"),
    st.Page("pages/4_Catalog_Manager.py", title="Catalog Manager", icon="📋"),
    st.Page("pages/5_Description_History.py", title="Description History", icon="📚"),
    st.Page("pages/6_Edit_Descriptions.py", title="Edit Descriptions", icon="✏️"),
]

st.navigation(pages).run()
