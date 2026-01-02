# Migration Guide: Using Universal Migration Service

## Overview

The Universal Migration Service replaces the need for separate microservices for each source-destination combination. Instead, you use adapters that work with all destinations.

## Current Status

### ✅ Implemented Adapters

**Sources:**
- PostgreSQL → Works with ALL destinations
- MySQL → Works with ALL destinations  
- Zoho CRM API → Works with ALL destinations
- SQL Server → Works with ALL destinations

**Destinations:**
- ClickHouse → Receives from ALL sources
- PostgreSQL → Receives from ALL sources

### Migration Combinations Available

1. **Zoho → ClickHouse** ✅
2. **Zoho → PostgreSQL** ✅
3. **SQL Server → ClickHouse** ✅
4. **SQL Server → PostgreSQL** ✅
5. **PostgreSQL → ClickHouse** ✅
6. **PostgreSQL → PostgreSQL** ✅
7. **MySQL → ClickHouse** ✅
8. **MySQL → PostgreSQL** ✅

## How to Use

### Example: Zoho to ClickHouse

```bash
POST http://localhost:5010/migrate
Content-Type: application/json

{
  "source_type": "zoho",
  "dest_type": "clickhouse",
  "source": {
    "refresh_token": "your_refresh_token",
    "client_id": "your_client_id",
    "client_secret": "your_client_secret",
    "api_domain": "https://www.zohoapis.in"
  },
  "destination": {
    "host": "localhost",
    "port": 8123,
    "database": "zoho_data",
    "username": "default",
    "password": "your_password"
  },
  "operation_type": "full"
}
```

### Example: SQL Server to PostgreSQL

```bash
POST http://localhost:5010/migrate
Content-Type: application/json

{
  "source_type": "sqlserver",
  "dest_type": "postgresql",
  "source": {
    "server": "localhost\\SQLEXPRESS",
    "username": "sa",
    "password": "your_password"
  },
  "destination": {
    "host": "localhost",
    "port": 5432,
    "database": "migrated_data",
    "username": "postgres",
    "password": "your_password"
  },
  "operation_type": "full"
}
```

## Old Services vs Universal Service

### Old Approach (Still Available)
- `postgres_service/` - PostgreSQL → ClickHouse only
- `zoho_service/` - Zoho → ClickHouse only
- `sql_postgres_service/` - SQL Server → PostgreSQL only

### New Approach (Recommended)
- `universal_migration_service/` - ALL combinations in one service

**Benefits:**
- One service instead of multiple
- Add new source → Works with ALL destinations automatically
- Add new destination → Receives from ALL sources automatically
- Easier maintenance and testing

## Testing

Run the test suite:

```bash
cd tests
python -m pytest test_adapters.py
python -m pytest test_pipeline.py
python -m pytest test_integration.py
```

## Next Steps

1. Install dependencies: `pip install -r requirements.txt`
2. Start the service: `python app.py`
3. Test with your databases
4. Gradually migrate from old services to universal service

