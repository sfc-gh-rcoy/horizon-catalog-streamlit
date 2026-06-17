"""
Edit Descriptions
Manually edit table and column descriptions
"""

import streamlit as st
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from ui_components import render_header

conn = st.session_state.connection

render_header("Edit Descriptions", "Manually edit table and column descriptions")

with st.sidebar:
    st.markdown("---")
    st.markdown("### 💡 Tips")
    st.info("""
    **Editing Tips:**
    - Changes save directly to Snowflake
    - Use Catalog Manager to sync with catalog
    - Preview AI descriptions before editing
    - Edit in bulk for efficiency
    """)

# Get tables
tables_df = conn.get_tables_and_views()

if tables_df.empty:
    st.warning("No tables found in the current schema")
    st.stop()

table_names = tables_df['TABLE_NAME'].tolist()

# Table selection
st.markdown("### 📊 Select Table to Edit")

# Check if table was pre-selected
default_idx = 0
if hasattr(st.session_state, 'selected_table') and st.session_state.selected_table in table_names:
    default_idx = table_names.index(st.session_state.selected_table)
    # Clear the selection after use
    del st.session_state.selected_table

selected_table = st.selectbox(
    "Choose a table:",
    table_names,
    index=default_idx
)

if selected_table:
    # Get current table info
    table_info = tables_df[tables_df['TABLE_NAME'] == selected_table].iloc[0]
    current_table_desc = table_info.get('DESCRIPTION', '') or ''
    
    st.markdown("---")
    st.markdown(f"### 📋 Table: {selected_table}")
    
    # Display table metadata
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Type", table_info['TABLE_TYPE'])
    
    with col2:
        if 'ROW_COUNT' in table_info and table_info['ROW_COUNT']:
            st.metric("Rows", f"{table_info['ROW_COUNT']:,}")
    
    with col3:
        if 'BYTES' in table_info and table_info['BYTES']:
            size_mb = table_info['BYTES'] / (1024 * 1024)
            st.metric("Size", f"{size_mb:.2f} MB")
    
    # Edit table description
    st.markdown("#### 📝 Table Description")
    
    new_table_desc = st.text_area(
        "Table description:",
        value=current_table_desc,
        height=100,
        key=f"table_desc_{selected_table}",
        help="Describe what this table contains and its business purpose"
    )
    
    # Save button for table
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("💾 Save Table Description", use_container_width=True):
            if conn.update_table_comment(selected_table, new_table_desc):
                st.success(f"✅ Table description saved for {selected_table}!")
                st.rerun()
            else:
                st.error("❌ Failed to save table description")
    
    # Column descriptions
    st.markdown("---")
    st.markdown("#### 📊 Column Descriptions")
    
    # Get columns
    columns_df = conn.get_columns_for_table(selected_table)
    
    if not columns_df.empty:
        st.info(f"📝 Editing descriptions for {len(columns_df)} columns")
        
        # Create a form for bulk editing
        with st.form(f"edit_columns_{selected_table}"):
            edited_columns = {}
            
            # Search/filter
            filter_term = st.text_input("🔍 Filter columns:", placeholder="Type to filter...")
            
            # Filter columns if search term provided
            display_columns = columns_df
            if filter_term:
                display_columns = columns_df[
                    columns_df['COLUMN_NAME'].str.contains(filter_term.upper(), na=False)
                ]
            
            st.markdown(f"**Showing {len(display_columns)} of {len(columns_df)} columns**")
            
            for idx, row in display_columns.iterrows():
                col_name = row['COLUMN_NAME']
                current_desc = row.get('DESCRIPTION', '') or ''
                data_type = row['DATA_TYPE']
                is_nullable = row['IS_NULLABLE']
                
                # Column header with metadata
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{col_name}**")
                with col2:
                    st.caption(f"{data_type} {'NULL' if is_nullable == 'YES' else 'NOT NULL'}")
                
                # Description text area
                edited_columns[col_name] = st.text_area(
                    f"Description for {col_name}:",
                    value=current_desc,
                    height=80,
                    key=f"col_edit_{selected_table}_{col_name}",
                    label_visibility="collapsed",
                    help=f"Describe what {col_name} represents"
                )
                
                st.markdown("---")
            
            # Submit button
            submitted = st.form_submit_button(
                "💾 Save All Column Descriptions",
                use_container_width=True,
                type="primary"
            )
            
            if submitted:
                success_count = 0
                failed_count = 0
                
                with st.spinner("Saving column descriptions..."):
                    for col_name, description in edited_columns.items():
                        if conn.update_column_comment(selected_table, col_name, description):
                            success_count += 1
                        else:
                            failed_count += 1
                
                if failed_count == 0:
                    st.success(f"✅ All {success_count} column descriptions saved successfully!")
                else:
                    st.warning(f"⚠️ Saved {success_count} descriptions, {failed_count} failed")
                
                st.rerun()
    
    else:
        st.info("No columns found for this table")
    
    # Action buttons
    st.markdown("---")
    st.markdown("### 🎯 Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🤖 Generate AI Descriptions", use_container_width=True):
            st.session_state.selected_table = selected_table
            st.switch_page("pages/3_AI_Generator.py")
    
    with col2:
        if st.button("📚 View History", use_container_width=True):
            st.session_state.selected_table = selected_table
            st.switch_page("pages/5_Description_History.py")
    
    with col3:
        if st.button("📊 Browse Tables", use_container_width=True):
            st.switch_page("pages/2_Tables_Browser.py")

# Bulk operations
st.markdown("---")
with st.expander("🔧 Bulk Operations"):
    st.markdown("""
    **For bulk operations across multiple tables:**
    
    - Use the **Catalog Manager** to generate or apply descriptions for all tables
    - Use **GENERATE_ONLY** mode to create descriptions without applying
    - Review and edit in the catalog before applying
    - Use **APPLY_ONLY** mode to apply edited descriptions
    
    This manual editor is best for:
    - Fine-tuning individual descriptions
    - Quick edits to specific tables
    - One-off corrections
    """)
    
    if st.button("📋 Go to Catalog Manager", use_container_width=True):
        st.switch_page("pages/4_Catalog_Manager.py")

