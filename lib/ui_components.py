"""
UI Components for Horizon Catalog
Reusable widgets and styling
"""

import streamlit as st
import pandas as pd
from typing import Optional, List, Dict


# Custom CSS for beautiful styling
CUSTOM_CSS = """
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f4e79;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border-left: 4px solid #4CAF50;
    }
    .success-message {
        padding: 1rem;
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        border-radius: 0.25rem;
        margin: 1rem 0;
    }
    .warning-message {
        padding: 1rem;
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        border-radius: 0.25rem;
        margin: 1rem 0;
    }
    .info-message {
        padding: 1rem;
        background-color: #d1ecf1;
        border-left: 4px solid #17a2b8;
        border-radius: 0.25rem;
        margin: 1rem 0;
    }
    .error-message {
        padding: 1rem;
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
        border-radius: 0.25rem;
        margin: 1rem 0;
    }
    .stat-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
    .coverage-bar {
        background-color: #e0e0e0;
        border-radius: 10px;
        overflow: hidden;
        height: 20px;
        margin: 0.5rem 0;
    }
    .coverage-fill {
        background: linear-gradient(90deg, #4CAF50 0%, #8BC34A 100%);
        height: 100%;
        transition: width 0.3s ease;
    }
    .table-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.875rem;
        font-weight: 500;
    }
    .badge-table {
        background-color: #e3f2fd;
        color: #1976d2;
    }
    .badge-view {
        background-color: #f3e5f5;
        color: #7b1fa2;
    }
    .badge-applied {
        background-color: #e8f5e9;
        color: #2e7d32;
    }
    .badge-pending {
        background-color: #fff3e0;
        color: #f57c00;
    }
</style>
"""


def apply_custom_styling():
    """Apply custom CSS styling to the app"""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_header(title: str, subtitle: str = ""):
    """Render a styled header"""
    st.markdown(f'<h1 class="main-header">🌅 {title}</h1>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<p class="sub-header">{subtitle}</p>', unsafe_allow_html=True)


def render_metric_card(label: str, value: str, icon: str = "📊"):
    """Render a metric card"""
    st.markdown(f"""
    <div class="metric-card">
        <div style="font-size: 2rem;">{icon}</div>
        <div style="font-size: 2rem; font-weight: bold; margin: 0.5rem 0;">{value}</div>
        <div style="color: #666;">{label}</div>
    </div>
    """, unsafe_allow_html=True)


def render_coverage_bar(percentage: float, label: str = "Coverage"):
    """Render a coverage progress bar"""
    color = "#4CAF50" if percentage >= 75 else "#FFC107" if percentage >= 50 else "#FF5722"
    st.markdown(f"""
    <div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
            <span>{label}</span>
            <span style="font-weight: bold;">{percentage:.1f}%</span>
        </div>
        <div class="coverage-bar">
            <div class="coverage-fill" style="width: {percentage}%; background: {color};"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_success_message(message: str):
    """Render a success message"""
    st.markdown(f'<div class="success-message">✅ {message}</div>', unsafe_allow_html=True)


def render_warning_message(message: str):
    """Render a warning message"""
    st.markdown(f'<div class="warning-message">⚠️ {message}</div>', unsafe_allow_html=True)


def render_info_message(message: str):
    """Render an info message"""
    st.markdown(f'<div class="info-message">ℹ️ {message}</div>', unsafe_allow_html=True)


def render_error_message(message: str):
    """Render an error message"""
    st.markdown(f'<div class="error-message">❌ {message}</div>', unsafe_allow_html=True)


def render_stats_grid(stats: List[Dict[str, str]]):
    """Render a grid of statistics"""
    cols = st.columns(len(stats))
    for col, stat in zip(cols, stats):
        with col:
            st.markdown(f"""
            <div class="stat-box">
                <div style="font-size: 2.5rem;">{stat.get('value', '0')}</div>
                <div style="font-size: 0.875rem; opacity: 0.9;">{stat.get('label', '')}</div>
            </div>
            """, unsafe_allow_html=True)


def render_context_selector(connection):
    """Render database and schema selector in sidebar"""
    with st.sidebar:
        st.markdown("### 🎯 Context")
        
        # Get available databases and schemas
        databases = connection.get_available_databases()
        
        if not databases:
            st.warning("No databases available")
            return False
        
        # Database selection
        current_db, current_schema = connection.get_current_context()
        
        db_index = 0
        if current_db and current_db in databases:
            db_index = databases.index(current_db)
        
        selected_db = st.selectbox(
            "Database:",
            databases,
            index=db_index,
            key="database_selector"
        )
        
        # Schema selection
        schemas = connection.get_available_schemas(selected_db)
        
        if not schemas:
            st.warning(f"No schemas available in {selected_db}")
            return False
        
        schema_index = 0
        if current_schema and current_schema in schemas:
            schema_index = schemas.index(current_schema)
        
        selected_schema = st.selectbox(
            "Schema:",
            schemas,
            index=schema_index,
            key="schema_selector"
        )
        
        # Update context if changed
        if selected_db != current_db or selected_schema != current_schema:
            if connection.set_context(selected_db, selected_schema):
                st.success(f"✅ Context: {selected_db}.{selected_schema}")
                st.rerun()
        
        st.caption(f"Current: {selected_db}.{selected_schema}")
        return True


def render_operation_mode_selector(default_mode: str = "FULL_SYNC") -> str:
    """Render operation mode selector with descriptions"""
    st.markdown("### ⚙️ Operation Mode")
    
    modes = {
        "GENERATE_ONLY": {
            "icon": "🤖",
            "description": "Generate AI descriptions and store in catalog only"
        },
        "APPLY_ONLY": {
            "icon": "📝",
            "description": "Apply existing catalog descriptions to database objects"
        },
        "FULL_SYNC": {
            "icon": "🔄",
            "description": "Generate descriptions AND apply them in one operation"
        },
        "CHECK_ONLY": {
            "icon": "👀",
            "description": "Preview what changes would be made (no modifications)"
        }
    }
    
    # Create radio options with icons
    mode_options = [f"{v['icon']} {k}" for k, v in modes.items()]
    mode_keys = list(modes.keys())
    
    default_index = mode_keys.index(default_mode) if default_mode in mode_keys else 0
    
    selected = st.radio(
        "Choose operation mode:",
        mode_options,
        index=default_index,
        help="Select how you want to manage descriptions"
    )
    
    # Extract the actual mode key
    selected_mode = selected.split(" ", 1)[1]
    
    # Show description for selected mode
    st.info(f"ℹ️ {modes[selected_mode]['description']}")
    
    return selected_mode


def render_generation_options() -> Dict[str, any]:
    """Render generation options and return configuration"""
    st.markdown("### 🎛️ Generation Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        include_sample_data = st.checkbox(
            "Use sample data",
            value=True,
            help="Analyze actual data for more accurate descriptions (may increase cost)"
        )
        
        force_regenerate = st.checkbox(
            "Force regenerate",
            value=False,
            help="Regenerate descriptions even if they already exist"
        )
    
    with col2:
        force_apply = st.checkbox(
            "Force apply comments",
            value=False,
            help="Overwrite existing comments on database objects"
        )
        
        dry_run = st.checkbox(
            "Dry run",
            value=False,
            help="Preview changes without executing them"
        )
    
    max_parallel_jobs = st.slider(
        "Max parallel jobs",
        min_value=1,
        max_value=8,
        value=4,
        help="Number of parallel threads for processing"
    )
    
    return {
        'include_sample_data': include_sample_data,
        'force_regenerate': force_regenerate,
        'force_apply_comments': force_apply,
        'dry_run': dry_run,
        'max_parallel_jobs': max_parallel_jobs
    }


def render_table_with_descriptions(df: pd.DataFrame, 
                                   show_description: bool = True,
                                   selectable: bool = False):
    """Render a table with proper column configuration"""
    if df.empty:
        st.info("No data to display")
        return None
    
    column_config = {}
    
    if 'TABLE_NAME' in df.columns:
        column_config['TABLE_NAME'] = st.column_config.TextColumn("Table", width="medium")
    
    if 'TABLE_TYPE' in df.columns:
        column_config['TABLE_TYPE'] = st.column_config.TextColumn("Type", width="small")
    
    if show_description and 'DESCRIPTION' in df.columns:
        column_config['DESCRIPTION'] = st.column_config.TextColumn("Description", width="large")
    
    if 'CREATED_DATE' in df.columns:
        column_config['CREATED_DATE'] = st.column_config.DatetimeColumn("Created", width="medium")
    
    if 'LAST_MODIFIED' in df.columns:
        column_config['LAST_MODIFIED'] = st.column_config.DatetimeColumn("Modified", width="medium")
    
    if selectable:
        return st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config=column_config,
            on_select="rerun",
            selection_mode="single-row"
        )
    else:
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config=column_config
        )
        return None


def render_execution_summary(result: str):
    """Render execution summary in a nice format"""
    if not result:
        st.error("No result returned")
        return
    
    # Parse the result
    lines = result.strip().split('\n')
    
    st.markdown("### 📊 Execution Summary")
    
    # Create an expander for full details
    with st.expander("View Full Details", expanded=True):
        st.code(result, language=None)
    
    # Extract key metrics if available
    for line in lines:
        if 'successful' in line.lower():
            st.success(line)
        elif 'failed' in line.lower() and 'failed: 0' not in line.lower():
            st.error(line)
        elif 'error' in line.lower():
            st.error(line)

