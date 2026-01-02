#!/usr/bin/env python3
"""
Diagnostic Tool for Migration Issues
Checks service status, connections, credentials, and generates diagnostic reports
"""

import requests
import sys
import socket
import time
import json
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

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

# Diagnostic results
diagnostic_results = {
    "timestamp": datetime.now().isoformat(),
    "service_status": {},
    "connections": {},
    "credentials": {},
    "network": {},
    "dependencies": {},
    "issues": [],
    "recommendations": []
}

def print_section_header(title: str):
    """Print formatted section header"""
    print(f"\n{'='*70}")
    print(f"{title}")
    print(f"{'='*70}\n")

def check_service_status() -> Dict[str, Any]:
    """Check Universal Migration Service status"""
    print_section_header("Service Status Check")
    
    result = {
        "available": False,
        "url": UNIVERSAL_MIGRATION_SERVICE_URL,
        "health_endpoint": None,
        "sources": [],
        "destinations": []
    }
    
    try:
        health_url = f"{UNIVERSAL_MIGRATION_SERVICE_URL}/health"
        response = requests.get(health_url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            result["available"] = True
            result["health_endpoint"] = data.get("status", "unknown")
            result["sources"] = data.get("available_sources", [])
            result["destinations"] = data.get("available_destinations", [])
            
            print(f"  ✓ Service is running")
            print(f"    Status: {result['health_endpoint']}")
            print(f"    Available sources: {', '.join(result['sources'])}")
            print(f"    Available destinations: {', '.join(result['destinations'])}")
        else:
            print(f"  ✗ Service returned status {response.status_code}")
            diagnostic_results["issues"].append(f"Service returned status {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print(f"  ✗ Service not reachable at {UNIVERSAL_MIGRATION_SERVICE_URL}")
        diagnostic_results["issues"].append(f"Service not reachable at {UNIVERSAL_MIGRATION_SERVICE_URL}")
        diagnostic_results["recommendations"].append("Start Universal Migration Service: python universal_migration_service/app.py")
    except Exception as e:
        print(f"  ✗ Error checking service: {str(e)}")
        diagnostic_results["issues"].append(f"Error checking service: {str(e)}")
    
    diagnostic_results["service_status"] = result
    return result

def check_connections() -> Dict[str, Any]:
    """Check all connections"""
    print_section_header("Connection Checks")
    
    result = {
        "zoho": {"connected": False, "error": None},
        "clickhouse": {"connected": False, "error": None}
    }
    
    # Check Zoho API connection
    print("  Checking Zoho API connection...")
    try:
        accounts_domain_map = {
            "https://www.zohoapis.in": "https://accounts.zoho.in",
        }
        accounts_domain = accounts_domain_map.get(ZOHO_CONFIG['api_domain'], "https://accounts.zoho.in")
        token_url = f"{accounts_domain}/oauth/v2/token"
        
        data = {
            "refresh_token": ZOHO_CONFIG['refresh_token'],
            "client_id": ZOHO_CONFIG['client_id'],
            "client_secret": ZOHO_CONFIG['client_secret'],
            "grant_type": "refresh_token"
        }
        
        response = requests.post(token_url, data=data, timeout=30)
        if response.status_code == 200:
            token_result = response.json()
            if token_result.get("access_token"):
                result["zoho"]["connected"] = True
                print(f"    ✓ Zoho API connection successful")
            else:
                result["zoho"]["error"] = "No access token in response"
                print(f"    ✗ Zoho API connection failed: No access token")
                diagnostic_results["issues"].append("Zoho API: No access token in response")
        else:
            result["zoho"]["error"] = f"Status {response.status_code}: {response.text[:100]}"
            print(f"    ✗ Zoho API connection failed: Status {response.status_code}")
            diagnostic_results["issues"].append(f"Zoho API: Status {response.status_code}")
    except Exception as e:
        result["zoho"]["error"] = str(e)
        print(f"    ✗ Zoho API connection error: {str(e)}")
        diagnostic_results["issues"].append(f"Zoho API: {str(e)}")
    
    # Check ClickHouse connection
    print("  Checking ClickHouse connection...")
    try:
        import clickhouse_connect
        client = clickhouse_connect.get_client(
            host=CLICKHOUSE_CONFIG['host'],
            port=CLICKHOUSE_CONFIG['port'],
            username=CLICKHOUSE_CONFIG['username'],
            password=CLICKHOUSE_CONFIG['password'],
            database=CLICKHOUSE_CONFIG['database']
        )
        result_query = client.query("SELECT 1")
        client.close()
        result["clickhouse"]["connected"] = True
        print(f"    ✓ ClickHouse connection successful")
    except ImportError:
        result["clickhouse"]["error"] = "clickhouse-connect not installed"
        print(f"    ✗ ClickHouse library not installed")
        diagnostic_results["issues"].append("ClickHouse: clickhouse-connect library not installed")
        diagnostic_results["recommendations"].append("Install clickhouse-connect: pip install clickhouse-connect")
    except Exception as e:
        result["clickhouse"]["error"] = str(e)
        print(f"    ✗ ClickHouse connection error: {str(e)}")
        diagnostic_results["issues"].append(f"ClickHouse: {str(e)}")
    
    diagnostic_results["connections"] = result
    return result

def check_credentials() -> Dict[str, Any]:
    """Check credential validity"""
    print_section_header("Credential Validation")
    
    result = {
        "zoho": {
            "refresh_token": {"valid": False, "error": None},
            "client_id": {"valid": False, "error": None},
            "client_secret": {"valid": False, "error": None},
            "api_domain": {"valid": False, "error": None}
        },
        "clickhouse": {
            "host": {"valid": False, "error": None},
            "port": {"valid": False, "error": None},
            "username": {"valid": False, "error": None},
            "password": {"valid": False, "error": None},
            "database": {"valid": False, "error": None}
        }
    }
    
    # Check Zoho credentials
    print("  Validating Zoho credentials...")
    if ZOHO_CONFIG.get('refresh_token'):
        result["zoho"]["refresh_token"]["valid"] = True
        print(f"    ✓ Refresh token provided")
    else:
        result["zoho"]["refresh_token"]["error"] = "Missing refresh token"
        print(f"    ✗ Refresh token missing")
        diagnostic_results["issues"].append("Zoho: Missing refresh token")
    
    if ZOHO_CONFIG.get('client_id'):
        result["zoho"]["client_id"]["valid"] = True
        print(f"    ✓ Client ID provided")
    else:
        result["zoho"]["client_id"]["error"] = "Missing client ID"
        print(f"    ✗ Client ID missing")
        diagnostic_results["issues"].append("Zoho: Missing client ID")
    
    if ZOHO_CONFIG.get('client_secret'):
        result["zoho"]["client_secret"]["valid"] = True
        print(f"    ✓ Client secret provided")
    else:
        result["zoho"]["client_secret"]["error"] = "Missing client secret"
        print(f"    ✗ Client secret missing")
        diagnostic_results["issues"].append("Zoho: Missing client secret")
    
    if ZOHO_CONFIG.get('api_domain'):
        result["zoho"]["api_domain"]["valid"] = True
        print(f"    ✓ API domain: {ZOHO_CONFIG['api_domain']}")
    else:
        result["zoho"]["api_domain"]["error"] = "Missing API domain"
        print(f"    ✗ API domain missing")
        diagnostic_results["issues"].append("Zoho: Missing API domain")
    
    # Check ClickHouse credentials
    print("  Validating ClickHouse credentials...")
    if CLICKHOUSE_CONFIG.get('host'):
        result["clickhouse"]["host"]["valid"] = True
        print(f"    ✓ Host: {CLICKHOUSE_CONFIG['host']}")
    else:
        result["clickhouse"]["host"]["error"] = "Missing host"
        print(f"    ✗ Host missing")
        diagnostic_results["issues"].append("ClickHouse: Missing host")
    
    if CLICKHOUSE_CONFIG.get('port'):
        result["clickhouse"]["port"]["valid"] = True
        print(f"    ✓ Port: {CLICKHOUSE_CONFIG['port']}")
    else:
        result["clickhouse"]["port"]["error"] = "Missing port"
        print(f"    ✗ Port missing")
        diagnostic_results["issues"].append("ClickHouse: Missing port")
    
    if CLICKHOUSE_CONFIG.get('username'):
        result["clickhouse"]["username"]["valid"] = True
        print(f"    ✓ Username: {CLICKHOUSE_CONFIG['username']}")
    else:
        result["clickhouse"]["username"]["error"] = "Missing username"
        print(f"    ✗ Username missing")
        diagnostic_results["issues"].append("ClickHouse: Missing username")
    
    if CLICKHOUSE_CONFIG.get('password'):
        result["clickhouse"]["password"]["valid"] = True
        print(f"    ✓ Password provided")
    else:
        result["clickhouse"]["password"]["error"] = "Missing password"
        print(f"    ✗ Password missing")
        diagnostic_results["issues"].append("ClickHouse: Missing password")
    
    if CLICKHOUSE_CONFIG.get('database'):
        result["clickhouse"]["database"]["valid"] = True
        print(f"    ✓ Database: {CLICKHOUSE_CONFIG['database']}")
    else:
        result["clickhouse"]["database"]["error"] = "Missing database"
        print(f"    ✗ Database missing")
        diagnostic_results["issues"].append("ClickHouse: Missing database")
    
    diagnostic_results["credentials"] = result
    return result

def check_network_connectivity() -> Dict[str, Any]:
    """Check network connectivity"""
    print_section_header("Network Connectivity Check")
    
    result = {
        "port_5011": {"accessible": False, "error": None},
        "clickhouse_port": {"accessible": False, "error": None},
        "zoho_api": {"accessible": False, "error": None}
    }
    
    # Check port 5011
    print("  Checking port 5011 (Universal Migration Service)...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result_check = sock.connect_ex(("localhost", 5011))
        sock.close()
        if result_check == 0:
            result["port_5011"]["accessible"] = True
            print(f"    ✓ Port 5011 is open")
        else:
            result["port_5011"]["error"] = "Port not accessible"
            print(f"    ✗ Port 5011 is not accessible")
            diagnostic_results["issues"].append("Port 5011: Not accessible (service may not be running)")
    except Exception as e:
        result["port_5011"]["error"] = str(e)
        print(f"    ✗ Error checking port 5011: {str(e)}")
    
    # Check ClickHouse port
    print(f"  Checking ClickHouse port {CLICKHOUSE_CONFIG['port']}...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result_check = sock.connect_ex((CLICKHOUSE_CONFIG['host'], CLICKHOUSE_CONFIG['port']))
        sock.close()
        if result_check == 0:
            result["clickhouse_port"]["accessible"] = True
            print(f"    ✓ Port {CLICKHOUSE_CONFIG['port']} is accessible")
        else:
            result["clickhouse_port"]["error"] = "Port not accessible"
            print(f"    ✗ Port {CLICKHOUSE_CONFIG['port']} is not accessible")
            diagnostic_results["issues"].append(f"ClickHouse port {CLICKHOUSE_CONFIG['port']}: Not accessible (may be blocked by firewall)")
    except Exception as e:
        result["clickhouse_port"]["error"] = str(e)
        print(f"    ✗ Error checking ClickHouse port: {str(e)}")
    
    # Check Zoho API
    print("  Checking Zoho API connectivity...")
    try:
        response = requests.get(ZOHO_CONFIG['api_domain'], timeout=10)
        result["zoho_api"]["accessible"] = True
        print(f"    ✓ Zoho API is reachable")
    except Exception as e:
        result["zoho_api"]["error"] = str(e)
        print(f"    ✗ Zoho API not reachable: {str(e)}")
        diagnostic_results["issues"].append(f"Zoho API: Not reachable - {str(e)}")
    
    diagnostic_results["network"] = result
    return result

def check_dependencies() -> Dict[str, Any]:
    """Check Python dependencies"""
    print_section_header("Dependency Check")
    
    result = {
        "flask": {"installed": False, "version": None},
        "clickhouse_connect": {"installed": False, "version": None},
        "requests": {"installed": False, "version": None},
        "psycopg2": {"installed": False, "version": None},
        "pymysql": {"installed": False, "version": None},
        "pyodbc": {"installed": False, "version": None}
    }
    
    dependencies = {
        "flask": "Flask",
        "clickhouse_connect": "clickhouse-connect",
        "requests": "requests",
        "psycopg2": "psycopg2-binary",
        "pymysql": "PyMySQL",
        "pyodbc": "pyodbc"
    }
    
    for key, package_name in dependencies.items():
        try:
            module = __import__(key.replace("-", "_"))
            version = getattr(module, "__version__", "unknown")
            result[key]["installed"] = True
            result[key]["version"] = version
            print(f"    ✓ {package_name}: {version}")
        except ImportError:
            result[key]["installed"] = False
            print(f"    ✗ {package_name}: Not installed")
            diagnostic_results["issues"].append(f"Missing dependency: {package_name}")
            diagnostic_results["recommendations"].append(f"Install {package_name}: pip install {package_name}")
    
    diagnostic_results["dependencies"] = result
    return result

def generate_report():
    """Generate diagnostic report"""
    print_section_header("Diagnostic Report")
    
    print(f"  Timestamp: {diagnostic_results['timestamp']}")
    print(f"  Total Issues Found: {len(diagnostic_results['issues'])}")
    print(f"  Recommendations: {len(diagnostic_results['recommendations'])}")
    
    if diagnostic_results["issues"]:
        print(f"\n  Issues:")
        for i, issue in enumerate(diagnostic_results["issues"], 1):
            print(f"    {i}. {issue}")
    
    if diagnostic_results["recommendations"]:
        print(f"\n  Recommendations:")
        for i, rec in enumerate(diagnostic_results["recommendations"], 1):
            print(f"    {i}. {rec}")
    
    # Save report to file
    report_file = f"diagnostic_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        with open(report_file, 'w') as f:
            json.dump(diagnostic_results, f, indent=2)
        print(f"\n  Report saved to: {report_file}")
    except Exception as e:
        print(f"\n  Could not save report: {str(e)}")

def main():
    """Run diagnostic checks"""
    print("="*70)
    print("MIGRATION DIAGNOSTIC TOOL")
    print("="*70)
    print("\nRunning comprehensive diagnostic checks...\n")
    
    # Run all checks
    check_service_status()
    check_connections()
    check_credentials()
    check_network_connectivity()
    check_dependencies()
    
    # Generate report
    generate_report()
    
    # Return exit code
    if len(diagnostic_results["issues"]) == 0:
        print("\n✓ No issues found. System is ready for migration.")
        return 0
    else:
        print(f"\n✗ Found {len(diagnostic_results['issues'])} issue(s). Please review and fix.")
        return 1

if __name__ == '__main__':
    sys.exit(main())

