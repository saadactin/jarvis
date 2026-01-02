"""
PostgreSQL Source Adapter
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Iterator, Dict, List, Any
from datetime import datetime
import logging
from .base_source import BaseSourceAdapter

logger = logging.getLogger(__name__)


class PostgreSQLSourceAdapter(BaseSourceAdapter):
    """PostgreSQL database source adapter"""
    
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
    
    def list_tables(self) -> List[str]:
        """List all tables in PostgreSQL public schema"""
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                SELECT table_schema, table_name 
                FROM information_schema.tables 
                WHERE table_type = 'BASE TABLE'
                AND table_schema NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
                ORDER BY table_schema, table_name;
            """)
            tables = []
            for row in cursor.fetchall():
                schema, table = row
                # Include schema prefix if not public
                if schema == 'public':
                    tables.append(table)
                else:
                    tables.append(f"{schema}.{table}")
            return tables
        except Exception as e:
            logger.error(f"Error listing tables: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
        finally:
            cursor.close()
    
    def get_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """Get table schema with full type information including default values"""
        cursor = self.conn.cursor()
        try:
            # Handle schema-qualified table names
            if '.' in table_name:
                schema_name, table = table_name.split('.', 1)
            else:
                schema_name = 'public'
                table = table_name
            
            cursor.execute("""
                SELECT 
                    column_name,
                    data_type,
                    character_maximum_length,
                    numeric_precision,
                    numeric_scale,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = %s 
                AND table_name = %s
                ORDER BY ordinal_position;
            """, (schema_name, table))
            
            schema = []
            for row in cursor.fetchall():
                col_name, data_type, char_max_len, num_precision, num_scale, is_nullable, col_default = row
                
                # Build full type string for better mapping (matching working script)
                full_type = data_type
                if char_max_len:
                    full_type = f"{data_type}({char_max_len})"
                elif num_precision is not None and num_scale is not None:
                    full_type = f"{data_type}({num_precision},{num_scale})"
                elif num_precision is not None:
                    full_type = f"{data_type}({num_precision})"
                
                schema.append({
                    "name": col_name,
                    "type": data_type,
                    "full_type": full_type,
                    "max_length": char_max_len,
                    "precision": num_precision,
                    "scale": num_scale,
                    "nullable": is_nullable == 'YES',
                    "default": col_default
                })
            return schema
        except Exception as e:
            logger.error(f"Error getting schema for table {table_name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
        finally:
            cursor.close()
    
    def read_data(self, table_name: str, batch_size: int = 1000) -> Iterator[List[Dict[str, Any]]]:
        """Read data from PostgreSQL in batches using quoted column names"""
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        # Use quoted table and column names for safety (matching working script)
        cursor.execute(f'SELECT * FROM "{table_name}"')
        
        batch = []
        for row in cursor:
            batch.append(dict(row))
            if len(batch) >= batch_size:
                yield batch
                batch = []
        
        if batch:
            yield batch
        
        cursor.close()
    
    def get_primary_key_columns(self, table_name: str) -> List[str]:
        """Get primary key column names for a table"""
        cursor = self.conn.cursor()
        try:
            # Handle schema-qualified table names
            if '.' in table_name:
                schema, table = table_name.split('.', 1)
            else:
                schema = 'public'
                table = table_name
            
            cursor.execute("""
                SELECT a.attname
                FROM pg_index i
                JOIN pg_class c ON c.oid = i.indrelid
                JOIN pg_namespace n ON n.oid = c.relnamespace
                JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                WHERE c.relname = %s
                AND n.nspname = %s
                AND i.indisprimary;
            """, (table, schema))
            
            pk_columns = [row[0] for row in cursor.fetchall()]
            return pk_columns
        except Exception as e:
            logger.warning(f"Error getting primary keys for {table_name}: {e}")
            return []
        finally:
            cursor.close()
    
    def read_incremental(self, table_name: str, last_sync_time: datetime, batch_size: int = 1000) -> Iterator[List[Dict[str, Any]]]:
        """Read incremental changes (assumes updated_at or similar timestamp column)"""
        # Try to find a timestamp column
        schema = self.get_schema(table_name)
        timestamp_cols = [col['name'] for col in schema if 'time' in col['type'].lower() or 'date' in col['type'].lower()]
        
        if not timestamp_cols:
            # Fallback: read all data if no timestamp column
            logger.warning(f"No timestamp column found in {table_name}, reading all data")
            yield from self.read_data(table_name, batch_size)
            return
        
        # Use first timestamp column found
        timestamp_col = timestamp_cols[0]
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            f"SELECT * FROM {table_name} WHERE {timestamp_col} > %s",
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
    
    def get_foreign_keys(self, table_name: str) -> List[Dict[str, Any]]:
        """Get foreign key constraints for a table"""
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        try:
            # Handle schema-qualified table names
            if '.' in table_name:
                schema, table = table_name.split('.', 1)
            else:
                schema = 'public'
                table = table_name
            
            cursor.execute("""
                SELECT
                    tc.constraint_name,
                    kcu.column_name,
                    ccu.table_schema AS foreign_table_schema,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name,
                    rc.update_rule,
                    rc.delete_rule
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                LEFT JOIN information_schema.referential_constraints AS rc
                    ON tc.constraint_name = rc.constraint_name
                    AND tc.table_schema = rc.constraint_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = %s
                AND tc.table_schema = %s;
            """, (table, schema))
            
            fks = [dict(row) for row in cursor.fetchall()]
            return fks
        except Exception as e:
            logger.warning(f"Error getting foreign keys for {table_name}: {e}")
            return []
        finally:
            cursor.close()
    
    def get_unique_constraints(self, table_name: str) -> List[Dict[str, Any]]:
        """Get unique constraints for a table"""
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        try:
            # Handle schema-qualified table names
            if '.' in table_name:
                schema, table = table_name.split('.', 1)
            else:
                schema = 'public'
                table = table_name
            
            cursor.execute("""
                SELECT
                    tc.constraint_name,
                    kcu.column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                WHERE tc.constraint_type = 'UNIQUE'
                AND tc.table_name = %s
                AND tc.table_schema = %s
                ORDER BY tc.constraint_name, kcu.ordinal_position;
            """, (table, schema))
            
            results = {}
            for row in cursor.fetchall():
                constraint_name = row['constraint_name']
                if constraint_name not in results:
                    results[constraint_name] = {
                        'constraint_name': constraint_name,
                        'columns': []
                    }
                results[constraint_name]['columns'].append(row['column_name'])
            
            return list(results.values())
        except Exception as e:
            logger.warning(f"Error getting unique constraints for {table_name}: {e}")
            return []
        finally:
            cursor.close()
    
    def get_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        """Get indexes for a table (excluding primary keys)"""
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        try:
            # Handle schema-qualified table names
            if '.' in table_name:
                schema, table = table_name.split('.', 1)
            else:
                schema = 'public'
                table = table_name
            
            cursor.execute("""
                SELECT
                    i.relname AS index_name,
                    a.attname AS column_name,
                    ix.indisunique AS is_unique,
                    am.amname AS index_type
                FROM pg_class t
                JOIN pg_namespace n ON t.relnamespace = n.oid
                JOIN pg_index ix ON t.oid = ix.indrelid
                JOIN pg_class i ON i.oid = ix.indexrelid
                JOIN pg_am am ON i.relam = am.oid
                JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
                WHERE t.relkind = 'r'
                AND t.relname = %s
                AND n.nspname = %s
                AND NOT ix.indisprimary
                ORDER BY i.relname, array_position(ix.indkey, a.attnum);
            """, (table, schema))
            
            results = {}
            for row in cursor.fetchall():
                index_name = row['index_name']
                if index_name not in results:
                    results[index_name] = {
                        'index_name': index_name,
                        'columns': [],
                        'is_unique': row['is_unique'],
                        'index_type': row['index_type']
                    }
                results[index_name]['columns'].append(row['column_name'])
            
            return list(results.values())
        except Exception as e:
            logger.warning(f"Error getting indexes for {table_name}: {e}")
            return []
        finally:
            cursor.close()
    
    def get_source_type(self) -> str:
        return "postgresql"

