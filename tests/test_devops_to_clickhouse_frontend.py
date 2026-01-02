"""
Test DevOps to ClickHouse migration via Frontend API (simulates frontend flow)
This test creates an operation via the backend API and executes it, just like the frontend does.
"""
import sys
import os
import time
import requests
from datetime import datetime, timedelta
import json
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()

# Add parent directory to path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, backend_dir)

# Configuration from environment variables
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:5009')
UNIVERSAL_SERVICE_URL = os.getenv('UNIVERSAL_SERVICE_URL', 'http://localhost:5011')

# DevOps credentials from environment
DEVOPS_CONFIG = {
    "access_token": os.getenv('DEVOPS_ACCESS_TOKEN', ''),
    "organization": os.getenv('DEVOPS_ORGANIZATION', ''),
    "api_version": os.getenv('DEVOPS_API_VERSION', '7.1')
}

# ClickHouse credentials from environment
CLICKHOUSE_CONFIG = {
    "host": os.getenv('CLICKHOUSE_HOST', 'localhost'),
    "port": int(os.getenv('CLICKHOUSE_PORT', '8123')),
    "database": os.getenv('CLICKHOUSE_DATABASE', 'default'),
    "username": os.getenv('CLICKHOUSE_USER', 'default'),
    "password": os.getenv('CLICKHOUSE_PASSWORD', '')
}

# Test user credentials from environment
TEST_USERNAME = os.getenv('TEST_USERNAME', '')
TEST_PASSWORD = os.getenv('TEST_PASSWORD', '')

# Validate required environment variables
if not DEVOPS_CONFIG["access_token"]:
    raise ValueError("DEVOPS_ACCESS_TOKEN environment variable is required")
if not DEVOPS_CONFIG["organization"]:
    raise ValueError("DEVOPS_ORGANIZATION environment variable is required")
if not CLICKHOUSE_CONFIG["password"]:
    raise ValueError("CLICKHOUSE_PASSWORD environment variable is required")
if not TEST_USERNAME or not TEST_PASSWORD:
    raise ValueError("TEST_USERNAME and TEST_PASSWORD environment variables are required")

def log(message):
    """Log with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    # Replace Unicode characters with ASCII equivalents for Windows console
    message = message.replace('✅', '[OK]').replace('❌', '[ERROR]').replace('⚠️', '[WARN]').replace('📊', '[INFO]').replace('📥', '[READ]').replace('📦', '[BATCH]').replace('🎉', '[SUCCESS]').replace('⏱️', '[TIME]').replace('⏳', '[WAIT]').replace('→', '->')
    print(f"[{timestamp}] {message}", flush=True)

def login():
    """Login and get JWT token"""
    log("=" * 70)
    log("Step 1: Logging in...")
    log("=" * 70)
    
    response = requests.post(
        f"{BACKEND_URL}/api/auth/login",
        json={
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD
        },
        timeout=10
    )
    
    if response.status_code != 200:
        log(f"❌ Login failed: {response.status_code} - {response.text}")
        return None
    
    data = response.json()
    token = data.get("access_token")
    if not token:
        log("❌ No access token in response")
        return None
    
    log("✅ Login successful")
    return token

def get_universal_service_id(token):
    """Get Universal Migration Service database master ID"""
    log("\n" + "=" * 70)
    log("Step 2: Getting Universal Migration Service...")
    log("=" * 70)
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BACKEND_URL}/api/database-master",
        headers=headers,
        timeout=10
    )
    
    if response.status_code != 200:
        log(f"❌ Failed to get database masters: {response.status_code}")
        return None
    
    data = response.json()
    databases = data.get("databases", [])
    
    # Find Universal Migration Service
    universal_service = None
    for db in databases:
        if "universal" in db.get("name", "").lower() or "5011" in db.get("service_url", ""):
            universal_service = db
            break
    
    if not universal_service:
        log("❌ Universal Migration Service not found")
        log(f"Available databases: {[db.get('name') for db in databases]}")
        return None
    
    log(f"✅ Found Universal Migration Service: {universal_service.get('name')} (ID: {universal_service.get('id')})")
    return universal_service.get("id")

def create_operation(token, source_id):
    """Create a DevOps to ClickHouse operation (like frontend does)"""
    log("\n" + "=" * 70)
    log("Step 3: Creating operation...")
    log("=" * 70)
    
    # Schedule for immediate execution (1 minute from now)
    schedule_time = datetime.utcnow() + timedelta(minutes=1)
    schedule_iso = schedule_time.isoformat()
    
    operation_data = {
        "source_id": source_id,
        "schedule": schedule_iso,
        "operation_type": "full",
        "config_data": {
            "source_type": "devops",
            "dest_type": "clickhouse",
            "source": DEVOPS_CONFIG,
            "destination": CLICKHOUSE_CONFIG,
            "operation_type": "full"
        }
    }
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    log(f"Creating operation with schedule: {schedule_iso}")
    log(f"Source: DevOps ({DEVOPS_CONFIG['organization']})")
    log(f"Destination: ClickHouse ({CLICKHOUSE_CONFIG['host']}:{CLICKHOUSE_CONFIG['port']}/{CLICKHOUSE_CONFIG['database']})")
    
    response = requests.post(
        f"{BACKEND_URL}/api/operations",
        json=operation_data,
        headers=headers,
        timeout=10
    )
    
    if response.status_code != 201:
        log(f"❌ Failed to create operation: {response.status_code}")
        log(f"Response: {response.text}")
        return None
    
    data = response.json()
    operation = data.get("operation")
    if not operation:
        log("❌ No operation in response")
        return None
    
    operation_id = operation.get("id")
    log(f"✅ Operation created successfully (ID: {operation_id})")
    return operation_id

def execute_operation(token, operation_id):
    """Execute the operation (like clicking 'Execute Now' in frontend)"""
    log("\n" + "=" * 70)
    log("Step 4: Executing operation...")
    log("=" * 70)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Execute with force=true to run immediately
    # Use a longer timeout since the backend might take time to start the service
    log("Executing operation (force=true)...")
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/operations/{operation_id}/execute?force=true",
            headers=headers,
            timeout=120  # 2 minutes for service startup and initial connection
        )
        
        if response.status_code not in [200, 202]:
            log(f"[WARN] Execute response: {response.status_code}")
            log(f"Response: {response.text}")
            # Continue anyway - operation might have started
        else:
            log("Execution request accepted by backend")
    except requests.exceptions.Timeout:
        log("[WARN] Execute request timed out (this is OK - operation may still be starting)")
        log("Continuing to monitor operation status...")
    except Exception as e:
        log(f"[WARN] Execute request error: {e}")
        log("Continuing to monitor operation status...")
    
    log("[OK] Execution request sent (or timed out - will monitor status)")
    return True

def check_operation_status(token, operation_id):
    """Check operation status"""
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(
        f"{BACKEND_URL}/api/operations/{operation_id}/status",
        headers=headers,
        timeout=10
    )
    
    if response.status_code != 200:
        return None
    
    return response.json()

def monitor_operation(token, operation_id, max_wait_hours=3):
    """Monitor operation progress"""
    log("\n" + "=" * 70)
    log("Step 5: Monitoring operation progress...")
    log("=" * 70)
    
    start_time = time.time()
    max_wait_seconds = max_wait_hours * 3600
    last_status = None
    last_log_time = 0
    
    log("Monitoring operation (this may take a while for large migrations)...")
    log("Press Ctrl+C to stop monitoring (operation will continue running)")
    
    try:
        while True:
            elapsed = time.time() - start_time
            
            if elapsed > max_wait_seconds:
                log(f"\n⚠️  Maximum wait time ({max_wait_hours} hours) exceeded")
                break
            
            status_data = check_operation_status(token, operation_id)
            if not status_data:
                log("⚠️  Could not get status")
                time.sleep(10)
                continue
            
            current_status = status_data.get("status")
            
            # Log status changes
            if current_status != last_status:
                log(f"\n📊 Status changed: {last_status} → {current_status}")
                last_status = current_status
            
            # Log progress every 30 seconds
            if time.time() - last_log_time >= 30:
                if current_status == "running":
                    log(f"⏳ Still running... (elapsed: {int(elapsed/60)}m {int(elapsed%60)}s)")
                last_log_time = time.time()
            
            # Check if completed
            if status_data.get("is_completed"):
                log("\n" + "=" * 70)
                log("Operation completed!")
                log("=" * 70)
                
                is_success = status_data.get("is_success", False)
                if is_success:
                    log("✅ Migration completed successfully!")
                else:
                    log("❌ Migration failed")
                
                # Show results
                migration_results = status_data.get("migration_results", {})
                if migration_results:
                    log(f"\n📊 Migration Results:")
                    log(f"   Total Tables: {migration_results.get('total_tables', 0)}")
                    log(f"   Tables Migrated: {migration_results.get('tables_migrated_count', 0)}")
                    log(f"   Tables Failed: {migration_results.get('tables_failed_count', 0)}")
                    log(f"   Total Records: {migration_results.get('total_records', 0):,}")
                    
                    tables_migrated = migration_results.get("tables_migrated", [])
                    if tables_migrated:
                        log(f"\n   Migrated Tables:")
                        for table in tables_migrated:
                            table_name = table.get("table", "Unknown")
                            records = table.get("records", 0)
                            log(f"      - {table_name}: {records:,} records")
                    
                    tables_failed = migration_results.get("tables_failed", [])
                    if tables_failed:
                        log(f"\n   Failed Tables:")
                        for table in tables_failed:
                            table_name = table.get("table", "Unknown")
                            error = table.get("error", "Unknown error")
                            log(f"      - {table_name}: {error}")
                
                error_message = status_data.get("error_message")
                if error_message:
                    log(f"\n⚠️  Error Message: {error_message}")
                
                duration = status_data.get("duration_formatted")
                if duration:
                    log(f"\n⏱️  Duration: {duration}")
                
                return is_success
            
            # Check if failed
            if current_status == "failed":
                log("\n" + "=" * 70)
                log("❌ Operation failed!")
                log("=" * 70)
                error_message = status_data.get("error_message")
                if error_message:
                    log(f"Error: {error_message}")
                return False
            
            time.sleep(5)  # Check every 5 seconds
            
    except KeyboardInterrupt:
        log("\n\n⚠️  Monitoring stopped by user")
        log("Operation will continue running in the background")
        log(f"You can check status at: {BACKEND_URL}/api/operations/{operation_id}/status")
        return None

def verify_clickhouse_data():
    """Verify data in ClickHouse"""
    log("\n" + "=" * 70)
    log("Step 6: Verifying ClickHouse data...")
    log("=" * 70)
    
    try:
        import clickhouse_connect
        
        client = clickhouse_connect.get_client(
            host=CLICKHOUSE_CONFIG["host"],
            port=CLICKHOUSE_CONFIG["port"],
            username=CLICKHOUSE_CONFIG["username"],
            password=CLICKHOUSE_CONFIG["password"],
            database=CLICKHOUSE_CONFIG["database"]
        )
        
        tables = [
            "DEVOPS_PROJECTS",
            "DEVOPS_TEAMS",
            "DEVOPS_WORKITEMS_MAIN",
            "DEVOPS_WORKITEMS_UPDATES",
            "DEVOPS_WORKITEMS_COMMENTS",
            "DEVOPS_WORKITEMS_RELATIONS",
            "DEVOPS_WORKITEMS_REVISIONS"
        ]
        
        total_records = 0
        log("\n📊 Table Record Counts:")
        for table in tables:
            ch_table_name = f"DEVOPS_{table}" if not table.startswith("DEVOPS_") else table
            try:
                result = client.query(f"SELECT count() FROM {ch_table_name}")
                count = result.result_rows[0][0]
                total_records += count
                status = "✅" if count > 0 else "⚠️"
                log(f"   {status} {table}: {count:,} records")
            except Exception as e:
                log(f"   ❌ {table}: Error - {e}")
        
        log(f"\n📊 Total Records: {total_records:,}")
        
        if total_records < 100:
            log("\n⚠️  WARNING: Very few records migrated. This might indicate an issue.")
            return False
        elif total_records < 1000:
            log("\n⚠️  WARNING: Fewer records than expected. Check logs for issues.")
            return False
        else:
            log("\n✅ Data verification looks good!")
            return True
            
    except ImportError:
        log("⚠️  clickhouse-connect not available, skipping verification")
        return None
    except Exception as e:
        log(f"❌ Error verifying ClickHouse data: {e}")
        return False

def main():
    """Main test function"""
    log("=" * 70)
    log("DevOps to ClickHouse Migration - Frontend API Test")
    log("=" * 70)
    log(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("")
    
    # Step 1: Login
    token = login()
    if not token:
        log("❌ Cannot proceed without authentication")
        return False
    
    # Step 2: Get Universal Migration Service
    source_id = get_universal_service_id(token)
    if not source_id:
        log("❌ Cannot proceed without Universal Migration Service")
        return False
    
    # Step 3: Create operation
    operation_id = create_operation(token, source_id)
    if not operation_id:
        log("❌ Cannot proceed without operation")
        return False
    
    # Step 4: Execute operation
    if not execute_operation(token, operation_id):
        log("⚠️  Execution request may have failed, but continuing...")
    
    # Step 5: Monitor operation
    success = monitor_operation(token, operation_id, max_wait_hours=3)
    
    # Step 6: Verify data
    verify_clickhouse_data()
    
    # Final summary
    log("\n" + "=" * 70)
    log("Test Summary")
    log("=" * 70)
    log(f"Operation ID: {operation_id}")
    log(f"Status: {'✅ SUCCESS' if success else '❌ FAILED' if success is False else '⚠️  UNKNOWN'}")
    log(f"View operation: {BACKEND_URL}/api/operations/{operation_id}")
    log("=" * 70)
    
    return success if success is not None else False

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

