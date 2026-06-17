"""
AI Description Generator
Generate AI-powered descriptions with preview before applying
"""

import streamlit as st
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from ui_components import render_header

conn = st.session_state.connection
catalog_ops = st.session_state.catalog_ops

render_header("AI Description Generator", "Generate intelligent descriptions with preview")

with st.sidebar:
    st.markdown("---")
    st.markdown("### ℹ️ About")
    st.info("""
    This page generates AI descriptions for a single table using Snowflake Cortex.
    
    **Features:**
    - Preview before applying
    - Edit generated descriptions
    - Table and column descriptions
    - Sample data analysis
    """)

# Get tables
tables_df = conn.get_tables_and_views()

if tables_df.empty:
    st.warning("No tables found")
    st.stop()

table_names = tables_df['TABLE_NAME'].tolist()

# Table selection
st.markdown("### 📊 Select Table")

# Check if table was pre-selected from another page
default_idx = 0
if hasattr(st.session_state, 'selected_table') and st.session_state.selected_table in table_names:
    default_idx = table_names.index(st.session_state.selected_table)

selected_table = st.selectbox(
    "Choose a table:",
    table_names,
    index=default_idx
)

# Configuration
st.markdown("### ⚙️ Generation Options")

col1, col2 = st.columns(2)

with col1:
    include_columns = st.checkbox(
        "Generate column descriptions",
        value=True,
        help="Generate descriptions for each column"
    )

with col2:
    use_sample_data = st.checkbox(
        "Use sample data for accuracy",
        value=True,
        help="Analyze actual data values (may increase cost)"
    )

# Generate button
if st.button("🚀 Generate AI Descriptions", type="primary", use_container_width=True):
    with st.spinner(f"🤖 Generating AI descriptions for {selected_table}..."):
        try:
            db, schema = conn.get_current_context()
            
            # Call the generate descriptions procedure for this single table
            result = catalog_ops.generate_descriptions(
                database_name=db,
                schema_name=schema,
                force_regenerate=True,  # Force regenerate for this single table
                include_sample_data=use_sample_data,
                max_parallel_jobs=1  # Single table
            )
            
            if result:
                st.success("✅ Descriptions generated successfully!")
                st.session_state.ai_generation_complete = True
                st.rerun()
            else:
                st.error("❌ Failed to generate descriptions")
        
        except Exception as e:
            st.error(f"Error: {str(e)}")

# Display generated descriptions if available
if hasattr(st.session_state, 'ai_generation_complete') and st.session_state.ai_generation_complete:
    st.markdown("---")
    st.markdown("### 👀 Preview Generated Descriptions")
    
    db, schema = conn.get_current_context()
    
    # Get catalog descriptions for this table
    catalog_df = catalog_ops.get_catalog_descriptions(
        database_name=db,
        schema_name=schema,
        table_name=selected_table,
        current_only=True
    )
    
    if not catalog_df.empty:
        # Table description
        table_desc_df = catalog_df[catalog_df['DOMAIN'] == 'TABLE']
        if not table_desc_df.empty:
            st.markdown("#### 📋 Table Description")
            table_desc = table_desc_df.iloc[0]['DESCRIPTION']
            
            # Editable text area
            edited_table_desc = st.text_area(
                "Table description (editable):",
                value=table_desc,
                height=100,
                key="table_desc_edit"
            )
            
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("💾 Apply Table Description", use_container_width=True):
                    if conn.update_table_comment(selected_table, edited_table_desc):
                        st.success("✅ Table description applied!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to apply")
        
        # Column descriptions
        if include_columns:
            column_desc_df = catalog_df[catalog_df['DOMAIN'] == 'COLUMN']
            if not column_desc_df.empty:
                st.markdown("#### 📊 Column Descriptions")
                st.info(f"📝 {len(column_desc_df)} column descriptions generated")
                
                # Create form for bulk edit
                with st.form("column_descriptions_form"):
                    edited_columns = {}
                    
                    for idx, row in column_desc_df.iterrows():
                        col_name = row['NAME']
                        col_desc = row['DESCRIPTION']
                        
                        st.markdown(f"**{col_name}**")
                        edited_columns[col_name] = st.text_area(
                            f"Description for {col_name}:",
                            value=col_desc,
                            height=80,
                            key=f"col_desc_{col_name}",
                            label_visibility="collapsed"
                        )
                        st.markdown("---")
                    
                    # Submit button
                    submitted = st.form_submit_button(
                        "💾 Apply All Column Descriptions",
                        use_container_width=True
                    )
                    
                    if submitted:
                        success_count = 0
                        for col_name, description in edited_columns.items():
                            if conn.update_column_comment(selected_table, col_name, description):
                                success_count += 1
                        
                        if success_count == len(edited_columns):
                            st.success(f"✅ All {success_count} column descriptions applied!")
                        else:
                            st.warning(f"⚠️ Applied {success_count} of {len(edited_columns)}")
                        
                        # Clear generation flag
                        if hasattr(st.session_state, 'ai_generation_complete'):
                            del st.session_state.ai_generation_complete
                        st.rerun()
        
        # Action buttons
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Generate Again", use_container_width=True):
                if hasattr(st.session_state, 'ai_generation_complete'):
                    del st.session_state.ai_generation_complete
                st.rerun()
        
        with col2:
            if st.button("📊 View in Browser", use_container_width=True):
                st.session_state.selected_table = selected_table
                st.switch_page("pages/2_Tables_Browser.py")
        
        with col3:
            if st.button("📚 View History", use_container_width=True):
                st.session_state.selected_table = selected_table
                st.switch_page("pages/5_Description_History.py")
    
    else:
        st.warning("No descriptions found in catalog")
        if st.button("🔄 Try Again"):
            if hasattr(st.session_state, 'ai_generation_complete'):
                del st.session_state.ai_generation_complete
            st.rerun()

# Tips
st.markdown("---")
with st.expander("💡 Tips for Better Descriptions"):
    st.markdown("""
    **Get the most out of AI generation:**
    
    - ✅ **Use sample data** when tables contain actual business data
    - ✅ **Review and edit** AI-generated descriptions before applying
    - ✅ **Check preview** to see exactly what will be applied
    - ⚠️ **Sample data** may increase Cortex API costs
    - 💡 **Regenerate** if the first attempt isn't perfect
    - 📝 **Manual edits** are saved when you apply descriptions
    """)

