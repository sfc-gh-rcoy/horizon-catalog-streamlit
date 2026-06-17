"""
Description History
View version history and track changes over time
"""

import streamlit as st
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from ui_components import render_header

conn = st.session_state.connection
catalog_ops = st.session_state.catalog_ops

render_header("Description History", "Track versions and changes over time")

with st.sidebar:
    st.markdown("---")
    st.markdown("### 📖 About")
    st.info("""
    View the complete history of description changes including:
    - All versions
    - Who made changes
    - When changes occurred
    - Applied vs pending status
    """)

# Get current context
db, schema = conn.get_current_context()

if not db or not schema:
    st.warning("⚠️ Please select a database and schema")
    st.stop()

# Tabs for different views
tab1, tab2, tab3 = st.tabs(["📋 All Descriptions", "⏳ Pending", "📊 By Table"])

with tab1:
    st.markdown("### 📋 All Catalog Descriptions")
    
    # Filters
    col1, col2 = st.columns([2, 1])
    
    with col1:
        show_current_only = st.checkbox("Show current versions only", value=True)
    
    with col2:
        domain_filter = st.selectbox("Filter by:", ["All", "TABLE", "COLUMN"])
    
    # Get descriptions
    try:
        catalog_df = catalog_ops.get_catalog_descriptions(
            database_name=db,
            schema_name=schema,
            current_only=show_current_only
        )
        
        if not catalog_df.empty:
            # Apply domain filter
            if domain_filter != "All":
                catalog_df = catalog_df[catalog_df['DOMAIN'] == domain_filter]
            
            st.markdown(f"**Found {len(catalog_df)} description(s)**")
            
            # Configure display
            column_config = {
                'DOMAIN': st.column_config.TextColumn('Type', width="small"),
                'NAME': st.column_config.TextColumn('Name', width="medium"),
                'TABLE_NAME': st.column_config.TextColumn('Table', width="medium"),
                'DESCRIPTION': st.column_config.TextColumn('Description', width="large"),
                'DESCRIPTION_VERSION': st.column_config.NumberColumn('Version', format="%d"),
                'IS_CURRENT': st.column_config.CheckboxColumn('Current'),
                'IS_APPLIED_AS_COMMENT': st.column_config.CheckboxColumn('Applied'),
                'GENERATION_TIMESTAMP': st.column_config.DatetimeColumn('Generated'),
                'CREATED_BY': st.column_config.TextColumn('Created By', width="small")
            }
            
            st.dataframe(
                catalog_df,
                use_container_width=True,
                hide_index=True,
                column_config=column_config
            )
        else:
            st.info("No descriptions found in catalog")
    
    except Exception as e:
        st.error(f"Error loading descriptions: {str(e)}")

with tab2:
    st.markdown("### ⏳ Pending Descriptions")
    st.info("Descriptions that have been generated but not yet applied to database objects")
    
    try:
        pending_df = catalog_ops.get_pending_descriptions(db, schema)
        
        if not pending_df.empty:
            st.markdown(f"**{len(pending_df)} pending description(s)**")
            
            column_config = {
                'DOMAIN': st.column_config.TextColumn('Type', width="small"),
                'NAME': st.column_config.TextColumn('Name', width="medium"),
                'TABLE_NAME': st.column_config.TextColumn('Table', width="medium"),
                'DESCRIPTION': st.column_config.TextColumn('Description', width="large"),
                'GENERATION_TIMESTAMP': st.column_config.DatetimeColumn('Generated'),
                'CREATED_BY': st.column_config.TextColumn('By', width="small")
            }
            
            st.dataframe(
                pending_df,
                use_container_width=True,
                hide_index=True,
                column_config=column_config
            )
            
            # Apply button
            st.markdown("---")
            if st.button("📝 Apply All Pending Descriptions", type="primary", use_container_width=True):
                st.info("To apply pending descriptions, use the Catalog Manager with APPLY_ONLY mode")
                if st.button("📋 Go to Catalog Manager"):
                    st.switch_page("pages/4_Catalog_Manager.py")
        else:
            st.success("✅ No pending descriptions - all are applied!")
    
    except Exception as e:
        st.error(f"Error loading pending descriptions: {str(e)}")

with tab3:
    st.markdown("### 📊 Coverage by Table")
    
    try:
        coverage_df = catalog_ops.get_coverage_by_table(db, schema)
        
        if not coverage_df.empty:
            st.markdown(f"**{len(coverage_df)} table(s)**")
            
            column_config = {
                'TABLE_NAME': 'Table Name',
                'TOTAL_COLUMNS': st.column_config.NumberColumn('Total Columns', format="%d"),
                'HAS_TABLE_DESCRIPTION': st.column_config.CheckboxColumn('Has Table Desc'),
                'COLUMNS_DESCRIBED': st.column_config.NumberColumn('Columns Described', format="%d"),
                'COLUMN_COVERAGE_PCT': st.column_config.ProgressColumn(
                    'Coverage',
                    format="%.1f%%",
                    min_value=0,
                    max_value=100
                )
            }
            
            st.dataframe(
                coverage_df,
                use_container_width=True,
                hide_index=True,
                column_config=column_config
            )
        else:
            st.info("No coverage data available")
    
    except Exception as e:
        st.error(f"Error loading coverage: {str(e)}")

# Detailed history lookup
st.markdown("---")
st.markdown("### 🔍 View Detailed History")

col1, col2 = st.columns(2)

with col1:
    tables_df = conn.get_tables_and_views()
    if not tables_df.empty:
        table_names = tables_df['TABLE_NAME'].tolist()
        selected_table = st.selectbox("Select table:", [""] + table_names)

with col2:
    object_type = st.selectbox("Object type:", ["TABLE", "COLUMN"])

if selected_table:
    if object_type == "TABLE":
        # Show table history
        history_df = catalog_ops.get_description_history(
            database_name=db,
            schema_name=schema,
            object_name=selected_table,
            domain="TABLE"
        )
        
        if not history_df.empty:
            st.markdown(f"#### 📋 Version History for {selected_table}")
            
            for idx, row in history_df.iterrows():
                with st.expander(f"Version {row['DESCRIPTION_VERSION']} - {row['GENERATION_TIMESTAMP']} by {row['CREATED_BY']}"):
                    st.markdown(f"**Description:**")
                    st.write(row['DESCRIPTION'])
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"**Current:** {'✅' if row['IS_CURRENT'] else '❌'}")
                    with col2:
                        st.write(f"**Applied:** {'✅' if row['IS_APPLIED_AS_COMMENT'] else '❌'}")
                    with col3:
                        st.write(f"**Source:** {row['GENERATION_SOURCE']}")
        else:
            st.info(f"No history found for {selected_table}")
    
    elif object_type == "COLUMN":
        # Get columns for selected table
        columns_df = conn.get_columns_for_table(selected_table)
        if not columns_df.empty:
            column_names = columns_df['COLUMN_NAME'].tolist()
            selected_column = st.selectbox("Select column:", column_names)
            
            if selected_column:
                history_df = catalog_ops.get_description_history(
                    database_name=db,
                    schema_name=schema,
                    object_name=selected_column,
                    domain="COLUMN"
                )
                
                if not history_df.empty:
                    st.markdown(f"#### 📊 Version History for {selected_table}.{selected_column}")
                    
                    for idx, row in history_df.iterrows():
                        with st.expander(f"Version {row['DESCRIPTION_VERSION']} - {row['GENERATION_TIMESTAMP']}"):
                            st.markdown(f"**Description:**")
                            st.write(row['DESCRIPTION'])
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write(f"**Current:** {'✅' if row['IS_CURRENT'] else '❌'}")
                            with col2:
                                st.write(f"**Applied:** {'✅' if row['IS_APPLIED_AS_COMMENT'] else '❌'}")
                else:
                    st.info(f"No history found for {selected_column}")

# Catalog statistics
st.markdown("---")
st.markdown("### 📈 Catalog Statistics")

try:
    catalog_stats = catalog_ops.get_catalog_statistics()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Entries", catalog_stats.get('TOTAL_ENTRIES', 0))
    
    with col2:
        st.metric("Current Entries", catalog_stats.get('CURRENT_ENTRIES', 0))
    
    with col3:
        st.metric("Applied", catalog_stats.get('APPLIED_ENTRIES', 0))
    
    with col4:
        avg_version = catalog_stats.get('AVG_VERSION', 0)
        st.metric("Avg Version", f"{avg_version:.1f}" if avg_version else "N/A")

except Exception as e:
    st.warning(f"Could not load catalog statistics: {str(e)}")

