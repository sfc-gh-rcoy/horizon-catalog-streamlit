"""
Snowpark Connection Wrapper for Horizon Catalog
Provides a clean interface for Snowflake Streamlit apps to interact with the database
"""

import streamlit as st
import pandas as pd
from typing import Optional, List, Dict, Any
from snowflake.snowpark.context import get_active_session
from snowflake.snowpark import Session


class HorizonConnection:
    """Wrapper for Snowpark session with Horizon Catalog convenience methods"""
    
    def __init__(self):
        """Initialize with active Snowpark session"""
        try:
            self.session = get_active_session()
            self._init_session_state()
        except Exception as e:
            st.error(f"Failed to get Snowpark session: {str(e)}")
            self.session = None
    
    def _init_session_state(self):
        """Initialize session state variables"""
        if 'current_database' not in st.session_state:
            st.session_state.current_database = self.session.get_current_database()
        if 'current_schema' not in st.session_state:
            st.session_state.current_schema = self.session.get_current_schema()
    
    def test_connection(self) -> bool:
        """Test if connection is working"""
        try:
            result = self.session.sql("SELECT CURRENT_VERSION()").collect()
            return len(result) > 0
        except:
            return False
    
    def execute_query(self, query: str) -> pd.DataFrame:
        """Execute a query and return results as DataFrame"""
        try:
            return self.session.sql(query).to_pandas()
        except Exception as e:
            st.error(f"Query execution failed: {str(e)}")
            return pd.DataFrame()
    
    def execute_procedure(self, proc_name: str, *args) -> Any:
        """Execute a stored procedure and return result"""
        try:
            result = self.session.call(proc_name, *args)
            return result
        except Exception as e:
            st.error(f"Procedure execution failed: {str(e)}")
            return None
    
    def _find_name_column(self, df: pd.DataFrame) -> Optional[str]:
        """Return the column from SHOW results that holds object names."""
        for col in df.columns:
            if "name" in col.lower():
                return col
        return None

    def get_available_databases(self) -> List[str]:
        """Get list of databases available to the user"""
        try:
            df = self.execute_query("SHOW DATABASES")
            if df.empty:
                return []
            col_name = self._find_name_column(df)
            if not col_name:
                st.warning(f"Could not find name column. Available: {list(df.columns)}")
                return []
            return sorted(df[col_name].tolist())
        except Exception as e:
            st.warning(f"Could not fetch databases: {str(e)}")
            return []
    
    def get_available_schemas(self, database: str) -> List[str]:
        """Get list of schemas in database (excludes system schemas)"""
        try:
            query = f"SHOW SCHEMAS IN DATABASE {database}"
            df = self.execute_query(query)
            if not df.empty:
                # Filter out system schemas
                system_schemas = ['INFORMATION_SCHEMA', 'ACCOUNT_USAGE', 
                                'READER_ACCOUNT_USAGE', 'ORGANIZATION_USAGE']
                col_name = self._find_name_column(df)
                if not col_name:
                    return []
                schemas = df[col_name].tolist()
                return sorted([s for s in schemas if s.upper() not in system_schemas])
            return []
        except Exception as e:
            st.warning(f"Could not fetch schemas: {str(e)}")
            return []
    
    def set_context(self, database: str, schema: str) -> bool:
        """Set the current database and schema context"""
        try:
            if database:
                self.session.use_database(database)
                st.session_state.current_database = database
            if schema:
                self.session.use_schema(schema)
                st.session_state.current_schema = schema
            return True
        except Exception as e:
            st.error(f"Failed to set context to {database}.{schema}: {str(e)}")
            return False
    
    def get_current_context(self) -> tuple:
        """Get current database and schema"""
        return (st.session_state.get('current_database'), 
                st.session_state.get('current_schema'))
    
    def get_tables_and_views(self) -> pd.DataFrame:
        """Get all tables and views in current schema"""
        query = """
        SELECT 
            table_name,
            table_type,
            comment as description,
            created as created_date,
            last_altered as last_modified,
            row_count,
            bytes
        FROM information_schema.tables 
        WHERE table_schema = CURRENT_SCHEMA()
        ORDER BY table_name
        """
        return self.execute_query(query)
    
    def get_columns_for_table(self, table_name: str) -> pd.DataFrame:
        """Get all columns for a specific table"""
        query = f"""
        SELECT 
            column_name,
            data_type,
            is_nullable,
            column_default,
            comment as description,
            ordinal_position
        FROM information_schema.columns 
        WHERE table_schema = CURRENT_SCHEMA()
        AND table_name = '{table_name}'
        ORDER BY ordinal_position
        """
        return self.execute_query(query)
    
    def update_table_comment(self, table_name: str, comment: str) -> bool:
        """Update table comment/description"""
        try:
            # Escape single quotes
            comment = comment.replace("'", "''")
            query = f"ALTER TABLE {table_name} SET COMMENT = '{comment}'"
            self.session.sql(query).collect()
            return True
        except Exception as e:
            st.error(f"Failed to update table comment: {str(e)}")
            return False
    
    def update_column_comment(self, table_name: str, column_name: str, comment: str) -> bool:
        """Update column comment/description"""
        try:
            # Escape single quotes
            comment = comment.replace("'", "''")
            query = f"ALTER TABLE {table_name} MODIFY COLUMN {column_name} COMMENT '{comment}'"
            self.session.sql(query).collect()
            return True
        except Exception as e:
            st.error(f"Failed to update column comment: {str(e)}")
            return False
    
    def get_description_statistics(self) -> Dict:
        """Get statistics about table and column descriptions"""
        try:
            # Table statistics
            table_stats_query = """
            SELECT 
                COUNT(*) as total_tables,
                COUNT(CASE WHEN comment IS NOT NULL AND comment != '' THEN 1 END) as tables_with_descriptions
            FROM information_schema.tables 
            WHERE table_schema = CURRENT_SCHEMA()
            """
            table_stats = self.execute_query(table_stats_query)
            
            # Column statistics
            column_stats_query = """
            SELECT 
                COUNT(*) as total_columns,
                COUNT(CASE WHEN comment IS NOT NULL AND comment != '' THEN 1 END) as columns_with_descriptions
            FROM information_schema.columns 
            WHERE table_schema = CURRENT_SCHEMA()
            """
            column_stats = self.execute_query(column_stats_query)
            
            # Recent updates
            recent_updates_query = """
            SELECT 
                table_name,
                table_type,
                last_altered
            FROM information_schema.tables 
            WHERE table_schema = CURRENT_SCHEMA()
            AND last_altered IS NOT NULL
            ORDER BY last_altered DESC
            LIMIT 10
            """
            recent_updates = self.execute_query(recent_updates_query)
            
            return {
                'table_stats': table_stats.iloc[0].to_dict() if not table_stats.empty else {},
                'column_stats': column_stats.iloc[0].to_dict() if not column_stats.empty else {},
                'recent_updates': recent_updates
            }
        except Exception as e:
            st.error(f"Failed to get statistics: {str(e)}")
            return {}


@st.cache_resource
def get_horizon_connection() -> HorizonConnection:
    """Get a cached Horizon connection instance"""
    return HorizonConnection()

