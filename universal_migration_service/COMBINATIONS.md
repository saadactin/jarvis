# Migration Combinations

This document lists all supported migration combinations in the Universal Migration Service.

## Overview

**Sources (4):**
- PostgreSQL
- MySQL
- Zoho CRM API
- SQL Server

**Destinations (3):**
- ClickHouse
- PostgreSQL
- MySQL

**Total Possible Combinations:** 4 × 3 = 12

**Valid Combinations:** 12 (excluding same source/destination)

**Invalid Combinations:** 2 (PostgreSQL → PostgreSQL, MySQL → MySQL)

---

## All Valid Migration Combinations

### 1. PostgreSQL → ClickHouse ✅
**Status:** Supported  
**Description:** Migrate data from PostgreSQL database to ClickHouse analytics database.

**Example Request:**
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
    "database": "analytics",
    "username": "default",
    "password": "password"
  },
  "operation_type": "full"
}
```

---

### 2. PostgreSQL → MySQL ✅
**Status:** Supported  
**Description:** Migrate data from PostgreSQL database to MySQL database.

**Example Request:**
```json
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
    "database": "target_db",
    "username": "mysql_user",
    "password": "password"
  },
  "operation_type": "full"
}
```

---

### 3. PostgreSQL → PostgreSQL ❌
**Status:** Invalid (Same source and destination)  
**Description:** Cannot migrate from PostgreSQL to PostgreSQL. Use database replication or native tools instead.

**Error Response:**
```json
{
  "error": "Cannot migrate from postgresql to postgresql. Source and destination cannot be the same.",
  "success": false
}
```

---

### 4. MySQL → ClickHouse ✅
**Status:** Supported  
**Description:** Migrate data from MySQL database to ClickHouse analytics database.

**Example Request:**
```json
{
  "source_type": "mysql",
  "dest_type": "clickhouse",
  "source": {
    "host": "localhost",
    "port": 3306,
    "database": "source_db",
    "username": "mysql_user",
    "password": "password"
  },
  "destination": {
    "host": "localhost",
    "port": 8123,
    "database": "analytics",
    "username": "default",
    "password": "password"
  },
  "operation_type": "full"
}
```

---

### 5. MySQL → PostgreSQL ✅
**Status:** Supported  
**Description:** Migrate data from MySQL database to PostgreSQL database.

**Example Request:**
```json
{
  "source_type": "mysql",
  "dest_type": "postgresql",
  "source": {
    "host": "localhost",
    "port": 3306,
    "database": "source_db",
    "username": "mysql_user",
    "password": "password"
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
```

---

### 6. MySQL → MySQL ❌
**Status:** Invalid (Same source and destination)  
**Description:** Cannot migrate from MySQL to MySQL. Use MySQL replication or native tools instead.

**Error Response:**
```json
{
  "error": "Cannot migrate from mysql to mysql. Source and destination cannot be the same.",
  "success": false
}
```

---

### 7. Zoho → ClickHouse ✅
**Status:** Supported  
**Description:** Migrate data from Zoho CRM API to ClickHouse analytics database.

**Example Request:**
```json
{
  "source_type": "zoho",
  "dest_type": "clickhouse",
  "source": {
    "refresh_token": "your_refresh_token",
    "client_id": "your_client_id",
    "client_secret": "your_client_secret",
    "api_domain": "https://www.zohoapis.com"
  },
  "destination": {
    "host": "localhost",
    "port": 8123,
    "database": "analytics",
    "username": "default",
    "password": "password"
  },
  "operation_type": "full"
}
```

---

### 8. Zoho → PostgreSQL ✅
**Status:** Supported  
**Description:** Migrate data from Zoho CRM API to PostgreSQL database.

**Example Request:**
```json
{
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
```

---

### 9. Zoho → MySQL ✅
**Status:** Supported  
**Description:** Migrate data from Zoho CRM API to MySQL database.

**Example Request:**
```json
{
  "source_type": "zoho",
  "dest_type": "mysql",
  "source": {
    "refresh_token": "your_refresh_token",
    "client_id": "your_client_id",
    "client_secret": "your_client_secret",
    "api_domain": "https://www.zohoapis.com"
  },
  "destination": {
    "host": "localhost",
    "port": 3306,
    "database": "target_db",
    "username": "mysql_user",
    "password": "password"
  },
  "operation_type": "full"
}
```

---

### 10. SQL Server → ClickHouse ✅
**Status:** Supported  
**Description:** Migrate data from SQL Server database to ClickHouse analytics database.

**Example Request:**
```json
{
  "source_type": "sqlserver",
  "dest_type": "clickhouse",
  "source": {
    "server": "localhost\\SQLEXPRESS",
    "database": "source_db",
    "username": "sa",
    "password": "password",
    "driver": "ODBC Driver 17 for SQL Server"
  },
  "destination": {
    "host": "localhost",
    "port": 8123,
    "database": "analytics",
    "username": "default",
    "password": "password"
  },
  "operation_type": "full"
}
```

---

### 11. SQL Server → PostgreSQL ✅
**Status:** Supported  
**Description:** Migrate data from SQL Server database to PostgreSQL database.

**Example Request:**
```json
{
  "source_type": "sqlserver",
  "dest_type": "postgresql",
  "source": {
    "server": "localhost\\SQLEXPRESS",
    "database": "source_db",
    "username": "sa",
    "password": "password",
    "driver": "ODBC Driver 17 for SQL Server"
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
```

---

### 12. SQL Server → MySQL ✅
**Status:** Supported  
**Description:** Migrate data from SQL Server database to MySQL database.

**Example Request:**
```json
{
  "source_type": "sqlserver",
  "dest_type": "mysql",
  "source": {
    "server": "localhost\\SQLEXPRESS",
    "database": "source_db",
    "username": "sa",
    "password": "password",
    "driver": "ODBC Driver 17 for SQL Server"
  },
  "destination": {
    "host": "localhost",
    "port": 3306,
    "database": "target_db",
    "username": "mysql_user",
    "password": "password"
  },
  "operation_type": "full"
}
```

---

## Summary Table

| Source | ClickHouse | PostgreSQL | MySQL |
|--------|-----------|------------|-------|
| **PostgreSQL** | ✅ | ❌ | ✅ |
| **MySQL** | ✅ | ✅ | ❌ |
| **Zoho** | ✅ | ✅ | ✅ |
| **SQL Server** | ✅ | ✅ | ✅ |

**Legend:**
- ✅ = Supported
- ❌ = Invalid (same source/destination)

---

## Incremental Migration

All valid combinations support incremental migration. Add `operation_type: "incremental"` and `last_sync_time` to the request:

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

---

## Notes

1. **Same Source/Destination Validation:** The service automatically prevents migrations where source and destination are the same database type.

2. **Type Mapping:** All adapters handle automatic type mapping from source to destination types.

3. **Error Handling:** Failed table migrations are logged but don't stop the entire migration process.

4. **Batch Processing:** All migrations use batch processing for efficiency.

5. **Connection Testing:** Use the `/test-connection` endpoint to verify credentials before migration.

---

## Future Combinations

As new sources and destinations are added, they will automatically work with all existing adapters:

- **New Source Added:** Works with ALL existing destinations
- **New Destination Added:** Receives from ALL existing sources

This is the power of the Universal Pipeline Architecture!

