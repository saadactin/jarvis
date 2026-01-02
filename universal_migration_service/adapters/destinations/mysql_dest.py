"""
MySQL Destination Adapter - Enhanced with PostgreSQL to MySQL migration logic
"""
import pymysql
from typing import List, Dict, Any, Optional
import logging
import re
import hashlib
import json
from decimal import Decimal
from .base_destination import BaseDestinationAdapter

logger = logging.getLogger(__name__)


class TypeConverter:
    """Converts PostgreSQL data types to MySQL data types."""
    
    TYPE_MAPPINGS = {
        # Integer types
        'smallint': 'SMALLINT',
        'integer': 'INT',
        'int': 'INT',
        'int4': 'INT',
        'int8': 'BIGINT',
        'bigint': 'BIGINT',
        'serial': 'INT AUTO_INCREMENT',
        'bigserial': 'BIGINT AUTO_INCREMENT',
        'smallserial': 'SMALLINT AUTO_INCREMENT',
        
        # Floating point types
        'real': 'FLOAT',
        'double precision': 'DOUBLE',
        'float4': 'FLOAT',
        'float8': 'DOUBLE',
        'numeric': 'DECIMAL',
        'decimal': 'DECIMAL',
        
        # Character types
        'character varying': 'VARCHAR',
        'varchar': 'VARCHAR',
        'character': 'CHAR',
        'char': 'CHAR',
        'text': 'TEXT',
        
        # Binary types
        'bytea': 'BLOB',
        
        # Date/Time types
        'timestamp': 'DATETIME',
        'timestamp without time zone': 'DATETIME',
        'timestamp with time zone': 'DATETIME',
        'timestamptz': 'DATETIME',
        'date': 'DATE',
        'time': 'TIME',
        'time without time zone': 'TIME',
        'time with time zone': 'TIME',
        'timetz': 'TIME',
        'interval': 'VARCHAR(255)',
        
        # Boolean
        'boolean': 'BOOLEAN',
        'bool': 'BOOLEAN',
        
        # JSON types
        'json': 'JSON',
        'jsonb': 'JSON',
        
        # UUID
        'uuid': 'VARCHAR(36)',
        
        # Network types
        'inet': 'VARCHAR(45)',
        'cidr': 'VARCHAR(45)',
        'macaddr': 'VARCHAR(17)',
        
        # Array types (stored as JSON in MySQL)
        'array': 'JSON',
        
        # SQL Server types (for compatibility)
        'nvarchar': 'VARCHAR',
        'nchar': 'CHAR',
        'ntext': 'TEXT',
        'datetime2': 'DATETIME',
        'smalldatetime': 'DATETIME',
        'datetimeoffset': 'VARCHAR(50)',
        'bit': 'BOOLEAN',
        'money': 'DECIMAL(19,4)',
        'smallmoney': 'DECIMAL(10,4)',
        'uniqueidentifier': 'CHAR(36)',
        
        # Generic string type (for Zoho and other sources)
        'string': 'TEXT',
    }
    
    @staticmethod
    def convert_type(pg_type: str, length: Optional[int] = None, 
                    precision: Optional[int] = None, 
                    scale: Optional[int] = None) -> str:
        """Convert PostgreSQL data type to MySQL data type."""
        pg_type_lower = pg_type.lower().strip()
        
        # Handle array types
        if '[]' in pg_type_lower or pg_type_lower.endswith(' array'):
            return 'JSON'
        
        # Handle types with length/precision
        if pg_type_lower in ['varchar', 'character varying', 'char', 'character', 'nvarchar', 'nchar']:
            if length:
                return f'VARCHAR({length})'
            return 'VARCHAR(255)'
        
        if pg_type_lower in ['numeric', 'decimal']:
            if precision is not None and scale is not None:
                return f'DECIMAL({precision},{scale})'
            elif precision is not None:
                default_scale = min(precision // 2, 30)
                return f'DECIMAL({precision},{default_scale})'
            return 'DECIMAL(65,30)'
        
        # Handle SERIAL types
        if pg_type_lower in ['serial', 'bigserial', 'smallserial']:
            return TypeConverter.TYPE_MAPPINGS.get(pg_type_lower, 'INT AUTO_INCREMENT')
        
        # Default mapping
        mysql_type = TypeConverter.TYPE_MAPPINGS.get(pg_type_lower, 'TEXT')
        
        # Add length if specified
        if length and 'AUTO_INCREMENT' not in mysql_type and '(' not in mysql_type:
            if mysql_type in ['VARCHAR', 'CHAR']:
                return f'{mysql_type}({length})'
        
        return mysql_type
    
    @staticmethod
    def convert_default_value(default: Optional[str], column_type: str) -> Optional[str]:
        """Convert PostgreSQL default value to MySQL compatible default value."""
        if default is None:
            return None
        
        default = default.strip()
        if not default:
            return None
        
        # Remove ::type casting
        default = re.sub(r'::\w+(\[\])?', '', default)
        
        # Handle sequence nextval
        if 'nextval' in default.lower():
            return None  # AUTO_INCREMENT handles this
        
        # Handle boolean defaults
        if default.lower() in ['true', 'false']:
            return default.upper()
        
        # Handle NULL
        if default.upper() == 'NULL':
            return 'NULL'
        
        # Handle current timestamp functions
        if 'now()' in default.lower() or 'current_timestamp' in default.lower():
            return 'CURRENT_TIMESTAMP'
        
        if 'current_date' in default.lower():
            return 'CURRENT_DATE'
        
        if 'current_time' in default.lower():
            return 'CURRENT_TIME'
        
        return default
    
    @staticmethod
    def convert_constraint_name(name: str) -> str:
        """Convert constraint name to MySQL compatible format (64 char limit)."""
        if len(name) > 64:
            hash_suffix = hashlib.md5(name.encode()).hexdigest()[:8]
            return f"{name[:55]}_{hash_suffix}"
        return name


class MySQLDestinationAdapter(BaseDestinationAdapter):
    """MySQL database destination adapter with enhanced PostgreSQL migration support"""
    
    def __init__(self):
        self.conn = None
        self.config = None
        self.type_converter = TypeConverter()
        self._table_constraints = {}  # Cache constraints per table
    
    def connect(self, config: Dict[str, Any]) -> bool:
        """Connect to MySQL and create database if needed"""
        try:
            self.config = config
            
            # First connect without database to create it if needed
            temp_conn = pymysql.connect(
                host=config['host'],
                port=config.get('port', 3306),
                user=config['username'],
                password=config['password']
            )
            
            # Create database if it doesn't exist
            cursor = temp_conn.cursor()
            db_name = config['database']
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            cursor.close()
            temp_conn.close()
            
            # Now connect to the database
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
    
    def map_types(self, source_schema: List[Dict[str, Any]], source_type: str = None) -> List[Dict[str, Any]]:
        """Map source types to MySQL types using enhanced TypeConverter"""
        dest_schema = []
        for col in source_schema:
            source_data_type = col.get('type', 'string').lower().strip()
            length = col.get('max_length')
            precision = col.get('precision')
            scale = col.get('scale')
            
            # Use TypeConverter for PostgreSQL sources
            if source_type == 'postgresql':
                mysql_type = self.type_converter.convert_type(
                    source_data_type, length, precision, scale
                )
            else:
                # Fallback to simple mapping for other sources
                mysql_type = self.type_converter.convert_type(
                    source_data_type, length, precision, scale
                )
            
            dest_schema.append({
                "name": col['name'],
                "type": mysql_type,
                "nullable": col.get('nullable', True),
                "default": col.get('default')
            })
        
        return dest_schema
    
    def create_table(self, table_name: str, schema: List[Dict[str, Any]], source_type: str = None, 
                     primary_keys: List[str] = None, **kwargs):
        """Create table in MySQL with enhanced schema support"""
        cursor = self.conn.cursor()
        
        try:
            # Check if table exists
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM information_schema.tables 
                WHERE table_schema = %s 
                AND table_name = %s
            """, (self.config['database'], table_name))
            
            result = cursor.fetchone()
            if result and result.get('count', 0) > 0:
                logger.info(f"Table {table_name} already exists")
                cursor.close()
                return
            
            # Build column definitions
            columns = []
            for col in schema:
                col_name = col['name']
                mysql_type = col['type']
                nullable = col.get('nullable', True)
                default = col.get('default')
                
                col_def = f"`{col_name}` {mysql_type}"
                
                # Handle NULL/NOT NULL
                if not nullable:
                    col_def += " NOT NULL"
                
                # Handle default values
                if default is not None and source_type == 'postgresql':
                    try:
                        mysql_default = self.type_converter.convert_default_value(default, mysql_type)
                        if mysql_default and mysql_default.strip():
                            # Handle special MySQL functions and keywords
                            mysql_default_upper = mysql_default.upper().strip()
                            if mysql_default_upper in ['NULL', 'CURRENT_TIMESTAMP', 'CURRENT_DATE', 'CURRENT_TIME', 'TRUE', 'FALSE']:
                                col_def += f" DEFAULT {mysql_default_upper}"
                            else:
                                # Try to determine if it's a number
                                try:
                                    # Try to parse as number (int or float)
                                    float(mysql_default)
                                    col_def += f" DEFAULT {mysql_default}"
                                except ValueError:
                                    # It's a string, escape and quote it
                                    # Escape single quotes in the string
                                    escaped_default = mysql_default.replace("'", "''")
                                    col_def += f" DEFAULT '{escaped_default}'"
                    except Exception as e:
                        logger.warning(f"Could not convert default value '{default}' for column {col_name}: {e}. Skipping default.")
                        # Skip default value if conversion fails - table will still be created
                elif default is not None:
                    # For non-PostgreSQL sources, use default as-is (but be careful with quoting)
                    try:
                        default_str = str(default).strip()
                        default_upper = default_str.upper()
                        if default_upper in ['NULL', 'CURRENT_TIMESTAMP', 'CURRENT_DATE', 'CURRENT_TIME', 'TRUE', 'FALSE']:
                            col_def += f" DEFAULT {default_upper}"
                        else:
                            # Try to parse as number
                            try:
                                float(default_str)
                                col_def += f" DEFAULT {default_str}"
                            except ValueError:
                                # It's a string, escape and quote it
                                escaped_default = default_str.replace("'", "''")
                                col_def += f" DEFAULT '{escaped_default}'"
                    except Exception as e:
                        logger.warning(f"Could not process default value '{default}' for column {col_name}: {e}. Skipping default.")
                        # Skip default value if processing fails
                
                columns.append(col_def)
            
            # Add primary key if provided
            if primary_keys:
                pk_cols = ', '.join([f"`{pk}`" for pk in primary_keys])
                columns.append(f"PRIMARY KEY ({pk_cols})")
            
            if not columns:
                logger.warning(f"No columns found for table {table_name}, skipping")
                cursor.close()
                return
            
            # Build CREATE TABLE statement
            columns_def = ',\n  '.join(columns)
            create_sql = f"""
            CREATE TABLE IF NOT EXISTS `{table_name}` (
              {columns_def}
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            
            try:
                cursor.execute(create_sql)
                self.conn.commit()
                logger.info(f"Created table {table_name}")
            except Exception as sql_error:
                self.conn.rollback()
                logger.error(f"SQL Error creating table {table_name}: {str(sql_error)}")
                logger.error(f"Generated SQL:\n{create_sql}")
                # Try to get more details about the error
                if hasattr(sql_error, 'args') and len(sql_error.args) > 0:
                    logger.error(f"SQL Error details: {sql_error.args}")
                raise
            
            # Store constraints for later creation
            if source_type == 'postgresql':
                foreign_keys = kwargs.get('foreign_keys', [])
                unique_constraints = kwargs.get('unique_constraints', [])
                indexes = kwargs.get('indexes', [])
                
                self._table_constraints[table_name] = {
                    'foreign_keys': foreign_keys,
                    'unique_constraints': unique_constraints,
                    'indexes': indexes
                }
            
            cursor.close()
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error creating table {table_name}: {str(e)}")
            import traceback
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            if 'create_sql' in locals():
                logger.error(f"Generated SQL:\n{create_sql}")
            raise
        finally:
            if cursor:
                cursor.close()
    
    def create_indexes(self, table_name: str, indexes: List[Dict[str, Any]]):
        """Create indexes on MySQL table"""
        if not indexes:
            return
        
        cursor = self.conn.cursor()
        try:
            for index in indexes:
                index_name = self.type_converter.convert_constraint_name(index['index_name'])
                columns = index['columns']
                is_unique = index.get('is_unique', False)
                
                col_list = ', '.join([f"`{col}`" for col in columns])
                unique_keyword = "UNIQUE" if is_unique else ""
                
                create_index_sql = f"CREATE {unique_keyword} INDEX `{index_name}` ON `{table_name}` ({col_list})"
                
                try:
                    cursor.execute(create_index_sql)
                    logger.info(f"Created index {index_name} on {table_name}")
                except Exception as e:
                    if 'Duplicate key name' in str(e) or '1061' in str(e):
                        logger.warning(f"Index {index_name} already exists, skipping")
                    else:
                        logger.warning(f"Could not create index {index_name}: {e}")
            
            self.conn.commit()
            cursor.close()
        except Exception as e:
            logger.error(f"Error creating indexes for table {table_name}: {e}")
            cursor.close()
    
    def create_unique_constraints(self, table_name: str, unique_constraints: List[Dict[str, Any]]):
        """Create unique constraints on MySQL table"""
        if not unique_constraints:
            return
        
        cursor = self.conn.cursor()
        try:
            for uc in unique_constraints:
                constraint_name = self.type_converter.convert_constraint_name(uc['constraint_name'])
                columns = uc['columns']
                
                col_list = ', '.join([f"`{col}`" for col in columns])
                create_unique_sql = f"ALTER TABLE `{table_name}` ADD CONSTRAINT `{constraint_name}` UNIQUE ({col_list})"
                
                try:
                    cursor.execute(create_unique_sql)
                    logger.info(f"Created unique constraint {constraint_name} on {table_name}")
                except Exception as e:
                    if 'Duplicate entry' in str(e) or '1062' in str(e):
                        logger.warning(f"Unique constraint {constraint_name} already exists or violates data, skipping")
                    else:
                        logger.warning(f"Could not create unique constraint {constraint_name}: {e}")
            
            self.conn.commit()
            cursor.close()
        except Exception as e:
            logger.error(f"Error creating unique constraints for table {table_name}: {e}")
            cursor.close()
    
    def create_foreign_keys(self, table_name: str, foreign_keys: List[Dict[str, Any]]):
        """Create foreign key constraints on MySQL table"""
        if not foreign_keys:
            return
        
        cursor = self.conn.cursor()
        try:
            for fk in foreign_keys:
                constraint_name = self.type_converter.convert_constraint_name(fk['constraint_name'])
                column_name = fk['column_name']
                foreign_table = fk['foreign_table_name']
                # Remove schema prefix if present
                mysql_foreign_table = foreign_table.split('.')[-1] if '.' in foreign_table else foreign_table
                foreign_column = fk['foreign_column_name']
                update_rule = fk.get('update_rule', 'NO ACTION')
                delete_rule = fk.get('delete_rule', 'NO ACTION')
                
                # Convert PostgreSQL rules to MySQL
                update_rule = 'RESTRICT' if update_rule == 'NO ACTION' else update_rule
                delete_rule = 'RESTRICT' if delete_rule == 'NO ACTION' else delete_rule
                
                create_fk_sql = f"""
                    ALTER TABLE `{table_name}`
                    ADD CONSTRAINT `{constraint_name}`
                    FOREIGN KEY (`{column_name}`)
                    REFERENCES `{mysql_foreign_table}` (`{foreign_column}`)
                    ON UPDATE {update_rule}
                    ON DELETE {delete_rule}
                """
                
                try:
                    cursor.execute(create_fk_sql)
                    logger.info(f"Created foreign key {constraint_name} on {table_name}")
                except Exception as e:
                    if 'Duplicate key name' in str(e) or '1022' in str(e):
                        logger.warning(f"Foreign key {constraint_name} already exists, skipping")
                    else:
                        logger.warning(f"Could not create foreign key {constraint_name}: {e}")
            
            self.conn.commit()
            cursor.close()
        except Exception as e:
            logger.error(f"Error creating foreign keys for table {table_name}: {e}")
            cursor.close()
    
    def write_data(self, table_name: str, data: List[Dict[str, Any]], source_type: str = None, 
                   primary_keys: List[str] = None, **kwargs):
        """Write data to MySQL with upsert support"""
        if not data:
            return
        
        cursor = self.conn.cursor()
        
        try:
            columns = list(data[0].keys())
            if not columns:
                logger.warning(f"No columns found in data for {table_name}")
                return
            
            # Sanitize column names
            sanitized_columns = []
            for col in columns:
                sanitized = ''.join(c if c.isalnum() or c == '_' else '_' for c in str(col))
                if sanitized and sanitized[0].isdigit():
                    sanitized = f"_{sanitized}"
                sanitized_columns.append(sanitized)
            
            columns_str = ', '.join([f'`{col}`' for col in sanitized_columns])
            placeholders = ', '.join(['%s'] * len(sanitized_columns))
            
            # Convert data types for MySQL compatibility (especially for PostgreSQL)
            mysql_rows = []
            for row in data:
                mysql_row = []
                for i, col in enumerate(columns):
                    value = row.get(col)
                    
                    # Handle None values
                    if value is None:
                        mysql_row.append(None)
                        continue
                    
                    # Type conversion for PostgreSQL sources
                    if source_type == 'postgresql':
                        # Get column type from schema if available
                        col_type = str(value.__class__.__name__).lower()
                        
                        # Handle JSON types
                        if isinstance(value, (dict, list)):
                            mysql_row.append(json.dumps(value))
                        # Handle Decimal types
                        elif isinstance(value, Decimal):
                            mysql_row.append(value)
                        # Handle bytes (bytea)
                        elif isinstance(value, bytes):
                            mysql_row.append(value)
                        # Handle UUID
                        elif hasattr(value, 'hex'):  # UUID object
                            mysql_row.append(str(value))
                        else:
                            mysql_row.append(value)
                    else:
                        # For other sources, preserve value as-is
                        mysql_row.append(value)
                
                mysql_rows.append(tuple(mysql_row))
            
            # Build INSERT query with upsert logic if primary keys exist
            if primary_keys and source_type == 'postgresql':
                # Build UPDATE clause for ON DUPLICATE KEY UPDATE
                update_clauses = [f"`{col}` = VALUES(`{col}`)" for col in sanitized_columns if col not in primary_keys]
                if update_clauses:
                    insert_sql = f"""
                        INSERT INTO `{table_name}` ({columns_str})
                        VALUES ({placeholders})
                        ON DUPLICATE KEY UPDATE {', '.join(update_clauses)}
                    """
                else:
                    # All columns are primary keys, use INSERT IGNORE
                    insert_sql = f"""
                        INSERT IGNORE INTO `{table_name}` ({columns_str})
                        VALUES ({placeholders})
                    """
            else:
                # Regular INSERT for non-PostgreSQL or no primary keys
                insert_sql = f'INSERT INTO `{table_name}` ({columns_str}) VALUES ({placeholders})'
            
            cursor.executemany(insert_sql, mysql_rows)
            self.conn.commit()
            logger.debug(f"Inserted {len(data)} rows into {table_name}")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error writing to {table_name}: {str(e)}")
            raise
        finally:
            cursor.close()
    
    def get_destination_type(self) -> str:
        return "mysql"
