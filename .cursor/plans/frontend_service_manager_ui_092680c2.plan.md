---
name: Frontend Service Manager UI
overview: Create a Service Manager UI in the frontend with backend API endpoints to start/stop services using subprocess. The UI will show all available services with status indicators and allow one-click start/stop functionality.
todos: []
---

#Frontend Service Manager UI - Implementation Plan

## Overview

Create a web-based service manager that allows users to start/stop backend services from the frontend. The system will use Python subprocess to manage services and provide real-time status updates.

## Architecture

```javascript
Frontend (Service Manager Page)
    ↓ HTTP Requests
Backend API (/api/services/*)
    ↓ Subprocess Management
Python Services (jarvis-main, universal_migration_service, etc.)
```



## Services to Manage

1. **Main Backend** (jarvis-main) - Port 5009 - Special case (the backend itself)
2. **Universal Migration Service** - Port 5010 - Required
3. **Postgres Service** - Port 5001 - Optional (legacy)
4. **Zoho Service** - Port 5002 - Optional (legacy)
5. **SQL Postgres Service** - Port 5003 - Optional (legacy)

## Implementation Steps

### 1. Backend: Service Configuration

**File:** `jarvis-main/service_manager.py` (new file)Create a service configuration module that defines all available services:

```python
SERVICES = {
    'universal_migration': {
        'id': 'universal_migration',
        'name': 'Universal Migration Service',
        'port': 5010,
        'path': 'universal_migration_service/app.py',
        'health_url': 'http://localhost:5010/health',
        'required': True
    },
    'postgres': {
        'id': 'postgres',
        'name': 'Postgres Service',
        'port': 5001,
        'path': 'postgres_service/app.py',
        'health_url': 'http://localhost:5001/health',
        'required': False
    },
    # ... other services
}
```



### 2. Backend: Service Management Module

**File:** `jarvis-main/service_manager.py`Implement process management:

- Store running process IDs in memory/database
- Start service: Use `subprocess.Popen` to start Python services
- Stop service: Find process by port or PID and terminate
- Check status: Call health endpoint or check if process is running
- Track process state (running, stopped, error)

Key functions:

- `start_service(service_id)` - Start a service
- `stop_service(service_id)` - Stop a service  
- `get_service_status(service_id)` - Get current status
- `get_all_services_status()` - Get status of all services

### 3. Backend: API Endpoints

**File:** `jarvis-main/app.py`Add new routes:

```python
# Service Management Routes
@app.route('/api/services', methods=['GET'])
@jwt_required()
def get_all_services():
    """Get list of all services with their status"""
    # Return services list with status (running/stopped)
    
@app.route('/api/services/<service_id>/start', methods=['POST'])
@jwt_required()
def start_service(service_id):
    """Start a specific service"""
    # Start service using subprocess
    # Return success/error
    
@app.route('/api/services/<service_id>/stop', methods=['POST'])
@jwt_required()
def stop_service(service_id):
    """Stop a specific service"""
    # Stop service by finding and terminating process
    # Return success/error
    
@app.route('/api/services/<service_id>/status', methods=['GET'])
@jwt_required()
def get_service_status(service_id):
    """Get status of a specific service"""
    # Check if service is running
    # Return status, port, health check result
```



### 4. Frontend: Service Manager Page

**File:** `frontend/services.html` (new file)Create a new page with:

- Page title: "Service Manager"
- Cards for each service showing:
- Service name
- Status badge (Running/Stopped/Error)
- Port number
- Description
- Start/Stop buttons
- Last updated timestamp
- Auto-refresh every 5 seconds for status updates

### 5. Frontend: Service Manager JavaScript

**File:** `frontend/js/pages/services.js` (new file)Implement:

- `loadServices()` - Fetch all services and their status
- `startService(serviceId)` - Call API to start service
- `stopService(serviceId)` - Call API to stop service
- `renderServices(services)` - Render service cards with status
- Auto-polling for status updates (every 5 seconds)

### 6. Frontend: API Integration

**File:** `frontend/js/api.js`Add service management API methods:

```javascript
const servicesAPI = {
    getAll: async () => { ... },
    start: async (serviceId) => { ... },
    stop: async (serviceId) => { ... },
    getStatus: async (serviceId) => { ... }
};
```



### 7. Frontend: Navigation Update

**File:** `frontend/js/components/sidebar.js`Add "Service Manager" menu item to sidebar navigation.**File:** `frontend/dashboard.html`, `frontend/operations.html`, etc.Add link to services page in navigation.

### 8. Backend: Process Storage

**Option A:** In-memory storage (simpler, lost on restart)

- Use dictionary to store process objects
- Process IDs lost when backend restarts

**Option B:** File-based storage (persistent)

- Store PIDs in JSON file
- Can recover processes on restart

**Recommendation:** Start with Option A (in-memory), can upgrade to Option B later.

### 9. Error Handling

- Handle service already running errors
- Handle service not found errors
- Handle port already in use errors
- Show user-friendly error messages in frontend
- Log errors in backend

### 10. Special Case: Main Backend

The Main Backend (jarvis-main) cannot be started/stopped from itself. Options:

- Show status only (no start/stop buttons)
- Or disable start/stop with message "This is the current backend"

## Files to Create/Modify

### New Files:

1. `jarvis-main/service_manager.py` - Service configuration and management
2. `frontend/services.html` - Service Manager page
3. `frontend/js/pages/services.js` - Service Manager page logic

### Modified Files:

1. `jarvis-main/app.py` - Add service management API endpoints
2. `frontend/js/api.js` - Add servicesAPI methods
3. `frontend/js/components/sidebar.js` - Add Service Manager menu item
4. `frontend/js/config.js` - Add service endpoints configuration

## Technical Considerations

1. **Process Management:**

- Use `subprocess.Popen` with appropriate flags
- Handle Windows vs Linux process management differences
- Store process objects safely (avoid garbage collection)

2. **Status Checking:**

- Try health endpoint first (more reliable)
- Fallback to port checking if health endpoint fails
- Cache status to avoid too many requests

3. **Security:**

- All endpoints require JWT authentication
- Validate service_id before starting/stopping
- Prevent starting multiple instances of same service

4. **User Experience:**

- Show loading states when starting/stopping
- Disable buttons while operation in progress
- Show success/error toast notifications
- Auto-refresh status to show real-time updates

## Testing Checklist

- [ ] Can list all services
- [ ] Can start a service
- [ ] Can stop a service
- [ ] Status updates correctly
- [ ] Shows error if service fails to start
- [ ] Shows error if port is already in use
- [ ] Prevents starting service that's already running
- [ ] Auto-refresh works correctly
- [ ] Navigation works from sidebar