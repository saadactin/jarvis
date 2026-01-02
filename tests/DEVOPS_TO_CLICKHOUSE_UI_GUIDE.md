# DevOps to ClickHouse Migration - Frontend UI Guide

This guide shows you how to perform an Azure DevOps to ClickHouse migration from the frontend UI.

## Prerequisites

✅ **All prerequisites are met:**
- Universal Migration Service is running (port 5011)
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
   - Click on "🔧 Azure DevOps" option
   - Click "Next"

3. **Step 2: Select Destination Database**
   - Click on "📊 ClickHouse" option
   - Click "Next"

4. **Step 3: Source Configuration (Azure DevOps)**
   Fill in the Azure DevOps connection details:
   ```
   Access Token: [Your Azure DevOps Personal Access Token]
   Organization: TORAI
   API Version: 7.1
   ```
   - Click "Next"

5. **Step 4: Destination Configuration (ClickHouse)**
   Fill in the ClickHouse connection details:
   ```
   Host: 74.225.251.123
   Port: 8123
   Database: test7
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

**Option A: From Operations List**
- Find your operation in the list
- Click "Execute" button
- Confirm

**Option B: From Operation Details**
- Click on the operation to view details
- Click "Execute Now" button
- Confirm

### Step 4: Monitor Progress

1. **View Status:**
   - Operation status will update automatically
   - Status can be: `pending`, `running`, `completed`, or `failed`

2. **View Details:**
   - Click on the operation to see detailed information
   - View migration results including:
     - Tables migrated
     - Records processed
     - Any errors encountered

3. **Check Results:**
   - After completion, check the operation details page
   - View the migration summary with table counts and status

## What Gets Migrated

The DevOps to ClickHouse migration migrates **7 tables**:

1. **DEVOPS_PROJECTS** - All Azure DevOps projects
2. **DEVOPS_TEAMS** - All teams in the organization
3. **DEVOPS_WORKITEMS_MAIN** - Main work item data
4. **DEVOPS_WORKITEMS_UPDATES** - Work item update history
5. **DEVOPS_WORKITEMS_COMMENTS** - Work item comments
6. **DEVOPS_WORKITEMS_RELATIONS** - Work item relationships
7. **DEVOPS_WORKITEMS_REVISIONS** - Work item revision history

## Notes

- The migration may take a long time depending on the amount of data
- Large migrations can take several hours
- The operation will show progress and can be monitored in real-time
- If the migration fails, you can retry it - it will skip already migrated tables
- All tables are created with the `DEVOPS_` prefix in ClickHouse

## Troubleshooting

**If the operation fails:**
1. Check the operation details page for error messages
2. Verify your Azure DevOps credentials are correct
3. Verify your ClickHouse connection details are correct
4. Check that the Universal Migration Service is running (Service Manager page)
5. Check the logs in `jarvis-main/logs/jarvis_main_errors.log`

**If connection fails:**
- Verify network connectivity to ClickHouse server
- Check firewall rules
- Verify ClickHouse server is running and accessible

## Example Configuration

**Source (Azure DevOps):**
```json
{
  "access_token": "<DEVOPS_ACCESS_TOKEN from .env>",
  "organization": "<DEVOPS_ORGANIZATION from .env>",
  "api_version": "7.1"
}
```

**Destination (ClickHouse):**
```json
{
  "host": "<CLICKHOUSE_HOST from .env>",
  "port": 8123,
  "database": "<CLICKHOUSE_DATABASE from .env>",
  "username": "<CLICKHOUSE_USER from .env>",
  "password": "<CLICKHOUSE_PASSWORD from .env>"
}
```

