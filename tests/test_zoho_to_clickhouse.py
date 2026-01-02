#!/usr/bin/env python3
"""
Test Zoho to ClickHouse Migration
Tests the Universal Migration Service with actual credentials
"""

import requests
import time
import json
import sys
import os
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()

# Force UTF-8 encoding for stdout
sys.stdout.reconfigure(encoding='utf-8')

# Zoho Credentials from environment
ZOHO_CONFIG = {
    "refresh_token": os.getenv('ZOHO_REFRESH_TOKEN', ''),
    "client_id": os.getenv('ZOHO_CLIENT_ID', ''),
    "client_secret": os.getenv('ZOHO_CLIENT_SECRET', ''),
    "api_domain": os.getenv('ZOHO_API_DOMAIN', 'https://www.zohoapis.com')
}

# ClickHouse Credentials from environment
CLICKHOUSE_CONFIG = {
    "host": os.getenv('CLICKHOUSE_HOST', 'localhost'),
    "port": int(os.getenv('CLICKHOUSE_PORT', '8123')),
    "username": os.getenv('CLICKHOUSE_USER', 'default'),
    "password": os.getenv('CLICKHOUSE_PASSWORD', ''),
    "database": os.getenv('CLICKHOUSE_DATABASE', 'default')
}

UNIVERSAL_MIGRATION_SERVICE_URL = os.getenv('UNIVERSAL_SERVICE_URL', 'http://localhost:5011')

# Validate required environment variables
if not ZOHO_CONFIG["refresh_token"]:
    raise ValueError("ZOHO_REFRESH_TOKEN environment variable is required")
if not ZOHO_CONFIG["client_id"]:
    raise ValueError("ZOHO_CLIENT_ID environment variable is required")
if not ZOHO_CONFIG["client_secret"]:
    raise ValueError("ZOHO_CLIENT_SECRET environment variable is required")
if not CLICKHOUSE_CONFIG["password"]:
    raise ValueError("CLICKHOUSE_PASSWORD environment variable is required")

def print_section_header(title):
    print(f"\n{'='*70}")
    print(f"{title}")
    print(f"{'='*70}\n")

def test_health_check():
    """Test if Universal Migration Service is running"""
    print_section_header("STEP 1: Health Check - Universal Migration Service")
    try:
        response = requests.get(f"{UNIVERSAL_MIGRATION_SERVICE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"  [OK] Service is running")
            print(f"  [OK] Available sources: {data.get('available_sources')}")
            print(f"  [OK] Available destinations: {data.get('available_destinations')}")
            return True
        else:
            print(f"  [FAIL] Service health check failed: Status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"  [FAIL] Service not reachable: {e}")
        print(f"  -> Make sure Universal Migration Service is running on {UNIVERSAL_MIGRATION_SERVICE_URL}")
        return False

def test_migration():
    """Test Zoho to ClickHouse migration"""
    print_section_header("STEP 2: Testing Zoho to ClickHouse Migration")
    
    payload = {
        "source_type": "zoho",
        "dest_type": "clickhouse",
        "source": ZOHO_CONFIG,
        "destination": CLICKHOUSE_CONFIG,
        "operation_type": "full"
    }
    
    print(f"  Request Configuration:")
    print(f"    Source: Zoho CRM ({ZOHO_CONFIG['api_domain']})")
    print(f"    Destination: ClickHouse ({CLICKHOUSE_CONFIG['host']}:{CLICKHOUSE_CONFIG['port']}/{CLICKHOUSE_CONFIG['database']})")
    print(f"    Operation: Full migration\n")
    
    print(f"  Sending migration request...")
    print(f"  This may take several minutes depending on data volume...\n")
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{UNIVERSAL_MIGRATION_SERVICE_URL}/migrate",
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=1800  # 30 minute timeout for large migrations
        )
        elapsed_time = time.time() - start_time
        
        response_json = response.json()
        
        print(f"  Migration completed in {int(elapsed_time // 60)}m {int(elapsed_time % 60)}s")
        print(f"  Response Status: {response.status_code}\n")
        
        if response.status_code == 200:
            success = response_json.get('success', False)
            total_tables = response_json.get('total_tables', 0)
            tables_migrated = response_json.get('tables_migrated', [])
            tables_failed = response_json.get('tables_failed', [])
            
            print(f"  Migration Results:")
            print(f"    Success: {success}")
            print(f"    Total Tables: {total_tables}")
            print(f"    Tables Migrated: {len(tables_migrated)}")
            print(f"    Tables Failed: {len(tables_failed)}\n")
            
            if tables_migrated:
                print(f"  ✅ Successfully Migrated Tables ({len(tables_migrated)}):")
                total_records = 0
                for table_info in tables_migrated:
                    records = table_info.get('records', 0)
                    total_records += records
                    print(f"    - {table_info['table']}: {records:,} records")
                print(f"    Total Records Migrated: {total_records:,}\n")
            
            if tables_failed:
                print(f"  ❌ Failed Tables ({len(tables_failed)}):")
                for table_info in tables_failed[:10]:  # Show first 10 errors
                    error_msg = table_info.get('error', 'Unknown error')
                    # Truncate long error messages
                    if len(error_msg) > 100:
                        error_msg = error_msg[:100] + "..."
                    print(f"    - {table_info['table']}: {error_msg}")
                if len(tables_failed) > 10:
                    print(f"    - ... and {len(tables_failed) - 10} more failures\n")
            
            if success:
                print(f"  ✅ ALL TABLES MIGRATED SUCCESSFULLY!")
                return True, response_json
            else:
                print(f"  ⚠️  Migration completed with some failures")
                print(f"  {len(tables_migrated)} tables succeeded, {len(tables_failed)} tables failed")
                return False, response_json
        else:
            print(f"  [FAIL] Migration failed with status code: {response.status_code}")
            print(f"  Error: {response_json.get('error', 'Unknown error')}")
            return False, response_json
            
    except requests.exceptions.Timeout:
        print(f"  [FAIL] Migration request timed out (exceeded 30 minutes)")
        return False, {"error": "Request timeout"}
    except requests.exceptions.RequestException as e:
        print(f"  [FAIL] Migration request failed: {e}")
        return False, {"error": str(e)}

def verify_clickhouse_tables():
    """Verify tables exist in ClickHouse"""
    print_section_header("STEP 3: Verifying Tables in ClickHouse")
    
    try:
        from clickhouse_connect import get_client
        
        client = get_client(
            host=CLICKHOUSE_CONFIG['host'],
            port=8123,  # Try HTTP API port
            username=CLICKHOUSE_CONFIG['username'],
            password=CLICKHOUSE_CONFIG['password'],
            database=CLICKHOUSE_CONFIG['database']
        )
        
        # Get all tables with zoho_ prefix
        result = client.query(f"SHOW TABLES FROM {CLICKHOUSE_CONFIG['database']} LIKE 'zoho_%'")
        tables = [row[0] for row in result.result_rows]
        
        print(f"  Found {len(tables)} Zoho tables in ClickHouse:")
        for table in sorted(tables):
            # Get record count
            try:
                count_result = client.query(f"SELECT count() FROM {CLICKHOUSE_CONFIG['database']}.{table}")
                count = count_result.result_rows[0][0]
                print(f"    - {table}: {count:,} records")
            except Exception as e:
                print(f"    - {table}: (could not get count: {e})")
        
        client.close()
        return len(tables) > 0
        
    except Exception as e:
        print(f"  [WARN] Could not verify tables: {e}")
        print(f"  -> This is okay if migration is still running or connection failed")
        return False

def main():
    print_section_header("ZOHO TO CLICKHOUSE MIGRATION TEST")
    print("This script tests:")
    print("  1. Universal Migration Service health check")
    print("  2. Zoho to ClickHouse migration execution")
    print("  3. Verification of migrated tables in ClickHouse")
    print_section_header("")
    
    # Wait for service to be ready
    print("Waiting for Universal Migration Service to be ready...")
    for i in range(10):
        if test_health_check():
            break
        print(f"  Waiting... ({i+1}/10)")
        time.sleep(2)
    else:
        print(f"\n[FAIL] Universal Migration Service did not start or respond.")
        print(f"  -> Ensure 'jarvis-main/app.py' is running")
        print(f"  -> Check that Universal Migration Service is configured to auto-start")
        return
    
    # Run migration
    success, results = test_migration()
    
    # Verify tables
    if success:
        time.sleep(2)  # Brief delay before verification
        verify_clickhouse_tables()
    
    # Final summary
    print_section_header("TEST SUMMARY")
    if success:
        tables_migrated = results.get('tables_migrated', [])
        total_records = sum(t.get('records', 0) for t in tables_migrated)
        print(f"  ✅ SUCCESS: All {len(tables_migrated)} tables migrated successfully")
        print(f"  ✅ Total Records: {total_records:,}")
        print(f"\n  🎉 ALL DATA HAS BEEN MIGRATED SUCCESSFULLY!")
    else:
        tables_migrated = results.get('tables_migrated', [])
        tables_failed = results.get('tables_failed', [])
        if tables_migrated:
            total_records = sum(t.get('records', 0) for t in tables_migrated)
            print(f"  ⚠️  PARTIAL SUCCESS:")
            print(f"    - {len(tables_migrated)} tables migrated ({sum(t.get('records', 0) for t in tables_migrated):,} records)")
            print(f"    - {len(tables_failed)} tables failed")
            print(f"  -> Check error messages above for failed tables")
        else:
            print(f"  ❌ FAILED: No tables were migrated")
    
    print_section_header("")

if __name__ == "__main__":
    main()

