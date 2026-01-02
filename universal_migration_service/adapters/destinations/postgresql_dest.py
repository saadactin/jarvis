"""
PostgreSQL Destination Adapter
"""
import psycopg2
from psycopg2.extras import execute_values
from typing import List, Dict, Any
import logging
from .base_destination import BaseDestinationAdapter

logger = logging.getLogger(__name__)


class PostgreSQLDestinationAdapter(BaseDestinationAdapter):
    """PostgreSQL database destination adapter"""
    
    def __init__(self):
        self.conn = None
        self.config = None
    
    def connect(self, config: Dict[str, Any]) -> bool:
        """Connect to PostgreSQL"""
        try:
            self.config = config
            self.conn = psycopg2.connect(
                host=config['host'],
                port=config.get('port', 5432),
                database=config['database'],
                user=config['username'],
                password=config['password']
            )
            logger.info(f"Connected to PostgreSQL: {config['host']}:{config.get('port', 5432)}/{config['database']}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {str(e)}")
            raise ConnectionError(f"Failed to connect to PostgreSQL: {str(e)}")
    
    def disconnect(self):
        """Close PostgreSQL connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def test_connection(self, config: Dict[str, Any]) -> bool:
        """Test PostgreSQL connection"""
        try:
            conn = psycopg2.connect(
                host=config['host'],
                port=config.get('port', 5432),
                database=config['database'],
                user=config['username'],
                password=config['password']
            )
            conn.close()
            return True
        except:
            return False
    
    def map_types(self, source_schema: List[Dict[str, Any]], source_type: str = None) -> List[Dict[str, Any]]:
        """Map source types to PostgreSQL types"""
        type_mapping = {
            'smallint': 'SMALLINT',
            'integer': 'INTEGER',
            'int': 'INTEGER',
            'bigint': 'BIGINT',
            'serial': 'SERIAL',
            'real': 'REAL',
            'float': 'REAL',
            'double precision': 'DOUBLE PRECISION',
            'double': 'DOUBLE PRECISION',
            'numeric': 'NUMERIC',
            'decimal': 'NUMERIC',
            'boolean': 'BOOLEAN',
            'bool': 'BOOLEAN',
            'varchar': 'VARCHAR',
            'character varying': 'VARCHAR',
            'text': 'TEXT',
            'char': 'CHAR',
            'timestamp': 'TIMESTAMP',
            'datetime': 'TIMESTAMP',
            'date': 'DATE',
            'time': 'TIME',
            'json': 'JSONB',
            'jsonb': 'JSONB',
            'uuid': 'UUID',
            'string': 'TEXT',  # For Zoho and other string-based sources
        }
        
        dest_schema = []
        for col in source_schema:
            source_type = col.get('type', 'string').lower().split('(')[0].strip()
            pg_type = type_mapping.get(source_type, 'TEXT')
            
            # Handle length/precision
            if 'max_length' in col and col['max_length']:
                if pg_type in ['VARCHAR', 'CHAR']:
                    pg_type = f"{pg_type}({col['max_length']})"
            
            dest_schema.append({
                "name": col['name'],
                "type": pg_type,
                "nullable": col.get('nullable', True)
            })
        
        return dest_schema
    
    def create_table(self, table_name: str, schema: List[Dict[str, Any]], source_type: str = None):
        """Create table in PostgreSQL if it doesn't exist"""
        cursor = self.conn.cursor()
        
        # Check if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = %s
            );
        """, (table_name,))
        
        if cursor.fetchone()[0]:
            logger.info(f"Table {table_name} already exists")
            cursor.close()
            return
        
        # Build CREATE TABLE statement
        columns = []
        for col in schema:
            col_def = f'"{col["name"]}" {col["type"]}'
            if not col.get('nullable', True):
                col_def += ' NOT NULL'
            columns.append(col_def)
        
        columns_def = ', '.join(columns)
        create_sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" ({columns_def})'
        
        try:
            cursor.execute(create_sql)
            self.conn.commit()
            logger.info(f"Created table {table_name}")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error creating table {table_name}: {str(e)}")
            raise
        finally:
            cursor.close()
    
    def write_data(self, table_name: str, data: List[Dict[str, Any]], batch_size: int = 1000, source_type: str = None):
        """Write data to PostgreSQL"""
        if not data:
            return
        
        cursor = self.conn.cursor()
        
        try:
            # Get column names (handle empty data case)
            if not data or len(data) == 0:
                return
            
            columns = list(data[0].keys())
            if not columns:
                logger.warning(f"No columns found in data for {table_name}")
                return
            
            # Sanitize column names (PostgreSQL safe)
            sanitized_columns = []
            for col in columns:
                # Replace special characters and ensure valid identifier
                sanitized = ''.join(c if c.isalnum() or c == '_' else '_' for c in str(col))
                if sanitized and sanitized[0].isdigit():
                    sanitized = f"_{sanitized}"
                sanitized_columns.append(sanitized)
            
            columns_str = ', '.join([f'"{col}"' for col in sanitized_columns])
            
            # Prepare data for bulk insert
            values = []
            for row in data:
                row_values = []
                for col in columns:
                    value = row.get(col)
                    # Handle None values
                    if value is None:
                        row_values.append(None)
                    else:
                        row_values.append(value)
                values.append(row_values)
            
            # Use execute_values for efficient bulk insert
            execute_values(
                cursor,
                f'INSERT INTO "{table_name}" ({columns_str}) VALUES %s',
                values
            )
            
            self.conn.commit()
            logger.debug(f"Inserted {len(data)} rows into {table_name}")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error writing to {table_name}: {str(e)}")
            raise
        finally:
            cursor.close()
    
    def get_destination_type(self) -> str:
        return "postgresql"

