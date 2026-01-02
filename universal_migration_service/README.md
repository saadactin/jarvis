# Universal Migration Service

A single, unified service for migrating data between any supported source and destination databases. Uses the adapter pattern to support multiple database types without creating separate services for each combination.

## Architecture

This service uses a **universal pipeline** with **source adapters** and **destination adapters**:

- **Source Adapters**: Read data from various sources (PostgreSQL, MySQL, MongoDB, etc.)
- **Destination Adapters**: Write data to various destinations (ClickHouse, PostgreSQL, etc.)
- **Pipeline Engine**: Orchestrates the migration from any source to any destination

### Benefits

- **Linear Growth**: Adding a new source works with ALL existing destinations
- **No Duplication**: One adapter per database type (not one per combination)
- **Easy Extension**: Just implement the adapter interface

## Installation

```bash
cd universal_migration_service
pip install -r requirements.txt
```

## Running the Service

```bash
python app.py
```

The service will start on `http://0.0.0.0:5010`

## API Endpoints

### Health Check

```
GET /health
```

Returns available sources and destinations.

### Universal Migration

```
POST /migrate
Content-Type: application/json

{
  "source_type": "postgresql",
  "dest_type": "clickhouse",
  "source": {
    "host": "localhost",
    "port": 5432,
    "database": "mydb",
    "username": "user",
    "password": "pass"
  },
  "destination": {
    "host": "localhost",
    "port": 8123,
    "database": "analytics",
    "username": "default",
    "password": "pass"
  },
  "operation_type": "full"
}
```

### Test Connection

```
POST /test-connection
Content-Type: application/json

{
  "type": "source",
  "adapter_type": "postgresql",
  "config": {
    "host": "localhost",
    "port": 5432,
    "database": "mydb",
    "username": "user",
    "password": "pass"
  }
}
```

## Supported Sources

- PostgreSQL
- MySQL
- Zoho CRM API
- SQL Server
- (More coming soon: MongoDB, Cassandra, etc.)

## Supported Destinations

- ClickHouse
- PostgreSQL
- MySQL
- (More coming soon: SQL Server, MongoDB, etc.)

## Migration Combinations

With the current adapters, you can migrate **ANY source to ANY destination** (except same source/destination):

### All Available Combinations (4 sources × 3 destinations = 12 valid combinations)

**From PostgreSQL:**
- PostgreSQL → ClickHouse ✅
- PostgreSQL → MySQL ✅
- PostgreSQL → PostgreSQL ❌ (Invalid: same source/destination)

**From MySQL:**
- MySQL → ClickHouse ✅
- MySQL → PostgreSQL ✅
- MySQL → MySQL ❌ (Invalid: same source/destination)

**From Zoho:**
- Zoho → ClickHouse ✅
- Zoho → PostgreSQL ✅
- Zoho → MySQL ✅

**From SQL Server:**
- SQL Server → ClickHouse ✅
- SQL Server → PostgreSQL ✅
- SQL Server → MySQL ✅

**Note:** The service automatically validates and prevents migrations where source and destination are the same database type.

For a complete list with examples, see [COMBINATIONS.md](COMBINATIONS.md).

### Universal Architecture Benefits

The universal pipeline architecture means:
- **Add one source** → Works with ALL destinations automatically
- **Add one destination** → Receives from ALL sources automatically
- **No need to create separate services** for each combination

## Adding a New Database Type

### Example: Adding Cassandra Source

1. **Create Source Adapter** (`adapters/sources/cassandra_source.py`):
   ```python
   from adapters.sources.base_source import BaseSourceAdapter
   
   class CassandraSourceAdapter(BaseSourceAdapter):
       # Implement all abstract methods
       def connect(self, config):
           # Connect to Cassandra
           pass
       # ... other methods
   ```

2. **Register in app.py**:
   ```python
   from adapters.sources.cassandra_source import CassandraSourceAdapter
   pipeline.register_source("cassandra", CassandraSourceAdapter)
   ```

3. **Done!** Cassandra now works with ALL existing destinations:
   - Cassandra → ClickHouse ✅
   - Cassandra → PostgreSQL ✅
   - Cassandra → Any future destination ✅

### Example: Adding MySQL Destination

1. **Create Destination Adapter** (`adapters/destinations/mysql_dest.py`)
2. **Register in app.py**
3. **Done!** MySQL now receives data from ALL existing sources

## Response Format

Success:
```json
{
  "success": true,
  "tables_migrated": [
    {"table": "users", "records": 1000},
    {"table": "orders", "records": 500}
  ],
  "tables_failed": [],
  "total_tables": 2,
  "errors": []
}
```

Error:
```json
{
  "success": false,
  "tables_migrated": [{"table": "users", "records": 1000}],
  "tables_failed": [{"table": "orders", "error": "Connection timeout"}],
  "total_tables": 2,
  "errors": ["orders: Connection timeout"]
}
```

## Incremental Migration

For incremental migration, include `last_sync_time`:

```json
{
  "source_type": "postgresql",
  "dest_type": "clickhouse",
  "source": {...},
  "destination": {...},
  "operation_type": "incremental",
  "last_sync_time": "2024-01-01T00:00:00Z"
}
```

## Features

- Universal endpoint for all migrations
- Automatic type mapping
- Batch processing for efficiency
- Error handling and logging
- Connection testing
- Incremental migration support

## Future Enhancements

- Data transformation rules
- Field mapping
- Filtering and validation
- Progress tracking
- Webhook notifications

