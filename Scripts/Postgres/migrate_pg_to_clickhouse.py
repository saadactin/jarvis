#!/usr/bin/env python3
"""
PostgreSQL to ClickHouse Migration Script
Migrates all tables from PostgreSQL public schema to ClickHouse with HR_ prefix
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import clickhouse_connect
from typing import Dict, List, Any
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
        'boolean': 'UInt8',  # ClickHouse uses UInt8 for boolean (0/1)
        
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
        'bytea': 'String',  # Store as base64 encoded string
        
        # JSON
        'json': 'String',
        'jsonb': 'String',
        
        # UUID
        'uuid': 'UUID',
        
        # Arrays (simplified - store as String)
        'ARRAY': 'String',
    }
    
    # Normalize the type name
    pg_type_lower = pg_type.lower().strip()
    
    # Check for array types
    if '[]' in pg_type_lower or 'array' in pg_type_lower:
        return 'String'
    
    # Check direct mapping
    if pg_type_lower in type_mapping:
        return type_mapping[pg_type_lower]
    
    # Check for types with length/precision (e.g., varchar(255), numeric(10,2))
    for pg_key, ch_type in type_mapping.items():
        if pg_type_lower.startswith(pg_key):
            return ch_type
    
    # Default to String for unknown types
    logger.warning(f"Unknown PostgreSQL type: {pg_type}, mapping to String")
    return 'String'


def get_postgresql_tables(conn) -> List[str]:
    """
    Get all table names from PostgreSQL public schema
    """
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
    """
    Get column information for a table
    """
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
        
        # Build full type string for better mapping
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
    """
    Get primary key column names for a table
    """
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


def table_exists_in_clickhouse(ch_client, table_name: str) -> bool:
    """
    Check if a table exists in ClickHouse
    """
    ch_table_name = f"HR_{table_name}"
    try:
        result = ch_client.command(f"EXISTS TABLE {ch_table_name}")
        return result == 1
    except Exception as e:
        logger.debug(f"Error checking table existence: {str(e)}")
        return False


def get_existing_keys_from_clickhouse(ch_client, table_name: str, key_columns: List[str]) -> set:
    """
    Get existing primary key values from ClickHouse table to avoid duplicates
    """
    ch_table_name = f"HR_{table_name}"
    
    if not key_columns:
        # If no primary key, return empty set (will use full row comparison)
        return set()
    
    try:
        # Build query to get all key combinations
        key_cols_str = ', '.join([f"`{col}`" for col in key_columns])
        query = f"SELECT {key_cols_str} FROM {ch_table_name}"
        result = ch_client.query(query)
        
        # Convert to set of tuples for comparison
        existing_keys = set()
        for row in result.result_rows:
            # Handle None values in keys
            key_tuple = tuple(None if val is None else val for val in row)
            existing_keys.add(key_tuple)
        
        return existing_keys
    except Exception as e:
        logger.warning(f"Could not fetch existing keys from ClickHouse: {str(e)}")
        return set()


def create_clickhouse_table(ch_client, table_name: str, columns: List[Dict[str, Any]]):
    """
    Create a table in ClickHouse based on PostgreSQL schema
    Only creates if it doesn't exist
    """
    ch_table_name = f"HR_{table_name}"
    
    # Check if table already exists
    if table_exists_in_clickhouse(ch_client, table_name):
        logger.info(f"Table {ch_table_name} already exists, skipping creation")
        return
    
    # Build column definitions
    column_defs = []
    for col in columns:
        ch_type = map_postgresql_to_clickhouse_type(col['full_type'])
        nullable = "Nullable(" + ch_type + ")" if col['is_nullable'] else ch_type
        column_defs.append(f"`{col['name']}` {nullable}")
    
    # Create table SQL
    create_sql = f"""
    CREATE TABLE IF NOT EXISTS {ch_table_name} (
        {', '.join(column_defs)}
    ) ENGINE = MergeTree()
    ORDER BY tuple()
    """
    
    logger.info(f"Creating ClickHouse table: {ch_table_name}")
    logger.debug(f"SQL: {create_sql}")
    
    ch_client.command(create_sql)
    logger.info(f"Successfully created table: {ch_table_name}")


def migrate_table_data(pg_conn, ch_client, table_name: str, columns: List[Dict[str, Any]], is_new_table: bool = False):
    """
    Migrate data from PostgreSQL table to ClickHouse
    For existing tables, only inserts new rows to avoid duplicates
    """
    ch_table_name = f"HR_{table_name}"
    
    # Get column names
    col_names = [col['name'] for col in columns]
    col_names_str = ', '.join([f'"{col}"' for col in col_names])
    
    # Fetch data from PostgreSQL
    logger.info(f"Fetching data from PostgreSQL table: {table_name}")
    pg_cursor = pg_conn.cursor(cursor_factory=RealDictCursor)
    pg_cursor.execute(f'SELECT {col_names_str} FROM "{table_name}"')
    
    rows = pg_cursor.fetchall()
    total_rows = len(rows)
    logger.info(f"Found {total_rows} rows in PostgreSQL table {table_name}")
    
    if total_rows == 0:
        logger.info(f"No data to migrate for table {table_name}")
        pg_cursor.close()
        return
    
    # If table exists, filter out duplicates
    if not is_new_table:
        logger.info(f"Table {ch_table_name} already exists, checking for new rows only")
        
        # Try to get primary key columns
        pk_columns = get_primary_key_columns(pg_conn, table_name)
        
        if pk_columns:
            logger.info(f"Using primary key columns for duplicate detection: {pk_columns}")
            # Get existing keys from ClickHouse
            existing_keys = get_existing_keys_from_clickhouse(ch_client, table_name, pk_columns)
            logger.info(f"Found {len(existing_keys)} existing rows in ClickHouse")
            
            # Filter rows that don't exist in ClickHouse
            new_rows = []
            for row in rows:
                # Build key tuple from primary key columns
                key_values = tuple(None if row[col] is None else row[col] for col in pk_columns)
                if key_values not in existing_keys:
                    new_rows.append(row)
            
            rows = new_rows
            logger.info(f"Found {len(rows)} new rows to insert (after filtering duplicates)")
        else:
            # No primary key - use full row comparison (more expensive but works)
            logger.info("No primary key found, using full row comparison for duplicate detection")
            try:
                # Get all existing rows from ClickHouse
                existing_result = ch_client.query(f"SELECT * FROM {ch_table_name}")
                existing_rows_set = set()
                
                for existing_row in existing_result.result_rows:
                    # Convert row to tuple for comparison
                    row_tuple = tuple(None if val is None else val for val in existing_row)
                    existing_rows_set.add(row_tuple)
                
                logger.info(f"Found {len(existing_rows_set)} existing rows in ClickHouse")
                
                # Filter new rows
                new_rows = []
                for row in rows:
                    row_tuple = tuple(None if row[col] is None else row[col] for col in col_names)
                    if row_tuple not in existing_rows_set:
                        new_rows.append(row)
                
                rows = new_rows
                logger.info(f"Found {len(rows)} new rows to insert (after filtering duplicates)")
            except Exception as e:
                logger.warning(f"Could not fetch existing data for comparison: {str(e)}")
                logger.info("Proceeding with full migration (may create duplicates)")
    else:
        logger.info(f"New table detected, migrating all {total_rows} rows")
    
    if len(rows) == 0:
        logger.info(f"No new rows to insert for table {table_name}")
        pg_cursor.close()
        return
    
    # Prepare data for ClickHouse insertion
    data_to_insert = []
    for row in rows:
        row_data = []
        for col in col_names:
            value = row[col]
            # Handle None values
            if value is None:
                row_data.append(None)
            else:
                row_data.append(value)
        data_to_insert.append(row_data)
    
    # Insert data into ClickHouse in batches
    batch_size = 1000
    inserted_count = 0
    
    for i in range(0, len(data_to_insert), batch_size):
        batch = data_to_insert[i:i + batch_size]
        try:
            ch_client.insert(ch_table_name, batch, column_names=col_names)
            inserted_count += len(batch)
            logger.info(f"Inserted {inserted_count}/{len(data_to_insert)} rows into {ch_table_name}")
        except Exception as e:
            logger.error(f"Error inserting batch into {ch_table_name}: {str(e)}")
            raise
    
    logger.info(f"Successfully migrated {inserted_count} new rows from {table_name} to {ch_table_name}")
    pg_cursor.close()


def main():
    """
    Main migration function
    """
    logger.info("Starting PostgreSQL to ClickHouse migration")
    
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
        tables = get_postgresql_tables(pg_conn)
        logger.info(f"Found {len(tables)} tables to migrate: {tables}")
        
        if len(tables) == 0:
            logger.warning("No tables found in PostgreSQL public schema")
            return
        
        # Migrate each table
        for table_name in tables:
            logger.info(f"\n{'='*60}")
            logger.info(f"Migrating table: {table_name}")
            logger.info(f"{'='*60}")
            
            try:
                # Check if table already exists in ClickHouse
                table_exists = table_exists_in_clickhouse(ch_client, table_name)
                
                # Get table schema
                columns = get_table_schema(pg_conn, table_name)
                logger.info(f"Table {table_name} has {len(columns)} columns")
                
                # Create ClickHouse table (only if it doesn't exist)
                create_clickhouse_table(ch_client, table_name, columns)
                
                # Migrate data (incremental if table exists, full if new)
                migrate_table_data(pg_conn, ch_client, table_name, columns, is_new_table=not table_exists)
                
                logger.info(f"Successfully migrated table: {table_name} -> HR_{table_name}")
                
            except Exception as e:
                logger.error(f"Error migrating table {table_name}: {str(e)}")
                logger.exception("Full error traceback:")
                continue
        
        logger.info("\n" + "="*60)
        logger.info("Migration completed!")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        logger.exception("Full error traceback:")
    finally:
        pg_conn.close()
        logger.info("Closed database connections")


if __name__ == "__main__":
    main()

