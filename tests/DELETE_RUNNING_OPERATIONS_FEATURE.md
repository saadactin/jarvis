# Delete Running Operations Feature

## Overview
Added the ability to delete running operations from the frontend. When a running operation is deleted, the migration is stopped and the operation record is removed, but any data already migrated to ClickHouse is preserved.

## Changes Made

### Backend (`jarvis-main/app.py`)

1. **Updated Delete Operation Endpoint**:
   - Now allows deletion of running operations
   - When deleting a running operation:
     - Marks it as "cancelled" first
     - Sets completion time
     - Adds a note that data is preserved
     - Then deletes the operation record

2. **Added "cancelled" Status Support**:
   - Updated status validation to include "cancelled"
   - Updated status checks to treat "cancelled" as completed

### Frontend

1. **Operations List Page** (`frontend/js/pages/operations.js`):
   - Delete button now shown for ALL operations (including running)
   - Special confirmation message for running operations
   - Warning about data preservation

2. **Operation Detail Page** (`frontend/js/pages/operationDetail.js`):
   - Delete button shown for running operations (labeled "Stop & Delete")
   - Special confirmation dialog for running operations
   - Stops polling when operation is deleted

3. **Status Badge Component** (`frontend/js/components/statusBadge.js`):
   - Added "cancelled" status icon (⏹️)

4. **Config** (`frontend/js/config.js`):
   - Added "cancelled" to STATUS_COLORS (#f57c00 - orange)
   - Added "cancelled" to STATUS_LABELS

5. **CSS** (`frontend/css/components.css`):
   - Added `.badge-cancelled` style (orange background)

## How It Works

### For Running Operations:

1. **User clicks Delete** on a running operation
2. **Confirmation dialog** appears with warning:
   ```
   ⚠️ WARNING: The migration will be stopped.
   ✅ Any tables and data already migrated to ClickHouse will be preserved.
   The operation record will be deleted from the system.
   ```
3. **Backend marks operation as "cancelled"**:
   - Sets status to "cancelled"
   - Sets completed_at timestamp
   - Adds error message explaining cancellation
4. **Operation record is deleted** from database
5. **Migration continues in background** (if still running), but:
   - Operation is no longer tracked
   - Any data already migrated is preserved in ClickHouse
   - No rollback occurs

### For Non-Running Operations:

- Works as before - simple deletion with standard confirmation

## Important Notes

⚠️ **Migration Continuation**: 
- When you delete a running operation, the HTTP request to the migration service may continue running in the background
- The operation record is deleted, so you won't see updates
- However, **all data already migrated is preserved** in ClickHouse

✅ **Data Preservation**:
- Tables already created in ClickHouse remain
- Records already inserted remain
- No rollback or cleanup occurs
- You can verify data by querying ClickHouse directly

## User Experience

### Operations List:
- **Delete button** visible for all operations
- **Special warning** for running operations
- **Success message** explains data preservation

### Operation Detail:
- **"Stop & Delete" button** for running operations
- **"Delete" button** for other operations
- **Auto-redirect** to operations list after deletion

## Testing

To test this feature:

1. Create a DevOps to ClickHouse operation
2. Execute it (it will start running)
3. Click **Delete** button while it's running
4. Confirm the deletion
5. Verify:
   - Operation disappears from the list
   - Any tables/data already in ClickHouse are still there
   - You can query ClickHouse to see partial data

## Example

**Before deletion:**
- Operation #21: Status = Running
- ClickHouse: 3 tables created, 50,000 records migrated

**After deletion:**
- Operation #21: Deleted from system
- ClickHouse: Still has 3 tables with 50,000 records (preserved)

