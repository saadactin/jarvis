# SQL Server to PostgreSQL Migration API Documentation

## Base URL
```
http://localhost:5003
```

## Overview

This microservice provides REST API endpoints for migrating data from SQL Server databases to PostgreSQL databases. It uses the migration scripts from `Scripts/sql_postgres/` folder and supports both full migration and incremental synchronization.

## Endpoints

### 1. Health Check

Check if the service is running and healthy.

**Endpoint:** `GET /health`

**Request:**
```http
GET /health HTTP/1.1
Host: localhost:5003
```

**Response:**
```json
{
  "status": "healthy",
  "service": "sql_postgres_migration"
}
```

**Status Codes:**
- `200 OK` - Service is healthy

---

### 2. Full Migration

Perform a complete migration of all tables from PostgreSQL to ClickHouse. Creates tables if they don't exist and migrates all data.

**Endpoint:** `POST /migrate/full`

**Request Headers:**
```http
Content-Type: application/json
```

**Request Body:**
```json
{
  "postgres": {
    "host": "string (required)",
    "port": "integer (optional, default: 5432)",
    "database": "string (required)",
    "username": "string (required)",
    "password": "string (required)"
  },
  "clickhouse": {
    "host": "string (required)",
    "database": "string (required)",
    "username": "string (required)",
    "password": "string (required)"
  }
}
```

**Request Example:**
```json
{
  "postgres": {
    "host": "localhost",
    "port": 5432,
    "database": "mydb",
    "username": "postgres",
    "password": "mypassword"
  },
  "clickhouse": {
    "host": "localhost",
    "database": "analytics",
    "username": "default",
    "password": "clickhouse_password"
  }
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "databases_processed": [
    "All databases"
  ],
  "databases_failed": [],
  "total_databases": 0,
  "errors": []
}
```

**Error Response (400 Bad Request):**
```json
{
  "error": "sql_server.server is required"
}
```

**Error Response (500 Internal Server Error):**
```json
{
  "success": false,
  "databases_processed": [],
  "databases_failed": [],
  "total_databases": 0,
  "errors": [
    "Connection timeout"
  ]
}
```

**Status Codes:**
- `200 OK` - Migration completed successfully
- `400 Bad Request` - Invalid request body or missing required fields
- `500 Internal Server Error` - Migration failed or partial failure

**Notes:**
- All databases on the SQL Server will be migrated
- Tables are created in PostgreSQL with schema names like `{server_clean}_{database}_{schema}_{table}`
- Migration is performed in batches (default: 5000 rows)
- Existing tables in PostgreSQL are not overwritten, only new rows are inserted
- Uses the migration script from `Scripts/sql_postgres/final_full_sql_post.py`
- Supports both Windows Authentication and SQL Server Authentication

---

### 3. Incremental Migration

Perform an incremental synchronization that keeps PostgreSQL in sync with SQL Server. Detects and syncs:
- New tables
- New columns
- New/updated rows
- Deleted rows
- Truncates

**Endpoint:** `POST /migrate/incremental`

**Request Headers:**
```http
Content-Type: application/json
```

**Request Body:**
```json
{
  "postgres": {
    "host": "string (required)",
    "port": "integer (optional, default: 5432)",
    "database": "string (required)",
    "username": "string (required)",
    "password": "string (required)"
  },
  "clickhouse": {
    "host": "string (required)",
    "database": "string (required)",
    "username": "string (required)",
    "password": "string (required)"
  }
}
```

**Request Example:**
```json
{
  "postgres": {
    "host": "localhost",
    "port": 5432,
    "database": "mydb",
    "username": "postgres",
    "password": "mypassword"
  },
  "clickhouse": {
    "host": "localhost",
    "database": "analytics",
    "username": "default",
    "password": "clickhouse_password"
  }
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "databases_processed": [
    "All databases"
  ],
  "databases_failed": [],
  "total_databases": 0,
  "errors": []
}
```

**Error Response (400 Bad Request):**
```json
{
  "error": "postgres.password is required"
}
```

**Error Response (500 Internal Server Error):**
```json
{
  "success": false,
  "databases_processed": [],
  "databases_failed": [],
  "total_databases": 0,
  "errors": [
    "Connection timeout"
  ]
}
```

**Status Codes:**
- `200 OK` - Incremental migration completed successfully
- `400 Bad Request` - Invalid request body or missing required fields
- `500 Internal Server Error` - Migration failed or partial failure

**Notes:**
- Uses primary keys, timestamp columns, or unique identifiers to detect new/changed rows
- Automatically adds new columns to existing tables
- Detects and deletes rows removed from SQL Server
- Handles table truncates
- For tables without primary keys, uses timestamp columns or full row comparison
- Uses the synchronization script from `Scripts/sql_postgres/final_incre_sql_post.py`

---

## Data Type Mapping

The service automatically maps SQL Server data types to PostgreSQL equivalents:

| SQL Server Type | PostgreSQL Type |
|----------------|-----------------|
| int, bigint, smallint, tinyint | BIGINT |
| decimal, numeric, float, real | DOUBLE PRECISION |
| bit | BOOLEAN |
| datetime, datetime2, smalldatetime, date | TIMESTAMP |
| varchar, nvarchar, text, ntext | TEXT |
| char, nchar | TEXT |
| binary, varbinary, image | BYTEA |
| uniqueidentifier | UUID |
| Unknown types | TEXT (default) |

---

## Error Handling

All endpoints return appropriate HTTP status codes:

- **200 OK**: Request succeeded
- **400 Bad Request**: Invalid request parameters
- **500 Internal Server Error**: Server error during processing

Error responses include a descriptive error message in the response body.

---

## Examples

### cURL Examples

**Health Check:**
```bash
curl -X GET http://localhost:5003/health
```

**Full Migration:**
```bash
curl -X POST http://localhost:5003/migrate/full \
  -H "Content-Type: application/json" \
  -d '{
    "sql_server": {
      "server": "localhost\\SQLEXPRESS",
      "username": "sa",
      "password": "sqlpassword"
    },
    "postgres": {
      "host": "localhost",
      "port": 5432,
      "database": "mydb",
      "username": "postgres",
      "password": "mypassword"
    }
  }'
```

**Incremental Migration:**
```bash
curl -X POST http://localhost:5003/migrate/incremental \
  -H "Content-Type: application/json" \
  -d '{
    "sql_server": {
      "server": "localhost\\SQLEXPRESS",
      "username": "sa",
      "password": "sqlpassword"
    },
    "postgres": {
      "host": "localhost",
      "port": 5432,
      "database": "mydb",
      "username": "postgres",
      "password": "mypassword"
    }
  }'
```

### Python Example

```python
import requests

# Health check
response = requests.get("http://localhost:5003/health")
print(response.json())

# Full migration
payload = {
    "sql_server": {
        "server": "localhost\\SQLEXPRESS",
        "username": "sa",
        "password": "sqlpassword"
    },
    "postgres": {
        "host": "localhost",
        "port": 5432,
        "database": "mydb",
        "username": "postgres",
        "password": "mypassword"
    }
}

response = requests.post(
    "http://localhost:5003/migrate/full",
    json=payload
)
print(response.json())
```

### JavaScript Example

```javascript
// Health check
fetch('http://localhost:5003/health')
  .then(response => response.json())
  .then(data => console.log(data));

// Full migration
const payload = {
  sql_server: {
    server: "localhost\\SQLEXPRESS",
    username: "sa",
    password: "sqlpassword"
  },
  postgres: {
    host: "localhost",
    port: 5432,
    database: "mydb",
    username: "postgres",
    password: "mypassword"
  }
};

fetch('http://localhost:5003/migrate/full', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(payload)
})
  .then(response => response.json())
  .then(data => console.log(data));
```

---

## Security Considerations

- Credentials are sent in the request body. Use HTTPS in production.
- Ensure proper network security between the service and databases.
- Consider implementing authentication/authorization for production use.
- Store credentials securely and never commit them to version control.

---

## Support

For issues or questions, please refer to the main README.md file or contact the development team.

