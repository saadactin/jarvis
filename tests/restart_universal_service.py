"""
Script to restart Universal Migration Service
"""
import subprocess
import time
import requests
import sys
import os

SERVICE_DIR = "universal_migration_service"
SERVICE_URL = "http://localhost:5011"

def check_service():
    try:
        response = requests.get(f"{SERVICE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def find_service_process():
    """Find Python process running the service"""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV"],
            capture_output=True,
            text=True
        )
        # This is a simple check - in production you'd want more sophisticated process detection
        return True
    except:
        return False

def start_service():
    """Start the Universal Migration Service"""
    print("Starting Universal Migration Service...")
    
    # Change to service directory
    service_path = os.path.join(os.getcwd(), SERVICE_DIR)
    if not os.path.exists(service_path):
        print(f"[ERROR] Service directory not found: {service_path}")
        return False
    
    # Start the service
    try:
        # On Windows, start in a new window
        subprocess.Popen(
            ["python", "app.py"],
            cwd=service_path,
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
        )
        print("[OK] Service start command issued")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to start service: {e}")
        return False

def main():
    print("=" * 70)
    print("Universal Migration Service Restart")
    print("=" * 70)
    
    # Check if service is running
    print("\n1. Checking service status...")
    if check_service():
        print("   [OK] Service is already running and responding")
        print("   Service is healthy, no restart needed")
        return
    
    print("   [WARN] Service is not responding")
    
    # Try to start service
    print("\n2. Starting service...")
    if start_service():
        print("   [OK] Service start command issued")
        
        # Wait and check
        print("\n3. Waiting for service to start...")
        max_wait = 30
        waited = 0
        while waited < max_wait:
            time.sleep(2)
            waited += 2
            if check_service():
                print(f"   [OK] Service is now responding (waited {waited}s)")
                health = requests.get(f"{SERVICE_URL}/health", timeout=5).json()
                print(f"   Available sources: {health.get('available_sources', [])}")
                print(f"   Available destinations: {health.get('available_destinations', [])}")
                return
            print(f"   Waiting... ({waited}/{max_wait}s)")
        
        print(f"   [WARN] Service did not respond after {max_wait}s")
        print("   Please check the service logs manually")
    else:
        print("   [ERROR] Failed to start service")
        print("\n   Manual steps:")
        print(f"   1. Open a new terminal")
        print(f"   2. cd {SERVICE_DIR}")
        print(f"   3. python app.py")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()

