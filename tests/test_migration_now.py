#!/usr/bin/env python3
"""
Quick Migration Test - Test Zoho to ClickHouse migration
"""
import requests
import json
import sys
import time

# Force UTF-8 encoding for stdout
sys.stdout.reconfigure(encoding='utf-8')

# Configuration
ZOHO_CONFIG = {
    "refresh_token": "1000.2cbaa36345c6d04b699b0cb6740c21ef.149922195c479d83c84826653ff84ff4",
    "client_id": "1000.0L3LLVLEKE9ELW7CE0I0KJ3K4FKBBT",
    "client_secret": "d99c479d4c0db451c653d8c380bf6a4c557a73528c",
    "api_domain": "https://www.zohoapis.in"
}

CLICKHOUSE_CONFIG = {
    "host": "74.225.251.123",
    "port": 8123,
    "username": "default",
    "password": "root",
    "database": "test6"
}

UNIVERSAL_MIGRATION_SERVICE_URL = "http://localhost:5011"

def test_migration():
    """Test Zoho to ClickHouse migration"""
    print("="*70)
    print("TESTING ZOHO TO CLICKHOUSE MIGRATION")
    print("="*70)
    print("\n1. Checking service health...")
    
    # Check service health
    try:
        response = requests.get(f"{UNIVERSAL_MIGRATION_SERVICE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   [OK] Service is healthy")
            print(f"   [OK] Available sources: {', '.join(data.get('available_sources', []))}")
            print(f"   [OK] Available destinations: {', '.join(data.get('available_destinations', []))}")
        else:
            print(f"   [FAIL] Service returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"   [FAIL] Service not reachable: {e}")
        return False
    
    print("\n2. Testing connections...")
    
    # Test source connection
    try:
        response = requests.post(
            f"{UNIVERSAL_MIGRATION_SERVICE_URL}/test-connection",
            json={
                "type": "source",
                "adapter_type": "zoho",
                "config": ZOHO_CONFIG
            },
            timeout=10
        )
        if response.status_code == 200 and response.json().get('valid'):
            print(f"   [OK] Zoho connection test passed")
        else:
            print(f"   [FAIL] Zoho connection test failed: {response.json()}")
            return False
    except Exception as e:
        print(f"   [FAIL] Zoho connection test error: {e}")
        return False
    
    # Test destination connection
    try:
        response = requests.post(
            f"{UNIVERSAL_MIGRATION_SERVICE_URL}/test-connection",
            json={
                "type": "destination",
                "adapter_type": "clickhouse",
                "config": CLICKHOUSE_CONFIG
            },
            timeout=10
        )
        if response.status_code == 200 and response.json().get('valid'):
            print(f"   [OK] ClickHouse connection test passed")
        else:
            print(f"   [FAIL] ClickHouse connection test failed: {response.json()}")
            return False
    except Exception as e:
        print(f"   [FAIL] ClickHouse connection test error: {e}")
        return False
    
    print("\n3. Starting migration (this may take a few minutes)...")
    print("   Note: This will migrate a small subset of Zoho modules to ClickHouse")
    
    payload = {
        "source_type": "zoho",
        "dest_type": "clickhouse",
        "source": ZOHO_CONFIG,
        "destination": CLICKHOUSE_CONFIG,
        "operation_type": "full"
    }
    
    try:
        start_time = time.time()
        print(f"   Sending migration request to {UNIVERSAL_MIGRATION_SERVICE_URL}/migrate...")
        
        response = requests.post(
            f"{UNIVERSAL_MIGRATION_SERVICE_URL}/migrate",
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=1800  # 30 minutes
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            success = result.get('success', False)
            total_tables = result.get('total_tables', 0)
            tables_migrated = result.get('tables_migrated', [])
            tables_failed = result.get('tables_failed', [])
            
            print(f"\n   Migration completed in {int(elapsed // 60)}m {int(elapsed % 60)}s")
            print(f"   [OK] Success: {success}")
            print(f"   [OK] Total tables: {total_tables}")
            print(f"   [OK] Migrated: {len(tables_migrated)} tables")
            print(f"   [{'WARN' if tables_failed else 'OK'}] Failed: {len(tables_failed)} tables")
            
            if tables_migrated:
                print(f"\n   Successfully migrated tables:")
                for table_info in tables_migrated[:10]:
                    table_name = table_info.get('table', 'unknown')
                    records = table_info.get('records', 0)
                    print(f"     - {table_name}: {records} records")
                if len(tables_migrated) > 10:
                    print(f"     ... and {len(tables_migrated) - 10} more")
            
            if tables_failed:
                print(f"\n   Failed tables:")
                for table_info in tables_failed[:5]:
                    table_name = table_info.get('table', 'unknown')
                    error = table_info.get('error', 'Unknown error')[:100]
                    print(f"     - {table_name}: {error}")
                if len(tables_failed) > 5:
                    print(f"     ... and {len(tables_failed) - 5} more")
            
            return success
        else:
            print(f"   [FAIL] Migration failed with status {response.status_code}")
            print(f"   Response: {response.text[:500]}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"   [FAIL] Migration timeout (30 minutes)")
        return False
    except Exception as e:
        print(f"   [FAIL] Migration error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_migration()
    if success:
        print("\n" + "="*70)
        print("[SUCCESS] MIGRATION TEST PASSED!")
        print("="*70)
        sys.exit(0)
    else:
        print("\n" + "="*70)
        print("[FAILED] MIGRATION TEST FAILED")
        print("="*70)
        sys.exit(1)

