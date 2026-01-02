#!/usr/bin/env python3
"""
Comprehensive Connection Testing Script
Tests Zoho API, ClickHouse, and Universal Migration Service connections
"""

import requests
import sys
import os
import socket
import time
from typing import Dict, Any, Tuple
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()

# Force UTF-8 encoding for stdout
sys.stdout.reconfigure(encoding='utf-8')

# Configuration from environment variables
ZOHO_CONFIG = {
    "refresh_token": os.getenv('ZOHO_REFRESH_TOKEN', ''),
    "client_id": os.getenv('ZOHO_CLIENT_ID', ''),
    "client_secret": os.getenv('ZOHO_CLIENT_SECRET', ''),
    "api_domain": os.getenv('ZOHO_API_DOMAIN', 'https://www.zohoapis.com')
}

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

# Test results tracking
test_results = {
    "passed": [],
    "failed": [],
    "warnings": []
}

def print_section_header(title: str):
    """Print formatted section header"""
    print(f"\n{'='*70}")
    print(f"{title}")
    print(f"{'='*70}\n")

def print_test_result(test_name: str, passed: bool, message: str = "", warning: bool = False):
    """Print test result and track it"""
    status = "✓ PASS" if passed else ("⚠ WARN" if warning else "✗ FAIL")
    print(f"  [{status}] {test_name}")
    if message:
        print(f"      {message}")
    
    if passed:
        test_results["passed"].append(test_name)
    elif warning:
        test_results["warnings"].append(test_name)
    else:
        test_results["failed"].append(test_name)

def test_port_connectivity(host: str, port: int, timeout: int = 5) -> bool:
    """Test if a port is accessible"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        return False

def test_zoho_api_connection() -> Tuple[bool, str]:
    """Test 2.1.1: Zoho API Connection"""
    print_section_header("Test 2.1.1: Zoho API Connection")
    
    try:
        # Test API domain accessibility
        api_domain = ZOHO_CONFIG['api_domain']
        print(f"  Testing API domain: {api_domain}")
        
        try:
            response = requests.get(api_domain, timeout=10)
            print_test_result("API Domain Reachable", True, f"Status: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print_test_result("API Domain Reachable", False, f"Error: {str(e)}")
            return False, f"API domain not reachable: {str(e)}"
        
        # Test token refresh
        accounts_domain_map = {
            "https://www.zohoapis.in": "https://accounts.zoho.in",
            "https://www.zohoapis.com": "https://accounts.zoho.com",
            "https://www.zohoapis.eu": "https://accounts.zoho.eu",
            "https://www.zohoapis.com.au": "https://accounts.zoho.com.au",
            "https://www.zohoapis.jp": "https://accounts.zoho.jp",
        }
        
        accounts_domain = accounts_domain_map.get(api_domain, "https://accounts.zoho.in")
        token_url = f"{accounts_domain}/oauth/v2/token"
        
        print(f"  Testing token refresh at: {token_url}")
        
        data = {
            "refresh_token": ZOHO_CONFIG['refresh_token'],
            "client_id": ZOHO_CONFIG['client_id'],
            "client_secret": ZOHO_CONFIG['client_secret'],
            "grant_type": "refresh_token"
        }
        
        try:
            response = requests.post(token_url, data=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                access_token = result.get("access_token")
                if access_token:
                    print_test_result("Refresh Token Valid", True, f"Access token obtained (expires in {result.get('expires_in', 'unknown')}s)")
                    print_test_result("Client ID/Secret Valid", True)
                    return True, "All Zoho API connection tests passed"
                else:
                    print_test_result("Refresh Token Valid", False, "No access token in response")
                    return False, "Token refresh failed: No access token"
            else:
                error_msg = response.text[:200]
                print_test_result("Refresh Token Valid", False, f"Status {response.status_code}: {error_msg}")
                return False, f"Token refresh failed: {response.status_code}"
                
        except requests.exceptions.Timeout:
            print_test_result("Token Refresh", False, "Request timeout")
            return False, "Token refresh timeout"
        except requests.exceptions.RequestException as e:
            print_test_result("Token Refresh", False, f"Error: {str(e)}")
            return False, f"Token refresh error: {str(e)}"
            
    except Exception as e:
        print_test_result("Zoho API Connection", False, f"Unexpected error: {str(e)}")
        return False, f"Unexpected error: {str(e)}"

def test_clickhouse_connection() -> Tuple[bool, str]:
    """Test 2.1.2: ClickHouse Connection"""
    print_section_header("Test 2.1.2: ClickHouse Connection")
    
    try:
        host = CLICKHOUSE_CONFIG['host']
        port = CLICKHOUSE_CONFIG['port']
        
        # Test host reachability
        print(f"  Testing host: {host}:{port}")
        
        if test_port_connectivity(host, port, timeout=5):
            print_test_result("Host Reachable", True, f"{host}:{port} is accessible")
        else:
            print_test_result("Host Reachable", False, f"Cannot connect to {host}:{port}")
            return False, f"Host {host}:{port} not reachable"
        
        # Test authentication and query execution
        try:
            import clickhouse_connect
            
            print(f"  Testing authentication...")
            client = clickhouse_connect.get_client(
                host=host,
                port=port,
                username=CLICKHOUSE_CONFIG['username'],
                password=CLICKHOUSE_CONFIG['password'],
                database=CLICKHOUSE_CONFIG['database']
            )
            
            print_test_result("Authentication", True, f"Connected as {CLICKHOUSE_CONFIG['username']}")
            
            # Test database existence
            try:
                result = client.query("SELECT 1")
                print_test_result("Database Access", True, f"Database '{CLICKHOUSE_CONFIG['database']}' is accessible")
            except Exception as e:
                print_test_result("Database Access", False, f"Error: {str(e)}")
                client.close()
                return False, f"Database access failed: {str(e)}"
            
            # Test query execution
            try:
                result = client.query("SELECT version()")
                version = result.result_rows[0][0] if result.result_rows else "unknown"
                print_test_result("Query Execution", True, f"ClickHouse version: {version}")
            except Exception as e:
                print_test_result("Query Execution", False, f"Error: {str(e)}")
                client.close()
                return False, f"Query execution failed: {str(e)}"
            
            client.close()
            return True, "All ClickHouse connection tests passed"
            
        except ImportError:
            print_test_result("ClickHouse Library", False, "clickhouse-connect not installed")
            return False, "clickhouse-connect library not available"
        except Exception as e:
            print_test_result("ClickHouse Connection", False, f"Error: {str(e)}")
            return False, f"Connection error: {str(e)}"
            
    except Exception as e:
        print_test_result("ClickHouse Connection", False, f"Unexpected error: {str(e)}")
        return False, f"Unexpected error: {str(e)}"

def test_service_health() -> Tuple[bool, str]:
    """Test 2.1.3: Service Health"""
    print_section_header("Test 2.1.3: Universal Migration Service Health")
    
    try:
        # Test service health endpoint
        health_url = f"{UNIVERSAL_MIGRATION_SERVICE_URL}/health"
        print(f"  Testing service at: {health_url}")
        
        try:
            response = requests.get(health_url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                print_test_result("Service Health Endpoint", True, f"Status: {data.get('status', 'unknown')}")
                
                available_sources = data.get('available_sources', [])
                available_destinations = data.get('available_destinations', [])
                
                print_test_result("Available Sources", True, f"{len(available_sources)} sources: {', '.join(available_sources)}")
                print_test_result("Available Destinations", True, f"{len(available_destinations)} destinations: {', '.join(available_destinations)}")
                
                # Check if zoho and clickhouse are available
                if 'zoho' in available_sources:
                    print_test_result("Zoho Source Registered", True)
                else:
                    print_test_result("Zoho Source Registered", False, "Zoho source not found in available sources")
                
                if 'clickhouse' in available_destinations:
                    print_test_result("ClickHouse Destination Registered", True)
                else:
                    print_test_result("ClickHouse Destination Registered", False, "ClickHouse destination not found")
                
                return True, "Service health check passed"
            else:
                print_test_result("Service Health Endpoint", False, f"Status code: {response.status_code}")
                return False, f"Service returned status {response.status_code}"
                
        except requests.exceptions.ConnectionError:
            print_test_result("Service Reachable", False, f"Cannot connect to {UNIVERSAL_MIGRATION_SERVICE_URL}")
            return False, "Service not reachable"
        except requests.exceptions.Timeout:
            print_test_result("Service Response", False, "Request timeout")
            return False, "Service timeout"
        except Exception as e:
            print_test_result("Service Health", False, f"Error: {str(e)}")
            return False, f"Error: {str(e)}"
            
    except Exception as e:
        print_test_result("Service Health", False, f"Unexpected error: {str(e)}")
        return False, f"Unexpected error: {str(e)}"

def test_network_connectivity() -> Tuple[bool, str]:
    """Test 2.2: Network Connectivity"""
    print_section_header("Test 2.2: Network Connectivity")
    
    # Test port 5011 (Universal Migration Service)
    print(f"  Testing port 5011 (Universal Migration Service)...")
    if test_port_connectivity("localhost", 5011, timeout=2):
        print_test_result("Port 5011 Available", True, "Universal Migration Service port is open")
    else:
        print_test_result("Port 5011 Available", False, "Port 5011 is not accessible (service may not be running)", warning=True)
    
    # Test port 8123 (ClickHouse)
    print(f"  Testing port 8123 (ClickHouse)...")
    ch_host = CLICKHOUSE_CONFIG['host']
    ch_port = CLICKHOUSE_CONFIG['port']
    if test_port_connectivity(ch_host, ch_port, timeout=5):
        print_test_result(f"Port {ch_port} Accessible", True, f"{ch_host}:{ch_port} is reachable")
    else:
        print_test_result(f"Port {ch_port} Accessible", False, f"Cannot reach {ch_host}:{ch_port} (may be blocked by firewall)")
    
    # Test outbound connections
    print(f"  Testing outbound connections...")
    try:
        # Test Zoho API
        response = requests.get("https://www.zohoapis.in", timeout=10)
        print_test_result("Zoho API Outbound", True, f"Status: {response.status_code}")
    except Exception as e:
        print_test_result("Zoho API Outbound", False, f"Error: {str(e)}")
    
    return True, "Network connectivity tests completed"

def print_summary():
    """Print test summary"""
    print_section_header("Test Summary")
    
    total = len(test_results["passed"]) + len(test_results["failed"]) + len(test_results["warnings"])
    
    print(f"  Total Tests: {total}")
    print(f"  Passed: {len(test_results['passed'])}")
    print(f"  Failed: {len(test_results['failed'])}")
    print(f"  Warnings: {len(test_results['warnings'])}")
    
    if test_results["failed"]:
        print(f"\n  Failed Tests:")
        for test in test_results["failed"]:
            print(f"    - {test}")
    
    if test_results["warnings"]:
        print(f"\n  Warnings:")
        for test in test_results["warnings"]:
            print(f"    - {test}")
    
    success_rate = (len(test_results["passed"]) / total * 100) if total > 0 else 0
    print(f"\n  Success Rate: {success_rate:.1f}%")
    
    if len(test_results["failed"]) == 0:
        print("\n  ✓ All critical tests passed!")
    else:
        print("\n  ✗ Some tests failed. Please review the errors above.")

def main():
    """Run all connection tests"""
    print("="*70)
    print("COMPREHENSIVE CONNECTION TESTING")
    print("="*70)
    print("\nThis script tests:")
    print("  - Zoho API connection and authentication")
    print("  - ClickHouse connection and authentication")
    print("  - Universal Migration Service health")
    print("  - Network connectivity")
    print("\nStarting tests...\n")
    
    # Run all tests
    test_zoho_api_connection()
    test_clickhouse_connection()
    test_service_health()
    test_network_connectivity()
    
    # Print summary
    print_summary()
    
    # Return exit code
    if len(test_results["failed"]) == 0:
        return 0
    else:
        return 1

if __name__ == '__main__':
    sys.exit(main())

