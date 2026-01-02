"""
ClickHouse Destination Adapter
"""
import clickhouse_connect
from typing import List, Dict, Any
import logging
from .base_destination import BaseDestinationAdapter

logger = logging.getLogger(__name__)


class ClickHouseDestinationAdapter(BaseDestinationAdapter):
    """ClickHouse database destination adapter"""
    
    def __init__(self):
        self.client = None
        self.config = None
    
    def connect(self, config: Dict[str, Any]) -> bool:
        """Connect to ClickHouse (clickhouse_connect uses HTTP API on port 8123, but handles port 9000 by trying 8123)"""
        try:
            self.config = config
            port = config.get('port', 8123)
            
            # clickhouse_connect uses HTTP API which typically runs on port 8123
            # If user specified port 9000 (native protocol), try 8123 first (HTTP API)
            # If that fails, try the specified port
            if port == 9000:
                try:
                    logger.info(f"Port 9000 specified, trying HTTP API port 8123 first...")
                    self.client = clickhouse_connect.get_client(
                        host=config['host'],
                        port=8123,  # HTTP API port (clickhouse_connect uses HTTP)
                        username=config['username'],
                        password=config['password'],
                        database=config['database']
                    )
                    logger.info(f"Connected to ClickHouse via HTTP API: {config['host']}:8123/{config['database']}")
                except Exception as e1:
                    logger.warning(f"Failed to connect on port 8123: {e1}. Trying specified port 9000...")
                    try:
                        self.client = clickhouse_connect.get_client(
                            host=config['host'],
                            port=port,
                            username=config['username'],
                            password=config['password'],
                            database=config['database']
                        )
                        logger.info(f"Connected to ClickHouse: {config['host']}:{port}/{config['database']}")
                    except Exception as e2:
                        logger.error(f"Failed to connect on port {port}: {e2}")
                        raise ConnectionError(f"Failed to connect to ClickHouse on port {port} or 8123: {e2}")
            else:
                self.client = clickhouse_connect.get_client(
                    host=config['host'],
                    port=port,
                    username=config['username'],
                    password=config['password'],
                    database=config['database']
                )
                logger.info(f"Connected to ClickHouse: {config['host']}:{port}/{config['database']}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to connect to ClickHouse: {str(e)}")
            raise ConnectionError(f"Failed to connect to ClickHouse: {str(e)}")
    
    def disconnect(self):
        """Close ClickHouse connection"""
        if self.client:
            self.client.close()
            self.client = None
    
    def test_connection(self, config: Dict[str, Any]) -> bool:
        """Test ClickHouse connection"""
        try:
            port = config.get('port', 8123)
            # If port is 9000, try 8123 first (HTTP API)
            if port == 9000:
                try:
                    client = clickhouse_connect.get_client(
                        host=config['host'],
                        port=8123,
                        username=config['username'],
                        password=config['password'],
                        database=config['database']
                    )
                    client.close()
                    return True
                except:
                    # Try the specified port
                    pass
            
            client = clickhouse_connect.get_client(
                host=config['host'],
                port=port,
                username=config['username'],
                password=config['password'],
                database=config['database']
            )
            client.close()
            return True
        except:
            return False
    
    def map_types(self, source_schema: List[Dict[str, Any]], source_type: str = None) -> List[Dict[str, Any]]:
        """Map PostgreSQL types to ClickHouse types (matching working script logic)"""
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
        
        dest_schema = []
        for col in source_schema:
            # Use full_type if available (from updated PostgreSQL source), otherwise use type
            pg_type = col.get('full_type', col.get('type', 'string'))
            ch_type = map_postgresql_to_clickhouse_type(pg_type)
            
            # Handle nullable
            nullable = col.get('nullable', False)
            if nullable:
                ch_type = f'Nullable({ch_type})'
            
            dest_schema.append({
                "name": col['name'],
                "type": ch_type
            })
        
        return dest_schema
    
    def _sanitize_column_name(self, name: str, used_names: set) -> str:
        """Convert field names into ClickHouse-safe identifiers (matching working script)"""
        import re
        sanitized = re.sub(r"[^0-9a-zA-Z_]", "_", name or "field")
        if sanitized and sanitized[0].isdigit():
            sanitized = f"_{sanitized}"
        sanitized = sanitized.lower()
        base = sanitized or "field"
        counter = 1
        candidate = base
        while candidate in used_names:
            candidate = f"{base}_{counter}"
            counter += 1
        used_names.add(candidate)
        return candidate
    
    def _get_table_name(self, table_name: str, source_type: str = None) -> str:
        """Get ClickHouse table name with appropriate prefix"""
        if source_type == "zoho":
            return f"zoho_{table_name.lower()}"
        elif source_type == "devops":
            # DevOps tables use exact names without prefix
            return table_name
        else:
            return f"HR_{table_name}"
    
    def table_exists(self, table_name: str, source_type: str = None) -> bool:
        """Check if a table exists in ClickHouse"""
        ch_table_name = self._get_table_name(table_name, source_type)
        try:
            result = self.client.command(f"EXISTS TABLE {ch_table_name}")
            return result == 1
        except Exception as e:
            logger.debug(f"Error checking table existence: {str(e)}")
            return False
    
    def create_table(self, table_name: str, schema: List[Dict[str, Any]], source_type: str = None):
        """Create table in ClickHouse if it doesn't exist (matching working script)"""
        ch_table_name = self._get_table_name(table_name, source_type)
        
        # Check if table exists (matching working script logic)
        if self.table_exists(table_name, source_type):
            logger.info(f"Table {ch_table_name} already exists, skipping creation")
            return
        
        # For DevOps tables, use special structure
        if source_type == "devops":
            create_sql = self._create_devops_table(ch_table_name, table_name, schema)
        # For Zoho tables, use special structure (matching working script)
        elif source_type == "zoho":
            # Get all field names and sanitize them
            used_names = {"id", "load_time"}
            column_map = {}
            for col in schema:
                if col['name'] != 'id':
                    column_map[col['name']] = self._sanitize_column_name(col['name'], used_names)
            
            # Build column definitions - all Nullable(String) for Zoho
            column_defs = []
            for field, sanitized_col in column_map.items():
                column_defs.append(f"`{sanitized_col}` Nullable(String)")
            
            column_section = ",\n            " + ",\n            ".join(column_defs) if column_defs else ""
            
            create_sql = f"""
        CREATE TABLE IF NOT EXISTS {ch_table_name} (
            id String{column_section},
            load_time DateTime DEFAULT now()
        )
        ENGINE = MergeTree()
        ORDER BY load_time
        """
        else:
            # For other sources, use standard structure
            columns = [f"`{col['name']}` {col['type']}" for col in schema]
            columns_def = ', '.join(columns)
            
            create_sql = f"""
        CREATE TABLE IF NOT EXISTS {ch_table_name} (
            {columns_def}
        ) ENGINE = MergeTree()
        ORDER BY tuple()
        """
        
        import time
        start_time = time.time()
        logger.info(f"Creating ClickHouse table: {ch_table_name}")
        logger.debug(f"SQL: {create_sql}")
        
        try:
            self.client.command(create_sql)
            elapsed = time.time() - start_time
            logger.info(f"Successfully created table: {ch_table_name} in {elapsed:.2f}s")
            
            # For Zoho tables, ensure all columns exist (add missing ones)
            if source_type == "zoho":
                try:
                    describe = self.client.query(f"DESCRIBE TABLE {ch_table_name}")
                    existing_columns = {row[0] for row in describe.result_rows}
                    
                    used_names = {"id", "load_time"}
                    column_map = {}
                    for col in schema:
                        if col['name'] != 'id':
                            column_map[col['name']] = self._sanitize_column_name(col['name'], used_names)
                    
                    for field, sanitized_col in column_map.items():
                        if sanitized_col not in existing_columns:
                            self.client.command(f"ALTER TABLE {ch_table_name} ADD COLUMN `{sanitized_col}` Nullable(String)")
                except Exception as e:
                    logger.warning(f"Could not ensure all columns exist: {e}")
        except Exception as e:
            logger.error(f"Error creating table {ch_table_name}: {str(e)}")
            raise
    
    def _create_devops_table(self, ch_table_name: str, table_name: str, schema: List[Dict[str, Any]]) -> str:
        """Create DevOps table with appropriate schema and ORDER BY"""
        # Fixed schema tables
        if table_name == "DEVOPS_PROJECTS":
            return f"""
        CREATE TABLE IF NOT EXISTS {ch_table_name} (
            `id` String,
            `name` Nullable(String),
            `description` Nullable(String),
            `state` Nullable(String),
            `revision` Nullable(Int64),
            `lastUpdateTime` Nullable(String)
        )
        ENGINE = MergeTree()
        ORDER BY id
        """
        elif table_name == "DEVOPS_TEAMS":
            return f"""
        CREATE TABLE IF NOT EXISTS {ch_table_name} (
            `id` String,
            `name` Nullable(String),
            `description` Nullable(String),
            `projectName` Nullable(String),
            `projectId` Nullable(String)
        )
        ENGINE = MergeTree()
        ORDER BY id
        """
        elif table_name == "DEVOPS_WORKITEMS_MAIN":
            # Dynamic schema - will be expanded during data write
            # Start with id as non-nullable String
            return f"""
        CREATE TABLE IF NOT EXISTS {ch_table_name} (
            `id` String
        )
        ENGINE = MergeTree()
        ORDER BY id
        """
        elif table_name == "DEVOPS_WORKITEMS_UPDATES":
            # Dynamic schema - will be expanded during data write
            # Start with work_item_id and rev as non-nullable
            return f"""
        CREATE TABLE IF NOT EXISTS {ch_table_name} (
            `work_item_id` String,
            `rev` Int64
        )
        ENGINE = MergeTree()
        ORDER BY rev
        """
        elif table_name == "DEVOPS_WORKITEMS_REVISIONS":
            # Dynamic schema - will be expanded during data write
            # Start with work_item_id and rev as non-nullable
            return f"""
        CREATE TABLE IF NOT EXISTS {ch_table_name} (
            `work_item_id` String,
            `rev` Int64
        )
        ENGINE = MergeTree()
        ORDER BY rev
        """
        elif table_name == "DEVOPS_WORKITEMS_COMMENTS":
            return f"""
        CREATE TABLE IF NOT EXISTS {ch_table_name} (
            `work_item_id` String,
            `comment_id` Nullable(String),
            `text` Nullable(String),
            `created_date` Nullable(String),
            `created_by` Nullable(String),
            `modified_date` Nullable(String),
            `modified_by` Nullable(String),
            `is_deleted` Nullable(Int64),
            load_time DateTime DEFAULT now()
        )
        ENGINE = MergeTree()
        ORDER BY load_time
        """
        elif table_name == "DEVOPS_WORKITEMS_RELATIONS":
            return f"""
        CREATE TABLE IF NOT EXISTS {ch_table_name} (
            `work_item_id` String,
            `relation_type` Nullable(String),
            `related_work_item_id` Nullable(String),
            `related_work_item_url` Nullable(String),
            `attributes_name` Nullable(String),
            load_time DateTime DEFAULT now()
        )
        ENGINE = MergeTree()
        ORDER BY load_time
        """
        else:
            # Fallback for unknown tables
            columns = [f"`{col['name']}` {col['type']}" for col in schema]
            columns_def = ', '.join(columns)
            return f"""
        CREATE TABLE IF NOT EXISTS {ch_table_name} (
            {columns_def}
        ) ENGINE = MergeTree()
        ORDER BY tuple()
        """
    
    def _get_existing_ids(self, table_name: str, source_type: str = None):
        """Get set of existing record IDs from ClickHouse table to prevent duplicates"""
        ch_table_name = self._get_table_name(table_name, source_type)
        try:
            result = self.client.query(f"SELECT id FROM {ch_table_name}")
            existing_ids = {str(row[0]) for row in result.result_rows}
            return existing_ids
        except Exception as e:
            # Table might not exist or be empty
            logger.debug(f"Could not fetch existing IDs for {ch_table_name}: {e}")
            return set()
    
    def write_data(self, table_name: str, data: List[Dict[str, Any]], batch_size: int = 1000, source_type: str = None):
        """Write data to ClickHouse (matching working script logic - with duplicate checking and dynamic column handling for Zoho and DevOps)"""
        if not data:
            return
        
        ch_table_name = self._get_table_name(table_name, source_type)
        
        try:
            if not data or len(data) == 0:
                return
            
            # For DevOps tables, handle dynamic schema and special requirements
            if source_type == "devops":
                self._write_devops_data(ch_table_name, table_name, data, batch_size)
            # For Zoho tables, handle duplicates and column mapping
            elif source_type == "zoho":
                # Get existing IDs to prevent duplication
                existing_ids = self._get_existing_ids(table_name, source_type)
                logger.info(f"{table_name}: Found {len(existing_ids)} existing records in {ch_table_name}")
                
                # Filter out records that already exist
                new_records = [record for record in data if str(record.get("id", "")) not in existing_ids]
                
                if not new_records:
                    logger.info(f"{table_name}: All {len(data)} records already exist in ClickHouse. Skipping insertion.")
                    return
                
                logger.info(f"{table_name}: Inserting {len(new_records)} new records (skipping {len(data) - len(new_records)} duplicates)")
                
                # Get all field names from all records (handle dynamic schema)
                all_fields = set()
                for record in new_records:
                    all_fields.update(record.keys())
                fields = sorted([f for f in all_fields if f != "id"])
                
                # Ensure all columns exist in the table
                try:
                    describe = self.client.query(f"DESCRIBE TABLE {ch_table_name}")
                    existing_columns = {row[0] for row in describe.result_rows}
                except Exception as e:
                    logger.warning(f"Could not describe table {ch_table_name}: {e}")
                    existing_columns = {"id", "load_time"}
                
                # Sanitize and map column names, add missing columns
                used_names = {"id", "load_time"}
                column_map = {}
                for field in fields:
                    sanitized = self._sanitize_column_name(field, used_names)
                    column_map[field] = sanitized
                    
                    # Add column if it doesn't exist
                    if sanitized not in existing_columns:
                        try:
                            self.client.command(f"ALTER TABLE {ch_table_name} ADD COLUMN IF NOT EXISTS `{sanitized}` Nullable(String)")
                            logger.debug(f"Added column {sanitized} to {ch_table_name}")
                        except Exception as e:
                            logger.warning(f"Could not add column {sanitized} to {ch_table_name}: {e}")
                
                # Build rows with sanitized column names
                column_names = ["id"] + [column_map[field] for field in fields]
                rows = []
                for record in new_records:
                    row = [str(record.get("id", ""))]
                    for field in fields:
                        row.append(record.get(field))
                    rows.append(row)
                
                if rows:
                    import time
                    insert_start = time.time()
                    total_inserted = 0
                    # Insert in batches to avoid memory issues
                    for i in range(0, len(rows), batch_size):
                        batch = rows[i:i + batch_size]
                        batch_start = time.time()
                        try:
                            self.client.insert(ch_table_name, batch, column_names=column_names)
                            batch_elapsed = time.time() - batch_start
                            total_inserted += len(batch)
                            logger.debug(f"{table_name}: Inserted batch {i//batch_size + 1} of {len(batch)} records in {batch_elapsed:.2f}s")
                        except Exception as e:
                            logger.error(f"Error inserting batch {i//batch_size + 1} for {table_name}: {e}")
                            # Try to insert records one by one to identify problematic records
                            for idx, single_row in enumerate(batch):
                                try:
                                    self.client.insert(ch_table_name, [single_row], column_names=column_names)
                                    total_inserted += 1
                                except Exception as e2:
                                    logger.error(f"Error inserting record {i + idx} for {table_name}: {e2}. Record ID: {single_row[0] if single_row else 'unknown'}")
                                    # Continue with next record
                            raise
                    
                    insert_elapsed = time.time() - insert_start
                    logger.info(f"{table_name}: Inserted {total_inserted} records into ClickHouse table {ch_table_name} in {insert_elapsed:.2f}s (avg {insert_elapsed/total_inserted*1000:.2f}ms/record)")
            else:
                # For other sources, use standard insertion
                columns = list(data[0].keys())
                if not columns:
                    logger.warning(f"No columns found in data for {table_name}")
                    return
                
                # Prepare data for ClickHouse insertion (matching working script)
                # Preserve None values - ClickHouse will handle them if column is Nullable
                rows = []
                for row in data:
                    row_values = []
                    for col in columns:
                        value = row.get(col)
                        # Preserve None values (don't convert to empty string)
                        row_values.append(value)
                    rows.append(row_values)
                
                # Insert data into ClickHouse (column names should match exactly)
                import time
                insert_start = time.time()
                self.client.insert(ch_table_name, rows, column_names=columns)
                insert_elapsed = time.time() - insert_start
                logger.debug(f"Inserted {len(data)} rows into {ch_table_name} in {insert_elapsed:.2f}s")
        except Exception as e:
            logger.error(f"Error writing to {ch_table_name}: {str(e)}")
            raise
    
    def _write_devops_data(self, ch_table_name: str, table_name: str, data: List[Dict[str, Any]], batch_size: int):
        """Write DevOps data to ClickHouse - matches script's save_to_table() function exactly"""
        if not data:
            logger.warning(f"{table_name}: No data to write")
            return
        
        logger.info(f"{table_name}: Writing {len(data)} records to {ch_table_name}")
        
        # For PROJECTS and TEAMS tables, delete existing data first (matching script's save_projects_to_table/save_teams_to_table)
        if table_name == "DEVOPS_PROJECTS" or table_name == "DEVOPS_TEAMS":
            try:
                self.client.command(f"ALTER TABLE {ch_table_name} DELETE WHERE 1=1")
                logger.info(f"{table_name}: Cleared existing data from {ch_table_name}")
            except Exception as e:
                logger.warning(f"{table_name}: Error clearing table (might be empty): {e}")
        
        # Flatten records using the exact flatten_json logic from script
        # For PROJECTS and TEAMS, data is already flat, so skip flattening
        flattened_records = []
        for record in data:
            if table_name == "DEVOPS_PROJECTS" or table_name == "DEVOPS_TEAMS":
                # Data is already flat, use as-is
                flattened_records.append(record)
            else:
                # Flatten nested structures for work item tables
                flattened = self._flatten_json_devops(record)
                flattened_records.append(flattened)
        
        # Get all fields from flattened records
        all_fields = set()
        for record in flattened_records:
            all_fields.update(record.keys())
        
        # Determine id_field based on table name (matching script logic)
        if any(x in table_name.lower() for x in ["relations", "comments", "updates", "revisions"]):
            if "work_item_id" in all_fields:
                id_field = "work_item_id"
            elif "comment_id" in all_fields:
                id_field = "comment_id"
            else:
                id_field = "id"
        else:
            id_field = "id"
        
        fields = sorted(all_fields - {id_field})
        
        # Sanitize column names (matching script's sanitize_column_name)
        used_names = {id_field}
        column_map = {field: self._sanitize_column_name(field, used_names) for field in fields}
        id_column_name = self._sanitize_column_name(id_field, set())
        
        # Check if table exists, create if not (matching script logic)
        try:
            describe = self.client.query(f"DESCRIBE TABLE {ch_table_name}")
            existing_columns = {row[0] for row in describe.result_rows}
            logger.debug(f"{table_name}: Table {ch_table_name} exists with {len(existing_columns)} columns")
        except Exception as e:
            # Table doesn't exist, create it (matching script's save_to_table logic)
            logger.info(f"{table_name}: Table {ch_table_name} doesn't exist, creating...")
            existing_columns = {id_column_name}
            columns_sql = [f"`{id_column_name}` Nullable(String)"]
            
            # Handle rev column specially for UPDATES and REVISIONS (must be Int64)
            if table_name == "DEVOPS_WORKITEMS_UPDATES" or table_name == "DEVOPS_WORKITEMS_REVISIONS":
                # Add rev as Int64 (non-nullable) for ORDER BY
                columns_sql.append("`rev` Int64")
                existing_columns.add("rev")
                # Remove rev from fields if it exists
                if "rev" in fields:
                    fields.remove("rev")
            
            columns_sql.extend([f"`{col}` Nullable(String)" for col in column_map.values() if col != "rev"])
            
            # Only add load_time for non-MAIN, non-REVISIONS, and non-UPDATES tables
            if table_name != "DEVOPS_WORKITEMS_MAIN" and table_name != "DEVOPS_WORKITEMS_REVISIONS" and table_name != "DEVOPS_WORKITEMS_UPDATES":
                columns_sql.append("load_time DateTime DEFAULT now()")
                existing_columns.add("load_time")
                order_by = "load_time"
            else:
                order_by = id_column_name
            
            # For MAIN, REVISIONS, and UPDATES tables, id/rev must be non-nullable for ORDER BY
            if table_name == "DEVOPS_WORKITEMS_MAIN":
                # Replace Nullable(String) with String for id column
                columns_sql[0] = f"`{id_column_name}` String"
                order_by = id_column_name
            elif table_name == "DEVOPS_WORKITEMS_REVISIONS" or table_name == "DEVOPS_WORKITEMS_UPDATES":
                # Use rev as ORDER BY for REVISIONS and UPDATES
                order_by = "rev"
            
            create_sql = f"""
            CREATE TABLE IF NOT EXISTS {ch_table_name} (
                {', '.join(columns_sql)}
            )
            ENGINE = MergeTree()
            ORDER BY {order_by}
            """
            try:
                self.client.command(create_sql)
                logger.info(f"{table_name}: Created table {ch_table_name}")
                # Re-describe to get actual columns
                describe = self.client.query(f"DESCRIBE TABLE {ch_table_name}")
                existing_columns = {row[0] for row in describe.result_rows}
            except Exception as e:
                logger.error(f"{table_name}: Error creating table {ch_table_name}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                # Fallback: create minimal table
                try:
                    if table_name != "DEVOPS_WORKITEMS_MAIN" and table_name != "DEVOPS_WORKITEMS_REVISIONS" and table_name != "DEVOPS_WORKITEMS_UPDATES":
                        self.client.command(f"""
                            CREATE TABLE IF NOT EXISTS {ch_table_name} (
                                `{id_column_name}` Nullable(String),
                                load_time DateTime DEFAULT now()
                            )
                            ENGINE = MergeTree()
                            ORDER BY load_time
                        """)
                        existing_columns = {id_column_name, "load_time"}
                    else:
                        if table_name == "DEVOPS_WORKITEMS_UPDATES" or table_name == "DEVOPS_WORKITEMS_REVISIONS":
                            self.client.command(f"""
                                CREATE TABLE IF NOT EXISTS {ch_table_name} (
                                    `{id_column_name}` String,
                                    `rev` Int64
                                )
                                ENGINE = MergeTree()
                                ORDER BY rev
                            """)
                            existing_columns = {id_column_name, "rev"}
                        else:
                            self.client.command(f"""
                                CREATE TABLE IF NOT EXISTS {ch_table_name} (
                                    `{id_column_name}` String
                                )
                                ENGINE = MergeTree()
                                ORDER BY {id_column_name}
                            """)
                            existing_columns = {id_column_name}
                except Exception as e2:
                    logger.error(f"{table_name}: Error creating fallback table {ch_table_name}: {e2}")
                    import traceback
                    logger.error(traceback.format_exc())
                    raise
        
        # Add missing columns (matching script logic)
        missing_columns = [col for col in column_map.values() if col not in existing_columns and col != "rev"]
        if missing_columns:
            logger.info(f"{table_name}: Adding {len(missing_columns)} missing columns to {ch_table_name}")
            try:
                alter_statements = [f"ADD COLUMN `{col}` Nullable(String)" for col in missing_columns]
                self.client.command(f"ALTER TABLE {ch_table_name} {', '.join(alter_statements)}")
                existing_columns.update(missing_columns)
            except Exception as e:
                logger.warning(f"{table_name}: Error adding columns in batch: {e}, trying one by one...")
                for col in missing_columns:
                    try:
                        self.client.command(f"ALTER TABLE {ch_table_name} ADD COLUMN `{col}` Nullable(String)")
                        existing_columns.add(col)
                    except Exception as e2:
                        logger.warning(f"{table_name}: Could not add column {col}: {e2}")
        
        # Build column names and rows (matching script logic)
        # For PROJECTS and TEAMS, use fixed column structure (matching script)
        if table_name == "DEVOPS_PROJECTS":
            column_names = ["id", "name", "description", "state", "revision", "lastUpdateTime"]
            rows = []
            for record in flattened_records:
                row = [
                    self._normalize_devops_value(record.get("id", "")),
                    self._normalize_devops_value(record.get("name", "")),
                    self._normalize_devops_value(record.get("description", "")),
                    self._normalize_devops_value(record.get("state", "")),
                    record.get("revision", 0) if record.get("revision") is not None else None,
                    self._normalize_devops_value(record.get("lastUpdateTime", ""))
                ]
                rows.append(row)
        elif table_name == "DEVOPS_TEAMS":
            column_names = ["id", "name", "description", "projectName", "projectId"]
            rows = []
            for record in flattened_records:
                row = [
                    self._normalize_devops_value(record.get("id", "")),
                    self._normalize_devops_value(record.get("name", "")),
                    self._normalize_devops_value(record.get("description", "")),
                    self._normalize_devops_value(record.get("projectName", "")),
                    self._normalize_devops_value(record.get("projectId", ""))
                ]
                rows.append(row)
        else:
            # For work item tables, use dynamic structure
            # For UPDATES and REVISIONS, rev must be included and be Int64
            column_names = [id_column_name]
            if (table_name == "DEVOPS_WORKITEMS_UPDATES" or table_name == "DEVOPS_WORKITEMS_REVISIONS") and "rev" in existing_columns:
                column_names.append("rev")
            
            column_names.extend([column_map[field] for field in fields if column_map[field] in existing_columns and column_map[field] != "rev"])
            
            rows = []
            for record in flattened_records:
                record_id = record.get(id_field) or record.get("id") or ""
                row = [self._normalize_devops_value(record_id)]
                
                # Add rev value for UPDATES and REVISIONS tables
                if (table_name == "DEVOPS_WORKITEMS_UPDATES" or table_name == "DEVOPS_WORKITEMS_REVISIONS") and "rev" in existing_columns:
                    rev_value = record.get("rev")
                    # Convert rev to int if it's a string
                    if rev_value is not None:
                        try:
                            rev_value = int(rev_value) if not isinstance(rev_value, int) else rev_value
                        except:
                            rev_value = 0
                    else:
                        rev_value = 0
                    row.append(rev_value)
                
                for field in fields:
                    if column_map[field] in existing_columns and column_map[field] != "rev":
                        row.append(self._normalize_devops_value(record.get(field)))
                rows.append(row)
        
        # Insert data (matching script logic - with/without load_time)
        if rows and column_names:
            try:
                import time
                insert_start = time.time()
                # For MAIN, REVISIONS, and UPDATES tables, don't include load_time
                if table_name == "DEVOPS_WORKITEMS_MAIN" or table_name == "DEVOPS_WORKITEMS_REVISIONS" or table_name == "DEVOPS_WORKITEMS_UPDATES":
                    # Insert in batches to avoid memory issues
                    for i in range(0, len(rows), batch_size):
                        batch = rows[i:i + batch_size]
                        batch_cols = column_names
                        self.client.insert(ch_table_name, batch, column_names=batch_cols)
                        logger.debug(f"{table_name}: Inserted batch {i//batch_size + 1} ({len(batch)} records)")
                else:
                    # For other tables, include load_time
                    from datetime import datetime
                    column_names_with_time = ["load_time"] + column_names
                    rows_with_time = [[datetime.now()] + row for row in rows]
                    # Insert in batches
                    for i in range(0, len(rows_with_time), batch_size):
                        batch = rows_with_time[i:i + batch_size]
                        self.client.insert(ch_table_name, batch, column_names=column_names_with_time)
                        logger.debug(f"{table_name}: Inserted batch {i//batch_size + 1} ({len(batch)} records)")
                
                insert_elapsed = time.time() - insert_start
                logger.info(f"{table_name}: Successfully inserted {len(rows)} records into {ch_table_name} in {insert_elapsed:.2f}s")
            except Exception as e:
                logger.error(f"{table_name}: Error inserting into {ch_table_name}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                # Try inserting without load_time as fallback
                try:
                    if table_name not in ["DEVOPS_WORKITEMS_MAIN", "DEVOPS_WORKITEMS_REVISIONS", "DEVOPS_WORKITEMS_UPDATES"]:
                        # Remove load_time and try again
                        rows_no_time = rows
                        self.client.insert(ch_table_name, rows_no_time, column_names=column_names)
                        logger.info(f"{table_name}: Inserted {len(rows)} records (without load_time)")
                except Exception as e2:
                    logger.error(f"{table_name}: Failed to insert data even without load_time: {e2}")
                    raise
        else:
            logger.warning(f"{table_name}: No rows to insert (rows: {len(rows) if rows else 0}, columns: {len(column_names) if column_names else 0})")
    
    def _flatten_json_devops(self, nested_dict, parent_key='', sep='_'):
        """Flatten nested JSON structure - exact copy of script's flatten_json function"""
        from collections.abc import MutableMapping
        import json
        
        if nested_dict is None:
            return {}
        
        if not isinstance(nested_dict, (dict, list, MutableMapping)):
            return {"value": nested_dict}
        
        items = []
        
        def flatten(obj, parent_key='', sep='_'):
            if obj is None:
                if parent_key:
                    items.append((parent_key, None))
                return
            
            if isinstance(obj, dict):
                if not obj:
                    if parent_key:
                        items.append((parent_key, None))
                    return
                for key, value in obj.items():
                    new_key = f"{parent_key}{sep}{key}" if parent_key else key
                    if isinstance(value, (dict, list)):
                        flatten(value, new_key, sep=sep)
                    else:
                        items.append((new_key, value))
            elif isinstance(obj, list):
                if not obj:
                    if parent_key:
                        items.append((parent_key, None))
                    return
                for idx, value in enumerate(obj):
                    new_key = f"{parent_key}{sep}{idx}" if parent_key else str(idx)
                    if isinstance(value, (dict, list)):
                        flatten(value, new_key, sep=sep)
                    else:
                        items.append((new_key, value))
            else:
                items.append((parent_key, obj))
        
        # Special handling for work items (matching script logic)
        if isinstance(nested_dict, dict) and "fields" in nested_dict and "id" in nested_dict:
            work_item_id = nested_dict.get("id")
            items.append(("id", work_item_id))
            
            fields_dict = nested_dict.get("fields", {})
            if isinstance(fields_dict, str):
                try:
                    fields_dict = json.loads(fields_dict)
                except:
                    fields_dict = {}
            if not isinstance(fields_dict, dict):
                fields_dict = {}
            
            for key, value in fields_dict.items():
                clean_key = key.replace("System.", "").replace("Microsoft.VSTS.", "").replace("Custom.", "")
                if isinstance(value, (dict, list)):
                    flatten(value, clean_key, sep=sep)
                else:
                    items.append((clean_key, value))
            
            for key, value in nested_dict.items():
                if key not in ["fields", "id"]:
                    new_key = key
                    if isinstance(value, (dict, list)):
                        flatten(value, new_key, sep=sep)
                    else:
                        items.append((new_key, value))
            
            return dict(items)
        
        flatten(nested_dict, parent_key, sep)
        return dict(items)
    
    def _normalize_devops_value(self, value):
        """Normalize values for ClickHouse (matching script's normalize_value)"""
        from datetime import datetime, date, time
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, time):
            return value.isoformat()
        if isinstance(value, bool):
            return str(value)
        if isinstance(value, (int, float)):
            return str(value)
        return str(value)
    
    def get_destination_type(self) -> str:
        return "clickhouse"

