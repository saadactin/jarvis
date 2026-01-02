# PostgreSQL to ClickHouse Migration API Documentation

## Base URL
```
http://localhost:5001
```

## Overview

This microservice provides REST API endpoints for migrating data from PostgreSQL databases to ClickHouse databases. It supports both full migration and incremental synchronization.

## Endpoints

### 1. Health Check

Check if the service is running and healthy.

**Endpoint:** `GET /health`

**Request:**
```http
GET /health HTTP/1.1
Host: localhost:5001
```

**Response:**
```json
{
  "status": "healthy",
  "service": "postgres_migration"
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
  "tables_migrated": [
    "users",
    "orders",
    "products"
  ],
  "tables_failed": [],
  "total_tables": 3,
  "errors": []
}
```

**Error Response (400 Bad Request):**
```json
{
  "error": "postgres.host is required"
}
```

**Error Response (500 Internal Server Error):**
```json
{
  "success": false,
  "tables_migrated": [
    "users",
    "orders"
  ],
  "tables_failed": [
    {
      "table": "products",
      "error": "Connection timeout"
    }
  ],
  "total_tables": 3,
  "errors": [
    "products: Connection timeout"
  ]
}
```

**Status Codes:**
- `200 OK` - Migration completed successfully
- `400 Bad Request` - Invalid request body or missing required fields
- `500 Internal Server Error` - Migration failed or partial failure

**Notes:**
- Tables in ClickHouse will be prefixed with `HR_` (e.g., `users` → `HR_users`)
- Only tables from PostgreSQL's `public` schema are migrated
- Migration is performed in batches of 1000 rows
- Existing tables in ClickHouse are not overwritten, only new rows are inserted

---

### 3. Incremental Migration

Perform an incremental migration that only inserts new rows. Compares existing data in ClickHouse to avoid duplicates.

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
  "tables_migrated": [
    "users",
    "orders",
    "products"
  ],
  "tables_failed": [],
  "total_tables": 3,
  "errors": []
}
```

**Error Response (400 Bad Request):**
```json
{
  "error": "clickhouse.password is required"
}
```

**Error Response (500 Internal Server Error):**
```json
{
  "success": false,
  "tables_migrated": ["users"],
  "tables_failed": [
    {
      "table": "orders",
      "error": "Table does not exist in ClickHouse"
    }
  ],
  "total_tables": 2,
  "errors": [
    "orders: Table does not exist in ClickHouse"
  ]
}
```

**Status Codes:**
- `200 OK` - Incremental migration completed successfully
- `400 Bad Request` - Invalid request body or missing required fields
- `500 Internal Server Error` - Migration failed or partial failure

**Notes:**
- Uses primary keys to detect duplicate rows
- Only inserts rows that don't exist in ClickHouse
- Tables must exist in ClickHouse before running incremental migration
- For tables without primary keys, uses full row comparison (less efficient)

---

## Data Type Mapping

The service automatically maps PostgreSQL data types to ClickHouse equivalents:

| PostgreSQL Type | ClickHouse Type |
|----------------|-----------------|
| smallint | Int16 |
| integer | Int32 |
| bigint | Int64 |
| serial | Int32 |
| real | Float32 |
| double precision | Float64 |
| numeric/decimal | Decimal64(2) |
| boolean | UInt8 |
| varchar/text | String |
| timestamp | DateTime |
| date | Date |
| json/jsonb | String |
| uuid | UUID |
| Unknown types | String (default) |

---

## Error Handling

All endpoints return appropriate HTTP status codes:

- **200 OK**: Request succeeded
- **400 Bad Request**: Invalid request parameters
- **500 Internal Server Error**: Server error during processing

Error responses include a descriptive error message in the response body.

---

## Rate Limiting

Currently, there are no rate limits imposed. However, large migrations may take significant time to complete.

---

## Examples

### cURL Examples

**Health Check:**
```bash
curl -X GET http://localhost:5001/health
```

**Full Migration:**
```bash
curl -X POST http://localhost:5001/migrate/full \
  -H "Content-Type: application/json" \
  -d '{
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
  }'
```

**Incremental Migration:**
```bash
curl -X POST http://localhost:5001/migrate/incremental \
  -H "Content-Type: application/json" \
  -d '{
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
  }'
```

### Python Example

```python
import requests

# Health check
response = requests.get("http://localhost:5001/health")
print(response.json())

# Full migration
payload = {
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

response = requests.post(
    "http://localhost:5001/migrate/full",
    json=payload
)
print(response.json())
```

### JavaScript Example

```javascript
// Health check
fetch('http://localhost:5001/health')
  .then(response => response.json())
  .then(data => console.log(data));

// Full migration
const payload = {
  postgres: {
    host: "localhost",
    port: 5432,
    database: "mydb",
    username: "postgres",
    password: "mypassword"
  },
  clickhouse: {
    host: "localhost",
    database: "analytics",
    username: "default",
    password: "clickhouse_password"
  }
};

fetch('http://localhost:5001/migrate/full', {
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

