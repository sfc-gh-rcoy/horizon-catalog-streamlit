"""
Catalog Manager
Multi-mode batch operations with preview capability
"""

import streamlit as st
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from ui_components import (
    render_header,
    render_operation_mode_selector,
    render_generation_options,
    render_execution_summary,
)

conn = st.session_state.connection
catalog_ops = st.session_state.catalog_ops

render_header("Catalog Manager", "Batch operations with multi-mode support")

with st.sidebar:
    st.markdown("---")
    st.markdown("### 📖 Operation Modes")
    st.markdown("""
    **GENERATE_ONLY**
    - Create descriptions
    - Store in catalog
    - Don't apply to objects
    
    **APPLY_ONLY**
    - Use existing catalog
    - Apply to objects
    - No AI generation
    
    **FULL_SYNC**
    - Generate descriptions
    - Apply immediately
    - One-step process
    
    **CHECK_ONLY** 👀
    - Preview mode
    - See what would change
    - No modifications
    """)

# Get current context
db, schema = conn.get_current_context()

if not db or not schema:
    st.warning("⚠️ Please select a database and schema from the sidebar")
    st.stop()

# Display current context
st.info(f"📍 Operating on: **{db}.{schema}**")

# Operation mode selector
operation_mode = render_operation_mode_selector(default_mode="CHECK_ONLY")

# Generation options
options = render_generation_options()

# Preview button for CHECK_ONLY
if operation_mode == "CHECK_ONLY":
    st.markdown("---")
    st.markdown("### 👀 Preview Mode")
    st.info("""
    **Preview Mode** will show you what changes would be made without actually applying them.
    This is perfect for understanding the impact before committing.
    """)

# Execute button
st.markdown("---")

button_labels = {
    "GENERATE_ONLY": "🤖 Generate Descriptions",
    "APPLY_ONLY": "📝 Apply Descriptions",
    "FULL_SYNC": "🔄 Generate & Apply",
    "CHECK_ONLY": "👀 Preview Changes"
}

button_label = button_labels.get(operation_mode, "▶️ Execute")

if st.button(button_label, type="primary", use_container_width=True):
    with st.spinner(f"⏳ Executing {operation_mode} operation..."):
        try:
            result = catalog_ops.manage_catalog(
                database_name=db,
                schema_name=schema,
                operation_mode=operation_mode,
                force_regenerate=options['force_regenerate'],
                force_apply_comments=options['force_apply_comments'],
                include_sample_data=options['include_sample_data'],
                max_parallel_jobs=options['max_parallel_jobs'],
                dry_run=options['dry_run']
            )
            
            if result:
                st.session_state.last_execution_result = result
                st.session_state.last_operation_mode = operation_mode
                st.rerun()
            else:
                st.error("❌ Operation failed - no result returned")
        
        except Exception as e:
            st.error(f"❌ Operation failed: {str(e)}")
            st.exception(e)

# Display results if available
if hasattr(st.session_state, 'last_execution_result'):
    st.markdown("---")
    
    operation = st.session_state.last_operation_mode
    
    if operation == "CHECK_ONLY":
        st.markdown("### 👀 Preview Results")
        st.info("These are the changes that **would** be made:")
    else:
        st.markdown("### ✅ Execution Results")
    
    render_execution_summary(st.session_state.last_execution_result)
    
    # Action buttons based on mode
    if operation == "CHECK_ONLY":
        st.markdown("---")
        st.markdown("### 🎯 Next Steps")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Apply Changes (FULL_SYNC)", use_container_width=True):
                # Clear result and switch to FULL_SYNC
                del st.session_state.last_execution_result
                st.rerun()
        
        with col2:
            if st.button("🤖 Just Generate (GENERATE_ONLY)", use_container_width=True):
                del st.session_state.last_execution_result
                st.rerun()
        
        with col3:
            if st.button("🗑️ Clear Results", use_container_width=True):
                del st.session_state.last_execution_result
                if hasattr(st.session_state, 'last_operation_mode'):
                    del st.session_state.last_operation_mode
                st.rerun()
    
    elif operation in ["GENERATE_ONLY", "FULL_SYNC"]:
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📚 View Catalog", use_container_width=True):
                st.switch_page("pages/5_Description_History.py")
        
        with col2:
            if st.button("📊 Browse Tables", use_container_width=True):
                st.switch_page("pages/2_Tables_Browser.py")
        
        with col3:
            if st.button("🗑️ Clear Results", use_container_width=True):
                del st.session_state.last_execution_result
                if hasattr(st.session_state, 'last_operation_mode'):
                    del st.session_state.last_operation_mode
                st.rerun()

# Coverage information
st.markdown("---")
st.markdown("### 📊 Current Coverage")

try:
    coverage_df = catalog_ops.get_coverage_by_table(db, schema)
    
    if not coverage_df.empty:
        st.dataframe(
            coverage_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                'TABLE_NAME': 'Table',
                'TOTAL_COLUMNS': st.column_config.NumberColumn('Total Columns', format="%d"),
                'HAS_TABLE_DESCRIPTION': st.column_config.CheckboxColumn('Has Table Desc'),
                'COLUMNS_DESCRIBED': st.column_config.NumberColumn('Columns Described', format="%d"),
                'COLUMN_COVERAGE_PCT': st.column_config.ProgressColumn(
                    'Column Coverage',
                    format="%.1f%%",
                    min_value=0,
                    max_value=100
                )
            }
        )
    else:
        st.info("No coverage data available")

except Exception as e:
    st.warning(f"Could not load coverage data: {str(e)}")

# Tips
st.markdown("---")
with st.expander("💡 Best Practices"):
    st.markdown("""
    **Recommended Workflow:**
    
    1. **👀 CHECK_ONLY** - Preview what will change
    2. **🤖 GENERATE_ONLY** - Generate and store in catalog
    3. **✏️ Review & Edit** - Use Edit Descriptions page to refine
    4. **📝 APPLY_ONLY** - Apply approved descriptions to objects
    
    **Or use:**
    - **🔄 FULL_SYNC** - If you trust the AI output completely
    
    **Cost Tips:**
    - Turn off "Use sample data" for faster, cheaper generation
    - Use "Force regenerate" sparingly to avoid duplicate API calls
    - Preview first to understand scope
    """)

