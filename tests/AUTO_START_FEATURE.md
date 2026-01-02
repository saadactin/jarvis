# Universal Migration Service Auto-Start Feature

## Overview

The system now **automatically starts the Universal Migration Service** if it's not running when you try to execute a migration from the frontend. This eliminates the need to manually start the service before running migrations.

## How It Works

### 1. **Automatic Detection**
When you click "Execute" or "Retry" on a migration operation:
- The system checks if the Universal Migration Service is running
- If not running, it automatically attempts to start it

### 2. **Auto-Start Process**
1. **Check Service Status**: Verifies if service is running via health check
2. **Start Service**: Automatically calls `start_service('universal_migration')`
3. **Wait for Ready**: Waits up to 30 seconds for the service to become ready
4. **Proceed with Migration**: Once ready, proceeds with the migration

### 3. **Error Handling**
If the service fails to start:
- Operation status is set to "failed"
- Clear error message is provided
- Suggests checking Service Manager page or starting manually

## Where Auto-Start is Implemented

### 1. **Manual Execution** (`/api/operations/<id>/execute`)
- When you click "Execute Now" or "Retry Migration" from the UI
- Auto-starts service if not running before calling the migration API

### 2. **Scheduled Execution** (Background Scheduler)
- When scheduled operations are executed automatically
- Auto-starts service if not running before processing each operation

## Benefits

✅ **No Manual Service Management**: You don't need to manually start the service  
✅ **Seamless User Experience**: Migrations work directly from the frontend  
✅ **Automatic Recovery**: If service crashes, it auto-restarts on next migration  
✅ **Smart Waiting**: Waits for service to be ready before proceeding  

## Configuration

The service port is configurable via environment variables:

```env
UNIVERSAL_MIGRATION_SERVICE_PORT=5010
UNIVERSAL_MIGRATION_SERVICE_HOST=localhost
```

## Testing

Run the test script to verify auto-start functionality:

```powershell
python test_service_auto_start.py
```

## Troubleshooting

### Service Fails to Start
If auto-start fails:
1. Check the main backend logs for error messages
2. Verify the service file exists: `universal_migration_service/app.py`
3. Check if port 5010 (or configured port) is already in use
4. Ensure all dependencies are installed: `pip install -r requirements.txt`

### Service Takes Too Long to Start
- Default wait time is 30 seconds
- If service needs more time, check for errors in service startup logs
- Verify Python environment and dependencies

## Manual Override

You can still manually start/stop services via:
- **Service Manager page** in the UI
- **API endpoints**: `/api/services/<service_id>/start` and `/api/services/<service_id>/stop`

