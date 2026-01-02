# Frontend DevOps to ClickHouse Migration Test - Instructions

## ✅ Fixes Applied

1. **Fixed Indentation Error**: Corrected syntax error in `pipeline_engine.py` that was preventing the service from starting
2. **Added DevOps Batch Size**: Pipeline now uses `batch_size=50` for DevOps (matching test script)
3. **Enhanced Logging**: Better progress logging for DevOps migrations
4. **Improved Error Handling**: Better exception handling during data iteration

## 🔄 Required: Restart Universal Migration Service

The Universal Migration Service needs to be restarted to pick up the code changes:

### Option 1: Via Service Manager (Frontend)
1. Go to **Service Manager** page in the frontend
2. Find **Universal Migration Service**
3. Click **Stop** (if running)
4. Wait a few seconds
5. Click **Start**

### Option 2: Manual Restart
1. Stop the Universal Migration Service process (if running)
2. Start it again:
   ```bash
   cd universal_migration_service
   python app.py
   ```

## 🧪 Testing from Frontend

### Step 1: Create Operation
1. Login to frontend
2. Go to **Operations** → **Create Operation**
3. Select:
   - **Source**: Azure DevOps 🔧
   - **Destination**: ClickHouse 📊
4. Enter credentials (from your .env file):
   - **DevOps**: 
     - Access Token: (from `DEVOPS_ACCESS_TOKEN` in .env)
     - Organization: (from `DEVOPS_ORGANIZATION` in .env)
     - API Version: `7.1` (or from `DEVOPS_API_VERSION` in .env)
   - **ClickHouse**:
     - Host: (from `CLICKHOUSE_HOST` in .env)
     - Port: (from `CLICKHOUSE_PORT` in .env, default: 8123)
     - Database: (from `CLICKHOUSE_DATABASE` in .env)
     - Username: (from `CLICKHOUSE_USER` in .env, default: default)
     - Password: (from `CLICKHOUSE_PASSWORD` in .env)
5. Set schedule to **"Run Now"** or immediate time
6. Click **Create Operation**

### Step 2: Execute Operation
1. Find your operation in the list
2. Click **Execute** button
3. Confirm execution

### Step 3: Monitor Progress
1. Click on the operation to view details
2. Watch the status update
3. Check the logs for batch-by-batch progress:
   ```
   DEVOPS_WORKITEMS_MAIN: Batch 1: 50 records, Total: 50 records
   DEVOPS_WORKITEMS_MAIN: Batch 2: 50 records, Total: 100 records
   ...
   ```

## 📊 Expected Results

After restarting the service and running the migration:

- ✅ **Migration should take hours** (not 2-3 minutes)
- ✅ **All 7 tables should have substantial data** (not just 98 records)
- ✅ **Logs should show continuous batch processing**
- ✅ **Record counts should match test script** (hundreds of thousands of records)

## 🔍 Verification

After migration completes, verify data in ClickHouse:

```sql
SELECT count() FROM DEVOPS_PROJECTS;
SELECT count() FROM DEVOPS_TEAMS;
SELECT count() FROM DEVOPS_WORKITEMS_MAIN;
SELECT count() FROM DEVOPS_WORKITEMS_UPDATES;
SELECT count() FROM DEVOPS_WORKITEMS_COMMENTS;
SELECT count() FROM DEVOPS_WORKITEMS_RELATIONS;
SELECT count() FROM DEVOPS_WORKITEMS_REVISIONS;
```

## 🐛 Troubleshooting

**If migration still shows only 98 records:**
1. Verify Universal Migration Service is restarted with new code
2. Check service logs for batch processing messages
3. Verify batch_size=50 is being used (check logs)
4. Check for any errors in the operation details page

**If service won't start:**
1. Check for syntax errors: `python -m py_compile universal_migration_service/pipeline_engine.py`
2. Check service logs for errors
3. Verify all dependencies are installed

## 📝 Test Script

A test script is available at `tests/test_devops_to_clickhouse_frontend.py` that:
- Simulates the exact frontend flow
- Creates operation via API
- Executes and monitors it
- Verifies results

Run it with:
```bash
python tests/test_devops_to_clickhouse_frontend.py
```

