"""
Incremental SQL Server to PostgreSQL Migration Tool with Scheduling
This script performs incremental migration of only new/changed data from SQL Server to PostgreSQL.
Supports scheduled execution using the schedule library.
"""

import os
import sys
import yaml
import pyodbc
import pandas as pd
import logging
import threading
import time
import hashlib
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine, text, inspect
from urllib.parse import quote_plus

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()
except ImportError:
    pass

# Schedule library
try:
    import schedule
except ImportError:
    print("ERROR: schedule library not installed. Install it with: pip install schedule")
    sys.exit(1)

# ==================== CONFIGURATION ====================

# Configuration file path (relative to script location)
CONFIG_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'config', 'db_connections.yaml')
)

# Batch size for data transfer
BATCH_SIZE = int(os.environ.get('HYBRID_SYNC_BATCH_SIZE', '5000'))

# Simple terminal mode (minimal output)
SIMPLE_TERMINAL = os.environ.get('HYBRID_SYNC_SIMPLE_TERMINAL', '1').lower() in ('1', 'true', 'yes')

# ==================== LOGGING SETUP ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('final_incre_sync.log'),
        logging.StreamHandler()
    ],
    force=True
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ==================== CONFIGURATION LOADING ====================

def load_config():
    """Load configuration from YAML file"""
    if not os.path.exists(CONFIG_PATH):
        logger.error(f"Configuration file not found: {CONFIG_PATH}")
        raise FileNotFoundError(f"Configuration file not found: {CONFIG_PATH}")
    
    with open(CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)
    
    if not config:
        raise ValueError("Configuration file is empty or invalid")
    
    return config

# ==================== DATABASE CONNECTIONS ====================

def get_pg_engine(target_db=None):
    """Get PostgreSQL engine"""
    config = load_config()
    pg_conf = config['postgresql']
    
    # Override with environment variables if available
    db_name = target_db or os.environ.get('PG_DATABASE') or pg_conf.get('database')
    host = os.environ.get('PG_HOST') or pg_conf.get('host', 'localhost')
    port = os.environ.get('PG_PORT') or pg_conf.get('port', 5432)
    username = os.environ.get('PG_USERNAME') or pg_conf.get('username')
    password = os.environ.get('PG_PASSWORD') or pg_conf.get('password')
    
    if not all([db_name, host, port, username, password]):
        raise ValueError("PostgreSQL configuration incomplete. Check config file or environment variables.")
    
    conn_str = f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{db_name}"
    return create_engine(conn_str)

def get_sql_connection(conf, database=None):
    """Get SQL Server connection using pyodbc"""
    server = conf['server']
    
    # Check authentication type
    username = conf.get('username', '')
    password = conf.get('password', '')
    use_windows_auth = username.lower() in ['windows', 'trusted', ''] or password.lower() in ['windows', 'trusted', '']
    
    # Handle named instances
    is_named_instance = "\\" in server
    escaped_server = server.replace("\\", "\\\\") if not is_named_instance else server
    
    # Build connection string
    conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={escaped_server};"
    
    if use_windows_auth:
        conn_str += "Trusted_Connection=yes;"
    else:
        conn_str += f"UID={username};PWD={password};"
    
    if database:
        conn_str += f"DATABASE={database};"
    
    conn_str += "MARS_Connection=Yes;Timeout=60;Pooling=No;"
    
    if is_named_instance:
        conn_str += "Encrypt=No;TrustServerCertificate=Yes;"
    
    try:
        conn = pyodbc.connect(conn_str)
        logger.info(f"Connected to SQL Server: {server}")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to SQL Server '{server}': {e}")
        raise

def get_sqlalchemy_engine(conf, database=None):
    """Get SQLAlchemy engine for SQL Server"""
    username = conf.get('username', '')
    password = conf.get('password', '')
    server = conf['server']
    db = database if database else "master"
    
    driver = quote_plus("ODBC Driver 17 for SQL Server")
    
    if "\\" in server:
        # Named instance - use odbc_connect
        if username.lower() in ['windows', 'trusted', ''] or password.lower() in ['windows', 'trusted', '']:
            odbc_conn = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};"
                f"DATABASE={db};Trusted_Connection=yes;Timeout=60;Encrypt=No;TrustServerCertificate=Yes;MARS_Connection=Yes;Pooling=No;"
            )
        else:
            odbc_conn = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};"
                f"DATABASE={db};UID={username};PWD={password};Timeout=60;Encrypt=No;TrustServerCertificate=Yes;MARS_Connection=Yes;Pooling=No;"
            )
        conn_url = 'mssql+pyodbc:///?odbc_connect=' + quote_plus(odbc_conn)
    else:
        # Standard connection
        if username.lower() in ['windows', 'trusted', ''] or password.lower() in ['windows', 'trusted', '']:
            conn_url = f"mssql+pyodbc://@{server}/{db}?driver={driver}&Trusted_Connection=yes"
        else:
            password_enc = quote_plus(password)
            conn_url = f"mssql+pyodbc://{username}:{password_enc}@{server}/{db}?driver={driver}"
    
    return create_engine(conn_url, fast_executemany=True)

# ==================== SCHEMA MANAGEMENT ====================

def create_schema_if_not_exists(engine, schema):
    """Create PostgreSQL schema if it doesn't exist"""
    with engine.connect() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
        conn.commit()

def get_pg_columns(engine, schema, table_name):
    """Get existing columns from PostgreSQL table"""
    insp = inspect(engine)
    try:
        cols = insp.get_columns(table_name, schema=schema)
        return {c['name']: c for c in cols}
    except Exception:
        return {}

def infer_pg_type_from_series(series: pd.Series) -> str:
    """Infer PostgreSQL data type from pandas series"""
    if pd.api.types.is_integer_dtype(series):
        return 'BIGINT'
    if pd.api.types.is_float_dtype(series):
        return 'DOUBLE PRECISION'
    if pd.api.types.is_bool_dtype(series):
        return 'BOOLEAN'
    if pd.api.types.is_datetime64_any_dtype(series):
        return 'TIMESTAMP'
    return 'TEXT'

def ensure_table_and_columns(engine, schema, table_name, df: pd.DataFrame):
    """Ensure table exists with proper columns"""
    create_schema_if_not_exists(engine, schema)
    existing_cols = get_pg_columns(engine, schema, table_name)
    
    if not existing_cols:
        # Create new table
        columns = []
        for col_name, series in df.items():
            pg_type = infer_pg_type_from_series(series)
            clean_col_name = ''.join(c for c in col_name if c.isalnum() or c in '_-')
            columns.append(f'"{clean_col_name}" {pg_type}')
        
        columns_def = ', '.join(columns)
        create_table_sql = f'CREATE TABLE IF NOT EXISTS "{schema}"."{table_name}" ({columns_def})'
        
        with engine.connect() as conn:
            conn.execute(text(create_table_sql))
            conn.commit()
    else:
        # Add missing columns
        missing = [c for c in df.columns if c not in existing_cols]
        if missing:
            alter_parts = []
            for col in missing:
                col_type = infer_pg_type_from_series(df[col])
                safe_col = ''.join(ch for ch in col if ch.isalnum() or ch in '_-')
                alter_parts.append(f'ADD COLUMN "{safe_col}" {col_type}')
            
            if alter_parts:
                sql = f'ALTER TABLE "{schema}"."{table_name}" ' + ', '.join(alter_parts)
                with engine.connect() as conn:
                    conn.execute(text(sql))
                    conn.commit()
                logger.info(f"Added columns on {schema}.{table_name}: {missing}")

# ==================== SYNC TRACKING ====================

def create_sync_tracking_table(engine):
    """Create table to track database sync status"""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS sync_database_status (
        server_name VARCHAR(100),
        database_name VARCHAR(100),
        last_full_sync TIMESTAMP,
        last_incremental_sync TIMESTAMP,
        sync_status VARCHAR(20),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (server_name, database_name)
    )
    """
    with engine.connect() as conn:
        conn.execute(text(create_table_sql))
        conn.commit()

def create_table_sync_tracking(engine):
    """Create table to track table-level sync status"""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS sync_table_status (
        server_name VARCHAR(100),
        database_name VARCHAR(100),
        schema_name VARCHAR(100),
        table_name VARCHAR(100),
        last_pk_value VARCHAR(255),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (server_name, database_name, schema_name, table_name)
    )
    """
    with engine.connect() as conn:
        conn.execute(text(create_table_sql))
        conn.commit()

def get_last_synced_pk(engine, server_name, database_name, schema, table):
    """Get last synced primary key/timestamp value"""
    query = """
    SELECT last_pk_value
    FROM sync_table_status
    WHERE server_name = :server_name AND database_name = :database_name AND schema_name = :schema AND table_name = :table
    """
    with engine.connect() as conn:
        result = conn.execute(
            text(query),
            {
                "server_name": server_name,
                "database_name": database_name,
                "schema": schema,
                "table": table,
            },
        )
        row = result.fetchone()
        return row[0] if row else None

def update_last_synced_pk(engine, server_name, database_name, schema, table, pk_value):
    """Update last synced primary key value"""
    if hasattr(pk_value, 'item'):
        pk_value = pk_value.item()
    
    query = """
    INSERT INTO sync_table_status (server_name, database_name, schema_name, table_name, last_pk_value, updated_at)
    VALUES (:server_name, :database_name, :schema, :table, :pk_value, :now)
    ON CONFLICT (server_name, database_name, schema_name, table_name) 
    DO UPDATE SET 
        last_pk_value = EXCLUDED.last_pk_value,
        updated_at = EXCLUDED.updated_at
    """
    
    with engine.connect() as conn:
        conn.execute(
            text(query),
            {
                "server_name": server_name,
                "database_name": database_name,
                "schema": schema,
                "table": table,
                "pk_value": str(pk_value) if pk_value is not None else None,
                "now": datetime.now(),
            },
        )
        conn.commit()

def update_sync_status(engine, server_name, database_name, sync_type, sync_status):
    """Update sync status for a database"""
    now = datetime.now()
    query = """
    INSERT INTO sync_database_status (server_name, database_name, last_incremental_sync, sync_status, updated_at)
    VALUES (:server_name, :database_name, :now, :sync_status, :now)
    ON CONFLICT (server_name, database_name) 
    DO UPDATE SET 
        last_incremental_sync = EXCLUDED.last_incremental_sync,
        sync_status = EXCLUDED.sync_status,
        updated_at = EXCLUDED.updated_at
    """
    
    with engine.connect() as conn:
        conn.execute(
            text(query),
            {
                "server_name": server_name,
                "database_name": database_name,
                "now": now,
                "sync_status": sync_status,
            },
        )
        conn.commit()

# ==================== HELPER FUNCTIONS ====================

def get_all_databases(conn):
    """Get list of all user databases on the server"""
    cursor = conn.cursor()
    databases = []
    query = """
    SELECT name 
    FROM sys.databases 
    WHERE state = 0  
    AND name NOT IN ('master', 'tempdb', 'model', 'msdb', 'distribution', 'ReportServer', 'ReportServerTempDB')
    ORDER BY name
    """
    cursor.execute(query)
    for row in cursor.fetchall():
        databases.append(row[0])
    return databases

def should_skip_table(schema, table):
    """Check if table should be skipped"""
    if schema.lower() == 'sys':
        return True
    system_tables = {
        'sys.trace_xe_event_map',
        'sys.trace_xe_action_map',
    }
    return f"{schema}.{table}" in system_tables

def get_primary_key_info(conn, schema, table):
    """Get primary key columns for a table"""
    try:
        query = f"""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = '{schema}' 
        AND TABLE_NAME = '{table}'
        AND CONSTRAINT_NAME LIKE 'PK_%'
        ORDER BY ORDINAL_POSITION
        """
        cursor = conn.cursor()
        cursor.execute(query)
        return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        logger.warning(f"Could not get PK info for {schema}.{table}: {e}")
        return []

def get_timestamp_column(conn, schema, table):
    """Get timestamp column for a table"""
    try:
        query = f"""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = '{schema}' 
        AND TABLE_NAME = '{table}'
        AND DATA_TYPE IN ('datetime', 'datetime2', 'smalldatetime', 'timestamp')
        ORDER BY COLUMN_NAME
        """
        cursor = conn.cursor()
        cursor.execute(query)
        cols = [row[0] for row in cursor.fetchall()]
        return cols[0] if cols else None
    except Exception as e:
        logger.warning(f"Could not get timestamp column for {schema}.{table}: {e}")
        return None

def get_unique_identifier_column(conn, schema, table):
    """Get unique identifier column for a table"""
    try:
        query = f"""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = '{schema}' 
        AND TABLE_NAME = '{table}'
        AND DATA_TYPE IN ('uniqueidentifier', 'int', 'bigint')
        ORDER BY COLUMN_NAME
        """
        cursor = conn.cursor()
        cursor.execute(query)
        cols = [row[0] for row in cursor.fetchall()]
        return cols[0] if cols else None
    except Exception as e:
        logger.warning(f"Could not get unique identifier column for {schema}.{table}: {e}")
        return None

def get_best_sync_column(conn, schema, table, df_columns=None):
    """Select the best column for syncing"""
    # First try primary key
    pk_columns = get_primary_key_info(conn, schema, table)
    if pk_columns and (df_columns is None or pk_columns[0] in df_columns):
        return pk_columns[0], 'pk'
    
    # Try timestamp column
    ts_col = get_timestamp_column(conn, schema, table)
    if ts_col and (df_columns is None or ts_col in df_columns):
        return ts_col, 'timestamp'
    
    # Try unique identifier
    uid_col = get_unique_identifier_column(conn, schema, table)
    if uid_col and (df_columns is None or uid_col in df_columns):
        return uid_col, 'uid'
    
    return None, None

def _coerce_param(value):
    """Coerce numpy/pandas types to native Python types"""
    if value is None:
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    try:
        if hasattr(value, 'item'):
            return value.item()
    except Exception:
        pass
    return value

def calculate_row_hash(row, hash_columns):
    """Calculate deterministic hash of row values"""
    values = []
    for col in hash_columns:
        val = row[col]
        if pd.isna(val):
            values.append('NULL')
        elif isinstance(val, (pd.Timestamp, datetime)):
            values.append(val.isoformat())
        else:
            values.append(str(val))
    row_str = '|'.join(values)
    return hashlib.md5(row_str.encode('utf-8')).hexdigest()

def batch_fetch_new_rows(engine, schema, table, sync_column, last_value, batch_size):
    """Yield batches of new rows ordered by sync_column"""
    next_marker = last_value
    
    # Get total count for progress tracking
    count_query = f"""
        SELECT COUNT(*) as total_count
        FROM [{schema}].[{table}]
        WHERE [{sync_column}] > ?
    """
    
    with engine.raw_connection().cursor() as cursor:
        cursor.execute(count_query, [_coerce_param(last_value if last_value is not None else -1)])
        total_count = cursor.fetchone()[0]
    
    if total_count == 0:
        logger.info(f"No new records to sync in {schema}.{table}")
        return
    
    logger.info(f"Found {total_count} new records to sync in {schema}.{table}")
    
    processed = 0
    while True:
        query = f"""
            SELECT TOP ({int(batch_size)}) * 
            FROM [{schema}].[{table}]
            WHERE [{sync_column}] > ?
            ORDER BY [{sync_column}] ASC
        """
        
        try:
            with engine.raw_connection().cursor() as cursor:
                cursor.execute(query, [_coerce_param(next_marker if next_marker is not None else -1)])
                
                columns = [column[0] for column in cursor.description]
                rows = cursor.fetchall()
                
                if not rows:
                    break
                
                df = pd.DataFrame.from_records(rows, columns=columns)
                
                if df.empty:
                    break
                
                next_marker = df[sync_column].max()
                processed += len(df)
                
                progress = (processed / total_count) * 100 if total_count > 0 else 0
                logger.info(f"Processing {schema}.{table}: {processed}/{total_count} records ({progress:.1f}%)")
                
                yield df, next_marker
                
        except Exception as e:
            logger.error(f"Error fetching batch from {schema}.{table}: {str(e)}")
            raise

# ==================== INCREMENTAL SYNC LOGIC ====================

def incremental_sync_table(pg_engine, server_conf, db_name, server_clean, sql_engine, conn, schema, table):
    """Perform incremental sync of a table from SQL Server to PostgreSQL"""
    if should_skip_table(schema, table):
        return 0
    
    try:
        logger.info(f"Starting incremental sync for {schema}.{table}")
        
        # Get schema information
        schema_query = f"""
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = '{schema}' AND TABLE_NAME = '{table}'
        ORDER BY ORDINAL_POSITION
        """
        schema_df = pd.read_sql(schema_query, sql_engine)
        
        if not schema_df.empty:
            # Create empty DataFrame with correct schema
            column_types = {}
            for _, row in schema_df.iterrows():
                col_name = row['COLUMN_NAME']
                data_type = row['DATA_TYPE']
                if data_type in ('int', 'bigint', 'smallint', 'tinyint'):
                    column_types[col_name] = 'int64'
                elif data_type in ('decimal', 'numeric', 'float', 'real'):
                    column_types[col_name] = 'float64'
                elif data_type in ('datetime', 'datetime2', 'smalldatetime', 'date'):
                    column_types[col_name] = 'datetime64[ns]'
                elif data_type in ('bit',):
                    column_types[col_name] = 'bool'
                else:
                    column_types[col_name] = 'object'
            
            empty_df = pd.DataFrame({col: pd.Series(dtype=dtype) for col, dtype in column_types.items()})
            schema_name = f"{server_clean}_{db_name}".replace('-', '_').replace(' ', '_')
            table_name = f"{schema}_{table}"
            ensure_table_and_columns(pg_engine, schema_name, table_name, empty_df)
        
        # Get last synced value
        last_value = get_last_synced_pk(pg_engine, server_conf['server'], db_name, schema, table)
        schema_name = f"{server_clean}_{db_name}".replace('-', '_').replace(' ', '_')
        table_name = f"{schema}_{table}"
        
        # Check if target table exists
        try:
            target_exists = False
            with pg_engine.connect() as pg_conn:
                check_query = f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = '{schema_name}'
                        AND table_name = '{table_name}'
                    )
                """
                target_exists = pg_conn.execute(text(check_query)).scalar()
            
            if not target_exists:
                logger.info(f"Target table doesn't exist. Performing initial sync.")
                # For initial sync, just do a full read
                query = f"SELECT * FROM [{schema}].[{table}]"
                df = pd.read_sql(query, sql_engine)
                if not df.empty:
                    df.to_sql(table_name, pg_engine, schema=schema_name, if_exists='append', index=False, chunksize=BATCH_SIZE)
                    sync_col, _ = get_best_sync_column(conn, schema, table, df.columns)
                    if sync_col and sync_col in df.columns:
                        update_last_synced_pk(pg_engine, server_conf['server'], db_name, schema, table, df[sync_col].max())
                    return len(df)
                return 0
        except Exception as e:
            logger.error(f"Error checking target table: {str(e)}")
            return 0
        
        # Get the best sync column
        sync_col, col_type = get_best_sync_column(conn, schema, table)
        if not sync_col:
            logger.warning(f"No suitable sync column found for {schema}.{table}, skipping incremental sync")
            return 0
        
        logger.info(f"Using {sync_col} ({col_type}) as sync column")
        processed = 0
        
        # Get primary key columns for deduplication
        pk_columns = get_primary_key_info(conn, schema, table)
        
        def get_effective_pk_columns(df_columns):
            """Get effective primary key columns"""
            if pk_columns and all(pk in df_columns for pk in pk_columns):
                return pk_columns
            elif sync_col and sync_col in df_columns:
                return [sync_col]
            return list(df_columns)
        
        if sync_col:
            if last_value is None:
                # First sync - fetch all data
                query = f"SELECT * FROM [{schema}].[{table}]"
                df = pd.read_sql(query, sql_engine)
                
                if df.empty:
                    return 0
                
                # Get existing data from target for deduplication
                try:
                    with pg_engine.connect() as pg_conn:
                        dst_df = pd.read_sql(f'SELECT * FROM "{schema_name}"."{table_name}"', pg_conn)
                except Exception:
                    dst_df = pd.DataFrame()
                
                if not dst_df.empty:
                    # Deduplicate using row hashes
                    hash_columns = get_effective_pk_columns(df.columns)
                    df['row_hash'] = df.apply(lambda row: calculate_row_hash(row, hash_columns), axis=1)
                    dst_df['row_hash'] = dst_df.apply(lambda row: calculate_row_hash(row, hash_columns), axis=1)
                    
                    new_rows_idx = df[~df['row_hash'].isin(dst_df['row_hash'])].index
                    df = df.drop('row_hash', axis=1)
                    
                    if len(new_rows_idx) > 0:
                        df.iloc[new_rows_idx].to_sql(table_name, pg_engine, schema=schema_name, 
                                                   if_exists='append', index=False, chunksize=BATCH_SIZE)
                        processed = len(new_rows_idx)
                        logger.info(f"Inserted {processed} new unique rows")
                else:
                    df.to_sql(table_name, pg_engine, schema=schema_name, 
                             if_exists='append', index=False, chunksize=BATCH_SIZE)
                    processed = len(df)
                    logger.info(f"Initial insert of {processed} rows")
                
                if sync_col in df.columns:
                    update_last_synced_pk(pg_engine, server_conf['server'], db_name, schema, table, df[sync_col].max())
            
            else:
                # Regular incremental sync with batching
                batch_count = 0
                for df, marker in batch_fetch_new_rows(sql_engine, schema, table, sync_col, last_value, BATCH_SIZE):
                    if df.empty:
                        continue
                    
                    batch_count += 1
                    logger.info(f"Processing batch {batch_count} for {schema}.{table}")
                    
                    # Get overlapping records from target for deduplication
                    min_val = df[sync_col].min()
                    max_val = df[sync_col].max()
                    
                    try:
                        overlap_query = f"""
                        SELECT * FROM "{schema_name}"."{table_name}" 
                        WHERE "{sync_col}" BETWEEN $1 AND $2
                        """
                        with pg_engine.connect() as pg_conn:
                            dst_df = pd.read_sql(overlap_query, pg_conn, 
                                               params=[_coerce_param(min_val), _coerce_param(max_val)])
                    except Exception as e:
                        logger.warning(f"Could not fetch overlapping records, assuming none: {e}")
                        dst_df = pd.DataFrame()
                    
                    if not dst_df.empty:
                        # Deduplicate against overlapping records
                        hash_columns = get_effective_pk_columns(df.columns)
                        df['row_hash'] = df.apply(lambda row: calculate_row_hash(row, hash_columns), axis=1)
                        dst_df['row_hash'] = dst_df.apply(lambda row: calculate_row_hash(row, hash_columns), axis=1)
                        
                        new_rows_idx = df[~df['row_hash'].isin(dst_df['row_hash'])].index
                        df = df.drop('row_hash', axis=1)
                        
                        if len(new_rows_idx) > 0:
                            df.iloc[new_rows_idx].to_sql(table_name, pg_engine, schema=schema_name,
                                                       if_exists='append', index=False, chunksize=BATCH_SIZE)
                            batch_processed = len(new_rows_idx)
                            processed += batch_processed
                            logger.info(f"Inserted {batch_processed} unique rows in batch {batch_count}")
                    else:
                        df.to_sql(table_name, pg_engine, schema=schema_name,
                                if_exists='append', index=False, chunksize=BATCH_SIZE)
                        processed += len(df)
                        logger.info(f"Inserted {len(df)} rows in batch {batch_count} (no overlap)")
                    
                    update_last_synced_pk(pg_engine, server_conf['server'], db_name, schema, table, marker)
                
                logger.info(f"Completed incremental sync of {processed} rows across {batch_count} batches")
        
        return processed
        
    except Exception as e:
        logger.error(f"Error during incremental sync of {schema}.{table}: {str(e)}")
        raise

def incremental_sync_database(sql_engine, conn, db_name, server_conf, server_clean, pg_engine):
    """Perform incremental sync of a database"""
    logger.info(f"=== Starting INCREMENTAL sync for database: {db_name} ===")
    
    cursor = conn.cursor()
    tables = []
    for row in cursor.tables(tableType='TABLE'):
        tables.append((row.table_schem, row.table_name))
    
    if not tables:
        logger.warning(f"No tables found in {db_name}.")
        return 0
    
    logger.info(f"Found {len(tables)} tables to process")
    processed_count = 0
    
    for i, (schema, table) in enumerate(tables, 1):
        try:
            row_count = get_table_row_count(conn, schema, table)
            pk_columns = get_primary_key_info(conn, schema, table)
            ts_col = get_timestamp_column(conn, schema, table)
            uid_col = get_unique_identifier_column(conn, schema, table)
            sync_col = pk_columns[0] if pk_columns else (ts_col if ts_col else uid_col)
            last_value = get_last_synced_pk(pg_engine, server_conf['server'], db_name, schema, table)
            
            logger.info(
                f"[INCR SYNC] {schema}.{table}: row_count={row_count}, sync_col={sync_col}, last_value={last_value}"
            )
            
            processed = incremental_sync_table(
                pg_engine, server_conf, db_name, server_clean, sql_engine, conn, schema, table
            )
            
            if not SIMPLE_TERMINAL:
                print(f" [OK] {schema}.{table} ({processed} rows)", flush=True)
            processed_count += 1
            
        except Exception as e:
            error_msg = f"Failed to sync {schema}.{table}: {e}"
            logger.error(error_msg)
            if not SIMPLE_TERMINAL:
                print(f" [ERROR] {schema}.{table}: {str(e)[:50]}...", flush=True)
    
    logger.info(f"=== INCREMENTAL sync completed for {db_name}, {processed_count}/{len(tables)} tables processed ===")
    return processed_count

def get_table_row_count(conn, schema, table):
    """Get row count for a table"""
    try:
        query = f"SELECT COUNT(*) FROM [{schema}].[{table}]"
        cursor = conn.cursor()
        cursor.execute(query)
        return cursor.fetchone()[0]
    except Exception as e:
        logger.warning(f"Could not get row count for {schema}.{table}: {e}")
        return 0

def process_sql_server_incremental(server_name, server_conf):
    """Process incremental sync for a SQL Server"""
    try:
        if SIMPLE_TERMINAL:
            print(f"=== INCREMENTAL SYNC STARTED for server: {server_name} ===", flush=True)
        logger.info(f"INCREMENTAL SYNC STARTED for {server_name}")
        
        if not SIMPLE_TERMINAL:
            print(f"[INIT] Initializing incremental sync for {server_name}...", flush=True)
        
        pg_engine = get_pg_engine(server_conf.get("target_postgres_db"))
        create_sync_tracking_table(pg_engine)
        create_table_sync_tracking(pg_engine)
        
        if not SIMPLE_TERMINAL:
            print(f"[OK] PostgreSQL connection established", flush=True)
            print(f"[INFO] Connecting to SQL Server {server_conf['server']}...", flush=True)
        
        master_conn = get_sql_connection(server_conf)
        logger.info(f"Connected to SQL Server: {server_conf['server']}")
        
        if not SIMPLE_TERMINAL:
            print(f"[OK] SQL Server connection established", flush=True)
            print(f"[INFO] Discovering databases...", flush=True)
        
        databases = get_all_databases(master_conn)
        master_conn.close()
        
        if not databases:
            logger.warning(f"No user databases found on {server_conf['server']}.")
            return
        
        logger.info(f"Found {len(databases)} databases on {server_conf['server']}")
        if SIMPLE_TERMINAL:
            print(f"[INFO] Found {len(databases)} databases", flush=True)
        else:
            print(f"[INFO] Found {len(databases)} databases: {', '.join(databases)}", flush=True)
        
        server_clean = ''.join(c for c in server_conf['server'] if c.isalnum() or c in '_-')
        processed_dbs = 0
        
        for db_name in databases:
            if db_name in server_conf.get('skip_databases', []):
                continue
            
            if SIMPLE_TERMINAL:
                print(f"=== DATABASE START: {db_name} ===", flush=True)
            logger.info(f"DATABASE START: {server_name}/{db_name}")
            
            db_conn = get_sql_connection(server_conf, db_name)
            sql_engine = get_sqlalchemy_engine(server_conf, db_name)
            
            try:
                if not SIMPLE_TERMINAL:
                    print(f"[INCREMENTAL SYNC] Performing INCREMENTAL sync for {db_name}", flush=True)
                
                processed = incremental_sync_database(sql_engine, db_conn, db_name, server_conf, server_clean, pg_engine)
                update_sync_status(pg_engine, server_conf['server'], db_name, 'incremental', 'COMPLETED')
                
                if SIMPLE_TERMINAL:
                    print(f"[DB COMPLETE] INCR {db_name}: {processed} tables", flush=True)
                else:
                    print(f"[OK] INCREMENTAL sync completed for {db_name}", flush=True)
                
                processed_dbs += 1
                
            finally:
                db_conn.close()
                sql_engine.dispose()
        
        if SIMPLE_TERMINAL:
            print(f"\n=== INCREMENTAL SYNC COMPLETE for server: {server_name} ===", flush=True)
            print(f"[COMPLETE] {processed_dbs}/{len(databases)} databases synced", flush=True)
        else:
            print(f"\n=== INCREMENTAL SYNC COMPLETE for server: {server_name} ===", flush=True)
            print(f"[COMPLETE] ALL DATABASES COMPLETED: {processed_dbs}/{len(databases)} databases synced", flush=True)
        
        logger.info(f"Completed incremental sync for {server_name}")
        
    except Exception as e:
        error_msg = f"Error processing {server_name}: {e}"
        logger.error(error_msg)
        print(f"[CRITICAL ERROR] {server_name}: {e}", flush=True)
        raise

# ==================== SCHEDULING ====================

scheduled_jobs = []
_scheduler_thread = None

def run_scheduler():
    """Run the scheduler loop"""
    while True:
        schedule.run_pending()
        time.sleep(1)

def _start_scheduler_thread():
    """Start scheduler thread"""
    global _scheduler_thread
    if _scheduler_thread is None or not _scheduler_thread.is_alive():
        _scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        _scheduler_thread.start()

def schedule_interval_sync(server_name, minutes):
    """Schedule interval-based incremental sync"""
    config = load_config()
    server_conf = config['sqlservers'].get(server_name)
    if not server_conf:
        raise ValueError(f"Server {server_name} not found in config")
    
    job_type = f"incremental_interval_{minutes}m"
    
    schedule.every(minutes).minutes.do(
        process_sql_server_incremental, server_name, server_conf
    ).tag(server_name, job_type)
    
    logger.info(f"Scheduled incremental sync for {server_name} every {minutes} minutes")
    _start_scheduler_thread()

def schedule_daily_sync(server_name, hour, minute):
    """Schedule daily incremental sync"""
    config = load_config()
    server_conf = config['sqlservers'].get(server_name)
    if not server_conf:
        raise ValueError(f"Server {server_name} not found in config")
    
    time_str = f"{hour:02d}:{minute:02d}"
    job_type = f"incremental_daily_{time_str}"
    
    schedule.every().day.at(time_str).do(
        process_sql_server_incremental, server_name, server_conf
    ).tag(server_name, job_type)
    
    logger.info(f"Scheduled daily incremental sync for {server_name} at {time_str}")
    _start_scheduler_thread()

# ==================== MAIN ====================

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Incremental SQL Server to PostgreSQL Migration Tool')
    parser.add_argument('--server', type=str, help='Server name from config to sync')
    parser.add_argument('--all', action='store_true', help='Sync all servers')
    parser.add_argument('--schedule-interval', type=int, metavar='MINUTES', help='Schedule interval sync (minutes)')
    parser.add_argument('--schedule-daily', type=str, metavar='HH:MM', help='Schedule daily sync (HH:MM format)')
    parser.add_argument('--run-scheduler', action='store_true', help='Run scheduler (keep script running)')
    
    args = parser.parse_args()
    
    config = load_config()
    sqlservers = config.get('sqlservers', {})
    
    if not sqlservers:
        logger.error("No SQL servers configured")
        return
    
    # Handle scheduling
    if args.schedule_interval and args.server:
        schedule_interval_sync(args.server, args.schedule_interval)
        print(f"✅ Scheduled incremental sync for {args.server} every {args.schedule_interval} minutes")
        args.run_scheduler = True
    
    if args.schedule_daily and args.server:
        try:
            hour, minute = map(int, args.schedule_daily.split(':'))
            schedule_daily_sync(args.server, hour, minute)
            print(f"✅ Scheduled daily incremental sync for {args.server} at {args.schedule_daily}")
            args.run_scheduler = True
        except ValueError:
            logger.error("Invalid time format. Use HH:MM (e.g., 02:30)")
            return
    
    # Run scheduler if needed
    if args.run_scheduler:
        print("🚀 Scheduler started. Press Ctrl+C to stop.")
        _start_scheduler_thread()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Scheduler stopped.")
            return
    
    # Execute syncs
    if args.all:
        for server_name, server_conf in sqlservers.items():
            process_sql_server_incremental(server_name, server_conf)
    elif args.server:
        if args.server not in sqlservers:
            logger.error(f"Server '{args.server}' not found in configuration")
            return
        process_sql_server_incremental(args.server, sqlservers[args.server])
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

