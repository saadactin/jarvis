# PostgreSQL to MySQL Migration Feature

## Overview
Enhanced the Universal Migration Service to support comprehensive PostgreSQL to MySQL migrations with advanced features from the provided migration script.

## Enhancements Made

### 1. PostgreSQL Source Adapter (`universal_migration_service/adapters/sources/postgresql_source.py`)

**New Methods Added:**
- `get_foreign_keys(table_name)` - Extracts foreign key constraints
- `get_unique_constraints(table_name)` - Extracts unique constraints  
- `get_indexes(table_name)` - Extracts indexes (excluding primary keys)

**Enhanced Methods:**
- `get_schema(table_name)` - Now includes default values in schema information

### 2. MySQL Destination Adapter (`universal_migration_service/adapters/destinations/mysql_dest.py`)

**Complete Rewrite with Advanced Features:**

#### TypeConverter Class
- Comprehensive PostgreSQL to MySQL type mapping
- Handles precision/scale for DECIMAL types
- Converts array types to JSON
- Handles SERIAL types with AUTO_INCREMENT
- Converts default values (removes PostgreSQL-specific syntax)
- Constraint name conversion (respects MySQL 64-char limit)

#### Enhanced Methods:
- `connect()` - Now creates database if it doesn't exist
- `map_types()` - Uses TypeConverter for sophisticated type mapping
- `create_table()` - Enhanced to support:
  - Primary keys
  - Default values
  - Foreign keys (stored for later creation)
  - Unique constraints (stored for later creation)
  - Indexes (stored for later creation)

#### New Methods:
- `create_indexes()` - Creates indexes after data migration
- `create_unique_constraints()` - Creates unique constraints after data migration
- `create_foreign_keys()` - Creates foreign key constraints after data migration

#### Enhanced `write_data()`:
- Upsert logic with `ON DUPLICATE KEY UPDATE` for tables with primary keys
- Type conversion for PostgreSQL-specific types (JSON, UUID, Decimal, bytes)
- Preserves data integrity during migration

### 3. Pipeline Engine (`universal_migration_service/pipeline_engine.py`)

**Enhanced Migration Flow:**
1. **Schema Extraction Phase:**
   - Extracts primary keys from PostgreSQL
   - Extracts foreign keys from PostgreSQL
   - Extracts unique constraints from PostgreSQL
   - Extracts indexes from PostgreSQL

2. **Table Creation Phase:**
   - Creates table with primary keys
   - Stores constraints for later creation

3. **Data Migration Phase:**
   - Uses upsert logic (ON DUPLICATE KEY UPDATE) for tables with primary keys
   - Handles type conversion during data migration

4. **Constraint Creation Phase (After Data Migration):**
   - Creates indexes
   - Creates unique constraints
   - Creates foreign keys

### 4. Compatibility Updates

Updated other destination adapters to accept `source_type` parameter:
- `clickhouse_dest.py` - Added optional `source_type` parameter
- `postgresql_dest.py` - Added optional `source_type` parameter

## Key Features

### ✅ Type Conversion
- **Comprehensive Mapping**: All PostgreSQL types mapped to MySQL equivalents
- **Precision Preservation**: DECIMAL types preserve precision and scale
- **Array Support**: PostgreSQL arrays converted to JSON in MySQL
- **UUID Support**: UUID types converted to VARCHAR(36)
- **JSON Support**: JSONB and JSON types properly handled

### ✅ Schema Migration
- **Primary Keys**: Automatically detected and created
- **Foreign Keys**: Extracted and created after data migration
- **Unique Constraints**: Extracted and created after data migration
- **Indexes**: Extracted and created after data migration
- **Default Values**: Converted from PostgreSQL syntax to MySQL syntax

### ✅ Data Migration
- **Upsert Logic**: Uses `ON DUPLICATE KEY UPDATE` for tables with primary keys
- **Batch Processing**: Efficient batch inserts
- **Type Safety**: Proper type conversion during data migration
- **Error Handling**: Comprehensive error handling with rollback

### ✅ Database Creation
- **Auto-Create**: Automatically creates MySQL database if it doesn't exist
- **Character Set**: Uses utf8mb4 with unicode_ci collation

## Usage

### From Frontend UI:
1. Create a new operation
2. Select **Source**: `postgresql`
3. Select **Destination**: `mysql`
4. Enter PostgreSQL connection details
5. Enter MySQL connection details
6. Execute the migration

### From API:
```json
POST /api/universal-migration-service/migrate
{
  "source_type": "postgresql",
  "dest_type": "mysql",
  "source": {
    "host": "localhost",
    "port": 5432,
    "database": "source_db",
    "username": "postgres",
    "password": "password"
  },
  "destination": {
    "host": "localhost",
    "port": 3306,
    "database": "dest_db",
    "username": "root",
    "password": "password"
  },
  "operation_type": "full"
}
```

## Migration Process

1. **Connection**: Connects to both PostgreSQL and MySQL
2. **Database Creation**: Creates MySQL database if needed
3. **Table Discovery**: Lists all tables from PostgreSQL
4. **For Each Table**:
   - Extract schema (columns, types, defaults)
   - Extract constraints (primary keys, foreign keys, unique, indexes)
   - Map types from PostgreSQL to MySQL
   - Create table in MySQL with primary keys
   - Migrate data with upsert logic
   - Create indexes
   - Create unique constraints
   - Create foreign keys

## Type Mappings

| PostgreSQL | MySQL |
|-----------|-------|
| `smallint` | `SMALLINT` |
| `integer`, `int`, `int4` | `INT` |
| `bigint`, `int8` | `BIGINT` |
| `serial` | `INT AUTO_INCREMENT` |
| `bigserial` | `BIGINT AUTO_INCREMENT` |
| `real`, `float4` | `FLOAT` |
| `double precision`, `float8` | `DOUBLE` |
| `numeric`, `decimal` | `DECIMAL(precision,scale)` |
| `varchar`, `character varying` | `VARCHAR(length)` |
| `text` | `TEXT` |
| `timestamp`, `timestamptz` | `DATETIME` |
| `date` | `DATE` |
| `time` | `TIME` |
| `boolean`, `bool` | `BOOLEAN` |
| `json`, `jsonb` | `JSON` |
| `uuid` | `VARCHAR(36)` |
| `bytea` | `BLOB` |
| `array[]` | `JSON` |

## Notes

- **Foreign Keys**: Created after data migration to avoid constraint violations
- **Unique Constraints**: Created after data migration to avoid constraint violations
- **Indexes**: Created after data migration for better performance
- **Upsert Logic**: Only used for tables with primary keys
- **Error Handling**: Comprehensive error handling with detailed logging
- **Data Preservation**: All data types are preserved during migration

## Testing

To test the migration:
1. Ensure PostgreSQL source database is accessible
2. Ensure MySQL destination database is accessible (or will be created)
3. Create operation from frontend or API
4. Execute migration
5. Verify data in MySQL database

## Compatibility

- ✅ Works with existing Universal Migration Service architecture
- ✅ Compatible with other source/destination combinations
- ✅ Backward compatible with existing migrations

