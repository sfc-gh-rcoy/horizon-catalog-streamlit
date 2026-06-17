"""
Tables & Views Browser
Explore tables, views, and their descriptions
"""

import streamlit as st

session = st.session_state.session

st.markdown("# 📊 Tables & Views Browser")
st.markdown("Explore your database objects and descriptions")
st.markdown("---")

# Get tables and views
try:
    tables_result = session.sql("""
        SELECT 
            table_name,
            table_type,
            comment as description,
            created,
            last_altered,
            row_count,
            bytes
        FROM information_schema.tables 
        WHERE table_schema = CURRENT_SCHEMA()
        ORDER BY table_name
    """).to_pandas()
    
    if tables_result.empty:
        st.warning("No tables or views found in the current schema")
        st.stop()
    
    # Filters
    st.markdown("### 🔍 Filters")
    col1, col2 = st.columns([2, 1])
    
    with col1:
        search_term = st.text_input(
            "Search tables:",
            placeholder="Enter table name...",
            label_visibility="collapsed"
        )
    
    with col2:
        table_type_filter = st.selectbox(
            "Type:",
            ["All", "BASE TABLE", "VIEW"],
            label_visibility="collapsed"
        )
    
    # Apply filters
    filtered_df = tables_result.copy()
    
    if search_term:
        filtered_df = filtered_df[
            filtered_df['TABLE_NAME'].str.contains(search_term.upper(), na=False)
        ]
    
    if table_type_filter != "All":
        filtered_df = filtered_df[filtered_df['TABLE_TYPE'] == table_type_filter]
    
    # Display count
    st.markdown(f"**Found {len(filtered_df)} of {len(tables_result)} objects**")
    
    # Display tables
    st.markdown("---")
    
    # Configure columns
    column_config = {
        'TABLE_NAME': st.column_config.TextColumn("Table Name", width="medium"),
        'TABLE_TYPE': st.column_config.TextColumn("Type", width="small"),
        'DESCRIPTION': st.column_config.TextColumn("Description", width="large"),
        'ROW_COUNT': st.column_config.NumberColumn("Rows", format="%d"),
        'BYTES': st.column_config.NumberColumn("Size (bytes)", format="%d"),
        'CREATED': st.column_config.DatetimeColumn("Created"),
        'LAST_ALTERED': st.column_config.DatetimeColumn("Last Modified")
    }
    
    # Display with selection
    event = st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        column_config=column_config,
        on_select="rerun",
        selection_mode="single-row"
    )
    
    # Show table details if selected
    if event and event.selection and event.selection.rows:
        selected_idx = event.selection.rows[0]
        selected_table = filtered_df.iloc[selected_idx]['TABLE_NAME']
        
        st.markdown("---")
        st.markdown(f"### 📋 Details: {selected_table}")
        
        # Get columns
        columns_result = session.sql(f"""
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default,
                comment as description,
                ordinal_position
            FROM information_schema.columns 
            WHERE table_schema = CURRENT_SCHEMA()
            AND table_name = '{selected_table}'
            ORDER BY ordinal_position
        """).to_pandas()
        
        if not columns_result.empty:
            st.markdown(f"**{len(columns_result)} columns**")
            
            column_config = {
                'COLUMN_NAME': st.column_config.TextColumn("Column", width="medium"),
                'DATA_TYPE': st.column_config.TextColumn("Data Type", width="medium"),
                'IS_NULLABLE': st.column_config.TextColumn("Nullable", width="small"),
                'DESCRIPTION': st.column_config.TextColumn("Description", width="large")
            }
            
            st.dataframe(
                columns_result[['COLUMN_NAME', 'DATA_TYPE', 'IS_NULLABLE', 'DESCRIPTION']],
                use_container_width=True,
                hide_index=True,
                column_config=column_config
            )
            
            # Show description status
            st.markdown("#### 📊 Description Coverage")
            total_cols = len(columns_result)
            described_cols = len(columns_result[columns_result['DESCRIPTION'].notna() & (columns_result['DESCRIPTION'] != '')])
            coverage = (described_cols / total_cols * 100) if total_cols > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Columns", total_cols)
            with col2:
                st.metric("Described", described_cols)
            with col3:
                st.metric("Coverage", f"{coverage:.1f}%")
        else:
            st.info("No columns found for this table")

except Exception as e:
    st.error(f"Error loading tables: {str(e)}")
    st.exception(e)
