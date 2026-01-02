# Migration Examples

This document provides complete examples for all supported migration combinations.

## Zoho to PostgreSQL

```bash
POST http://localhost:5010/migrate
Content-Type: application/json

{
  "source_type": "zoho",
  "dest_type": "postgresql",
  "source": {
    "refresh_token": "your_zoho_refresh_token",
    "client_id": "your_zoho_client_id",
    "client_secret": "your_zoho_client_secret",
    "api_domain": "https://www.zohoapis.in"
  },
  "destination": {
    "host": "localhost",
    "port": 5432,
    "database": "zoho_data",
    "username": "postgres",
    "password": "your_postgres_password"
  },
  "operation_type": "full"
}
```

**What happens:**
1. Connects to Zoho CRM API
2. Fetches all modules (Accounts, Contacts, etc.)
3. For each module, fetches all records
4. Creates PostgreSQL tables with appropriate schema
5. Inserts all Zoho records into PostgreSQL

## SQL Server to ClickHouse

```bash
POST http://localhost:5010/migrate
Content-Type: application/json

{
  "source_type": "sqlserver",
  "dest_type": "clickhouse",
  "source": {
    "server": "localhost\\SQLEXPRESS",
    "username": "sa",
    "password": "your_sql_server_password"
  },
  "destination": {
    "host": "localhost",
    "port": 8123,
    "database": "analytics",
    "username": "default",
    "password": "your_clickhouse_password"
  },
  "operation_type": "full"
}
```

**What happens:**
1. Connects to SQL Server
2. Discovers all databases and tables
3. For each table, reads schema and data
4. Maps SQL Server types to ClickHouse types
5. Creates ClickHouse tables with `HR_` prefix
6. Inserts all data into ClickHouse

## Zoho to ClickHouse

```bash
POST http://localhost:5010/migrate
Content-Type: application/json

{
  "source_type": "zoho",
  "dest_type": "clickhouse",
  "source": {
    "refresh_token": "your_zoho_refresh_token",
    "client_id": "your_zoho_client_id",
    "client_secret": "your_zoho_client_secret",
    "api_domain": "https://www.zohoapis.in"
  },
  "destination": {
    "host": "localhost",
    "port": 8123,
    "database": "zoho_analytics",
    "username": "default",
    "password": "your_clickhouse_password"
  },
  "operation_type": "full"
}
```

## SQL Server to PostgreSQL

```bash
POST http://localhost:5010/migrate
Content-Type: application/json

{
  "source_type": "sqlserver",
  "dest_type": "postgresql",
  "source": {
    "server": "localhost\\SQLEXPRESS",
    "username": "sa",
    "password": "your_sql_server_password"
  },
  "destination": {
    "host": "localhost",
    "port": 5432,
    "database": "migrated_data",
    "username": "postgres",
    "password": "your_postgres_password"
  },
  "operation_type": "full"
}
```

## PostgreSQL to ClickHouse

```bash
POST http://localhost:5010/migrate
Content-Type: application/json

{
  "source_type": "postgresql",
  "dest_type": "clickhouse",
  "source": {
    "host": "localhost",
    "port": 5432,
    "database": "source_db",
    "username": "postgres",
    "password": "source_password"
  },
  "destination": {
    "host": "localhost",
    "port": 8123,
    "database": "analytics",
    "username": "default",
    "password": "clickhouse_password"
  },
  "operation_type": "full"
}
```

## MySQL to PostgreSQL

```bash
POST http://localhost:5010/migrate
Content-Type: application/json

{
  "source_type": "mysql",
  "dest_type": "postgresql",
  "source": {
    "host": "localhost",
    "port": 3306,
    "database": "mysql_db",
    "username": "root",
    "password": "mysql_password"
  },
  "destination": {
    "host": "localhost",
    "port": 5432,
    "database": "postgres_db",
    "username": "postgres",
    "password": "postgres_password"
  },
  "operation_type": "full"
}
```

## Incremental Migration Example

For incremental migrations, add `last_sync_time`:

```bash
POST http://localhost:5010/migrate
Content-Type: application/json

{
  "source_type": "postgresql",
  "dest_type": "clickhouse",
  "source": {
    "host": "localhost",
    "port": 5432,
    "database": "source_db",
    "username": "postgres",
    "password": "source_password"
  },
  "destination": {
    "host": "localhost",
    "port": 8123,
    "database": "analytics",
    "username": "default",
    "password": "clickhouse_password"
  },
  "operation_type": "incremental",
  "last_sync_time": "2024-01-01T00:00:00Z"
}
```

## Response Format

All migrations return the same response format:

```json
{
  "success": true,
  "tables_migrated": [
    {
      "table": "Accounts",
      "records": 1500
    },
    {
      "table": "Contacts",
      "records": 3000
    }
  ],
  "tables_failed": [],
  "total_tables": 2,
  "errors": []
}
```

## Notes

- **Zoho**: Modules are treated as "tables". All Zoho CRM modules (Accounts, Contacts, etc.) are automatically discovered and migrated.
- **SQL Server**: All databases and tables are discovered. Tables are named as `database.schema.table`.
- **Type Mapping**: Automatic type conversion between source and destination types.
- **Error Handling**: If one table fails, others continue to migrate.
- **Batch Processing**: Data is processed in batches for efficiency.

