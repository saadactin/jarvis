"""
Force restart Universal Migration Service by killing old process and starting fresh
"""
import subprocess
import time
import requests
import sys
import os

SERVICE_DIR = "universal_migration_service"
SERVICE_URL = "http://localhost:5011"
SERVICE_PORT = 5011

def kill_process_on_port(port):
    """Kill process using the specified port on Windows"""
    try:
        # Find process using the port
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True
        )
        
        lines = result.stdout.split('\n')
        pids = []
        for line in lines:
            if f":{port}" in line and "LISTENING" in line:
                parts = line.split()
                if len(parts) > 4:
                    pid = parts[-1]
                    if pid.isdigit():
                        pids.append(pid)
        
        # Kill processes
        killed = []
        for pid in set(pids):
            try:
                subprocess.run(["taskkill", "/F", "/PID", pid], 
                             capture_output=True, check=True)
                killed.append(pid)
                print(f"   [OK] Killed process {pid}")
            except:
                print(f"   [WARN] Could not kill process {pid}")
        
        return len(killed) > 0
    except Exception as e:
        print(f"   [ERROR] Error killing processes: {e}")
        return False

def check_service():
    try:
        response = requests.get(f"{SERVICE_URL}/health", timeout=2)
        return response.status_code == 200
    except:
        return False

def start_service():
    """Start the Universal Migration Service"""
    service_path = os.path.join(os.getcwd(), SERVICE_DIR)
    if not os.path.exists(service_path):
        print(f"[ERROR] Service directory not found: {service_path}")
        return False
    
    try:
        # Start in background
        subprocess.Popen(
            ["python", "app.py"],
            cwd=service_path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
        )
        return True
    except Exception as e:
        print(f"[ERROR] Failed to start: {e}")
        return False

def main():
    print("=" * 70)
    print("Force Restart Universal Migration Service")
    print("=" * 70)
    
    # Step 1: Kill existing process
    print(f"\n1. Killing process on port {SERVICE_PORT}...")
    if kill_process_on_port(SERVICE_PORT):
        print("   [OK] Process killed")
        time.sleep(2)  # Wait for port to be released
    else:
        print("   [WARN] No process found on port (might already be stopped)")
    
    # Step 2: Verify port is free
    print(f"\n2. Verifying port {SERVICE_PORT} is free...")
    if check_service():
        print("   [WARN] Service is still responding - might need manual kill")
    else:
        print("   [OK] Port is free")
    
    # Step 3: Start service
    print(f"\n3. Starting service from {SERVICE_DIR}...")
    if start_service():
        print("   [OK] Service start command issued")
        
        # Step 4: Wait and verify
        print(f"\n4. Waiting for service to start (max 30s)...")
        max_wait = 30
        waited = 0
        while waited < max_wait:
            time.sleep(2)
            waited += 2
            if check_service():
                print(f"   [OK] Service is responding! (waited {waited}s)")
                try:
                    health = requests.get(f"{SERVICE_URL}/health", timeout=5).json()
                    print(f"\n   Service Health:")
                    print(f"   - Status: {health.get('status')}")
                    print(f"   - Sources: {', '.join(health.get('available_sources', []))}")
                    print(f"   - Destinations: {', '.join(health.get('available_destinations', []))}")
                except:
                    pass
                print("\n" + "=" * 70)
                print("[SUCCESS] Service restarted successfully!")
                print("You can now retry your migration operation.")
                print("=" * 70)
                return True
            if waited % 5 == 0:
                print(f"   Waiting... ({waited}/{max_wait}s)")
        
        print(f"   [WARN] Service did not respond after {max_wait}s")
        print("\n   Manual start required:")
        print(f"   1. Open new terminal")
        print(f"   2. cd {SERVICE_DIR}")
        print(f"   3. python app.py")
    else:
        print("   [ERROR] Failed to start service")
    
    print("\n" + "=" * 70)
    return False

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[WARN] Interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()

