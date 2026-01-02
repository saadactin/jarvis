# SQL Server to PostgreSQL Migration Microservice

Flask microservice for migrating data from SQL Server databases to PostgreSQL databases using the migration scripts from `Scripts/sql_postgres/`.

## Installation

```bash
cd sql_postgres_service
pip install -r requirements.txt
```

## Running the Service

```bash
python app.py
```

The service will start on `http://0.0.0.0:5003`

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
  "sql_server": {
    "server": "localhost\\SQLEXPRESS",
    "username": "sa",
    "password": "your_password"
  },
  "postgres": {
    "host": "localhost",
    "port": 5432,
    "database": "your_database",
    "username": "your_username",
    "password": "your_password"
  }
}
```

### Incremental Migration
```
POST /migrate/incremental
Content-Type: application/json

{
  "sql_server": {
    "server": "localhost\\SQLEXPRESS",
    "username": "sa",
    "password": "your_password"
  },
  "postgres": {
    "host": "localhost",
    "port": 5432,
    "database": "your_database",
    "username": "your_username",
    "password": "your_password"
  }
}
```

## Response Format

Success response:
```json
{
  "success": true,
  "databases_processed": ["All databases"],
  "databases_failed": [],
  "total_databases": 0,
  "errors": []
}
```

Error response:
```json
{
  "success": false,
  "databases_processed": [],
  "databases_failed": [],
  "total_databases": 0,
  "errors": ["error message"]
}
```

## Features

- Migrates all databases and tables from SQL Server to PostgreSQL
- Creates schemas in PostgreSQL with format `{server_clean}_{database}`
- Handles type mapping between SQL Server and PostgreSQL
- Full migration: Migrates all data from all databases
- Incremental migration: Syncs changes (inserts, updates, deletes)
- Comprehensive error handling and logging
- Uses migration scripts from `Scripts/sql_postgres/` folder
- Supports both Windows Authentication and SQL Server Authentication
- Handles named instances (e.g., `localhost\\SQLEXPRESS`)

## Migration Scripts

This service uses the actual migration scripts from `Scripts/sql_postgres/` folder:
- `final_full_sql_post.py` - For full migrations
- `final_incre_sql_post.py` - For incremental synchronizations

This ensures consistency with the standalone scripts and includes all advanced features like:
- Column detection and addition
- Row deletion detection
- Truncate handling
- Primary key/timestamp-based synchronization
- Batch processing for large datasets

