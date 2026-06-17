"""
Horizon Catalog Operations
Wrappers for calling Horizon Catalog stored procedures
"""

import streamlit as st
import pandas as pd
from typing import Optional, Dict, List

from config import CATALOG_TABLE, GENERATE_DESCRIPTIONS_PROC, CATALOG_MANAGER_PROC


class CatalogOperations:
    """Operations for Horizon Catalog procedures"""
    
    def __init__(self, connection):
        """Initialize with Horizon connection"""
        self.conn = connection
        self.session = connection.session
    
    def generate_descriptions(self, 
                            database_name: str,
                            schema_name: str,
                            catalog_table: str = CATALOG_TABLE,
                            force_regenerate: bool = False,
                            include_sample_data: bool = True,
                            max_parallel_jobs: Optional[int] = None) -> str:
        """
        Call HORIZON_CATALOG_GENERATE_DESCRIPTIONS procedure
        
        Returns: Summary string of operation results
        """
        try:
            result = self.conn.execute_procedure(
                GENERATE_DESCRIPTIONS_PROC,
                database_name,
                schema_name,
                catalog_table,
                force_regenerate,
                include_sample_data,
                max_parallel_jobs
            )
            return result
        except Exception as e:
            st.error(f"Failed to generate descriptions: {str(e)}")
            return None
    
    def manage_catalog(self,
                      database_name: str,
                      schema_name: str,
                      operation_mode: str = 'FULL_SYNC',
                      catalog_table: str = CATALOG_TABLE,
                      force_regenerate: bool = False,
                      force_apply_comments: bool = False,
                      include_sample_data: bool = True,
                      max_parallel_jobs: Optional[int] = None,
                      dry_run: bool = False) -> str:
        """
        Call HORIZON_CATALOG_MANAGER procedure
        
        Operation modes:
        - GENERATE_ONLY: Create descriptions and store in catalog
        - APPLY_ONLY: Apply existing catalog descriptions to objects
        - FULL_SYNC: Generate and apply in one operation
        - CHECK_ONLY: Preview what would change
        
        Returns: Summary string of operation results
        """
        try:
            result = self.conn.execute_procedure(
                CATALOG_MANAGER_PROC,
                database_name,
                schema_name,
                operation_mode,
                catalog_table,
                force_regenerate,
                force_apply_comments,
                include_sample_data,
                max_parallel_jobs,
                dry_run
            )
            return result
        except Exception as e:
            st.error(f"Failed to execute catalog manager: {str(e)}")
            return None
    
    def get_catalog_descriptions(self, 
                               database_name: Optional[str] = None,
                               schema_name: Optional[str] = None,
                               table_name: Optional[str] = None,
                               current_only: bool = True) -> pd.DataFrame:
        """
        Query horizon_catalog_descriptions table
        
        Args:
            database_name: Filter by database (None = no filter)
            schema_name: Filter by schema (None = no filter)
            table_name: Filter by table (None = no filter)
            current_only: Only return current descriptions
        
        Returns: DataFrame of catalog descriptions
        """
        try:
            query = f"""
            SELECT 
                id,
                domain,
                name,
                database_name,
                schema_name,
                table_name,
                description,
                description_version,
                is_current,
                is_applied_as_comment,
                generation_timestamp,
                applied_timestamp,
                created_by,
                notes
            FROM {CATALOG_TABLE}
            WHERE 1=1
            """
            
            if database_name:
                query += f" AND database_name = '{database_name}'"
            if schema_name:
                query += f" AND schema_name = '{schema_name}'"
            if table_name:
                query += f" AND table_name = '{table_name}'"
            if current_only:
                query += " AND is_current = TRUE"
            
            query += " ORDER BY generation_timestamp DESC"
            
            return self.conn.execute_query(query)
        except Exception as e:
            st.error(f"Failed to query catalog: {str(e)}")
            return pd.DataFrame()
    
    def get_catalog_statistics(self) -> Dict:
        """Get statistics about catalog contents"""
        try:
            query = f"""
            SELECT 
                COUNT(*) as total_entries,
                COUNT(CASE WHEN is_current = TRUE THEN 1 END) as current_entries,
                COUNT(CASE WHEN is_applied_as_comment = TRUE THEN 1 END) as applied_entries,
                COUNT(DISTINCT database_name || '.' || schema_name) as schemas_covered,
                COUNT(DISTINCT CASE WHEN domain = 'TABLE' THEN name END) as tables_described,
                COUNT(DISTINCT CASE WHEN domain = 'COLUMN' THEN table_name END) as tables_with_column_desc,
                AVG(description_version) as avg_version,
                MAX(generation_timestamp) as last_generation
            FROM {CATALOG_TABLE}
            """
            
            df = self.conn.execute_query(query)
            return df.iloc[0].to_dict() if not df.empty else {}
        except Exception as e:
            st.error(f"Failed to get catalog statistics: {str(e)}")
            return {}
    
    def get_description_history(self,
                              database_name: str,
                              schema_name: str,
                              object_name: str,
                              domain: str = 'TABLE') -> pd.DataFrame:
        """
        Get version history for a specific object
        
        Args:
            database_name: Database name
            schema_name: Schema name
            object_name: Object name (table or column)
            domain: 'TABLE' or 'COLUMN'
        
        Returns: DataFrame of all versions
        """
        try:
            query = f"""
            SELECT 
                id,
                domain,
                name,
                description,
                description_version,
                is_current,
                is_applied_as_comment,
                generation_timestamp,
                applied_timestamp,
                created_by,
                generation_source,
                notes
            FROM {CATALOG_TABLE}
            WHERE database_name = '{database_name}'
              AND schema_name = '{schema_name}'
              AND name = '{object_name}'
              AND domain = '{domain}'
            ORDER BY description_version DESC
            """
            
            return self.conn.execute_query(query)
        except Exception as e:
            st.error(f"Failed to get description history: {str(e)}")
            return pd.DataFrame()
    
    def get_pending_descriptions(self,
                               database_name: Optional[str] = None,
                               schema_name: Optional[str] = None) -> pd.DataFrame:
        """Get descriptions that haven't been applied yet"""
        try:
            query = f"""
            SELECT 
                domain,
                name,
                database_name,
                schema_name,
                table_name,
                description,
                generation_timestamp,
                created_by
            FROM {CATALOG_TABLE}
            WHERE is_current = TRUE
              AND is_applied_as_comment = FALSE
            """
            
            if database_name:
                query += f" AND database_name = '{database_name}'"
            if schema_name:
                query += f" AND schema_name = '{schema_name}'"
            
            query += " ORDER BY generation_timestamp DESC"
            
            return self.conn.execute_query(query)
        except Exception as e:
            st.error(f"Failed to get pending descriptions: {str(e)}")
            return pd.DataFrame()
    
    def get_coverage_by_table(self,
                             database_name: str,
                             schema_name: str) -> pd.DataFrame:
        """
        Get coverage statistics by table
        
        Returns: DataFrame with table-level coverage info
        """
        try:
            query = f"""
            WITH table_info AS (
                SELECT 
                    table_name,
                    COUNT(*) as total_columns
                FROM information_schema.columns
                WHERE table_schema = '{schema_name}'
                  AND table_catalog = '{database_name}'
                GROUP BY table_name
            ),
            catalog_info AS (
                SELECT 
                    table_name,
                    COUNT(CASE WHEN domain = 'TABLE' THEN 1 END) as has_table_desc,
                    COUNT(CASE WHEN domain = 'COLUMN' THEN 1 END) as columns_with_desc
                FROM {CATALOG_TABLE}
                WHERE database_name = '{database_name}'
                  AND schema_name = '{schema_name}'
                  AND is_current = TRUE
                GROUP BY table_name
            )
            SELECT 
                ti.table_name,
                ti.total_columns,
                COALESCE(ci.has_table_desc, 0) > 0 as has_table_description,
                COALESCE(ci.columns_with_desc, 0) as columns_described,
                ROUND(COALESCE(ci.columns_with_desc, 0) * 100.0 / ti.total_columns, 1) as column_coverage_pct
            FROM table_info ti
            LEFT JOIN catalog_info ci ON ti.table_name = ci.table_name
            ORDER BY ti.table_name
            """
            
            return self.conn.execute_query(query)
        except Exception as e:
            st.error(f"Failed to get coverage by table: {str(e)}")
            return pd.DataFrame()

