# PostgreSQL to ClickHouse Migration Microservice

Flask microservice for migrating data from PostgreSQL to ClickHouse.

## Installation

```bash
cd postgres_service
pip install -r requirements.txt
```

## Running the Service

```bash
python app.py
```

The service will start on `http://0.0.0.0:5001`

## API Endpoints

### Health Check
```
GET /health
```

### Full Migration
```
POST /migrate/full
Content-Type: application/json

{
  "postgres": {
    "host": "localhost",
    "port": 5432,
    "database": "your_database",
    "username": "your_username",
    "password": "your_password"
  },
  "clickhouse": {
    "host": "localhost",
    "database": "your_database",
    "username": "default",
    "password": "your_password"
  }
}
```

### Incremental Migration
```
POST /migrate/incremental
Content-Type: application/json

{
  "postgres": {
    "host": "localhost",
    "port": 5432,
    "database": "your_database",
    "username": "your_username",
    "password": "your_password"
  },
  "clickhouse": {
    "host": "localhost",
    "database": "your_database",
    "username": "default",
    "password": "your_password"
  }
}
```

## Response Format

Success response:
```json
{
  "success": true,
  "tables_migrated": ["table1", "table2"],
  "tables_failed": [],
  "total_tables": 2,
  "errors": []
}
```

Error response:
```json
{
  "success": false,
  "tables_migrated": ["table1"],
  "tables_failed": [{"table": "table2", "error": "error message"}],
  "total_tables": 2,
  "errors": ["table2: error message"]
}
```

## Features

- Migrates all tables from PostgreSQL public schema to ClickHouse
- Adds `HR_` prefix to table names in ClickHouse
- Handles type mapping between PostgreSQL and ClickHouse
- Incremental migration detects and only inserts new rows
- Comprehensive error handling and logging

