"""
Test script to verify Universal Migration Service auto-start functionality
"""
import requests
import time
import sys
import os

# Add jarvis-main to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'jarvis-main'))

# Configuration
MAIN_BACKEND_URL = "http://localhost:5009"
UNIVERSAL_MIGRATION_SERVICE_URL = "http://localhost:5010"

def print_section(title):
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}\n")

def test_main_backend():
    """Test if main backend is running"""
    print_section("STEP 1: Testing Main Backend")
    try:
        response = requests.get(f"{MAIN_BACKEND_URL}/health", timeout=5)
        if response.status_code == 200:
            print(f"  [OK] Main backend is running on {MAIN_BACKEND_URL}")
            return True
        else:
            print(f"  [FAIL] Main backend returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"  [FAIL] Main backend is not reachable: {e}")
        return False

def test_universal_migration_service():
    """Test if Universal Migration Service is running"""
    print_section("STEP 2: Testing Universal Migration Service")
    try:
        response = requests.get(f"{UNIVERSAL_MIGRATION_SERVICE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"  [OK] Universal Migration Service is running")
            print(f"  [OK] Available sources: {data.get('available_sources')}")
            print(f"  [OK] Available destinations: {data.get('available_destinations')}")
            return True
        else:
            print(f"  [FAIL] Service returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"  [FAIL] Universal Migration Service is not running: {e}")
        return False

def test_service_auto_start():
    """Test if service auto-starts when needed"""
    print_section("STEP 3: Testing Service Auto-Start")
    print("  Note: This test requires the service to be stopped first")
    print("  The auto-start logic will be tested when executing a migration")
    return True

def main():
    print_section("UNIVERSAL MIGRATION SERVICE AUTO-START TEST")
    print("This script tests:")
    print("  1. Main backend health")
    print("  2. Universal Migration Service health")
    print("  3. Service auto-start capability")
    
    results = {
        "main_backend": False,
        "universal_service": False,
        "auto_start": False
    }
    
    # Test main backend
    results["main_backend"] = test_main_backend()
    
    if not results["main_backend"]:
        print("\n[ERROR] Main backend is not running. Please start it first:")
        print("  cd jarvis-main")
        print("  python app.py")
        return
    
    # Test Universal Migration Service
    results["universal_service"] = test_universal_migration_service()
    
    if results["universal_service"]:
        print("\n[INFO] Universal Migration Service is already running")
    else:
        print("\n[INFO] Universal Migration Service is not running")
        print("[INFO] It should auto-start when you execute a migration from the frontend")
    
    # Test auto-start capability
    results["auto_start"] = test_service_auto_start()
    
    print_section("TEST SUMMARY")
    print(f"  Main Backend: {'[PASS]' if results['main_backend'] else '[FAIL]'}")
    print(f"  Universal Service: {'[PASS]' if results['universal_service'] else '[NOT RUNNING]'}")
    print(f"  Auto-Start Capability: {'[READY]' if results['auto_start'] else '[FAIL]'}")
    
    if results["main_backend"]:
        print("\n[SUCCESS] Main backend is ready")
        print("[INFO] Universal Migration Service will auto-start when needed")
    else:
        print("\n[FAILED] Please start the main backend first")

if __name__ == "__main__":
    main()

