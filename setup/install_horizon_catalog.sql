-- ============================================================================
-- HORIZON CATALOG COMPLETE INSTALLATION
-- ============================================================================
-- This file creates the complete Horizon Catalog system in one script:
-- 1. Database, schema, and catalog table with clustering
-- 2. Current descriptions view for easy querying
-- 3. HORIZON_CATALOG_GENERATE_DESCRIPTIONS stored procedure
-- 4. HORIZON_CATALOG_MANAGER stored procedure with multi-mode operation
--
-- Prerequisites:
-- - Snowflake account with Cortex AI functionality enabled
-- - SNOWFLAKE.CORTEX_USER database role
-- - SYSADMIN or equivalent privileges
-- - Running warehouse for execution
--
-- Execution time: 2-5 minutes
-- ============================================================================

-- ============================================================================
-- SECTION 1: DATABASE, SCHEMA, AND CATALOG TABLE CREATION
-- ============================================================================

USE ROLE ACCOUNTADMIN;
CREATE DATABASE IF NOT EXISTS HORIZON_DB;
CREATE SCHEMA IF NOT EXISTS HORIZON_CATALOG;
GRANT ALL PRIVILEGES ON DATABASE HORIZON_DB TO ROLE SYSADMIN;
GRANT ALL PRIVILEGES ON SCHEMA HORIZON_CATALOG TO ROLE SYSADMIN;
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE SYSADMIN;

USE ROLE SYSADMIN;
USE DATABASE HORIZON_DB;
USE SCHEMA HORIZON_CATALOG;

-- Horizon Catalog Table for AI-Generated Descriptions
-- This table serves as both audit log and source of truth for object descriptions

CREATE OR REPLACE TABLE HORIZON_DB.HORIZON_CATALOG.horizon_catalog_descriptions (
  id INTEGER IDENTITY(1,1),                                    -- Auto-incrementing ID (more efficient than UUID)
  domain VARCHAR(10) NOT NULL,                                 -- 'TABLE' or 'COLUMN'
  name VARCHAR(256) NOT NULL,                                  -- Object name (table or column name)
  database_name VARCHAR(256) NOT NULL,
  schema_name VARCHAR(256) NOT NULL,
  table_name VARCHAR(256),                                     -- NULL for table descriptions, populated for column descriptions
  description VARCHAR(16777216),                               -- Generated description (max size for VARCHAR)
  description_version INTEGER DEFAULT 1,                       -- Version tracking for description updates
  is_current BOOLEAN DEFAULT TRUE,                             -- Whether this is the current/active version
  is_applied_as_comment BOOLEAN DEFAULT FALSE,                 -- Whether this description has been applied as object comment
  generation_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),  -- When description was generated
  applied_timestamp TIMESTAMP,                                 -- When description was applied as comment (if applicable)
  source_metadata VARIANT,                                     -- Store original AI response for reference
  generation_source VARCHAR(50) DEFAULT 'AI_CORTEX',           -- Source of description generation
  created_by STRING DEFAULT CURRENT_USER(),                    -- User who triggered generation
  notes VARCHAR(1000)                                          -- Optional notes or context
  
  -- Note: Snowflake only enforces NOT NULL constraints
) 
-- Add clustering for better query performance (Snowflake's equivalent to indexing)
CLUSTER BY (database_name, schema_name, is_current);

-- Note: Snowflake doesn't support traditional indexes
-- Instead, we use clustering keys (defined above) and rely on Snowflake's automatic micro-partitioning
-- For additional performance on timestamp queries, consider partitioning by date if the table grows large:
-- ALTER TABLE HORIZON_DB.HORIZON_CATALOG.horizon_catalog_descriptions ADD CLUSTER BY (DATE(generation_timestamp));

-- Create a view for easy access to current descriptions
CREATE OR REPLACE VIEW horizon_catalog_current_descriptions AS
SELECT 
  id,
  domain,
  name,
  database_name,
  schema_name,
  table_name,
  description,
  is_applied_as_comment,
  generation_timestamp,
  applied_timestamp,
  created_by
FROM HORIZON_DB.HORIZON_CATALOG.horizon_catalog_descriptions
WHERE is_current = TRUE;

-- Grant appropriate permissions (adjust as needed for your environment)
GRANT SELECT, INSERT, UPDATE ON HORIZON_DB.HORIZON_CATALOG.horizon_catalog_descriptions TO ROLE PUBLIC;
GRANT SELECT ON HORIZON_DB.HORIZON_CATALOG.horizon_catalog_current_descriptions TO ROLE PUBLIC;

-- ============================================================================
-- SECTION 2: HORIZON CATALOG DESCRIPTION GENERATION PROCEDURE
-- ============================================================================

-- Horizon Catalog Description Generation with Existence Checking and Improved Error Handling
-- This function generates AI descriptions only for objects that don't already have them
use role accountadmin;
use schema HORIZON_DB.HORIZON_CATALOG;
CREATE OR REPLACE PROCEDURE HORIZON_CATALOG_GENERATE_DESCRIPTIONS (
  database_name STRING, 
  schema_name STRING, 
  catalog_table STRING DEFAULT 'HORIZON_DB.HORIZON_CATALOG.horizon_catalog_descriptions',
  force_regenerate BOOLEAN DEFAULT FALSE,           -- Force regeneration even if description exists
  include_sample_data BOOLEAN DEFAULT TRUE,         -- Whether to use sample data for better descriptions
  max_parallel_jobs INTEGER DEFAULT NULL            -- Limit parallel processing (NULL = use all CPUs)
)
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
PACKAGES=('snowflake-snowpark-python','joblib')
HANDLER = 'main'
AS
$$
import json
from joblib import Parallel, delayed
import multiprocessing
from datetime import datetime

def check_existing_descriptions(session, database_name, schema_name, table_name, catalog_table):
    """Check if descriptions already exist for a table and its columns"""
    try:
        # Check for existing table description
        table_query = f"""
        SELECT COUNT(*) as count 
        FROM {catalog_table} 
        WHERE database_name = '{database_name}' 
          AND schema_name = '{schema_name}' 
          AND name = '{table_name}' 
          AND domain = 'TABLE' 
          AND is_current = TRUE
        """
        table_result = session.sql(table_query).collect()
        has_table_desc = table_result[0]['COUNT'] > 0
        
        # Check for existing column descriptions
        column_query = f"""
        SELECT COUNT(*) as count 
        FROM {catalog_table} 
        WHERE database_name = '{database_name}' 
          AND schema_name = '{schema_name}' 
          AND table_name = '{table_name}' 
          AND domain = 'COLUMN' 
          AND is_current = TRUE
        """
        column_result = session.sql(column_query).collect()
        has_column_desc = column_result[0]['COUNT'] > 0
        
        return has_table_desc, has_column_desc
    except Exception as e:
        # If catalog table doesn't exist or other error, assume no descriptions exist
        return False, False

def invalidate_old_descriptions(session, database_name, schema_name, table_name, catalog_table):
    """Mark existing descriptions as not current when regenerating"""
    try:
        # Invalidate old table description
        session.sql(f"""
        UPDATE {catalog_table} 
        SET is_current = FALSE 
        WHERE database_name = '{database_name}' 
          AND schema_name = '{schema_name}' 
          AND name = '{table_name}' 
          AND domain = 'TABLE' 
          AND is_current = TRUE
        """).collect()
        
        # Invalidate old column descriptions
        session.sql(f"""
        UPDATE {catalog_table} 
        SET is_current = FALSE 
        WHERE database_name = '{database_name}' 
          AND schema_name = '{schema_name}' 
          AND table_name = '{table_name}' 
          AND domain = 'COLUMN' 
          AND is_current = TRUE
        """).collect()
        
        return True
    except Exception as e:
        return False

def generate_descr(session, database_name, schema_name, table, catalog_table, force_regenerate, include_sample_data):
    """Generate descriptions for a single table and its columns"""
    table_name = table['TABLE_NAME']
    processing_result = {
        'table_name': table_name,
        'success': False,
        'message': '',
        'table_desc_generated': False,
        'column_desc_generated': False,
        'columns_processed': 0
    }
    
    try:
        # Check existing descriptions
        has_table_desc, has_column_desc = check_existing_descriptions(
            session, database_name, schema_name, table_name, catalog_table
        )
        
        # Skip if descriptions exist and not forcing regeneration
        if (has_table_desc and has_column_desc) and not force_regenerate:
            processing_result['message'] = 'Descriptions already exist, skipping'
            processing_result['success'] = True
            return processing_result
        
        # If regenerating, invalidate old descriptions
        if force_regenerate and (has_table_desc or has_column_desc):
            invalidate_old_descriptions(session, database_name, schema_name, table_name, catalog_table)
        
        # Generate new descriptions using AI
        ai_config = {
            'describe_columns': True, 
            'use_table_data': include_sample_data
        }
        
        async_job = session.sql(
            f"CALL AI_GENERATE_TABLE_DESC('{database_name}.{schema_name}.{table_name}', {ai_config})"
        ).collect_nowait()
        
        result = async_job.result()
        output = json.loads(result[0][0])
        columns_ret = output["COLUMNS"]
        table_ret = output["TABLE"][0]

        # Get next version number for this table
        version_query = f"""
        SELECT COALESCE(MAX(description_version), 0) + 1 as next_version
        FROM {catalog_table} 
        WHERE database_name = '{database_name}' 
          AND schema_name = '{schema_name}' 
          AND name = '{table_name}' 
          AND domain = 'TABLE'
        """
        version_result = session.sql(version_query).collect()
        next_version = version_result[0]['NEXT_VERSION']

        # Process table description
        if not has_table_desc or force_regenerate:
            table_description = table_ret["description"].replace("'", "''")  # Proper SQL escaping
            
            insert_table_sql = f"""
            INSERT INTO {catalog_table} (
                domain, name, database_name, schema_name, table_name, 
                description, description_version, is_current, 
                source_metadata, generation_timestamp
            ) VALUES (
                'TABLE', '{table_name}', '{database_name}', '{schema_name}', NULL,
                '{table_description}', {next_version}, TRUE,
                NULL, CURRENT_TIMESTAMP()
            )
            """
            session.sql(insert_table_sql).collect()
            processing_result['table_desc_generated'] = True

        # Process column descriptions
        columns_processed = 0
        if not has_column_desc or force_regenerate:
            for column in columns_ret:
                column_description = column["description"].replace("'", "''")
                column_name = column["name"]
                
                insert_column_sql = f"""
                INSERT INTO {catalog_table} (
                    domain, name, database_name, schema_name, table_name, 
                    description, description_version, is_current,
                    source_metadata, generation_timestamp
                ) VALUES (
                    'COLUMN', '{column_name}', '{database_name}', '{schema_name}', '{table_name}',
                    '{column_description}', {next_version}, TRUE,
                    NULL, CURRENT_TIMESTAMP()
                )
                """
                session.sql(insert_column_sql).collect()
                columns_processed += 1
            
            processing_result['column_desc_generated'] = True
            processing_result['columns_processed'] = columns_processed

        processing_result['success'] = True
        processing_result['message'] = f'Generated descriptions - Table: {processing_result["table_desc_generated"]}, Columns: {columns_processed}'
        
    except Exception as e:
        processing_result['message'] = f'Error: {str(e)}'
        
    return processing_result

def main(session, database_name, schema_name, catalog_table, force_regenerate, include_sample_data, max_parallel_jobs):
    """Main function to orchestrate description generation"""
    
    # Normalize inputs
    schema_name = schema_name.upper()
    database_name = database_name.upper()
    
    # Determine number of parallel jobs
    if max_parallel_jobs is None:
        max_parallel_jobs = multiprocessing.cpu_count()
    else:
        max_parallel_jobs = min(max_parallel_jobs, multiprocessing.cpu_count())
    
    # Get list of tables to process
    tables_query = f"""
    SELECT table_name
    FROM {database_name}.information_schema.tables
    WHERE table_schema = '{schema_name}'
      AND table_type = 'BASE TABLE'
    ORDER BY table_name
    """
    
    try:
        tablenames = session.sql(tables_query).collect()
        
        if not tablenames:
            return f"No tables found in {database_name}.{schema_name}"
        
        # Process tables in parallel
        results = Parallel(n_jobs=max_parallel_jobs, backend="threading")(
            delayed(generate_descr)(
                session,
                database_name,
                schema_name,
                table,
                catalog_table,
                force_regenerate,
                include_sample_data
            ) for table in tablenames
        )
        
        # Compile summary
        total_tables = len(results)
        successful_tables = sum(1 for r in results if r['success'])
        total_table_descriptions = sum(1 for r in results if r['table_desc_generated'])
        total_column_descriptions = sum(r['columns_processed'] for r in results)
        
        # Log any failures
        failures = [r for r in results if not r['success']]
        
        summary = f"""Processing complete for {database_name}.{schema_name}:
- Tables processed: {total_tables}
- Successful: {successful_tables}
- Failed: {len(failures)}
- Table descriptions generated: {total_table_descriptions}
- Column descriptions generated: {total_column_descriptions}
- Force regenerate: {force_regenerate}
- Include sample data: {include_sample_data}"""

        if failures:
            failure_details = "\\n".join([f"  - {f['table_name']}: {f['message']}" for f in failures])
            summary += f"\\n\\nFailures:\\n{failure_details}"
        
        return summary
        
    except Exception as e:
        return f"An error occurred: {str(e)}"
$$;

-- ============================================================================
-- SECTION 3: HORIZON CATALOG MANAGER PROCEDURE (MULTI-MODE OPERATION)
-- ============================================================================

-- Horizon Catalog Manager with Multiple Operation Modes
-- This procedure can generate descriptions, apply comments, or do both in a single operation
use role sysadmin;
use schema HORIZON_DB.HORIZON_CATALOG;
CREATE OR REPLACE PROCEDURE HORIZON_CATALOG_MANAGER (
  database_name STRING,
  schema_name STRING,
  operation_mode STRING DEFAULT 'FULL_SYNC',           -- 'GENERATE_ONLY', 'APPLY_ONLY', 'FULL_SYNC', 'CHECK_ONLY'
  catalog_table STRING DEFAULT 'HORIZON_DB.HORIZON_CATALOG.horizon_catalog_descriptions',
  force_regenerate BOOLEAN DEFAULT FALSE,              -- Force regeneration of descriptions
  force_apply_comments BOOLEAN DEFAULT FALSE,          -- Force overwrite existing comments
  include_sample_data BOOLEAN DEFAULT TRUE,            -- Use sample data for AI descriptions
  max_parallel_jobs INTEGER DEFAULT NULL,              -- Limit parallel processing
  dry_run BOOLEAN DEFAULT FALSE                        -- Preview changes without executing
)
RETURNS STRING
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
PACKAGES=('snowflake-snowpark-python','joblib')
HANDLER = 'main'
AS
$$
import json
from joblib import Parallel, delayed
import multiprocessing
from datetime import datetime

def get_existing_comments(session, database_name, schema_name, table_name):
    """Get existing comments on table and columns"""
    comments = {
        'table_comment': None,
        'column_comments': {}
    }
    
    try:
        # Get table comment
        table_info_query = f"""
        SELECT comment as table_comment
        FROM {database_name}.information_schema.tables
        WHERE table_schema = '{schema_name}' 
          AND table_name = '{table_name}'
          AND table_type = 'BASE TABLE'
        """
        table_result = session.sql(table_info_query).collect()
        if table_result and table_result[0]['TABLE_COMMENT']:
            comments['table_comment'] = table_result[0]['TABLE_COMMENT']
        
        # Get column comments
        columns_info_query = f"""
        SELECT column_name, comment as column_comment
        FROM {database_name}.information_schema.columns
        WHERE table_schema = '{schema_name}' 
          AND table_name = '{table_name}'
          AND comment IS NOT NULL
        """
        column_results = session.sql(columns_info_query).collect()
        for row in column_results:
            comments['column_comments'][row['COLUMN_NAME']] = row['COLUMN_COMMENT']
            
    except Exception as e:
        # If error getting comments, assume none exist
        pass
    
    return comments

def get_catalog_descriptions(session, database_name, schema_name, table_name, catalog_table):
    """Get current descriptions from catalog table"""
    descriptions = {
        'table_description': None,
        'column_descriptions': {}
    }
    
    try:
        # Get table description
        table_desc_query = f"""
        SELECT description
        FROM {catalog_table}
        WHERE database_name = '{database_name}'
          AND schema_name = '{schema_name}'
          AND name = '{table_name}'
          AND domain = 'TABLE'
          AND is_current = TRUE
        """
        table_result = session.sql(table_desc_query).collect()
        if table_result:
            descriptions['table_description'] = table_result[0]['DESCRIPTION']
        
        # Get column descriptions
        column_desc_query = f"""
        SELECT name, description
        FROM {catalog_table}
        WHERE database_name = '{database_name}'
          AND schema_name = '{schema_name}'
          AND table_name = '{table_name}'
          AND domain = 'COLUMN'
          AND is_current = TRUE
        """
        column_results = session.sql(column_desc_query).collect()
        for row in column_results:
            descriptions['column_descriptions'][row['NAME']] = row['DESCRIPTION']
            
    except Exception as e:
        # If catalog doesn't exist or error, return empty
        pass
    
    return descriptions

def apply_table_comment(session, database_name, schema_name, table_name, description, dry_run):
    """Apply description as table comment"""
    if dry_run:
        return f"[DRY RUN] Would set table comment: {description[:100]}..."
    
    try:
        escaped_description = description.replace("'", "''")
        comment_sql = f"""
        ALTER TABLE {database_name}.{schema_name}.{table_name} 
        SET COMMENT = '{escaped_description}'
        """
        session.sql(comment_sql).collect()
        return "SUCCESS"
    except Exception as e:
        return f"ERROR: {str(e)}"

def apply_column_comment(session, database_name, schema_name, table_name, column_name, description, dry_run):
    """Apply description as column comment"""
    if dry_run:
        return f"[DRY RUN] Would set column {column_name} comment: {description[:50]}..."
    
    try:
        escaped_description = description.replace("'", "''")
        # Handle case-sensitive column names
        if not column_name.isupper():
            column_name = f'"{column_name}"'
        
        comment_sql = f"""
        ALTER TABLE {database_name}.{schema_name}.{table_name} 
        MODIFY COLUMN {column_name} COMMENT '{escaped_description}'
        """
        session.sql(comment_sql).collect()
        return "SUCCESS"
    except Exception as e:
        return f"ERROR: {str(e)}"

def update_applied_status(session, database_name, schema_name, table_name, catalog_table, domain, name, dry_run):
    """Mark description as applied in catalog"""
    if dry_run:
        return "DRY_RUN"
    
    try:
        update_sql = f"""
        UPDATE {catalog_table}
        SET is_applied_as_comment = TRUE,
            applied_timestamp = CURRENT_TIMESTAMP()
        WHERE database_name = '{database_name}'
          AND schema_name = '{schema_name}'
          AND name = '{name}'
          AND domain = '{domain}'
          AND is_current = TRUE
        """
        if domain == 'COLUMN':
            update_sql += f" AND table_name = '{table_name}'"
        
        result = session.sql(update_sql).collect()
        return f"SUCCESS: Updated {domain} {name}"
    except Exception as e:
        # Return error instead of silently failing
        return f"UPDATE_ERROR: {str(e)}"

def process_table(session, database_name, schema_name, table, operation_mode, catalog_table, 
                 force_regenerate, force_apply_comments, include_sample_data, dry_run):
    """Process a single table according to operation mode"""
    table_name = table['TABLE_NAME']
    result = {
        'table_name': table_name,
        'success': False,
        'operation_mode': operation_mode,
        'actions_taken': [],
        'descriptions_generated': 0,
        'comments_applied': 0,
        'errors': []
    }
    
    try:
        # STEP 1: Generate descriptions if needed
        if operation_mode in ['GENERATE_ONLY', 'FULL_SYNC']:
            # Call the enhanced catalog function for this table
            generate_proc_call = f"""
            CALL HORIZON_CATALOG_GENERATE_DESCRIPTIONS(
                '{database_name}', '{schema_name}', '{catalog_table}',
                {str(force_regenerate).lower()}, {str(include_sample_data).lower()}, 1
            )
            """
            
            if not dry_run:
                # Note: This would require the table to be processed individually
                # For now, we'll simulate the generation logic here
                pass
            else:
                result['actions_taken'].append(f"[DRY RUN] Would generate descriptions for {table_name}")
        
        # STEP 2: Apply comments if needed
        if operation_mode in ['APPLY_ONLY', 'FULL_SYNC', 'CHECK_ONLY']:
            # Get existing comments
            existing_comments = get_existing_comments(session, database_name, schema_name, table_name)
            
            # Get catalog descriptions
            catalog_descriptions = get_catalog_descriptions(session, database_name, schema_name, table_name, catalog_table)
            
            # Apply table comment
            if catalog_descriptions['table_description']:
                should_apply_table = (
                    force_apply_comments or 
                    existing_comments['table_comment'] is None or
                    operation_mode == 'CHECK_ONLY'
                )
                
                if should_apply_table:
                    table_result = apply_table_comment(
                        session, database_name, schema_name, table_name,
                        catalog_descriptions['table_description'], 
                        dry_run or operation_mode == 'CHECK_ONLY'
                    )
                    
                    if table_result == "SUCCESS" or "DRY RUN" in table_result:
                        result['comments_applied'] += 1
                        result['actions_taken'].append(f"Applied table comment: {table_result}")
                        if not dry_run and operation_mode != 'CHECK_ONLY':
                            update_result = update_applied_status(session, database_name, schema_name, table_name, 
                                                catalog_table, 'TABLE', table_name, False)
                            result['actions_taken'].append(f"Update tracking: {update_result}")
                    else:
                        result['errors'].append(f"Table comment: {table_result}")
            
            # Apply column comments
            for column_name, description in catalog_descriptions['column_descriptions'].items():
                should_apply_column = (
                    force_apply_comments or
                    column_name not in existing_comments['column_comments'] or
                    operation_mode == 'CHECK_ONLY'
                )
                
                if should_apply_column:
                    column_result = apply_column_comment(
                        session, database_name, schema_name, table_name, column_name,
                        description, dry_run or operation_mode == 'CHECK_ONLY'
                    )
                    
                    if column_result == "SUCCESS" or "DRY RUN" in column_result:
                        result['comments_applied'] += 1
                        result['actions_taken'].append(f"Applied column comment {column_name}: {column_result}")
                        if not dry_run and operation_mode != 'CHECK_ONLY':
                            update_result = update_applied_status(session, database_name, schema_name, table_name,
                                                catalog_table, 'COLUMN', column_name, False)
                            result['actions_taken'].append(f"Update tracking {column_name}: {update_result}")
                    else:
                        result['errors'].append(f"Column {column_name}: {column_result}")
        
        result['success'] = len(result['errors']) == 0
        
    except Exception as e:
        result['errors'].append(f"Processing error: {str(e)}")
    
    return result

def main(session, database_name, schema_name, operation_mode, catalog_table, force_regenerate, 
         force_apply_comments, include_sample_data, max_parallel_jobs, dry_run):
    """Main orchestration function"""
    
    # Validate operation mode
    valid_modes = ['GENERATE_ONLY', 'APPLY_ONLY', 'FULL_SYNC', 'CHECK_ONLY']
    if operation_mode not in valid_modes:
        return f"Invalid operation_mode. Must be one of: {', '.join(valid_modes)}"
    
    # Normalize inputs
    schema_name = schema_name.upper()
    database_name = database_name.upper()
    
    # Handle parallel processing
    if max_parallel_jobs is None:
        max_parallel_jobs = multiprocessing.cpu_count()
    else:
        max_parallel_jobs = min(max_parallel_jobs, multiprocessing.cpu_count())
    
    # For comment operations, we should be more conservative with parallelism
    if operation_mode in ['APPLY_ONLY', 'FULL_SYNC']:
        max_parallel_jobs = min(max_parallel_jobs, 4)  # Limit DDL operations
    
    try:
        # STEP 1: Handle GENERATE_ONLY mode efficiently
        if operation_mode == 'GENERATE_ONLY':
            # Call the Horizon Catalog generation procedure directly
            generate_call = f"""
            CALL HORIZON_CATALOG_GENERATE_DESCRIPTIONS(
                '{database_name}', '{schema_name}', '{catalog_table}',
                {str(force_regenerate).lower()}, {str(include_sample_data).lower()}, {max_parallel_jobs}
            )
            """
            
            if not dry_run:
                result = session.sql(generate_call).collect()
                return f"GENERATE_ONLY mode completed:\\n{result[0][0]}"
            else:
                return f"[DRY RUN] GENERATE_ONLY mode would execute:\\n{generate_call}"
        
        # STEP 2: Handle other modes (APPLY_ONLY, FULL_SYNC, CHECK_ONLY)
        # Get tables to process
        tables_query = f"""
        SELECT table_name
        FROM {database_name}.information_schema.tables
        WHERE table_schema = '{schema_name}'
          AND table_type = 'BASE TABLE'
        ORDER BY table_name
        """
        
        tablenames = session.sql(tables_query).collect()
        
        if not tablenames:
            return f"No tables found in {database_name}.{schema_name}"
        
        # For FULL_SYNC, first generate descriptions
        if operation_mode == 'FULL_SYNC' and not dry_run:
            generate_call = f"""
            CALL HORIZON_CATALOG_GENERATE_DESCRIPTIONS(
                '{database_name}', '{schema_name}', '{catalog_table}',
                {str(force_regenerate).lower()}, {str(include_sample_data).lower()}, {max_parallel_jobs}
            )
            """
            session.sql(generate_call).collect()
        
        # Process tables for comment application
        results = Parallel(n_jobs=max_parallel_jobs, backend="threading")(
            delayed(process_table)(
                session, database_name, schema_name, table, operation_mode, catalog_table,
                force_regenerate, force_apply_comments, include_sample_data, dry_run
            ) for table in tablenames
        )
        
        # Compile summary
        total_tables = len(results)
        successful_tables = sum(1 for r in results if r['success'])
        total_comments_applied = sum(r['comments_applied'] for r in results)
        total_errors = sum(len(r['errors']) for r in results)
        
        # Build detailed summary
        mode_description = {
            'APPLY_ONLY': 'Applied comments from catalog to database objects',
            'FULL_SYNC': 'Generated descriptions and applied as comments', 
            'CHECK_ONLY': 'Analyzed what changes would be made (no changes applied)'
        }
        
        summary = f"""{'[DRY RUN] ' if dry_run else ''}{mode_description.get(operation_mode, operation_mode)} for {database_name}.{schema_name}:

SUMMARY:
- Tables processed: {total_tables}
- Successful: {successful_tables}
- Failed: {total_tables - successful_tables}
- Comments applied: {total_comments_applied}
- Total errors: {total_errors}
- Force apply comments: {force_apply_comments}
- Operation mode: {operation_mode}"""

        # Add failure details
        failures = [r for r in results if not r['success']]
        if failures:
            summary += "\\n\\nFAILURES:"
            for failure in failures:
                summary += f"\\n  - {failure['table_name']}: {'; '.join(failure['errors'])}"
        
        # Add sample of successful actions
        successful_actions = [r for r in results if r['success'] and r['actions_taken']]
        if successful_actions and len(successful_actions) <= 5:
            summary += "\\n\\nACTIONS TAKEN:"
            for action in successful_actions[:5]:
                for taken in action['actions_taken'][:2]:  # Limit to first 2 actions per table
                    summary += f"\\n  - {action['table_name']}: {taken}"
        
        return summary
        
    except Exception as e:
        return f"An error occurred: {str(e)}"
$$;

-- ============================================================================
-- INSTALLATION COMPLETE
-- ============================================================================

SELECT 
    '🎉 HORIZON CATALOG COMPLETE INSTALLATION FINISHED' AS status,
    CURRENT_TIMESTAMP() AS completion_time,
    'Ready for use!' AS next_step;

-- Quick verification queries
SELECT 'Database created:' AS verification, COUNT(*) AS objects FROM HORIZON_DB.INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'HORIZON_CATALOG';
SHOW PROCEDURES LIKE '%HORIZON_CATALOG%';

-- Usage examples:
-- CALL HORIZON_CATALOG_GENERATE_DESCRIPTIONS('YOUR_DATABASE', 'YOUR_SCHEMA');
-- CALL HORIZON_CATALOG_MANAGER('YOUR_DATABASE', 'YOUR_SCHEMA', 'CHECK_ONLY');
-- CALL HORIZON_CATALOG_MANAGER('YOUR_DATABASE', 'YOUR_SCHEMA', 'FULL_SYNC');
