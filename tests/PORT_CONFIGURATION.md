# Port Configuration Guide

## Universal Migration Service Port Configuration

The Universal Migration Service port is now **configurable** via environment variables instead of being hardcoded.

### Environment Variables

Add these to your `.env` file:

```env
# Universal Migration Service Configuration
UNIVERSAL_MIGRATION_SERVICE_PORT=5010
UNIVERSAL_MIGRATION_SERVICE_HOST=localhost
```

### Default Values

- **Port**: `5010` (if not specified)
- **Host**: `localhost` (if not specified)

### How to Change the Port

1. **Edit your `.env` file** in the root `Backend` directory:
   ```env
   UNIVERSAL_MIGRATION_SERVICE_PORT=5011  # Change to your desired port
   ```

2. **Restart the services**:
   - Stop the Universal Migration Service if running
   - Restart the main backend (`jarvis-main/app.py`)
   - The service will auto-start on the new port

3. **Update Database Master** (if needed):
   - The service URL is automatically registered/updated
   - If you manually registered it, update the URL in Database Masters page

### Files Updated

The following files now use the configurable port:

- ✅ `jarvis-main/config.py` - Loads port from environment
- ✅ `jarvis-main/service_manager.py` - Uses configurable port for service management
- ✅ `jarvis-main/app.py` - Uses configurable port for auto-registration
- ✅ `universal_migration_service/app.py` - Reads port from environment when starting

### Verification

After changing the port, verify it's working:

```powershell
# Check if service is running on new port
curl http://localhost:5011/health  # Replace 5011 with your port
```

Or check the Service Manager page in the UI - it should show the correct port.

