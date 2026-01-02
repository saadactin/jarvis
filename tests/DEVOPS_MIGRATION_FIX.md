# DevOps to ClickHouse Migration Fix

## Problem
When running DevOps to ClickHouse migration from the UI, only 98 records were migrated across all 7 tables, while the test script successfully migrates hundreds of thousands of records.

## Root Cause
1. **Batch Size Mismatch**: The pipeline engine was using the default `batch_size=1000` for DevOps, but the test script uses `batch_size=50`. Azure DevOps API has limits and a batch size of 1000 can cause timeouts or API rejections.

2. **Insufficient Error Handling**: Errors during data iteration might have been silently caught, causing the migration to stop early.

3. **Limited Logging**: Not enough progress logging for DevOps migrations, making it hard to diagnose issues.

## Solution
Updated `universal_migration_service/pipeline_engine.py` to:

1. **Use Appropriate Batch Sizes**:
   - DevOps: `batch_size=50` (matches test script)
   - Zoho: `batch_size=200` (existing default)
   - Other sources: `batch_size=1000` (default)

2. **Improved Error Handling**:
   - Better exception handling around data iteration
   - Empty batch detection and logging
   - Warning when very few records are processed for DevOps

3. **Enhanced Logging**:
   - Log every batch for DevOps migrations (not just every 10 batches)
   - Better error messages with stack traces
   - Warning messages when record counts seem low

## Changes Made

### File: `universal_migration_service/pipeline_engine.py`

1. Added batch size selection based on source type:
```python
# Use appropriate batch size based on source type
if source_type == 'devops':
    batch_size = 50  # Match test script batch size for DevOps
elif source_type == 'zoho':
    batch_size = 200  # Zoho default
else:
    batch_size = 1000  # Default for database sources
```

2. Pass batch_size to read_data and read_incremental:
```python
data_iterator = source.read_data(table_name, batch_size=batch_size)
```

3. Added better error handling and logging:
```python
# Log progress more frequently for DevOps (every batch)
if source_type == 'devops':
    logger.info(f"{table_name}: Batch {batch_count}: {len(batch)} records, Total: {records_processed:,} records")
```

4. Added warning for low record counts:
```python
if records_processed > 0 and records_processed < 100 and source_type == 'devops':
    logger.warning(f"{table_name}: Only {records_processed} records processed. This might indicate an early termination issue.")
```

## Testing
After these changes, DevOps migrations should:
- Process all work items (not just a few)
- Use the same batch size as the test script (50)
- Provide better logging to diagnose issues
- Handle errors more gracefully

## Next Steps
1. Restart the Universal Migration Service
2. Create a new DevOps to ClickHouse operation from the UI
3. Monitor the logs to see batch-by-batch progress
4. Verify that all records are being migrated

## Expected Behavior
- Migration should take much longer (hours, not minutes)
- Logs should show batch-by-batch progress for DevOps
- Record counts should match what the test script produces
- All 7 tables should have substantial data (not just 98 records total)

