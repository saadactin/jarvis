# Complete Guide: SQL Server to PostgreSQL Migration

This guide provides step-by-step instructions for migrating data from SQL Server to PostgreSQL using the Jarvis Migration System.

## Prerequisites

1. **Main Backend** (jarvis-main) running on port 5009
2. **Universal Migration Service** running on port 5010
3. **Frontend** accessible (localhost:8080)
4. **SQL Server** accessible with credentials
5. **PostgreSQL** database ready to receive data

---

## Step-by-Step Migration Flow

### Step 1: Start Required Services

#### Option A: Using Service Manager UI (Recommended)

1. Open the frontend: `http://localhost:8080`
2. Login to your account
3. Navigate to **Service Manager** from the sidebar
4. Click **"Start All Required"** button
5. Wait for "Universal Migration Service" to show status: **Running** (green badge)

#### Option B: Using Terminal Commands

```powershell
# Terminal 1: Main Backend (if not already running)
cd jarvis-main
python app.py

# Terminal 2: Universal Migration Service
cd universal_migration_service
python app.py
```

**Verify Services:**
```bash
# Check main backend
curl http://localhost:5009/health

# Check universal migration service
curl http://localhost:5010/health
```

---

### Step 2: Register Universal Migration Service (First Time Only)

1. Go to **Database Masters** page from sidebar
2. Click **"Add Database Master"** button
3. In the dropdown, select **"Universal Migration Service"**
   - Name and URL will auto-fill:
     - Name: `Universal Migration Service`
     - URL: `http://localhost:5010`
4. Click **"Save"**

**Note:** If already registered, skip this step.

---

### Step 3: Create Migration Operation

1. Navigate to **Operations** page
2. Click **"Create Operation"** button
3. Follow the 6-step wizard:

#### Step 1: Source Configuration
- **Source Type:** Select `SQL Server` 🗄️
- Click **Next**

#### Step 2: Destination Configuration  
- **Destination Type:** Select `PostgreSQL` 🗄️
- Click **Next**

#### Step 3: Source Connection Details
Fill in your SQL Server connection details:

```
Server: localhost\SQLEXPRESS
        (or your SQL Server instance name)
Database: Desserts
        (or your source database name)
Username: sa
        (or your SQL Server username)
Password: your_sql_server_password
```

- Click **Next**

#### Step 4: Destination Connection Details
Fill in your PostgreSQL connection details:

```
Host: localhost
Port: 5432
Database: test3
        (or your target PostgreSQL database name)
Username: migration_user
        (or your PostgreSQL username)
Password: your_postgresql_password
```

- Click **Next**

#### Step 5: Schedule & Operation Type
- **Operation Type:** Select `Full Migration` (or `Incremental Migration` if you've run it before)
- **Schedule:** 
  - For immediate execution: Set to current time or earlier
  - For scheduled: Set future date/time
- Click **Next**

#### Step 6: Review & Submit
- Review all configuration details
- Click **"Create Operation"** button

---

### Step 4: Execute Migration

#### Option A: Execute Immediately (If scheduled for past time)
- The background scheduler will automatically execute pending operations
- Go to **Operations** page and monitor the status

#### Option B: Execute Manually
1. Go to **Operations** page
2. Find your created operation
3. Click **"View"** button
4. Click **"Execute Now"** button
5. Wait for the migration to complete

---

### Step 5: Monitor Migration Status

1. **Operations Page:**
   - Status badges: `Pending` → `Running` → `Completed` / `Failed`
   - Filter by status to find your operation

2. **Operation Details Page:**
   - Click **"View"** on any operation
   - See detailed status:
     - Started at: Timestamp when migration started
     - Completed at: Timestamp when migration finished
     - Result data: Migration statistics
     - Error message: If migration failed

3. **Dashboard:**
   - Overview of all operations
   - Statistics and charts

---

## What Happens During Migration

### Technical Flow

1. **Connection Validation:**
   - System validates SQL Server connection
   - System validates PostgreSQL connection

2. **Schema Discovery:**
   - SQL Server Source Adapter discovers all tables in the database
   - Reads table schemas (column names, data types)

3. **Type Mapping:**
   - SQL Server types → PostgreSQL types
   - Example: `nvarchar(max)` → `TEXT`, `int` → `INTEGER`

4. **Table Creation:**
   - PostgreSQL Destination Adapter creates tables in target database
   - Uses same table names as source (or with prefix if configured)

5. **Data Migration:**
   - Reads data from SQL Server tables in batches
   - Transforms data if needed
   - Inserts data into PostgreSQL tables
   - Processes all tables sequentially

6. **Completion:**
   - All tables migrated successfully
   - Returns migration statistics
   - Status updated to `Completed`

---

## Example: Complete Request Flow

### Via Frontend (Recommended)

Follow the wizard steps above - the frontend handles all API calls automatically.

### Via API (Direct)

```bash
# 1. Login and get token
curl -X POST http://localhost:5009/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password"
  }'

# Response:
# {
#   "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
#   "message": "Login successful"
# }

# 2. Create Operation
curl -X POST http://localhost:5009/api/operations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "source_id": 1,
    "schedule": "2024-12-26T10:00:00+05:30",
    "operation_type": "full",
    "config_data": {
      "source_type": "sqlserver",
      "dest_type": "postgresql",
      "source": {
        "server": "localhost\\SQLEXPRESS",
        "database": "Desserts",
        "username": "sa",
        "password": "your_sql_server_password"
      },
      "destination": {
        "host": "localhost",
        "port": 5432,
        "database": "test3",
        "username": "migration_user",
        "password": "your_postgresql_password"
      }
    }
  }'

# 3. Execute Operation
curl -X POST http://localhost:5009/api/operations/1/execute?force=true \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# 4. Check Status
curl -X GET http://localhost:5009/api/operations/1/status \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## Troubleshooting

### Service Not Running
**Problem:** Cannot connect to Universal Migration Service

**Solution:**
1. Go to **Service Manager**
2. Check if "Universal Migration Service" status is **Running**
3. If **Stopped**, click **Start** button
4. Wait for status to change to **Running**

### Connection Failed
**Problem:** "Connection test failed" error

**Solutions:**
1. Verify SQL Server credentials are correct
2. Check if SQL Server is running and accessible
3. Verify network connectivity
4. Check if PostgreSQL database exists and credentials are correct
5. Ensure firewall allows connections

### Migration Failed
**Problem:** Operation status shows "Failed"

**Solutions:**
1. Go to operation details page
2. Check the error message
3. Common issues:
   - Invalid credentials → Verify and update credentials
   - Database doesn't exist → Create target PostgreSQL database
   - Permission denied → Check database user permissions
   - Table name conflicts → Drop conflicting tables or use different database

### Slow Migration
**Problem:** Migration takes too long

**Solutions:**
1. Check network connection speed
2. Large tables take time - monitor progress in operation details
3. Check source SQL Server performance
4. Check destination PostgreSQL performance

---

## Expected Migration Results

### Success Response
```json
{
  "status": "completed",
  "result_data": {
    "tables_migrated": 5,
    "total_rows": 10000,
    "duration_seconds": 120,
    "success": true
  },
  "started_at": "2024-12-26T10:00:00",
  "completed_at": "2024-12-26T10:02:00"
}
```

### Tables Created in PostgreSQL
- All tables from SQL Server database
- Same table names (or with configured prefix)
- Same column structure (with type mapping)
- All data migrated

---

## Best Practices

1. **Test with Small Database First:**
   - Test migration with a small database before migrating production data

2. **Backup Before Migration:**
   - Always backup your PostgreSQL database before running migration

3. **Use Full Migration for First Time:**
   - Use "Full Migration" for initial data transfer
   - Use "Incremental Migration" for subsequent updates

4. **Monitor During Migration:**
   - Keep the Operations page open to monitor progress
   - Check operation details for detailed status

5. **Verify Data After Migration:**
   - Check row counts match between source and destination
   - Verify data integrity by sampling records
   - Compare table structures

6. **Schedule During Off-Peak Hours:**
   - For large databases, schedule migrations during low-traffic periods

---

## Quick Reference

| Item | Value |
|------|-------|
| Source Type | `sqlserver` |
| Destination Type | `postgresql` |
| Main Backend Port | 5009 |
| Universal Service Port | 5010 |
| Operation Types | `full`, `incremental` |
| Status Values | `pending`, `running`, `completed`, `failed` |

---

## Summary

**Complete Flow:**
1. ✅ Start services (Service Manager UI or terminal)
2. ✅ Register Universal Migration Service (first time only)
3. ✅ Create operation via 6-step wizard
4. ✅ Execute migration (automatic or manual)
5. ✅ Monitor status and verify results

**Total Time:** Depends on data size
- Small databases (< 1GB): 1-5 minutes
- Medium databases (1-10GB): 5-30 minutes  
- Large databases (> 10GB): 30+ minutes

The system handles all technical details automatically - you just need to provide credentials and configuration!

