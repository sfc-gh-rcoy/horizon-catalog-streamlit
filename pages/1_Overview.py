"""
Overview Dashboard
Display metrics, coverage, and recent activity
"""

import streamlit as st

session = st.session_state.session

st.markdown("# 🌅 Horizon Catalog")
st.markdown("Monitor your description coverage and activity")
st.markdown("---")

# Get statistics
try:
    # Table statistics
    table_stats_result = session.sql("""
        SELECT 
            COUNT(*) as total_tables,
            COUNT(CASE WHEN comment IS NOT NULL AND comment != '' THEN 1 END) as tables_with_descriptions
        FROM information_schema.tables 
        WHERE table_schema = CURRENT_SCHEMA()
    """).collect()
    
    # Column statistics
    column_stats_result = session.sql("""
        SELECT 
            COUNT(*) as total_columns,
            COUNT(CASE WHEN comment IS NOT NULL AND comment != '' THEN 1 END) as columns_with_descriptions
        FROM information_schema.columns 
        WHERE table_schema = CURRENT_SCHEMA()
    """).collect()
    
    # Top-level metrics
    st.markdown("### 📊 Key Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_tables = table_stats_result[0]['TOTAL_TABLES']
    tables_described = table_stats_result[0]['TABLES_WITH_DESCRIPTIONS']
    total_columns = column_stats_result[0]['TOTAL_COLUMNS']
    columns_described = column_stats_result[0]['COLUMNS_WITH_DESCRIPTIONS']
    
    with col1:
        st.metric("Total Tables", total_tables)
    
    with col2:
        st.metric("Tables Described", tables_described)
    
    with col3:
        st.metric("Total Columns", total_columns)
    
    with col4:
        st.metric("Columns Described", columns_described)
    
    st.markdown("---")
    
    # Coverage section
    st.markdown("### 📈 Description Coverage")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Table Coverage")
        if total_tables > 0:
            table_coverage = (tables_described / total_tables) * 100
            st.progress(table_coverage / 100, text=f"{table_coverage:.1f}% of tables have descriptions")
        else:
            st.info("No tables found")
    
    with col2:
        st.markdown("#### Column Coverage")
        if total_columns > 0:
            column_coverage = (columns_described / total_columns) * 100
            st.progress(column_coverage / 100, text=f"{column_coverage:.1f}% of columns have descriptions")
        else:
            st.info("No columns found")
    
    # Recent activity
    st.markdown("---")
    st.markdown("### 📅 Recent Activity")
    
    recent_result = session.sql("""
        SELECT 
            table_name,
            table_type,
            last_altered
        FROM information_schema.tables 
        WHERE table_schema = CURRENT_SCHEMA()
        AND last_altered IS NOT NULL
        ORDER BY last_altered DESC
        LIMIT 10
    """).to_pandas()
    
    if not recent_result.empty:
        st.dataframe(
            recent_result,
            use_container_width=True,
            hide_index=True,
            column_config={
                'TABLE_NAME': 'Table',
                'TABLE_TYPE': 'Type',
                'LAST_ALTERED': st.column_config.DatetimeColumn('Last Modified')
            }
        )
    else:
        st.info("No recent activity")

except Exception as e:
    st.error(f"Error loading statistics: {str(e)}")
    st.exception(e)

# Quick actions
st.markdown("---")
st.markdown("### ⚡ Quick Actions")

col1, col2 = st.columns(2)

with col1:
    if st.button("📊 Browse Tables", use_container_width=True, type="primary"):
        st.switch_page("pages/2_Tables_Browser.py")

with col2:
    if st.button("✏️ Edit Descriptions", use_container_width=True):
        st.switch_page("pages/6_Edit_Descriptions.py")
