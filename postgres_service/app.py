"""
Flask Microservice for PostgreSQL to ClickHouse Migration
Accepts credentials in request body and performs full or incremental migration
"""

from flask import Flask, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
import clickhouse_connect
from typing import Dict, List, Any, Set, Tuple
import logging
import sys
import os

# Add the Scripts directory to path to import helper functions
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Scripts', 'Postgres'))

app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import helper functions from the migration scripts
# We'll need to extract and include these functions here
TABLE_PREFIX = "HR_"


def map_postgresql_to_clickhouse_type(pg_type: str) -> str:
    """Map PostgreSQL data types to ClickHouse data types"""
    type_mapping = {
        'smallint': 'Int16',
        'integer': 'Int32',
        'bigint': 'Int64',
        'serial': 'Int32',
        'bigserial': 'Int64',
        'smallserial': 'Int16',
        'real': 'Float32',
        'double precision': 'Float64',
        'numeric': 'Decimal64(2)',
        'decimal': 'Decimal64(2)',
        'money': 'Decimal64(2)',
        'boolean': 'UInt8',
        'character varying': 'String',
        'varchar': 'String',
        'character': 'FixedString(255)',
        'char': 'FixedString(255)',
        'text': 'String',
        'timestamp without time zone': 'DateTime',
        'timestamp with time zone': 'DateTime',
        'timestamp': 'DateTime',
        'date': 'Date',
        'time without time zone': 'String',
        'time with time zone': 'String',
        'interval': 'String',
        'bytea': 'String',
        'json': 'String',
        'jsonb': 'String',
        'uuid': 'UUID',
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


def table_exists_in_clickhouse(ch_client, table_name: str) -> bool:
    """Check if a table exists in ClickHouse"""
    ch_table_name = f"{TABLE_PREFIX}{table_name}"
    try:
        result = ch_client.command(f"EXISTS TABLE {ch_table_name}")
        return result == 1
    except Exception:
        return False


def create_clickhouse_table(ch_client, table_name: str, columns: List[Dict[str, Any]]):
    """Create a table in ClickHouse based on PostgreSQL schema"""
    ch_table_name = f"{TABLE_PREFIX}{table_name}"
    if table_exists_in_clickhouse(ch_client, table_name):
        logger.info(f"Table {ch_table_name} already exists, skipping creation")
        return
    
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


def migrate_table_data(pg_conn, ch_client, table_name: str, columns: List[Dict[str, Any]], is_new_table: bool = False):
    """Migrate data from PostgreSQL table to ClickHouse"""
    ch_table_name = f"{TABLE_PREFIX}{table_name}"
    col_names = [col['name'] for col in columns]
    col_names_str = ', '.join([f'"{col}"' for col in col_names])
    
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
    
    if not is_new_table:
        logger.info(f"Table {ch_table_name} already exists, checking for new rows only")
        pk_columns = get_primary_key_columns(pg_conn, table_name)
        if pk_columns:
            logger.info(f"Using primary key columns for duplicate detection: {pk_columns}")
            try:
                key_cols_str = ', '.join([f"`{col}`" for col in pk_columns])
                query = f"SELECT {key_cols_str} FROM {ch_table_name}"
                result = ch_client.query(query)
                existing_keys = set()
                for row in result.result_rows:
                    key_tuple = tuple(None if val is None else val for val in row)
                    existing_keys.add(key_tuple)
                logger.info(f"Found {len(existing_keys)} existing rows in ClickHouse")
                
                new_rows = []
                for row in rows:
                    key_values = tuple(None if row[col] is None else row[col] for col in pk_columns)
                    if key_values not in existing_keys:
                        new_rows.append(row)
                rows = new_rows
                logger.info(f"Found {len(rows)} new rows to insert (after filtering duplicates)")
            except Exception as e:
                logger.warning(f"Could not fetch existing keys from ClickHouse: {str(e)}")
    
    if len(rows) == 0:
        logger.info(f"No new rows to insert for table {table_name}")
        pg_cursor.close()
        return
    
    data_to_insert = []
    for row in rows:
        row_data = []
        for col in col_names:
            value = row[col]
            row_data.append(None if value is None else value)
        data_to_insert.append(row_data)
    
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
    
    logger.info(f"Successfully migrated {inserted_count} rows from {table_name} to {ch_table_name}")
    pg_cursor.close()


def perform_full_migration(pg_config: dict, ch_config: dict) -> dict:
    """Perform full migration from PostgreSQL to ClickHouse"""
    logger.info("Starting PostgreSQL to ClickHouse full migration")
    
    try:
        pg_conn = psycopg2.connect(
            host=pg_config['host'],
            port=pg_config.get('port', 5432),
            database=pg_config['database'],
            user=pg_config['username'],
            password=pg_config['password']
        )
        logger.info("Successfully connected to PostgreSQL")
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {str(e)}")
        raise
    
    try:
        ch_client = clickhouse_connect.get_client(
            host=ch_config['host'],
            username=ch_config['username'],
            password=ch_config['password'],
            database=ch_config['database']
        )
        logger.info("Successfully connected to ClickHouse")
    except Exception as e:
        logger.error(f"Failed to connect to ClickHouse: {str(e)}")
        pg_conn.close()
        raise
    
    results = {
        "success": True,
        "tables_migrated": [],
        "tables_failed": [],
        "total_tables": 0,
        "errors": []
    }
    
    try:
        tables = get_postgresql_tables(pg_conn)
        logger.info(f"Found {len(tables)} tables to migrate: {tables}")
        results["total_tables"] = len(tables)
        
        if len(tables) == 0:
            logger.warning("No tables found in PostgreSQL public schema")
            return results
        
        for table_name in tables:
            try:
                table_exists = table_exists_in_clickhouse(ch_client, table_name)
                columns = get_table_schema(pg_conn, table_name)
                logger.info(f"Table {table_name} has {len(columns)} columns")
                
                create_clickhouse_table(ch_client, table_name, columns)
                migrate_table_data(pg_conn, ch_client, table_name, columns, is_new_table=not table_exists)
                
                results["tables_migrated"].append(table_name)
                logger.info(f"Successfully migrated table: {table_name} -> {TABLE_PREFIX}{table_name}")
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error migrating table {table_name}: {error_msg}")
                results["tables_failed"].append({"table": table_name, "error": error_msg})
                results["errors"].append(f"{table_name}: {error_msg}")
        
        logger.info("Migration completed!")
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        results["success"] = False
        results["errors"].append(str(e))
    finally:
        pg_conn.close()
        logger.info("Closed database connections")
    
    results["success"] = len(results["tables_failed"]) == 0
    return results


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "postgres_migration"}), 200


@app.route('/migrate/full', methods=['POST'])
def full_migration():
    """Full migration endpoint - accepts credentials in request body"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        # Validate PostgreSQL config
        pg_config = data.get('postgres')
        if not pg_config:
            return jsonify({"error": "postgres configuration is required"}), 400
        
        required_pg_fields = ['host', 'database', 'username', 'password']
        for field in required_pg_fields:
            if field not in pg_config:
                return jsonify({"error": f"postgres.{field} is required"}), 400
        
        # Validate ClickHouse config
        ch_config = data.get('clickhouse')
        if not ch_config:
            return jsonify({"error": "clickhouse configuration is required"}), 400
        
        required_ch_fields = ['host', 'database', 'username', 'password']
        for field in required_ch_fields:
            if field not in ch_config:
                return jsonify({"error": f"clickhouse.{field} is required"}), 400
        
        # Perform migration
        result = perform_full_migration(pg_config, ch_config)
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
        
    except Exception as e:
        logger.error(f"Error in full_migration endpoint: {str(e)}")
        return jsonify({"error": str(e), "success": False}), 500


@app.route('/migrate/incremental', methods=['POST'])
def incremental_migration():
    """Incremental migration endpoint - accepts credentials in request body"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        # Validate PostgreSQL config
        pg_config = data.get('postgres')
        if not pg_config:
            return jsonify({"error": "postgres configuration is required"}), 400
        
        required_pg_fields = ['host', 'database', 'username', 'password']
        for field in required_pg_fields:
            if field not in pg_config:
                return jsonify({"error": f"postgres.{field} is required"}), 400
        
        # Validate ClickHouse config
        ch_config = data.get('clickhouse')
        if not ch_config:
            return jsonify({"error": "clickhouse configuration is required"}), 400
        
        required_ch_fields = ['host', 'database', 'username', 'password']
        for field in required_ch_fields:
            if field not in ch_config:
                return jsonify({"error": f"clickhouse.{field} is required"}), 400
        
        # For incremental, we use the same logic but with is_new_table=False
        # In a real implementation, you'd use the sync_table logic from post_increment.py
        # For now, we'll call full migration but mark tables as existing
        logger.info("Starting incremental migration (using existing table logic)")
        result = perform_full_migration(pg_config, ch_config)
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
        
    except Exception as e:
        logger.error(f"Error in incremental_migration endpoint: {str(e)}")
        return jsonify({"error": str(e), "success": False}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)

