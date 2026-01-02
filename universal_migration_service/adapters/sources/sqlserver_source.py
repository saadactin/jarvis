"""
SQL Server Source Adapter
"""
import pyodbc
from typing import Iterator, Dict, List, Any
from datetime import datetime
import logging
from .base_source import BaseSourceAdapter

logger = logging.getLogger(__name__)


class SQLServerSourceAdapter(BaseSourceAdapter):
    """SQL Server database source adapter"""
    
    def __init__(self):
        self.conn = None
        self.config = None
    
    def connect(self, config: Dict[str, Any]) -> bool:
        """Connect to SQL Server"""
        try:
            self.config = config
            server = config.get('server', config.get('host', 'localhost'))
            username = config.get('username', '')
            password = config.get('password', '')
            
            # Check authentication type
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
            
            conn_str += "MARS_Connection=Yes;Timeout=60;Pooling=No;"
            
            if is_named_instance:
                conn_str += "Encrypt=No;TrustServerCertificate=Yes;"
            
            self.conn = pyodbc.connect(conn_str)
            logger.info(f"Connected to SQL Server: {server}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to SQL Server: {str(e)}")
            raise ConnectionError(f"Failed to connect to SQL Server: {str(e)}")
    
    def disconnect(self):
        """Close SQL Server connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def test_connection(self, config: Dict[str, Any]) -> bool:
        """Test SQL Server connection"""
        try:
            server = config.get('server', config.get('host', 'localhost'))
            username = config.get('username', '')
            password = config.get('password', '')
            
            use_windows_auth = username.lower() in ['windows', 'trusted', ''] or password.lower() in ['windows', 'trusted', '']
            is_named_instance = "\\" in server
            escaped_server = server.replace("\\", "\\\\") if not is_named_instance else server
            
            conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={escaped_server};"
            
            if use_windows_auth:
                conn_str += "Trusted_Connection=yes;"
            else:
                conn_str += f"UID={username};PWD={password};"
            
            conn_str += "MARS_Connection=Yes;Timeout=60;Pooling=No;"
            
            if is_named_instance:
                conn_str += "Encrypt=No;TrustServerCertificate=Yes;"
            
            conn = pyodbc.connect(conn_str)
            conn.close()
            return True
        except:
            return False
    
    def list_tables(self) -> List[str]:
        """List all tables from all databases"""
        if not self.conn:
            raise ConnectionError("Not connected to SQL Server")
        
        # Get all user databases
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sys.databases WHERE database_id > 4")
        databases = [row[0] for row in cursor.fetchall()]
        
        all_tables = []
        for db_name in databases:
            try:
                cursor.execute(f"USE [{db_name}]")
                cursor.execute("""
                    SELECT TABLE_SCHEMA, TABLE_NAME 
                    FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_TYPE = 'BASE TABLE'
                """)
                tables = cursor.fetchall()
                for schema, table in tables:
                    all_tables.append(f"{db_name}.{schema}.{table}")
            except Exception as e:
                logger.warning(f"Error accessing database {db_name}: {str(e)}")
                continue
        
        cursor.close()
        return all_tables
    
    def get_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """Get table schema"""
        # Parse database.schema.table format
        parts = table_name.split('.')
        if len(parts) == 3:
            db_name, schema_name, table = parts
        elif len(parts) == 2:
            db_name, table = parts
            schema_name = 'dbo'
        else:
            raise ValueError(f"Invalid table name format: {table_name}")
        
        cursor = self.conn.cursor()
        cursor.execute(f"USE [{db_name}]")
        cursor.execute("""
            SELECT 
                COLUMN_NAME,
                DATA_TYPE,
                CHARACTER_MAXIMUM_LENGTH,
                NUMERIC_PRECISION,
                NUMERIC_SCALE,
                IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
            ORDER BY ORDINAL_POSITION
        """, (schema_name, table))
        
        schema = []
        for row in cursor.fetchall():
            schema.append({
                "name": row[0],
                "type": row[1],
                "max_length": row[2],
                "precision": row[3],
                "scale": row[4],
                "nullable": row[5] == 'YES'
            })
        cursor.close()
        return schema
    
    def read_data(self, table_name: str, batch_size: int = 1000) -> Iterator[List[Dict[str, Any]]]:
        """Read data from SQL Server in batches"""
        if not self.conn:
            raise ConnectionError("Not connected to SQL Server")
        
        # Parse table name
        parts = table_name.split('.')
        if len(parts) == 3:
            db_name, schema_name, table = parts
        elif len(parts) == 2:
            db_name, table = parts
            schema_name = 'dbo'
        else:
            raise ValueError(f"Invalid table name format: {table_name}")
        
        cursor = self.conn.cursor()
        cursor.execute(f"USE [{db_name}]")
        cursor.execute(f"SELECT * FROM [{schema_name}].[{table}]")
        
        # Get column names
        columns = [column[0] for column in cursor.description]
        
        batch = []
        for row in cursor.fetchall():
            record = dict(zip(columns, row))
            batch.append(record)
            if len(batch) >= batch_size:
                yield batch
                batch = []
        
        if batch:
            yield batch
        
        cursor.close()
    
    def read_incremental(self, table_name: str, last_sync_time: datetime, batch_size: int = 1000) -> Iterator[List[Dict[str, Any]]]:
        """Read incremental changes"""
        # Try to find a timestamp column
        schema = self.get_schema(table_name)
        timestamp_cols = [col['name'] for col in schema if 'time' in col['type'].lower() or 'date' in col['type'].lower()]
        
        if not timestamp_cols:
            logger.warning(f"No timestamp column found in {table_name}, reading all data")
            yield from self.read_data(table_name, batch_size)
            return
        
        # Use first timestamp column found
        timestamp_col = timestamp_cols[0]
        parts = table_name.split('.')
        if len(parts) == 3:
            db_name, schema_name, table = parts
        elif len(parts) == 2:
            db_name, table = parts
            schema_name = 'dbo'
        
        cursor = self.conn.cursor()
        cursor.execute(f"USE [{db_name}]")
        cursor.execute(
            f"SELECT * FROM [{schema_name}].[{table}] WHERE [{timestamp_col}] > ?",
            (last_sync_time,)
        )
        
        columns = [column[0] for column in cursor.description]
        
        batch = []
        for row in cursor.fetchall():
            record = dict(zip(columns, row))
            batch.append(record)
            if len(batch) >= batch_size:
                yield batch
                batch = []
        
        if batch:
            yield batch
        
        cursor.close()
    
    def get_source_type(self) -> str:
        return "sqlserver"

