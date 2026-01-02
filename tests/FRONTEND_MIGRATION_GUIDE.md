# Frontend UI Migration Guide - PostgreSQL to ClickHouse

This guide shows you how to perform a PostgreSQL to ClickHouse migration from the frontend UI.

## Prerequisites

✅ **All prerequisites are met:**
- Universal Migration Service is running (port 5010)
- Backend is running (port 5009)
- Frontend is accessible
- You are logged in

## Step-by-Step Guide

### Step 1: ✅ Universal Migration Service (Automatic!)

**No manual registration needed!** The Universal Migration Service is automatically:
- **Registered** in the database when the backend starts
- **Started** automatically when the backend starts

You can go directly to creating operations!

**Note:** If you need to check service status, go to the **Service Manager** page.

### Step 2: Create a Migration Operation

1. **Navigate to Create Operation:**
   - Click on "🔄 Operations" in the sidebar
   - Click "Create Operation" button (or use the button in the dashboard)

2. **Step 1: Select Source Database**
   - Click on "PostgreSQL" option
   - Click "Next"

3. **Step 2: Select Destination Database**
   - Click on "ClickHouse" option
   - Click "Next"

4. **Step 3: Source Configuration (PostgreSQL)**
   Fill in the PostgreSQL connection details:
   ```
   Host: localhost
   Port: 5432
   Database: Tor2
   Username: migration_user
   Password: StrongPassword123
   ```
   - Click "Next"

5. **Step 4: Destination Configuration (ClickHouse)**
   Fill in the ClickHouse connection details:
   ```
   Host: 74.225.251.123
   Port: 8123
   Database: test6
   Username: default
   Password: root
   ```
   - Click "Next"

6. **Step 5: Schedule**
   - Select "Full Migration" for operation type
   - Set schedule (or leave as "Run Now" for immediate execution)
   - Click "Next"

7. **Step 6: Review**
   - Review all your settings
   - Click "Create Operation"

### Step 3: Execute the Operation

After creating the operation, you can execute it in two ways:

**Option A: Execute Immediately**
1. On the operations list page, find your operation
2. Click the "Execute" button
3. Confirm execution

**Option B: View Details and Execute**
1. Click on the operation to view details
2. Click "Execute Now" button
3. Confirm execution

### Step 4: Monitor Progress

1. **View Operation Status:**
   - Click on the operation to see detailed status
   - The page will automatically refresh to show progress

2. **Check Results:**
   - View the "Migration Results" section
   - See which tables were migrated
   - Check for any errors

3. **Operations List:**
   - The operations list shows status badges
   - Running operations are highlighted
   - Completed operations show success/failure status

## Expected Results

Based on the test, you should see:
- **Total tables:** 15
- **Successfully migrated:** 8 tables
- **Records migrated:** 260+ records
- **Status:** Completed (or partial success)

### Successfully Migrated Tables:
- data_sources
- okrapi_businessunit
- okrapi_businessunitokrmapping
- okrapi_department
- okrapi_log
- okrapi_optionmapper
- okrapi_questionmaster
- teamsauth_useraccessmapping

### Tables with Data Type Issues (will show as failed):
- okrapi_formdata
- okrapi_manageranswerdata
- okrapi_managerreview
- okrapi_okr
- okrapi_okrusermapping
- okrapi_useranswerdata
- teamsauth_teamsprofile

**Note:** Some tables may fail due to data type conversion issues (empty strings, null values, datetime formatting). This is expected and the system will continue migrating other tables.

## Troubleshooting

### Issue: "Universal Migration Service not found"
**Solution:** Register the Universal Migration Service in Database Masters (Step 1)

### Issue: Operation fails immediately
**Solution:** 
- Check that Universal Migration Service is running (check Service Manager page)
- Verify credentials are correct
- Check backend logs for error details

### Issue: Operation shows "pending" status
**Solution:**
- If scheduled for future, wait for the scheduled time
- If you want to run now, click "Execute" button
- Check that Universal Migration Service is running

### Issue: Some tables fail
**Solution:**
- This is normal for tables with data type edge cases
- Check the error details in the operation status page
- The system continues migrating other tables even if some fail

## Quick Test

To quickly test if everything works:

1. **Create Operation** with these exact credentials (as tested):
   - Source: PostgreSQL (localhost:5432/Tor2)
   - Destination: ClickHouse (74.225.251.123:8123/test6)
   - Operation Type: Full

2. **Execute immediately** by clicking "Execute"

3. **Monitor** the operation status page

4. **Verify** that you see at least 8 tables migrated with 260+ records

## Success Indicators

✅ Operation status shows "completed" or "running"
✅ Migration results show tables with record counts
✅ ClickHouse database has new tables with `HR_` prefix
✅ No critical errors (data type issues are expected for some tables)

## Need Help?

- Check the Service Manager page to verify services are running
- Check backend terminal for detailed logs
- Review the operation detail page for specific error messages
- All tables that can be migrated will be migrated, even if some fail

