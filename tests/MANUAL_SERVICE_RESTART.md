# Manual Service Restart Instructions

## Problem
The Universal Migration Service needs to be restarted to pick up the code fixes. The service is currently running old code that has syntax errors.

## Solution: Manual Restart

### Step 1: Stop the Old Service

**Option A: Via Task Manager**
1. Open Task Manager (Ctrl+Shift+Esc)
2. Find Python processes running `app.py` from `universal_migration_service`
3. End those processes

**Option B: Via Command Line**
```powershell
# Find process using port 5011
netstat -ano | findstr :5011

# Kill the process (replace PID with actual process ID)
taskkill /F /PID <PID>
```

### Step 2: Start the Service Fresh

1. **Open a NEW terminal/command prompt**
2. **Navigate to the service directory:**
   ```powershell
   cd C:\Users\SaadSayyed\Desktop\jarvis_best\Backend\universal_migration_service
   ```

3. **Start the service:**
   ```powershell
   python app.py
   ```

4. **Verify it's running:**
   - You should see: `Starting Universal Migration Service...`
   - You should see: `Service will run on 0.0.0.0:5011`
   - The service should be listening

### Step 3: Verify Service is Working

Open another terminal and run:
```powershell
python check_migration_status.py
```

You should see:
```
[OK] Service is running
Available sources: ['postgresql', 'mysql', 'zoho', 'sqlserver', 'devops']
Available destinations: ['clickhouse', 'postgresql', 'mysql']
```

### Step 4: Retry Your Migration

1. Go back to the frontend
2. Find Operation #21 (or create a new one)
3. Click **Execute** or **Retry**
4. The migration should now work properly

## What Was Fixed

1. ✅ **Syntax Error**: Fixed indentation error in `pipeline_engine.py`
2. ✅ **Batch Size**: Now uses `batch_size=50` for DevOps (matching test script)
3. ✅ **Better Logging**: Batch-by-batch progress logging for DevOps
4. ✅ **Error Handling**: Improved exception handling during data iteration

## Expected Behavior After Restart

When you run the migration, you should see:
- ✅ Tables being created in ClickHouse
- ✅ Batch-by-batch progress in logs
- ✅ Hundreds of thousands of records being migrated
- ✅ Migration taking hours (not minutes)

## Troubleshooting

**If service won't start:**
- Check for Python errors in the terminal
- Verify all dependencies are installed: `pip install -r requirements.txt`
- Check if port 5011 is already in use

**If migration still shows only 98 records:**
- Verify service is using new code (check logs for batch_size=50 messages)
- Check operation details for error messages
- Verify ClickHouse connection is working

## Quick Test

After restarting, you can test with:
```powershell
python tests\test_devops_to_clickhouse_frontend.py
```

This will create and execute a migration operation via the API (same as frontend).

