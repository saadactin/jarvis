"""
Quick script to check migration status and service logs
"""
import requests
import json

BACKEND_URL = "http://localhost:5009"
UNIVERSAL_SERVICE_URL = "http://localhost:5011"

# Test credentials
TEST_USERNAME = "saad12"
TEST_PASSWORD = "saad12"

def login():
    response = requests.post(
        f"{BACKEND_URL}/api/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
        timeout=10
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    return None

def check_operation(token, op_id):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BACKEND_URL}/api/operations/{op_id}",
        headers=headers,
        timeout=10
    )
    if response.status_code == 200:
        return response.json().get("operation")
    return None

def check_service_health():
    try:
        response = requests.get(f"{UNIVERSAL_SERVICE_URL}/health", timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

def main():
    print("=" * 70)
    print("Migration Status Check")
    print("=" * 70)
    
    # Check service health
    print("\n1. Checking Universal Migration Service health...")
    health = check_service_health()
    if health:
        print(f"   [OK] Service is running")
        print(f"   Available sources: {health.get('available_sources', [])}")
        print(f"   Available destinations: {health.get('available_destinations', [])}")
    else:
        print(f"   [ERROR] Service is not responding at {UNIVERSAL_SERVICE_URL}")
        print("   Please restart the Universal Migration Service")
        return
    
    # Check operation
    token = login()
    if not token:
        print("\n[ERROR] Cannot login")
        return
    
    op_id = 21  # Current operation
    print(f"\n2. Checking Operation #{op_id}...")
    operation = check_operation(token, op_id)
    if operation:
        print(f"   Status: {operation.get('status')}")
        print(f"   Started: {operation.get('started_at')}")
        print(f"   Error: {operation.get('error_message', 'None')}")
        
        result_data = operation.get('result_data')
        if result_data:
            print(f"\n   Migration Results:")
            print(f"   - Success: {result_data.get('success', False)}")
            print(f"   - Total Tables: {result_data.get('total_tables', 0)}")
            print(f"   - Tables Migrated: {len(result_data.get('tables_migrated', []))}")
            print(f"   - Tables Failed: {len(result_data.get('tables_failed', []))}")
            
            if result_data.get('tables_failed'):
                print(f"\n   Failed Tables:")
                for table in result_data.get('tables_failed', []):
                    print(f"   - {table.get('table')}: {table.get('error')}")
            
            if result_data.get('tables_migrated'):
                print(f"\n   Migrated Tables:")
                for table in result_data.get('tables_migrated', []):
                    print(f"   - {table.get('table')}: {table.get('records', 0)} records")
        else:
            print(f"   [WARN] No result data yet - migration may still be running")
    else:
        print(f"   [ERROR] Cannot get operation details")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()

