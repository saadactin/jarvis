"""
Test script for Azure DevOps to ClickHouse migration
Tests all 7 tables: PROJECTS, TEAMS, MAIN, UPDATES, COMMENTS, RELATIONS, REVISIONS
"""
import sys
import os
import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()

# Add universal_migration_service to path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ums_dir = os.path.join(backend_dir, 'universal_migration_service')
sys.path.insert(0, ums_dir)

from adapters.sources.devops_source import DevOpsSourceAdapter
from adapters.destinations.clickhouse_dest import ClickHouseDestinationAdapter

# Configuration from environment variables
ACCESS_TOKEN = os.getenv('DEVOPS_ACCESS_TOKEN', '')
ORGANIZATION = os.getenv('DEVOPS_ORGANIZATION', '')
API_VERSION = os.getenv('DEVOPS_API_VERSION', '7.1')

CLICKHOUSE_HOST = os.getenv('CLICKHOUSE_HOST', 'localhost')
CLICKHOUSE_PORT = int(os.getenv('CLICKHOUSE_PORT', '8123'))
CLICKHOUSE_USER = os.getenv('CLICKHOUSE_USER', 'default')
CLICKHOUSE_PASSWORD = os.getenv('CLICKHOUSE_PASSWORD', '')
CLICKHOUSE_DATABASE = os.getenv('CLICKHOUSE_DATABASE', 'default')

# Validate required environment variables
if not ACCESS_TOKEN:
    raise ValueError("DEVOPS_ACCESS_TOKEN environment variable is required")
if not ORGANIZATION:
    raise ValueError("DEVOPS_ORGANIZATION environment variable is required")
if not CLICKHOUSE_PASSWORD:
    raise ValueError("CLICKHOUSE_PASSWORD environment variable is required")

# Table names
TABLES = [
    "DEVOPS_PROJECTS",
    "DEVOPS_TEAMS",
    "DEVOPS_WORKITEMS_MAIN",
    "DEVOPS_WORKITEMS_UPDATES",
    "DEVOPS_WORKITEMS_COMMENTS",
    "DEVOPS_WORKITEMS_RELATIONS",
    "DEVOPS_WORKITEMS_REVISIONS"
]

def log(message):
    """Log with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    # Replace Unicode characters with ASCII equivalents for Windows console
    message = message.replace('✅', '[OK]').replace('❌', '[ERROR]').replace('⚠️', '[WARN]').replace('📊', '[INFO]').replace('📥', '[READ]').replace('📦', '[BATCH]').replace('🎉', '[SUCCESS]').replace('⏱️', '[TIME]').replace('→', '->')
    print(f"[{timestamp}] {message}", flush=True)

def test_connection(source, dest):
    """Test connections"""
    log("=" * 70)
    log("Testing Connections")
    log("=" * 70)
    
    # Test source connection
    log("Testing Azure DevOps connection...")
    source_config = {
        "access_token": ACCESS_TOKEN,
        "organization": ORGANIZATION,
        "api_version": API_VERSION
    }
    if source.connect(source_config):
        log("✅ Azure DevOps connection successful")
    else:
        log("❌ Azure DevOps connection failed")
        return False
    
    # Test destination connection
    log("Testing ClickHouse connection...")
    dest_config = {
        "host": CLICKHOUSE_HOST,
        "port": CLICKHOUSE_PORT,
        "username": CLICKHOUSE_USER,
        "password": CLICKHOUSE_PASSWORD,
        "database": CLICKHOUSE_DATABASE
    }
    if dest.connect(dest_config):
        log("✅ ClickHouse connection successful")
    else:
        log("❌ ClickHouse connection failed")
        return False
    
    return True

def check_table_counts(dest, table_name):
    """Check row count in a table"""
    try:
        ch_table_name = dest._get_table_name(table_name, "devops")
        result = dest.client.query(f"SELECT count() FROM {ch_table_name}")
        count = result.result_rows[0][0]
        return count
    except Exception as e:
        # Table might not exist yet, that's OK
        return 0

def migrate_table(source, dest, table_name, batch_size=50):
    """Migrate a single table"""
    log(f"\n{'='*70}")
    log(f"Migrating Table: {table_name}")
    log(f"{'='*70}")
    
    start_time = time.time()
    
    # Get schema
    try:
        schema = source.get_schema(table_name)
        log(f"✅ Got schema for {table_name}: {len(schema)} columns")
    except Exception as e:
        log(f"❌ Error getting schema for {table_name}: {e}")
        return False
    
    # Create table
    try:
        dest.create_table(table_name, schema, source_type="devops")
        log(f"✅ Created/verified table for {table_name}")
    except Exception as e:
        log(f"❌ Error creating table for {table_name}: {e}")
        import traceback
        log(traceback.format_exc())
        return False
    
    # Check initial count
    initial_count = check_table_counts(dest, table_name)
    log(f"   📊 Initial row count: {initial_count:,}")
    
    # Read and write data
    try:
        records_processed = 0
        batch_count = 0
        
        log(f"   📥 Reading data from Azure DevOps...")
        data_iterator = source.read_data(table_name, batch_size=batch_size)
        
        for batch in data_iterator:
            batch_count += 1
            if batch:
                log(f"   📦 Batch {batch_count}: {len(batch)} records")
                try:
                    dest.write_data(table_name, batch, batch_size=batch_size, source_type="devops")
                    records_processed += len(batch)
                    log(f"   ✅ Batch {batch_count} written: {records_processed:,} total records")
                except Exception as e:
                    log(f"   ❌ Error writing batch {batch_count}: {e}")
                    import traceback
                    log(traceback.format_exc())
                    return False
            else:
                log(f"   ⚠️  Batch {batch_count} is empty")
        
        elapsed = time.time() - start_time
        
        # Check final count
        final_count = check_table_counts(dest, table_name)
        new_records = final_count - initial_count
        
        log(f"\n   📊 Results for {table_name}:")
        log(f"      - Records processed: {records_processed:,}")
        log(f"      - Initial count: {initial_count:,}")
        log(f"      - Final count: {final_count:,}")
        log(f"      - New records: {new_records:,}")
        log(f"      - Time elapsed: {elapsed:.2f}s")
        
        if records_processed > 0 and new_records == 0:
            log(f"   ⚠️  WARNING: Processed {records_processed} records but no new rows in table!")
            return False
        elif records_processed > 0:
            log(f"   ✅ Successfully migrated {records_processed:,} records")
            return True
        else:
            log(f"   ⚠️  No records to migrate")
            return True
            
    except Exception as e:
        log(f"   ❌ Error during migration: {e}")
        import traceback
        log(traceback.format_exc())
        return False

def main():
    """Main test function"""
    log("=" * 70)
    log("Azure DevOps to ClickHouse Migration Test")
    log("=" * 70)
    log(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("")
    
    # Initialize adapters
    source = DevOpsSourceAdapter()
    dest = ClickHouseDestinationAdapter()
    
    # Test connections
    if not test_connection(source, dest):
        log("❌ Connection test failed. Exiting.")
        return False
    
    # Check initial table counts
    log("\n" + "=" * 70)
    log("Initial Table Counts")
    log("=" * 70)
    initial_counts = {}
    for table_name in TABLES:
        count = check_table_counts(dest, table_name)
        initial_counts[table_name] = count
        log(f"   {table_name}: {count:,} rows")
    
    # Migrate each table
    results = {}
    total_start = time.time()
    
    for table_name in TABLES:
        success = migrate_table(source, dest, table_name, batch_size=50)
        results[table_name] = success
        if not success:
            log(f"   ❌ Migration failed for {table_name}")
        time.sleep(1)  # Small delay between tables
    
    total_elapsed = time.time() - total_start
    
    # Final summary
    log("\n" + "=" * 70)
    log("Final Summary")
    log("=" * 70)
    
    for table_name in TABLES:
        initial = initial_counts[table_name]
        final = check_table_counts(dest, table_name)
        new = final - initial
        status = "✅" if results.get(table_name, False) else "❌"
        log(f"   {status} {table_name}: {initial:,} → {final:,} (+{new:,})")
    
    log(f"\n   ⏱️  Total time: {total_elapsed:.2f}s")
    
    # Check if all tables have data
    all_have_data = all(check_table_counts(dest, table) > 0 for table in TABLES)
    all_success = all(results.values())
    
    if all_have_data and all_success:
        log("\n   🎉 SUCCESS: All tables migrated successfully with data!")
        return True
    else:
        log("\n   ⚠️  WARNING: Some tables may be empty or migration failed")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        log("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        log(f"\n\n❌ Fatal error: {e}")
        import traceback
        log(traceback.format_exc())
        sys.exit(1)

