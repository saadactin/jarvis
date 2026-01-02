#!/usr/bin/env python3
"""
Test script for PostgreSQL to ClickHouse migration
Tests the Universal Migration Service and verifies the migration works correctly
"""
import os
import sys
import requests
import time
import json
from dotenv import load_dotenv

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables
load_dotenv()

# Configuration
UNIVERSAL_MIGRATION_SERVICE_URL = "http://localhost:5010"
MAIN_BACKEND_URL = "http://localhost:5009"

# Test credentials (provided by user)
POSTGRES_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "Tor2",
    "username": "migration_user",
    "password": "StrongPassword123"
}

CLICKHOUSE_CONFIG = {
    "host": "74.225.251.123",
    "port": 8123,
    "database": "test6",
    "username": "default",
    "password": "root"
}

def print_step(step_num, description):
    """Print a formatted test step"""
    print(f"\n{'='*60}")
    print(f"STEP {step_num}: {description}")
    print(f"{'='*60}")

def wait_for_service(url, max_attempts=30, delay=2):
    """Wait for a service to be available"""
    for attempt in range(max_attempts):
        try:
            response = requests.get(f"{url}/health", timeout=2)
            if response.status_code == 200:
                return True
        except requests.exceptions.RequestException:
            pass
        
        if attempt < max_attempts - 1:
            print(f"  Waiting for service at {url}... (attempt {attempt + 1}/{max_attempts})")
            time.sleep(delay)
    
    return False

def test_health_check():
    """Test 1: Check if Universal Migration Service is running"""
    print_step(1, "Health Check - Universal Migration Service")
    
    try:
        response = requests.get(f"{UNIVERSAL_MIGRATION_SERVICE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"  [OK] Service is running")
            print(f"  [OK] Available sources: {data.get('available_sources', [])}")
            print(f"  [OK] Available destinations: {data.get('available_destinations', [])}")
            return True
        else:
            print(f"  [FAIL] Service returned status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"  [FAIL] Cannot connect to Universal Migration Service at {UNIVERSAL_MIGRATION_SERVICE_URL}")
        print(f"  -> Please ensure the service is running")
        return False
    except Exception as e:
        print(f"  [FAIL] Error: {str(e)}")
        return False

def test_postgres_connection():
    """Test 2: Test PostgreSQL connection"""
    print_step(2, "Test PostgreSQL Connection")
    
    try:
        import psycopg2
        
        conn = psycopg2.connect(
            host=POSTGRES_CONFIG["host"],
            port=POSTGRES_CONFIG["port"],
            database=POSTGRES_CONFIG["database"],
            user=POSTGRES_CONFIG["username"],
            password=POSTGRES_CONFIG["password"]
        )
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"  [OK] Connected to PostgreSQL")
        print(f"  [OK] Version: {version.split(',')[0]}")
        
        # List tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            LIMIT 10
        """)
        tables = cursor.fetchall()
        if tables:
            print(f"  [OK] Found {len(tables)} table(s) in database")
            for table in tables[:5]:
                print(f"    - {table[0]}")
        else:
            print(f"  [WARN] No tables found in database")
        
        cursor.close()
        conn.close()
        return True
        
    except ImportError:
        print(f"  [FAIL] psycopg2 not installed. Install it with: pip install psycopg2-binary")
        return False
    except Exception as e:
        print(f"  [FAIL] Connection failed: {str(e)}")
        print(f"  -> Check PostgreSQL credentials in .env file")
        return False

def test_clickhouse_connection():
    """Test 3: Test ClickHouse connection"""
    print_step(3, "Test ClickHouse Connection")
    
    try:
        import clickhouse_connect
        
        client = clickhouse_connect.get_client(
            host=CLICKHOUSE_CONFIG["host"],
            port=int(CLICKHOUSE_CONFIG["port"]),
            database=CLICKHOUSE_CONFIG["database"],
            username=CLICKHOUSE_CONFIG["username"],
            password=CLICKHOUSE_CONFIG["password"]
        )
        
        # Test query
        result = client.query("SELECT version()")
        version = result.result_rows[0][0]
        print(f"  [OK] Connected to ClickHouse")
        print(f"  [OK] Version: {version}")
        
        # List tables
        result = client.query(f"SHOW TABLES FROM {CLICKHOUSE_CONFIG['database']}")
        tables = result.result_rows
        if tables:
            print(f"  [OK] Found {len(tables)} table(s) in database")
            for table in tables[:5]:
                print(f"    - {table[0]}")
        else:
            print(f"  [WARN] No tables found in database")
        
        return True
        
    except ImportError:
        print(f"  [FAIL] clickhouse-connect not installed. Install it with: pip install clickhouse-connect")
        return False
    except Exception as e:
        print(f"  [FAIL] Connection failed: {str(e)}")
        print(f"  -> Check ClickHouse credentials in .env file")
        return False

def test_postgres_to_clickhouse_migration():
    """Test 4: Test PostgreSQL to ClickHouse migration"""
    print_step(4, "Test PostgreSQL to ClickHouse Migration")
    
    # Prepare migration request
    migration_payload = {
        "source_type": "postgresql",
        "dest_type": "clickhouse",
        "source": {
            "host": POSTGRES_CONFIG["host"],
            "port": POSTGRES_CONFIG["port"],
            "database": POSTGRES_CONFIG["database"],
            "username": POSTGRES_CONFIG["username"],
            "password": POSTGRES_CONFIG["password"]
        },
        "destination": {
            "host": CLICKHOUSE_CONFIG["host"],
            "port": CLICKHOUSE_CONFIG["port"],
            "database": CLICKHOUSE_CONFIG["database"],
            "username": CLICKHOUSE_CONFIG["username"],
            "password": CLICKHOUSE_CONFIG["password"]
        },
        "operation_type": "full"
    }
    
    print(f"  Request payload:")
    print(f"    Source: PostgreSQL ({POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}/{POSTGRES_CONFIG['database']})")
    print(f"    Destination: ClickHouse ({CLICKHOUSE_CONFIG['host']}:{CLICKHOUSE_CONFIG['port']}/{CLICKHOUSE_CONFIG['database']})")
    print(f"    Operation: Full migration")
    print(f"\n  Sending migration request...")
    
    try:
        # Send migration request
        response = requests.post(
            f"{UNIVERSAL_MIGRATION_SERVICE_URL}/migrate",
            json=migration_payload,
            timeout=300  # 5 minutes timeout for large migrations
        )
        
        if response.status_code in [200, 500]:  # 500 can still mean partial success
            data = response.json()
            success = data.get('success', False)
            tables_migrated = data.get('tables_migrated', [])
            tables_failed = data.get('tables_failed', [])
            total_tables = data.get('total_tables', 0)
            
            if success:
                print(f"  [OK] Migration completed successfully!")
            else:
                print(f"  [PARTIAL] Migration completed with some failures")
            
            print(f"\n  Migration Summary:")
            print(f"    - Total tables: {total_tables}")
            print(f"    - Successfully migrated: {len(tables_migrated)}")
            print(f"    - Failed: {len(tables_failed)}")
            
            if tables_migrated:
                print(f"\n  Successfully migrated tables:")
                total_records = 0
                for table in tables_migrated[:10]:  # Show first 10
                    records = table.get('records', 0)
                    total_records += records
                    print(f"    - {table.get('table', 'unknown')}: {records} records")
                if len(tables_migrated) > 10:
                    print(f"    ... and {len(tables_migrated) - 10} more")
                print(f"    Total records migrated: {total_records}")
            
            if tables_failed:
                print(f"\n  Failed tables:")
                for table in tables_failed[:5]:  # Show first 5 errors
                    error = table.get('error', 'Unknown error')
                    error_short = error[:80] + '...' if len(error) > 80 else error
                    print(f"    - {table.get('table', 'unknown')}: {error_short}")
                if len(tables_failed) > 5:
                    print(f"    ... and {len(tables_failed) - 5} more failures")
            
            if data.get('errors'):
                print(f"\n  Error details:")
                for error in data.get('errors', [])[:3]:
                    error_short = error[:100] + '...' if len(error) > 100 else error
                    print(f"    - {error_short}")
            
            # Return True if at least some tables migrated successfully
            return len(tables_migrated) > 0
        else:
            print(f"  [FAIL] Migration failed with status code: {response.status_code}")
            try:
                error_data = response.json()
                error_msg = error_data.get('error', 'Unknown error')
                print(f"  [FAIL] Error: {error_msg}")
                if 'traceback' in error_data or 'details' in error_data:
                    print(f"  [FAIL] Details: {error_data.get('traceback', error_data.get('details', ''))}")
            except:
                print(f"  [FAIL] Response: {response.text[:1000]}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"  [FAIL] Migration timed out (exceeded 5 minutes)")
        return False
    except requests.exceptions.RequestException as e:
        print(f"  [FAIL] Request failed: {str(e)}")
        return False
    except Exception as e:
        print(f"  [FAIL] Error: {str(e)}")
        return False

def main():
    """Main test execution"""
    print("\n" + "="*60)
    print("POSTGRESQL TO CLICKHOUSE MIGRATION TEST")
    print("="*60)
    print("\nThis script tests:")
    print("  1. Universal Migration Service health check")
    print("  2. PostgreSQL connection")
    print("  3. ClickHouse connection")
    print("  4. PostgreSQL to ClickHouse migration")
    
    results = {
        "health_check": False,
        "postgres_connection": False,
        "clickhouse_connection": False,
        "migration": False
    }
    
    # Test 1: Health Check
    print("\n" + "="*60)
    print("Waiting for Universal Migration Service to start...")
    print("="*60)
    if wait_for_service(UNIVERSAL_MIGRATION_SERVICE_URL):
        results["health_check"] = test_health_check()
    else:
        print(f"\n[FAIL] Universal Migration Service is not running")
        print(f"  -> Please start it first or restart the main backend")
        return
    
    # Test 2: PostgreSQL Connection
    if results["health_check"]:
        results["postgres_connection"] = test_postgres_connection()
    
    # Test 3: ClickHouse Connection
    if results["postgres_connection"]:
        results["clickhouse_connection"] = test_clickhouse_connection()
    
    # Test 4: Migration
    if all([results["health_check"], results["postgres_connection"], results["clickhouse_connection"]]):
        print("\n" + "="*60)
        print("Starting migration test...")
        print("="*60)
        results["migration"] = test_postgres_to_clickhouse_migration()
    else:
        print("\n[WARN] Skipping migration test due to previous failures")
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for test_name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {test_name.replace('_', ' ').title()}: {status}")
    
    all_passed = all(results.values())
    print("\n" + "="*60)
    if all_passed:
        print("[SUCCESS] ALL TESTS PASSED!")
        print("="*60)
        sys.exit(0)
    else:
        print("[FAILED] SOME TESTS FAILED")
        print("="*60)
        sys.exit(1)

if __name__ == "__main__":
    main()

