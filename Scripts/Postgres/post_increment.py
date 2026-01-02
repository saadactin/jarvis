#!/usr/bin/env python3
"""
PostgreSQL to ClickHouse Incremental Synchronization Script
Keeps ClickHouse 100% in sync with PostgreSQL:
- Detects and syncs new tables
- Detects and adds new columns
- Inserts new rows
- Deletes removed rows
- Handles truncates
- Uses HR_ prefix for all tables
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import clickhouse_connect
from typing import Dict, List, Any, Set, Tuple
import logging
import os
from dotenv import load_dotenv

# Load environment variables from .env file (looks in parent directories too)
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# PostgreSQL connection details
PG_HOST = os.getenv('PG_HOST', 'localhost')
PG_PORT = int(os.getenv('PG_PORT', 5432))
PG_DATABASE = os.getenv('PG_DATABASE')
PG_USERNAME = os.getenv('PG_USERNAME')
PG_PASSWORD = os.getenv('PG_PASSWORD')

# ClickHouse connection details
CLICKHOUSE_HOST = os.getenv('CLICKHOUSE_HOST')
CLICKHOUSE_USER = os.getenv('CLICKHOUSE_USER', 'default')
CLICKHOUSE_PASS = os.getenv('CLICKHOUSE_PASS', '')
CLICKHOUSE_DB = os.getenv('CLICKHOUSE_DB')

# Validate required environment variables
if not all([PG_DATABASE, PG_USERNAME, PG_PASSWORD, CLICKHOUSE_HOST, CLICKHOUSE_DB]):
    raise ValueError("Missing required environment variables. Please set PG_DATABASE, PG_USERNAME, PG_PASSWORD, CLICKHOUSE_HOST, and CLICKHOUSE_DB in .env file")

# Table prefix
TABLE_PREFIX = "HR_"


def map_postgresql_to_clickhouse_type(pg_type: str) -> str:
    """
    Map PostgreSQL data types to ClickHouse data types
    """
    type_mapping = {
        # Integer types
        'smallint': 'Int16',
        'integer': 'Int32',
        'bigint': 'Int64',
        'serial': 'Int32',
        'bigserial': 'Int64',
        'smallserial': 'Int16',
        
        # Floating point
        'real': 'Float32',
        'double precision': 'Float64',
        'numeric': 'Decimal64(2)',
        'decimal': 'Decimal64(2)',
        'money': 'Decimal64(2)',
        
        # Boolean
        'boolean': 'UInt8',
        
        # Character types
        'character varying': 'String',
        'varchar': 'String',
        'character': 'FixedString(255)',
        'char': 'FixedString(255)',
        'text': 'String',
        
        # Date/Time types
        'timestamp without time zone': 'DateTime',
        'timestamp with time zone': 'DateTime',
        'timestamp': 'DateTime',
        'date': 'Date',
        'time without time zone': 'String',
        'time with time zone': 'String',
        'interval': 'String',
        
        # Binary
        'bytea': 'String',
        
        # JSON
        'json': 'String',
        'jsonb': 'String',
        
        # UUID
        'uuid': 'UUID',
        
        # Arrays
        'ARRAY': 'String',
    }
    
    pg_type_lower = pg_type.lower().strip()
    
    if '[]' in pg_type_lower or 'array' in pg_type_lower:
        return 'String'
    
    if pg_type_lower in type_mapping:
        return type_mapping[pg_type_lower]
    
    for pg_key, ch_type in type_mapping.items():
        if pg_type_lower.startswith(pg_key):
            return ch_type
    
    logger.warning(f"Unknown PostgreSQL type: {pg_type}, mapping to String")
    return 'String'


def get_postgresql_tables(conn) -> List[str]:
    """Get all table names from PostgreSQL public schema"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """)
    tables = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return tables


def get_table_schema(conn, table_name: str) -> List[Dict[str, Any]]:
    """Get column information for a table"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            column_name,
            data_type,
            character_maximum_length,
            numeric_precision,
            numeric_scale,
            is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public' 
        AND table_name = %s
        ORDER BY ordinal_position;
    """, (table_name,))
    
    columns = []
    for row in cursor.fetchall():
        col_name, data_type, char_max_len, num_precision, num_scale, is_nullable = row
        
        full_type = data_type
        if char_max_len:
            full_type = f"{data_type}({char_max_len})"
        elif num_precision and num_scale:
            full_type = f"{data_type}({num_precision},{num_scale})"
        elif num_precision:
            full_type = f"{data_type}({num_precision})"
        
        columns.append({
            'name': col_name,
            'type': data_type,
            'full_type': full_type,
            'is_nullable': is_nullable == 'YES'
        })
    
    cursor.close()
    return columns


def get_primary_key_columns(conn, table_name: str) -> List[str]:
    """Get primary key column names for a table"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.attname
        FROM pg_index i
        JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
        WHERE i.indrelid = %s::regclass
        AND i.indisprimary;
    """, (table_name,))
    
    pk_columns = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return pk_columns


def get_clickhouse_table_columns(ch_client, table_name: str) -> Set[str]:
    """Get column names from ClickHouse table"""
    ch_table_name = f"{TABLE_PREFIX}{table_name}"
    try:
        result = ch_client.query(f"DESCRIBE TABLE {ch_table_name}")
        columns = set()
        for row in result.result_rows:
            columns.add(row[0])  # Column name is first element
        return columns
    except Exception as e:
        logger.debug(f"Could not get columns from ClickHouse table {ch_table_name}: {str(e)}")
        return set()


def table_exists_in_clickhouse(ch_client, table_name: str) -> bool:
    """Check if a table exists in ClickHouse"""
    ch_table_name = f"{TABLE_PREFIX}{table_name}"
    try:
        result = ch_client.command(f"EXISTS TABLE {ch_table_name}")
        return result == 1
    except Exception:
        return False


def get_row_count(conn, table_name: str) -> int:
    """Get row count from PostgreSQL table"""
    cursor = conn.cursor()
    cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
    count = cursor.fetchone()[0]
    cursor.close()
    return count


def get_clickhouse_row_count(ch_client, table_name: str) -> int:
    """Get row count from ClickHouse table"""
    ch_table_name = f"{TABLE_PREFIX}{table_name}"
    try:
        result = ch_client.query(f"SELECT COUNT(*) FROM {ch_table_name}")
        return result.result_rows[0][0] if result.result_rows else 0
    except Exception:
        return 0


def create_clickhouse_table(ch_client, table_name: str, columns: List[Dict[str, Any]]):
    """Create a table in ClickHouse based on PostgreSQL schema"""
    ch_table_name = f"{TABLE_PREFIX}{table_name}"
    
    column_defs = []
    for col in columns:
        ch_type = map_postgresql_to_clickhouse_type(col['full_type'])
        nullable = f"Nullable({ch_type})" if col['is_nullable'] else ch_type
        column_defs.append(f"`{col['name']}` {nullable}")
    
    create_sql = f"""
    CREATE TABLE IF NOT EXISTS {ch_table_name} (
        {', '.join(column_defs)}
    ) ENGINE = MergeTree()
    ORDER BY tuple()
    """
    
    logger.info(f"Creating ClickHouse table: {ch_table_name}")
    ch_client.command(create_sql)
    logger.info(f"Successfully created table: {ch_table_name}")


def add_column_to_clickhouse_table(ch_client, table_name: str, column: Dict[str, Any]):
    """Add a new column to existing ClickHouse table"""
    ch_table_name = f"{TABLE_PREFIX}{table_name}"
    ch_type = map_postgresql_to_clickhouse_type(column['full_type'])
    nullable = f"Nullable({ch_type})" if column['is_nullable'] else ch_type
    
    alter_sql = f"ALTER TABLE {ch_table_name} ADD COLUMN `{column['name']}` {nullable}"
    
    logger.info(f"Adding column {column['name']} to {ch_table_name}")
    ch_client.command(alter_sql)
    logger.info(f"Successfully added column {column['name']}")


def get_all_keys_from_postgresql(conn, table_name: str, key_columns: List[str]) -> Set[Tuple]:
    """Get all primary key values from PostgreSQL table"""
    if not key_columns:
        return set()
    
    cursor = conn.cursor()
    key_cols_str = ', '.join([f'"{col}"' for col in key_columns])
    cursor.execute(f'SELECT {key_cols_str} FROM "{table_name}"')
    
    keys = set()
    for row in cursor.fetchall():
        key_tuple = tuple(None if val is None else val for val in row)
        keys.add(key_tuple)
    
    cursor.close()
    return keys


def get_all_keys_from_clickhouse(ch_client, table_name: str, key_columns: List[str]) -> Set[Tuple]:
    """Get all primary key values from ClickHouse table"""
    if not key_columns:
        return set()
    
    ch_table_name = f"{TABLE_PREFIX}{table_name}"
    key_cols_str = ', '.join([f"`{col}`" for col in key_columns])
    
    try:
        result = ch_client.query(f"SELECT {key_cols_str} FROM {ch_table_name}")
        keys = set()
        for row in result.result_rows:
            key_tuple = tuple(None if val is None else val for val in row)
            keys.add(key_tuple)
        return keys
    except Exception as e:
        logger.warning(f"Could not fetch keys from ClickHouse: {str(e)}")
        return set()


def delete_rows_from_clickhouse(ch_client, table_name: str, key_columns: List[str], keys_to_delete: Set[Tuple]):
    """Delete rows from ClickHouse table based on primary keys"""
    if not keys_to_delete or not key_columns:
        return
    
    ch_table_name = f"{TABLE_PREFIX}{table_name}"
    deleted_count = 0
    
    # ClickHouse uses ALTER TABLE DELETE for row deletion
    # Build OR conditions for multiple deletes in batches
    keys_list = list(keys_to_delete)
    batch_size = 100  # Delete in batches to avoid very long queries
    
    for batch_start in range(0, len(keys_list), batch_size):
        batch = keys_list[batch_start:batch_start + batch_size]
        or_conditions = []
        
        for key_tuple in batch:
            and_conditions = []
            for i, col in enumerate(key_columns):
                val = key_tuple[i]
                if val is None:
                    and_conditions.append(f"`{col}` IS NULL")
                else:
                    # Properly escape and format the value
                    if isinstance(val, str):
                        val_escaped = val.replace("'", "''").replace("\\", "\\\\")
                        and_conditions.append(f"`{col}` = '{val_escaped}'")
                    elif isinstance(val, (int, float)):
                        and_conditions.append(f"`{col}` = {val}")
                    else:
                        val_escaped = str(val).replace("'", "''").replace("\\", "\\\\")
                        and_conditions.append(f"`{col}` = '{val_escaped}'")
            
            or_conditions.append(f"({' AND '.join(and_conditions)})")
        
        where_clause = " OR ".join(or_conditions)
        delete_sql = f"ALTER TABLE {ch_table_name} DELETE WHERE {where_clause}"
        
        try:
            ch_client.command(delete_sql)
            deleted_count += len(batch)
            logger.info(f"Deleted {deleted_count}/{len(keys_to_delete)} rows from {ch_table_name}")
        except Exception as e:
            logger.error(f"Error deleting batch from {ch_table_name}: {str(e)}")
            # Try deleting one by one if batch fails
            for key_tuple in batch:
                try:
                    conditions = []
                    for i, col in enumerate(key_columns):
                        val = key_tuple[i]
                        if val is None:
                            conditions.append(f"`{col}` IS NULL")
                        else:
                            if isinstance(val, str):
                                val_escaped = val.replace("'", "''").replace("\\", "\\\\")
                                conditions.append(f"`{col}` = '{val_escaped}'")
                            elif isinstance(val, (int, float)):
                                conditions.append(f"`{col}` = {val}")
                            else:
                                val_escaped = str(val).replace("'", "''").replace("\\", "\\\\")
                                conditions.append(f"`{col}` = '{val_escaped}'")
                    
                    where_clause = " AND ".join(conditions)
                    delete_sql = f"ALTER TABLE {ch_table_name} DELETE WHERE {where_clause}"
                    ch_client.command(delete_sql)
                    deleted_count += 1
                except Exception as e2:
                    logger.error(f"Error deleting individual row: {str(e2)}")
    
    if deleted_count > 0:
        logger.info(f"Successfully deleted {deleted_count} rows from {ch_table_name}")


def insert_rows_to_clickhouse(ch_client, table_name: str, columns: List[Dict[str, Any]], rows: List[Dict]):
    """Insert rows into ClickHouse table"""
    if not rows:
        return
    
    ch_table_name = f"{TABLE_PREFIX}{table_name}"
    col_names = [col['name'] for col in columns]
    
    # Prepare data for insertion
    data_to_insert = []
    for row in rows:
        row_data = []
        for col in col_names:
            value = row.get(col)
            row_data.append(None if value is None else value)
        data_to_insert.append(row_data)
    
    # Insert in batches
    batch_size = 1000
    inserted_count = 0
    
    for i in range(0, len(data_to_insert), batch_size):
        batch = data_to_insert[i:i + batch_size]
        try:
            ch_client.insert(ch_table_name, batch, column_names=col_names)
            inserted_count += len(batch)
            logger.info(f"Inserted {inserted_count}/{len(data_to_insert)} rows into {ch_table_name}")
        except Exception as e:
            logger.error(f"Error inserting batch: {str(e)}")
            raise
    
    logger.info(f"Successfully inserted {inserted_count} rows into {ch_table_name}")


def truncate_clickhouse_table(ch_client, table_name: str):
    """Truncate ClickHouse table"""
    ch_table_name = f"{TABLE_PREFIX}{table_name}"
    try:
        ch_client.command(f"TRUNCATE TABLE {ch_table_name}")
        logger.info(f"Truncated table {ch_table_name}")
    except Exception as e:
        logger.error(f"Error truncating table {ch_table_name}: {str(e)}")
        raise


def sync_table(pg_conn, ch_client, table_name: str):
    """Synchronize a single table between PostgreSQL and ClickHouse"""
    logger.info(f"\n{'='*60}")
    logger.info(f"Synchronizing table: {table_name}")
    logger.info(f"{'='*60}")
    
    ch_table_name = f"{TABLE_PREFIX}{table_name}"
    
    # Get PostgreSQL schema
    pg_columns = get_table_schema(pg_conn, table_name)
    pg_col_names = {col['name'] for col in pg_columns}
    
    # Check if table exists in ClickHouse
    table_exists = table_exists_in_clickhouse(ch_client, table_name)
    
    if not table_exists:
        logger.info(f"Table {ch_table_name} does not exist, creating it")
        create_clickhouse_table(ch_client, table_name, pg_columns)
    else:
        # Check for new columns
        ch_col_names = get_clickhouse_table_columns(ch_client, table_name)
        new_columns = [col for col in pg_columns if col['name'] not in ch_col_names]
        
        if new_columns:
            logger.info(f"Found {len(new_columns)} new columns to add")
            for col in new_columns:
                add_column_to_clickhouse_table(ch_client, table_name, col)
    
    # Get row counts
    pg_row_count = get_row_count(pg_conn, table_name)
    ch_row_count = get_clickhouse_row_count(ch_client, table_name)
    
    logger.info(f"PostgreSQL rows: {pg_row_count}, ClickHouse rows: {ch_row_count}")
    
    # Handle truncate case (PG has 0 rows but CH has rows)
    if pg_row_count == 0 and ch_row_count > 0:
        logger.info(f"PostgreSQL table is empty but ClickHouse has {ch_row_count} rows - truncating")
        truncate_clickhouse_table(ch_client, table_name)
        return
    
    if pg_row_count == 0:
        logger.info("Both tables are empty, nothing to sync")
        return
    
    # Get primary key columns
    pk_columns = get_primary_key_columns(pg_conn, table_name)
    
    if pk_columns:
        logger.info(f"Using primary key for sync: {pk_columns}")
        
        # Get all keys from both databases
        pg_keys = get_all_keys_from_postgresql(pg_conn, table_name, pk_columns)
        ch_keys = get_all_keys_from_clickhouse(ch_client, table_name, pk_columns)
        
        logger.info(f"PostgreSQL keys: {len(pg_keys)}, ClickHouse keys: {len(ch_keys)}")
        
        # Find keys to delete (in CH but not in PG)
        keys_to_delete = ch_keys - pg_keys
        if keys_to_delete:
            logger.info(f"Found {len(keys_to_delete)} rows to delete")
            delete_rows_from_clickhouse(ch_client, table_name, pk_columns, keys_to_delete)
        
        # Find keys to insert (in PG but not in CH)
        keys_to_insert = pg_keys - ch_keys
        if keys_to_insert:
            logger.info(f"Found {len(keys_to_insert)} new rows to insert")
            
            # Fetch rows from PostgreSQL in batches to avoid very long WHERE clauses
            cursor = pg_conn.cursor(cursor_factory=RealDictCursor)
            all_cols_str = ', '.join([f'"{col}"' for col in pg_col_names])
            all_new_rows = []
            
            keys_list = list(keys_to_insert)
            batch_size = 500  # Process keys in batches
            
            for batch_start in range(0, len(keys_list), batch_size):
                batch = keys_list[batch_start:batch_start + batch_size]
                
                # Build WHERE clause for this batch
                conditions = []
                for key_tuple in batch:
                    key_conditions = []
                    for i, col in enumerate(pk_columns):
                        val = key_tuple[i]
                        if val is None:
                            key_conditions.append(f'"{col}" IS NULL')
                        else:
                            if isinstance(val, str):
                                val = val.replace("'", "''")
                            key_conditions.append(f'"{col}" = \'{val}\'')
                    conditions.append(f"({' AND '.join(key_conditions)})")
                
                where_clause = " OR ".join(conditions)
                query = f'SELECT {all_cols_str} FROM "{table_name}" WHERE {where_clause}'
                
                try:
                    cursor.execute(query)
                    batch_rows = cursor.fetchall()
                    all_new_rows.extend(batch_rows)
                except Exception as e:
                    logger.error(f"Error fetching batch from PostgreSQL: {str(e)}")
                    # Try fetching one by one if batch fails
                    for key_tuple in batch:
                        try:
                            key_conditions = []
                            for i, col in enumerate(pk_columns):
                                val = key_tuple[i]
                                if val is None:
                                    key_conditions.append(f'"{col}" IS NULL')
                                else:
                                    if isinstance(val, str):
                                        val = val.replace("'", "''")
                                    key_conditions.append(f'"{col}" = \'{val}\'')
                            where_clause = " AND ".join(key_conditions)
                            query = f'SELECT {all_cols_str} FROM "{table_name}" WHERE {where_clause}'
                            cursor.execute(query)
                            rows = cursor.fetchall()
                            all_new_rows.extend(rows)
                        except Exception as e2:
                            logger.error(f"Error fetching individual row: {str(e2)}")
            
            cursor.close()
            
            if all_new_rows:
                insert_rows_to_clickhouse(ch_client, table_name, pg_columns, all_new_rows)
        else:
            logger.info("No new rows to insert")
    else:
        # No primary key - use full comparison (less efficient)
        logger.warning("No primary key found, using full row comparison (may be slow)")
        
        # Get all rows from PostgreSQL
        cursor = pg_conn.cursor(cursor_factory=RealDictCursor)
        all_cols_str = ', '.join([f'"{col}"' for col in pg_col_names])
        cursor.execute(f'SELECT {all_cols_str} FROM "{table_name}"')
        pg_rows = cursor.fetchall()
        cursor.close()
        
        # Get all rows from ClickHouse
        try:
            ch_result = ch_client.query(f"SELECT * FROM {ch_table_name}")
            ch_rows_set = set()
            for row in ch_result.result_rows:
                row_tuple = tuple(None if val is None else val for val in row)
                ch_rows_set.add(row_tuple)
        except Exception as e:
            logger.warning(f"Could not fetch ClickHouse rows: {str(e)}")
            ch_rows_set = set()
        
        # Find new rows
        new_rows = []
        for row in pg_rows:
            row_tuple = tuple(None if row[col] is None else row[col] for col in pg_col_names)
            if row_tuple not in ch_rows_set:
                new_rows.append(row)
        
        if new_rows:
            logger.info(f"Found {len(new_rows)} new rows to insert")
            insert_rows_to_clickhouse(ch_client, table_name, pg_columns, new_rows)
        else:
            logger.info("No new rows to insert")
        
        # For deletes without primary key, we'd need to compare all rows
        # This is expensive, so we'll skip it and rely on periodic full sync
        logger.warning("Delete detection skipped (no primary key). Consider adding primary keys for better sync.")
    
    logger.info(f"Successfully synchronized table: {table_name}")


def main():
    """Main synchronization function"""
    logger.info("Starting PostgreSQL to ClickHouse incremental synchronization")
    
    # Connect to PostgreSQL
    try:
        logger.info(f"Connecting to PostgreSQL: {PG_HOST}:{PG_PORT}/{PG_DATABASE}")
        pg_conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            database=PG_DATABASE,
            user=PG_USERNAME,
            password=PG_PASSWORD
        )
        logger.info("Successfully connected to PostgreSQL")
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {str(e)}")
        return
    
    # Connect to ClickHouse
    try:
        logger.info(f"Connecting to ClickHouse: {CLICKHOUSE_HOST}")
        ch_client = clickhouse_connect.get_client(
            host=CLICKHOUSE_HOST,
            username=CLICKHOUSE_USER,
            password=CLICKHOUSE_PASS,
            database=CLICKHOUSE_DB
        )
        logger.info("Successfully connected to ClickHouse")
    except Exception as e:
        logger.error(f"Failed to connect to ClickHouse: {str(e)}")
        pg_conn.close()
        return
    
    try:
        # Get all tables from PostgreSQL
        pg_tables = set(get_postgresql_tables(pg_conn))
        logger.info(f"Found {len(pg_tables)} tables in PostgreSQL: {sorted(pg_tables)}")
        
        if len(pg_tables) == 0:
            logger.warning("No tables found in PostgreSQL")
            return
        
        # Sync each table
        for table_name in sorted(pg_tables):
            try:
                sync_table(pg_conn, ch_client, table_name)
            except Exception as e:
                logger.error(f"Error synchronizing table {table_name}: {str(e)}")
                logger.exception("Full error traceback:")
                continue
        
        logger.info("\n" + "="*60)
        logger.info("Synchronization completed!")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"Synchronization failed: {str(e)}")
        logger.exception("Full error traceback:")
    finally:
        pg_conn.close()
        logger.info("Closed database connections")


if __name__ == "__main__":
    main()

