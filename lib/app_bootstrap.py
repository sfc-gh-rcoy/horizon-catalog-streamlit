"""Shared app initialization and sidebar context for all pages."""

import streamlit as st

from catalog_operations import CatalogOperations
from snowpark_connection import get_horizon_connection


def init_app():
    """Initialize shared session state for all pages."""
    if "connection" not in st.session_state:
        st.session_state.connection = get_horizon_connection()
    if "catalog_ops" not in st.session_state and st.session_state.connection:
        st.session_state.catalog_ops = CatalogOperations(st.session_state.connection)
    if st.session_state.connection and st.session_state.connection.session:
        st.session_state.session = st.session_state.connection.session


def ensure_connection():
    """Stop the app if Snowflake session is unavailable."""
    init_app()
    if not st.session_state.connection or not st.session_state.connection.test_connection():
        st.error("Failed to connect to Snowflake. Run this app inside Snowflake Streamlit.")
        st.stop()


def _find_name_column(df):
    for col in df.columns:
        if "name" in col.lower():
            return col
    return None


def render_database_context_sidebar():
    """Render database/schema selectors shared across all pages."""
    session = st.session_state.session

    st.markdown("### 📍 Database Context")

    if "selected_database" not in st.session_state:
        st.session_state.selected_database = session.get_current_database()
    if "selected_schema" not in st.session_state:
        st.session_state.selected_schema = session.get_current_schema()

    try:
        db_df = session.sql("SHOW DATABASES").to_pandas()
        db_col = _find_name_column(db_df)
        if not db_col:
            raise ValueError(f"Could not find name column. Available: {list(db_df.columns)}")

        databases = sorted(db_df[db_col].tolist())
        selected_db = st.selectbox(
            "Database:",
            databases,
            index=(
                databases.index(st.session_state.selected_database)
                if st.session_state.selected_database in databases
                else 0
            ),
            key="database_selector",
        )

        schema_df = session.sql(f"SHOW SCHEMAS IN DATABASE {selected_db}").to_pandas()
        schema_col = _find_name_column(schema_df)
        if not schema_col:
            raise ValueError(
                f"Could not find schema name column. Available: {list(schema_df.columns)}"
            )

        system_schemas = ["INFORMATION_SCHEMA", "ACCOUNT_USAGE"]
        schemas = sorted(
            s for s in schema_df[schema_col].tolist() if s not in system_schemas
        )

        schema_index = 0
        if st.session_state.selected_schema in schemas:
            schema_index = schemas.index(st.session_state.selected_schema)

        selected_schema = st.selectbox(
            "Schema:",
            schemas,
            index=schema_index,
            key="schema_selector",
        )

        context_changed = False
        if selected_db != st.session_state.selected_database:
            st.session_state.selected_database = selected_db
            context_changed = True
        if selected_schema != st.session_state.selected_schema:
            st.session_state.selected_schema = selected_schema
            context_changed = True

        if context_changed:
            session.use_database(st.session_state.selected_database)
            session.use_schema(st.session_state.selected_schema)
            st.session_state.connection.set_context(
                st.session_state.selected_database,
                st.session_state.selected_schema,
            )
            st.success(
                f"Switched to {st.session_state.selected_database}.{st.session_state.selected_schema}"
            )
            st.rerun()

        st.caption(
            f"Current: {st.session_state.selected_database}.{st.session_state.selected_schema}"
        )

    except Exception as e:
        st.error(f"Context error: {str(e)}")
        st.caption(
            f"Using: {st.session_state.selected_database}.{st.session_state.selected_schema}"
        )
