# Jarvis Backend - Complete API Documentation

Complete guide to running, scheduling, and executing data migrations in the Jarvis Backend system.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Environment Setup](#environment-setup)
4. [Starting the Services](#starting-the-services)
5. [Authentication](#authentication)
6. [Database Master Management](#database-master-management)
7. [Scheduling Migrations](#scheduling-migrations)
8. [Executing Migrations](#executing-migrations)
9. [Universal Migration Service](#universal-migration-service)
10. [Complete Examples](#complete-examples)
11. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

The Jarvis Backend consists of multiple services:

```
┌─────────────────────────────────────────────────────────────┐
│                    Main Backend (jarvis-main)                │
│                    Port: 5009                                │
│  - User Authentication                                       │
│  - Database Master Registry                                   │
│  - Operations Scheduling & Execution                         │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ Calls
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Universal Migration Service                     │
│              Port: 5010                                      │
│  - Handles ALL source → destination migrations               │
│  - Supports: PostgreSQL, MySQL, Zoho, SQL Server              │
│  - Destinations: ClickHouse, PostgreSQL, MySQL               │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ OR (Legacy Services)
                            ▼
┌──────────────┬──────────────┬──────────────────────────────┐
│ Postgres     │ Zoho         │ SQL Postgres                  │
│ Service      │ Service      │ Service                       │
│ Port: 5001   │ Port: 5002   │ Port: 5003                   │
└──────────────┴──────────────┴──────────────────────────────┘
```

### Key Components

1. **Main Backend (jarvis-main)**: Central orchestrator for user management, service registry, and operation scheduling
2. **Universal Migration Service**: Single service handling all database migrations using adapter pattern
3. **Legacy Microservices**: Individual services for specific migrations (optional, can use Universal Service instead)

---

## Prerequisites

### Required Software

- Python 3.8+
- PostgreSQL (for main backend database)
- ClickHouse (optional, for analytics destination)
- MySQL (optional, for source/destination)
- SQL Server (optional, for source)
- pip (Python package manager)

### Required Python Packages

All services have their own `requirements.txt` files. Install dependencies for each service:

```bash
# Main Backend
cd jarvis-main
pip install -r requirements.txt

# Universal Migration Service
cd ../universal_migration_service
pip install -r requirements.txt

# Legacy Services (optional)
cd ../postgres_service
pip install -r requirements.txt

cd ../zoho_service
pip install -r requirements.txt

cd ../sql_postgres_service
pip install -r requirements.txt
```

---

## Environment Setup

### Step 1: Create .env File

Copy the `.env.example` file to `.env` in the root directory:

```bash
cp .env.example .env
```

### Step 2: Configure Environment Variables

Edit `.env` file with your actual credentials:

```env
# Main Backend
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here
HOST=0.0.0.0
PORT=5009
DEBUG=True

# Main Database (PostgreSQL for jarvis-main)
DATABASE_URL=postgresql://postgres:password@localhost:5432/jarvis_db

# PostgreSQL Credentials
PG_HOST=localhost
PG_PORT=5432
PG_DATABASE=source_database
PG_USERNAME=postgres
PG_PASSWORD=your_password

# MySQL Credentials
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=source_database
MYSQL_USERNAME=root
MYSQL_PASSWORD=your_password

# ClickHouse Credentials
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123
CLICKHOUSE_USER=default
CLICKHOUSE_PASS=your_password
CLICKHOUSE_DB=analytics_db

# Zoho CRM API Credentials
ZOHO_REFRESH_TOKEN=your_refresh_token
ZOHO_CLIENT_ID=your_client_id
ZOHO_CLIENT_SECRET=your_client_secret
ZOHO_API_DOMAIN=https://www.zohoapis.com

# SQL Server Credentials (Source)
# For Named Instance: use SERVER=hostname\instancename (e.g., localhost\SQLEXPRESS)
# For Default Instance: use SERVER=hostname (e.g., localhost)
SQL_SERVER_SERVER=localhost\SQLEXPRESS
SQL_SERVER_DATABASE=source_db
SQL_SERVER_USERNAME=sa
SQL_SERVER_PASSWORD=your_password
SQL_SERVER_DRIVER=ODBC Driver 17 for SQL Server

# For Windows Authentication (leave username/password empty or set to 'windows'):
# SQL_SERVER_USERNAME=windows
# SQL_SERVER_PASSWORD=windows
```

### Step 3: Initialize Main Database

Initialize the PostgreSQL database for the main backend:

```bash
cd jarvis-main
python init_db.py
```

This creates the necessary tables:
- `users` - User authentication
- `database_master` - Microservice registry
- `operations` - Migration operations

---

## Starting the Services

### Option 1: Start All Services Manually

#### Terminal 1: Main Backend
```bash
cd jarvis-main
python app.py
```
**Output:**
```
Starting Jarvis Main Backend...
Running on http://0.0.0.0:5009
```

#### Terminal 2: Universal Migration Service
```bash
cd universal_migration_service
python app.py
```
**Output:**
```
Starting Universal Migration Service...
Available sources: ['postgresql', 'mysql', 'zoho', 'sqlserver']
Available destinations: ['clickhouse', 'postgresql', 'mysql']
Running on http://0.0.0.0:5010
```

#### Terminal 3: Legacy Services (Optional)
```bash
# Postgres Service
cd postgres_service
python app.py

# Zoho Service (in another terminal)
cd zoho_service
python app.py

# SQL Postgres Service (in another terminal)
cd sql_postgres_service
python app.py
```

### Option 2: Using Background Processes (Windows PowerShell)

```powershell
# Start Main Backend
Start-Process python -ArgumentList "jarvis-main/app.py" -WindowStyle Minimized

# Start Universal Migration Service
Start-Process python -ArgumentList "universal_migration_service/app.py" -WindowStyle Minimized
```

### Verify Services are Running

Check health endpoints:

```bash
# Main Backend
curl http://localhost:5009/health

# Universal Migration Service
curl http://localhost:5010/health
```

---

## Authentication

All API endpoints (except `/health` and `/api/auth/*`) require JWT authentication.

### Step 1: Register a User

**Endpoint:** `POST /api/auth/register`

**Request:**
```bash
curl -X POST http://localhost:5009/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@example.com",
    "password": "securepassword123"
  }'
```

**Response:**
```json
{
  "message": "User registered successfully",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
}
```

### Step 2: Login

**Endpoint:** `POST /api/auth/login`

**Request:**
```bash
curl -X POST http://localhost:5009/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "securepassword123"
  }'
```

**Response:**
```json
{
  "message": "Login successful",
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com"
  }
}
```

**Save the `access_token` for subsequent requests!**

### Step 3: Use Token in Requests

Include the token in the `Authorization` header:

```bash
curl -X GET http://localhost:5009/api/database-master \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
```

---

## Database Master Management

The Database Master table stores information about available migration services.

### Register Universal Migration Service

**Endpoint:** `POST /api/database-master`

**Request:**
```bash
curl -X POST http://localhost:5009/api/database-master \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Universal Migration Service",
    "service_url": "http://localhost:5010"
  }'
```

**Response:**
```json
{
  "message": "Database master created successfully",
  "database": {
    "id": 1,
    "name": "Universal Migration Service",
    "service_url": "http://localhost:5010",
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
}
```

### Get All Database Masters

**Endpoint:** `GET /api/database-master`

**Request:**
```bash
curl -X GET http://localhost:5009/api/database-master \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "databases": [
    {
      "id": 1,
      "name": "Universal Migration Service",
      "service_url": "http://localhost:5010",
      "created_at": "2024-01-01T00:00:00",
      "updated_at": "2024-01-01T00:00:00"
    }
  ]
}
```

### Update Database Master

**Endpoint:** `PUT /api/database-master/<id>`

**Request:**
```bash
curl -X PUT http://localhost:5009/api/database-master/1 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Universal Migration Service",
    "service_url": "http://localhost:5010"
  }'
```

### Delete Database Master

**Endpoint:** `DELETE /api/database-master/<id>`

**Request:**
```bash
curl -X DELETE http://localhost:5009/api/database-master/1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Scheduling Migrations

Operations can be scheduled for future execution. The system automatically executes pending operations when their scheduled time arrives.

### Create a Scheduled Operation

**Endpoint:** `POST /api/operations`

**Request Body:**
```json
{
  "source_id": 1,
  "schedule": "2024-01-15T10:30:00",
  "operation_type": "full",
  "config_data": {
    "source_type": "postgresql",
    "dest_type": "clickhouse",
    "source": {
      "host": "localhost",
      "port": 5432,
      "database": "source_db",
      "username": "postgres",
      "password": "password"
    },
    "destination": {
      "host": "localhost",
      "port": 8123,
      "database": "analytics_db",
      "username": "default",
      "password": "password"
    },
    "operation_type": "full"
  }
}
```

**Important Notes:**
- `schedule` can be in UTC or IST format. If not specified, IST (UTC+5:30) is assumed.
- `source_id` must match a registered Database Master ID.
- `config_data` contains the actual migration configuration.

**Full Example Request:**
```bash
curl -X POST http://localhost:5009/api/operations \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source_id": 1,
    "schedule": "2024-01-15T10:30:00",
    "operation_type": "full",
    "config_data": {
      "source_type": "postgresql",
      "dest_type": "clickhouse",
      "source": {
        "host": "localhost",
        "port": 5432,
        "database": "source_db",
        "username": "postgres",
        "password": "password"
      },
      "destination": {
        "host": "localhost",
        "port": 8123,
        "database": "analytics_db",
        "username": "default",
        "password": "password"
      },
      "operation_type": "full"
    }
  }'
```

**Response:**
```json
{
  "message": "Operation created successfully",
  "operation": {
    "id": 1,
    "source_id": 1,
    "source_name": "Universal Migration Service",
    "user_id": 1,
    "username": "admin",
    "schedule": "2024-01-15T10:30:00",
    "status": "pending",
    "operation_type": "full",
    "config_data": {...},
    "result_data": null,
    "error_message": null,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00",
    "started_at": null,
    "completed_at": null
  }
}
```

### Get All Operations

**Endpoint:** `GET /api/operations`

**Request:**
```bash
curl -X GET http://localhost:5009/api/operations \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "operations": [
    {
      "id": 1,
      "source_id": 1,
      "source_name": "Universal Migration Service",
      "user_id": 1,
      "username": "admin",
      "schedule": "2024-01-15T10:30:00",
      "status": "pending",
      "operation_type": "full",
      "config_data": {...},
      "result_data": null,
      "error_message": null,
      "created_at": "2024-01-01T00:00:00",
      "updated_at": "2024-01-01T00:00:00",
      "started_at": null,
      "completed_at": null
    }
  ]
}
```

### Get Operation by ID

**Endpoint:** `GET /api/operations/<id>`

**Request:**
```bash
curl -X GET http://localhost:5009/api/operations/1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "operation": {
    "id": 1,
    "source_id": 1,
    "source_name": "Universal Migration Service",
    "user_id": 1,
    "username": "admin",
    "schedule": "2024-01-15T10:30:00",
    "status": "completed",
    "operation_type": "full",
    "config_data": {...},
    "result_data": {...},
    "error_message": null,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00",
    "started_at": "2024-01-15T10:30:00",
    "completed_at": "2024-01-15T10:35:00"
  }
}
```

### Get Operation Status (Detailed)

**Endpoint:** `GET /api/operations/<id>/status`

**Description:** Get detailed status information about an operation, including migration results, duration, and completion status.

**Request:**
```bash
curl -X GET http://localhost:5009/api/operations/1/status \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "operation_id": 1,
  "status": "completed",
  "is_completed": true,
  "is_success": true,
  "operation_type": "full",
  "source_name": "Universal Migration Service",
  "schedule_time": "2024-01-15T10:30:00",
  "started_at": "2024-01-15T10:30:00",
  "completed_at": "2024-01-15T10:35:00",
  "created_at": "2024-01-01T00:00:00",
  "error_message": null,
  "duration_seconds": 300,
  "duration_formatted": "5m 0s",
  "migration_results": {
    "success": true,
    "total_tables": 2,
    "tables_migrated_count": 2,
    "tables_failed_count": 0,
    "tables_migrated": [
      {"table": "users", "records": 1000},
      {"table": "orders", "records": 500}
    ],
    "tables_failed": [],
    "total_records": 1500,
    "errors": []
  }
}
```

**Status Values:**
- `is_completed`: `true` if status is `completed` or `failed`, `false` otherwise
- `is_success`: `true` if status is `completed`, `false` otherwise
- `duration_seconds`: Total execution time in seconds (only if completed)
- `duration_formatted`: Human-readable duration (e.g., "5m 30s")
- `migration_results`: Detailed migration statistics (only if operation has completed)

**Use Cases:**
- Check if an operation has completed
- Get detailed migration statistics
- Monitor operation progress
- Debug failed migrations

### Get Operations Summary

**Endpoint:** `GET /api/operations/summary`

**Description:** Get a summary of all operations with statistics grouped by status and type.

**Request:**
```bash
curl -X GET http://localhost:5009/api/operations/summary \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "total_operations": 10,
  "by_status": {
    "pending": 2,
    "running": 1,
    "completed": 6,
    "failed": 1
  },
  "by_type": {
    "full": 7,
    "incremental": 3
  },
  "recent_operations": [
    {
      "id": 10,
      "status": "completed",
      "operation_type": "full",
      "source_name": "Universal Migration Service",
      "created_at": "2024-01-20T10:00:00",
      "completed_at": "2024-01-20T10:05:00"
    },
    {
      "id": 9,
      "status": "running",
      "operation_type": "incremental",
      "source_name": "Universal Migration Service",
      "created_at": "2024-01-20T09:00:00",
      "completed_at": null
    }
  ]
}
```

**Response Fields:**
- `total_operations`: Total number of operations for the user
- `by_status`: Count of operations grouped by status (pending, running, completed, failed)
- `by_type`: Count of operations grouped by type (full, incremental)
- `recent_operations`: List of 10 most recent operations (sorted by creation date)

**Use Cases:**
- Dashboard overview of all operations
- Quick status check
- Monitoring operation health
- Statistics and reporting

### Update Operation

**Endpoint:** `PUT /api/operations/<id>`

**Request:**
```bash
curl -X PUT http://localhost:5009/api/operations/1 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "schedule": "2024-01-16T10:30:00",
    "operation_type": "incremental",
    "config_data": {...}
  }'
```

### Delete Operation

**Endpoint:** `DELETE /api/operations/<id>`

**Request:**
```bash
curl -X DELETE http://localhost:5009/api/operations/1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Executing Migrations

### Automatic Execution

The main backend runs a background scheduler that automatically executes operations when their scheduled time arrives. No manual intervention needed!

### Manual Execution (Immediate)

**Endpoint:** `POST /api/operations/<id>/execute?force=true`

**Description:** Manually execute an operation immediately, bypassing the scheduled time. The system will:
1. Test source and destination connections (for Universal Migration Service)
2. Update operation status to `running`
3. Call the microservice API
4. Update operation with results

**Request:**
```bash
curl -X POST "http://localhost:5009/api/operations/1/execute?force=true" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Query Parameters:**
- `force=true`: Execute immediately, even if scheduled for future (optional, default: false)

**Response (Success):**
```json
{
  "message": "Operation executed successfully",
  "operation": {
    "id": 1,
    "status": "completed",
    "started_at": "2024-01-01T10:30:00",
    "completed_at": "2024-01-01T10:35:00",
    "result_data": {
      "success": true,
      "tables_migrated": [
        {"table": "users", "records": 1000},
        {"table": "orders", "records": 500}
      ],
      "tables_failed": [],
      "total_tables": 2,
      "errors": []
    }
  },
  "microservice_response": {
    "success": true,
    "tables_migrated": [...],
    "total_tables": 2
  },
  "status_code": 200
}
```

**Response (Connection Test Failed):**
```json
{
  "error": "Source connection test failed",
  "operation": {
    "id": 1,
    "status": "failed",
    "error_message": "Source connection failed: Connection timeout"
  }
}
```

**Response (Already Completed):**
```json
{
  "message": "Operation already completed",
  "operation": {
    "id": 1,
    "status": "completed",
    ...
  }
}
```

**Status Codes:**
- `200 OK` - Operation executed successfully or already completed
- `400 Bad Request` - Operation already running, scheduled for future (without force), or connection test failed
- `403 Forbidden` - Not authorized
- `404 Not Found` - Operation not found
- `500 Internal Server Error` - Error calling microservice

**Features:**
- **Connection Testing**: Automatically tests source and destination connections before migration (Universal Migration Service only)
- **Status Tracking**: Operation status is updated to `running` during execution
- **Result Storage**: Migration results are stored in `result_data` field
- **Error Handling**: Failed operations are marked with detailed error messages
- **Success Validation**: Checks `success` field in response to determine actual migration success

---

## Universal Migration Service

The Universal Migration Service handles all migrations using a single endpoint.

### Direct Migration (Without Scheduling)

**Endpoint:** `POST http://localhost:5010/migrate`

**Request:**
```json
{
  "source_type": "postgresql",
  "dest_type": "clickhouse",
  "source": {
    "host": "localhost",
    "port": 5432,
    "database": "source_db",
    "username": "postgres",
    "password": "password"
  },
  "destination": {
    "host": "localhost",
    "port": 8123,
    "database": "analytics_db",
    "username": "default",
    "password": "password"
  },
  "operation_type": "full"
}
```

**Example Request:**
```bash
curl -X POST http://localhost:5010/migrate \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "postgresql",
    "dest_type": "clickhouse",
    "source": {
      "host": "localhost",
      "port": 5432,
      "database": "source_db",
      "username": "postgres",
      "password": "password"
    },
    "destination": {
      "host": "localhost",
      "port": 8123,
      "database": "analytics_db",
      "username": "default",
      "password": "password"
    },
    "operation_type": "full"
  }'
```

**Response:**
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

### Incremental Migration

**Request:**
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

### Supported Combinations

See [COMBINATIONS.md](universal_migration_service/COMBINATIONS.md) for all supported migration paths.

**Valid Examples:**
- PostgreSQL → ClickHouse ✅
- PostgreSQL → MySQL ✅
- MySQL → ClickHouse ✅
- MySQL → PostgreSQL ✅
- Zoho → ClickHouse ✅
- Zoho → PostgreSQL ✅
- Zoho → MySQL ✅
- SQL Server → ClickHouse ✅
- SQL Server → PostgreSQL ✅
- SQL Server → MySQL ✅

**Invalid (Blocked):**
- PostgreSQL → PostgreSQL ❌
- MySQL → MySQL ❌

---

## Complete Examples

### Example 1: Full Migration from PostgreSQL to ClickHouse (Scheduled)

**Step 1: Register User**
```bash
curl -X POST http://localhost:5009/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "email": "admin@example.com", "password": "pass123"}'
```

**Step 2: Login**
```bash
TOKEN=$(curl -X POST http://localhost:5009/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "pass123"}' | jq -r '.access_token')
```

**Step 3: Register Universal Migration Service**
```bash
curl -X POST http://localhost:5009/api/database-master \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Universal Migration", "service_url": "http://localhost:5010"}'
```

**Step 4: Create Scheduled Operation**
```bash
curl -X POST http://localhost:5009/api/operations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source_id": 1,
    "schedule": "2024-01-15T10:30:00",
    "operation_type": "full",
    "config_data": {
      "source_type": "postgresql",
      "dest_type": "clickhouse",
      "source": {
        "host": "localhost",
        "port": 5432,
        "database": "source_db",
        "username": "postgres",
        "password": "password"
      },
      "destination": {
        "host": "localhost",
        "port": 8123,
        "database": "analytics_db",
        "username": "default",
        "password": "password"
      },
      "operation_type": "full"
    }
  }'
```

**Step 5: Check Operation Status**
```bash
curl -X GET http://localhost:5009/api/operations/1 \
  -H "Authorization: Bearer $TOKEN"
```

### Example 2: Immediate Migration from Zoho to PostgreSQL

**Step 1: Create Operation (Scheduled for Now)**
```bash
curl -X POST http://localhost:5009/api/operations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source_id": 1,
    "schedule": "2024-01-01T00:00:00",
    "operation_type": "full",
    "config_data": {
      "source_type": "zoho",
      "dest_type": "postgresql",
      "source": {
        "refresh_token": "your_refresh_token",
        "client_id": "your_client_id",
        "client_secret": "your_client_secret",
        "api_domain": "https://www.zohoapis.com"
      },
      "destination": {
        "host": "localhost",
        "port": 5432,
        "database": "target_db",
        "username": "postgres",
        "password": "password"
      },
      "operation_type": "full"
    }
  }'
```

**Step 2: Execute Immediately**
```bash
curl -X POST "http://localhost:5009/api/operations/2/execute?force=true" \
  -H "Authorization: Bearer $TOKEN"
```

### Example 3: Direct Migration (Without Main Backend)

```bash
curl -X POST http://localhost:5010/migrate \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "mysql",
    "dest_type": "clickhouse",
    "source": {
      "host": "localhost",
      "port": 3306,
      "database": "source_db",
      "username": "root",
      "password": "password"
    },
    "destination": {
      "host": "localhost",
      "port": 8123,
      "database": "analytics_db",
      "username": "default",
      "password": "password"
    },
    "operation_type": "full"
  }'
```

---

## Troubleshooting

### Service Not Starting

**Problem:** `ModuleNotFoundError: No module named 'xxx'`

**Solution:**
```bash
cd <service_directory>
pip install -r requirements.txt
```

### Database Connection Error

**Problem:** `Failed to connect to PostgreSQL`

**Solution:**
1. Verify PostgreSQL is running: `pg_isready`
2. Check credentials in `.env` file
3. Verify database exists: `psql -U postgres -l`

### JWT Token Expired

**Problem:** `Token has expired`

**Solution:** Login again to get a new token:
```bash
curl -X POST http://localhost:5009/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "pass123"}'
```

### Operation Not Executing

**Problem:** Operation status remains "pending"

**Solution:**
1. Check if scheduled time has passed
2. Verify main backend is running
3. Check logs for errors
4. Try manual execution: `POST /api/operations/<id>/execute?force=true`

### Migration Fails

**Problem:** `tables_failed` in response

**Solution:**
1. Check source database connection
2. Verify destination database exists
3. Check table permissions
4. Review error messages in `result_data`

### Port Already in Use

**Problem:** `Address already in use`

**Solution:**
1. Find process using port: `netstat -ano | findstr :5009`
2. Kill process or change port in `.env`

---

## API Reference Summary

### Main Backend (Port 5009)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | No | Health check |
| `/api/auth/register` | POST | No | Register user |
| `/api/auth/login` | POST | No | Login |
| `/api/auth/me` | GET | Yes | Get current user |
| `/api/database-master` | GET | Yes | List all services |
| `/api/database-master` | POST | Yes | Register service |
| `/api/database-master/<id>` | GET | Yes | Get service |
| `/api/database-master/<id>` | PUT | Yes | Update service |
| `/api/database-master/<id>` | DELETE | Yes | Delete service |
| `/api/operations` | GET | Yes | List operations |
| `/api/operations` | POST | Yes | Create operation |
| `/api/operations/<id>` | GET | Yes | Get operation |
| `/api/operations/<id>` | PUT | Yes | Update operation |
| `/api/operations/<id>` | DELETE | Yes | Delete operation |
| `/api/operations/<id>/status` | GET | Yes | Get detailed operation status |
| `/api/operations/<id>/execute` | POST | Yes | Execute operation |
| `/api/operations/summary` | GET | Yes | Get operations summary |

### Universal Migration Service (Port 5010)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | No | Health check |
| `/migrate` | POST | No | Execute migration |
| `/test-connection` | POST | No | Test connection |

---

## Best Practices

1. **Use Universal Migration Service**: Prefer the universal service over legacy microservices
2. **Schedule Operations**: Use scheduling for regular migrations
3. **Monitor Operations**: Regularly check operation status using `/api/operations/<id>/status`
4. **Check Summary**: Use `/api/operations/summary` for quick overview of all operations
5. **Secure Credentials**: Never commit `.env` file to version control
6. **Error Handling**: Always check `result_data` for migration results
7. **Incremental Migrations**: Use incremental for large datasets
8. **Test Connections**: Use `/test-connection` before scheduling (automatic for Universal Migration Service)
9. **Verify Completion**: Use `is_completed` and `is_success` fields in status endpoint
10. **Monitor Duration**: Check `duration_seconds` to track migration performance

---

## Support

For issues or questions:
1. Check logs in service directories
2. Review error messages in operation `result_data`
3. Verify all services are running
4. Check `.env` configuration

---

**Last Updated:** 2024-01-20  
**Version:** 1.1.0

## Changelog

### Version 1.1.0 (2024-01-20)
- Added `/api/operations/<id>/status` endpoint for detailed operation status
- Added `/api/operations/summary` endpoint for operations overview
- Improved connection testing before migration execution
- Enhanced error handling with better success validation
- Increased timeout for large migrations (10 minutes)
- Better support for Universal Migration Service in scheduler

