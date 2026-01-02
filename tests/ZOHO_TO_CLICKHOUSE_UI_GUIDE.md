# Zoho to ClickHouse Migration - UI Guide

## ✅ System Ready for Zoho to ClickHouse Migration

The system has been updated and tested to ensure accurate Zoho to ClickHouse migrations from the UI.

## Step-by-Step Guide

### 1. Login/Register
- Open the frontend UI (e.g., `http://localhost:8080`)
- Login with your credentials or register a new account

### 2. Create Zoho to ClickHouse Operation

1. **Go to Operations Page**
   - Click "🔄 Operations" in the sidebar
   - Click "+ Create Operation" button

2. **Step 1: Select Source**
   - Click on "☁️ Zoho CRM" card
   - Click "Next"

3. **Step 2: Select Destination**
   - Click on "📊 ClickHouse" card
   - Click "Next"

4. **Step 3: Source Configuration (Zoho)**
   Fill in your Zoho credentials:
   ```
   Refresh Token: 1000.2cbaa36345c6d04b699b0cb6740c21ef.149922195c479d83c84826653ff84ff4
   Client ID: 1000.0L3LLVLEKE9ELW7CE0I0KJ3K4FKBBT
   Client Secret: d99c479d4c0db451c653d8c380bf6a4c557a73528c
   API Domain: Select "India (https://www.zohoapis.in)"
   ```
   - Click "Next"

5. **Step 4: Destination Configuration (ClickHouse)**
   Fill in your ClickHouse credentials:
   ```
   Host: 74.225.251.123
   Port: 9000 (will automatically try 8123 first for HTTP API)
   Database: test6
   Username: default
   Password: root
   ```
   - Click "Next"

6. **Step 5: Schedule**
   - Operation Type: Select "Full Migration"
   - Schedule: Select a date/time (or set to current time for immediate execution)
   - Click "Next"

7. **Step 6: Review**
   - Review all your settings
   - Click "Create Operation"

### 3. Execute the Operation

**Option A: Execute Immediately**
- After creating the operation, you'll be redirected to the operation details page
- Click "Execute Now" button
- Confirm the execution

**Option B: Execute from Operations List**
- Go to Operations page
- Find your operation
- Click "Execute" button

### 4. Monitor Progress

The operation will:
- Show status as "Running" while migration is in progress
- Auto-refresh every 5 seconds to show progress
- Display detailed migration results when completed

**What to Expect:**
- Migration may take 10-60 minutes depending on data volume
- Status will update automatically
- You can see which tables are being migrated
- Progress is shown in real-time

### 5. Verify Results

Once migration completes:
- **Status**: Will show "COMPLETED" if all tables succeeded
- **Migration Results**: Shows:
  - Total tables processed
  - Tables successfully migrated (with record counts)
  - Tables failed (if any, with error messages)
  - Total records migrated

**In ClickHouse:**
- Tables are created with `zoho_` prefix (e.g., `zoho_accounts`, `zoho_contacts`)
- All data is stored in the `test6` database
- You can query the data using ClickHouse SQL

## System Improvements Made

### ✅ Backend Improvements
1. **Increased Timeout**: 60 minutes (3600 seconds) for long-running migrations
2. **Retry Logic**: Automatic retries for failed tables (up to 2 retries)
3. **Better Error Handling**: Detailed error messages for troubleshooting
4. **Token Refresh**: Automatic Zoho token refresh if expired

### ✅ Zoho Source Adapter
1. **Retry Logic**: Up to 3 retries for failed API requests
2. **Token Management**: Automatic token refresh on expiration
3. **Timeout Handling**: 120-second timeout with retries
4. **Better Error Messages**: Clear error reporting

### ✅ ClickHouse Destination Adapter
1. **Port Handling**: Automatically tries HTTP API port 8123 if port 9000 is specified
2. **Dynamic Columns**: Automatically adds missing columns for Zoho tables
3. **Duplicate Prevention**: Checks existing IDs before insertion
4. **Batch Insertion**: Inserts data in batches to avoid memory issues

### ✅ Frontend Improvements
1. **Default Port**: ClickHouse port defaults to 9000 (with helpful note)
2. **Long Timeout**: Frontend timeout increased to 60 minutes
3. **Real-time Updates**: Auto-refreshes every 5 seconds during migration
4. **Better Status Display**: Shows detailed migration results

## Troubleshooting

### Issue: Operation shows "FAILED" but some data was migrated
- **Solution**: Check the operation details page
- Look at "Migration Results" section
- You'll see which tables succeeded and which failed
- Data from successful tables IS in ClickHouse

### Issue: Operation times out
- **Solution**: The timeout is now 60 minutes
- For very large migrations, you may need to:
  - Check backend logs for progress
  - Verify tables are being created in ClickHouse
  - The migration continues even if the request times out

### Issue: Some tables fail
- **Solution**: The system retries failed tables automatically
- Check error messages in operation details
- Common issues:
  - Network connectivity
  - Zoho API rate limits
  - ClickHouse connection issues

### Issue: Can't connect to ClickHouse
- **Solution**: 
  - Verify ClickHouse is running
  - Check host and port (9000 will try 8123 automatically)
  - Verify credentials are correct
  - Check firewall settings

## Success Criteria

✅ **Operation Status**: "COMPLETED" (all tables succeeded)
✅ **Tables Migrated**: All Zoho modules migrated
✅ **Records Migrated**: Total count shown in results
✅ **ClickHouse Tables**: All tables visible with `zoho_` prefix
✅ **Data Verified**: Can query data in ClickHouse

## Notes

- **Table Prefix**: All Zoho tables use `zoho_` prefix in ClickHouse
- **Column Names**: Zoho field names are sanitized for ClickHouse compatibility
- **Data Types**: All Zoho fields are stored as `Nullable(String)` in ClickHouse
- **Duplicate Prevention**: Existing records are skipped (based on ID)
- **Load Time**: Each record has a `load_time` column with insertion timestamp

## Support

If you encounter issues:
1. Check the operation details page for error messages
2. Check backend logs for detailed error information
3. Verify credentials are correct
4. Ensure Universal Migration Service is running (check Service Manager page)

