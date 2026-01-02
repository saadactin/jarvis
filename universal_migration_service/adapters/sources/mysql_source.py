"""
MySQL Source Adapter
"""
import pymysql
from typing import Iterator, Dict, List, Any
from datetime import datetime
import logging
from .base_source import BaseSourceAdapter

logger = logging.getLogger(__name__)


class MySQLSourceAdapter(BaseSourceAdapter):
    """MySQL database source adapter"""
    
    def __init__(self):
        self.conn = None
        self.config = None
    
    def connect(self, config: Dict[str, Any]) -> bool:
        """Connect to MySQL"""
        try:
            self.config = config
            self.conn = pymysql.connect(
                host=config['host'],
                port=config.get('port', 3306),
                database=config['database'],
                user=config['username'],
                password=config['password'],
                cursorclass=pymysql.cursors.DictCursor
            )
            logger.info(f"Connected to MySQL: {config['host']}:{config.get('port', 3306)}/{config['database']}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MySQL: {str(e)}")
            raise ConnectionError(f"Failed to connect to MySQL: {str(e)}")
    
    def disconnect(self):
        """Close MySQL connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def test_connection(self, config: Dict[str, Any]) -> bool:
        """Test MySQL connection"""
        try:
            conn = pymysql.connect(
                host=config['host'],
                port=config.get('port', 3306),
                database=config['database'],
                user=config['username'],
                password=config['password']
            )
            conn.close()
            return True
        except:
            return False
    
    def list_tables(self) -> List[str]:
        """List all tables in MySQL database"""
        cursor = self.conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [row[f'Tables_in_{self.config["database"]}'] for row in cursor.fetchall()]
        cursor.close()
        return tables
    
    def get_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """Get table schema"""
        cursor = self.conn.cursor()
        cursor.execute(f"DESCRIBE {table_name}")
        
        schema = []
        for row in cursor.fetchall():
            schema.append({
                "name": row['Field'],
                "type": row['Type'],
                "nullable": row['Null'] == 'YES',
                "key": row['Key'],
                "default": row['Default']
            })
        cursor.close()
        return schema
    
    def read_data(self, table_name: str, batch_size: int = 1000) -> Iterator[List[Dict[str, Any]]]:
        """Read data from MySQL in batches"""
        cursor = self.conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(f"SELECT * FROM `{table_name}`")
        
        batch = []
        for row in cursor:
            batch.append(dict(row))
            if len(batch) >= batch_size:
                yield batch
                batch = []
        
        if batch:
            yield batch
        
        cursor.close()
    
    def read_incremental(self, table_name: str, last_sync_time: datetime, batch_size: int = 1000) -> Iterator[List[Dict[str, Any]]]:
        """Read incremental changes"""
        schema = self.get_schema(table_name)
        timestamp_cols = [col['name'] for col in schema if 'time' in col['type'].lower() or 'date' in col['type'].lower()]
        
        if not timestamp_cols:
            logger.warning(f"No timestamp column found in {table_name}, reading all data")
            yield from self.read_data(table_name, batch_size)
            return
        
        timestamp_col = timestamp_cols[0]
        cursor = self.conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            f"SELECT * FROM `{table_name}` WHERE `{timestamp_col}` > %s",
            (last_sync_time,)
        )
        
        batch = []
        for row in cursor:
            batch.append(dict(row))
            if len(batch) >= batch_size:
                yield batch
                batch = []
        
        if batch:
            yield batch
        
        cursor.close()
    
    def get_source_type(self) -> str:
        return "mysql"

