# Detailed Logging System

## Overview

The system now includes **comprehensive detailed logging** for all failures, making it easy to diagnose issues.

## Log Files

### Main Log File
- **Location**: `jarvis-main/logs/jarvis_main.log`
- **Content**: All INFO, WARNING, and ERROR level logs
- **Rotation**: 10MB max, keeps 5 backup files

### Error Log File
- **Location**: `jarvis-main/logs/jarvis_main_errors.log`
- **Content**: Only ERROR level logs with detailed failure information
- **Rotation**: 10MB max, keeps 10 backup files

## What Gets Logged

### 1. **Service Startup Failures**
When Universal Migration Service fails to start:
- Operation details (ID, user, type)
- Source and destination types
- Service URL and configuration
- Process return codes
- STDOUT and STDERR output
- Full stack traces
- Troubleshooting suggestions

### 2. **Connection Errors**
When connection to service fails:
- Operation details
- Service URL
- Error type and message
- Retry attempts and delays
- Full stack traces
- Network error details

### 3. **Migration Failures**
When migration fails:
- Operation details
- Source and destination configuration
- Total tables processed
- Tables migrated vs failed
- Detailed error for each failed table
- Full migration response
- Stack traces

### 4. **Process Crashes**
When service process crashes:
- Process PID and return code
- Wait time before crash
- STDOUT and STDERR output
- Process status information

### 5. **Timeout Errors**
When service doesn't become ready:
- Total wait time
- Health check URL
- Process status
- Possible causes and suggestions

## Log Format

Each failure entry includes:
```
================================================================================
OPERATION FAILURE: Operation #X - [Failure Type]
Timestamp: [ISO timestamp]
Operation ID: [ID]
User ID: [User ID]
Operation Type: [full/incremental]
Source Type: [source type]
Destination Type: [destination type]
[Additional context-specific fields]
Error Type: [Error class name]
Error Message: [Error message]
Stack Trace:
[Full stack trace]
[Additional troubleshooting information]
================================================================================
```

## How to Use Logs

### 1. **Check Error Log File**
```powershell
# View recent errors
Get-Content jarvis-main\logs\jarvis_main_errors.log -Tail 100

# Search for specific operation
Select-String -Path jarvis-main\logs\jarvis_main_errors.log -Pattern "Operation #12"
```

### 2. **Check Main Log File**
```powershell
# View all logs
Get-Content jarvis-main\logs\jarvis_main.log -Tail 100
```

### 3. **Real-time Monitoring**
```powershell
# Watch logs in real-time
Get-Content jarvis-main\logs\jarvis_main_errors.log -Wait -Tail 50
```

## Log Locations in Code

### Main Backend (`jarvis-main/app.py`)
- Service startup failures: Lines ~1157-1200
- Connection errors: Lines ~1330-1345
- Migration failures: Lines ~1350-1380
- Process crashes: Lines ~1224-1263
- Timeout errors: Lines ~1327-1359

### Universal Migration Service
- Pipeline errors: `pipeline_engine.py`
- Table migration errors: `pipeline_engine.py`
- Endpoint errors: `app.py`

## Example Log Entry

```
================================================================================
OPERATION FAILURE: Operation #12 - Service Did Not Become Ready
Timestamp: 2025-12-29T11:36:00.123456
Operation ID: 12
User ID: 1
Operation Type: full
Source Type: zoho
Destination Type: clickhouse
Total Wait Time: 60s
Service URL: http://localhost:5010
Health Check URL: http://localhost:5010/health
Process Status: No process found in manager
Error Type: Service Timeout - Health Check Failed
Possible Causes:
  1. Service is starting very slowly
  2. Service crashed after process was removed from manager
  3. Port conflict or network issue
  4. Service dependencies not installed
================================================================================
```

## Benefits

✅ **Complete Context**: Every failure includes full operation details  
✅ **Stack Traces**: Full Python stack traces for debugging  
✅ **Troubleshooting Hints**: Suggestions for common issues  
✅ **Process Information**: PID, return codes, STDOUT/STDERR  
✅ **Separate Error Log**: Easy to find failures without filtering  
✅ **File Rotation**: Logs don't grow indefinitely  

## Next Steps After Failure

1. **Check Error Log**: `jarvis-main/logs/jarvis_main_errors.log`
2. **Search for Operation ID**: Find your specific operation
3. **Review Stack Trace**: See exactly where it failed
4. **Check Suggestions**: Follow troubleshooting steps in log
5. **Review Process Output**: Check STDOUT/STDERR for service errors

