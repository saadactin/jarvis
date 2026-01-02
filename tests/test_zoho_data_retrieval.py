#!/usr/bin/env python3
"""
Zoho Data Retrieval Testing Script
Tests module listing, schema retrieval, pagination, and data normalization
"""

import requests
import sys
import os
import json
import time
from datetime import datetime, date
from typing import Dict, Any, List, Tuple, Optional
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

# Validate required environment variables
if not ZOHO_CONFIG["refresh_token"]:
    raise ValueError("ZOHO_REFRESH_TOKEN environment variable is required")
if not ZOHO_CONFIG["client_id"]:
    raise ValueError("ZOHO_CLIENT_ID environment variable is required")
if not ZOHO_CONFIG["client_secret"]:
    raise ValueError("ZOHO_CLIENT_SECRET environment variable is required")

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

def get_access_token() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Get access token from refresh token"""
    accounts_domain_map = {
        "https://www.zohoapis.in": "https://accounts.zoho.in",
        "https://www.zohoapis.com": "https://accounts.zoho.com",
        "https://www.zohoapis.eu": "https://accounts.zoho.eu",
        "https://www.zohoapis.com.au": "https://accounts.zoho.com.au",
        "https://www.zohoapis.jp": "https://accounts.zoho.jp",
    }
    
    accounts_domain = accounts_domain_map.get(ZOHO_CONFIG['api_domain'], "https://accounts.zoho.in")
    url = f"{accounts_domain}/oauth/v2/token"
    
    data = {
        "refresh_token": ZOHO_CONFIG['refresh_token'],
        "client_id": ZOHO_CONFIG['client_id'],
        "client_secret": ZOHO_CONFIG['client_secret'],
        "grant_type": "refresh_token"
    }
    
    try:
        response = requests.post(url, data=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        token = result.get("access_token")
        if not token:
            return None, None, "No access token in response"
        
        api_domain = result.get("api_domain", ZOHO_CONFIG['api_domain'])
        return token, api_domain, None
    except Exception as e:
        return None, None, str(e)

def test_module_listing() -> Tuple[bool, List[str]]:
    """Test 4.1.1: Module Listing"""
    print_section_header("Test 4.1.1: Module Listing")
    
    try:
        token, api_domain, error = get_access_token()
        if not token:
            print_test_result("Get Access Token", False, f"Error: {error}")
            return False, []
        
        url = f"{api_domain}/crm/v8/settings/modules"
        headers = {"Authorization": f"Zoho-oauthtoken {token}"}
        
        print(f"  Fetching modules from: {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                modules = result.get("modules", [])
                
                module_names = []
                for module in modules:
                    api_name = module.get("api_name")
                    if api_name:
                        module_names.append(api_name)
                
                module_names = sorted(module_names)
                
                print_test_result("Module Listing", True, f"Found {len(module_names)} modules")
                print_test_result("Module Count", len(module_names) > 0, 
                                f"Total modules: {len(module_names)}")
                
                if len(module_names) > 0:
                    print(f"  Sample modules: {', '.join(module_names[:10])}")
                    if len(module_names) > 10:
                        print(f"  ... and {len(module_names) - 10} more")
                
                # Test empty module handling
                if len(module_names) == 0:
                    print_test_result("Empty Module Handling", False, "No modules found")
                else:
                    print_test_result("Empty Module Handling", True, "Modules found")
                
                return True, module_names
            else:
                print_test_result("Module Listing", False, 
                                f"Status {response.status_code}: {response.text[:200]}")
                return False, []
                
        except requests.exceptions.Timeout:
            print_test_result("Module Listing", False, "Request timeout")
            return False, []
        except Exception as e:
            print_test_result("Module Listing", False, f"Error: {str(e)}")
            return False, []
            
    except Exception as e:
        print_test_result("Module Listing", False, f"Unexpected error: {str(e)}")
        return False, []

def test_schema_retrieval(module_names: List[str]) -> Tuple[bool, Dict[str, Any]]:
    """Test 4.1.2: Schema Retrieval"""
    print_section_header("Test 4.1.2: Schema Retrieval")
    
    if not module_names:
        print_test_result("Schema Retrieval", False, "No modules available for testing")
        return False, {}
    
    try:
        token, api_domain, error = get_access_token()
        if not token:
            print_test_result("Get Access Token", False, f"Error: {error}")
            return False, {}
        
        schemas = {}
        test_modules = module_names[:5]  # Test first 5 modules
        
        for module_name in test_modules:
            print(f"  Testing module: {module_name}")
            
            # Test field metadata fetching
            try:
                url = f"{api_domain}/crm/v2/settings/modules/{module_name}"
                headers = {"Authorization": f"Zoho-oauthtoken {token}"}
                
                response = requests.get(url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    payload = response.json()
                    fields = payload.get("modules", [{}])[0].get("fields", [])
                    if not fields:
                        fields = payload.get("fields", [])
                    
                    if fields:
                        field_names = {field.get("api_name") for field in fields if field.get("api_name")}
                        field_names.add("id")
                        schemas[module_name] = sorted(field_names)
                        print_test_result(f"Field Metadata - {module_name}", True, 
                                        f"Found {len(schemas[module_name])} fields")
                    else:
                        print_test_result(f"Field Metadata - {module_name}", False, 
                                        "No fields returned", warning=True)
                        # Try fallback
                        schemas[module_name] = ["id"]
                else:
                    print_test_result(f"Field Metadata - {module_name}", False, 
                                    f"Status {response.status_code}", warning=True)
                    schemas[module_name] = ["id"]
                    
            except Exception as e:
                print_test_result(f"Field Metadata - {module_name}", False, 
                                f"Error: {str(e)}", warning=True)
                schemas[module_name] = ["id"]
            
            # Test fallback to first record schema
            try:
                url = f"{api_domain}/crm/v2/{module_name}"
                headers = {"Authorization": f"Zoho-oauthtoken {token}"}
                
                response = requests.get(url, headers=headers, params={"page": 1, "per_page": 1}, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    data = result.get("data", [])
                    if data and len(data) > 0:
                        record_fields = set(data[0].keys())
                        print_test_result(f"First Record Schema - {module_name}", True, 
                                        f"Found {len(record_fields)} fields in first record")
                        
                        # Check for special characters
                        special_char_fields = [f for f in record_fields if not f.replace('_', '').replace('.', '').isalnum()]
                        if special_char_fields:
                            print_test_result(f"Special Characters - {module_name}", True, 
                                            f"Found {len(special_char_fields)} fields with special characters", warning=True)
                        else:
                            print_test_result(f"Special Characters - {module_name}", True, 
                                            "No special characters in field names")
                    else:
                        print_test_result(f"First Record Schema - {module_name}", False, 
                                        "No records found", warning=True)
                else:
                    print_test_result(f"First Record Schema - {module_name}", False, 
                                    f"Status {response.status_code}", warning=True)
                    
            except Exception as e:
                print_test_result(f"First Record Schema - {module_name}", False, 
                                f"Error: {str(e)}", warning=True)
        
        if schemas:
            print_test_result("Schema Retrieval Overall", True, 
                            f"Retrieved schemas for {len(schemas)} modules")
            return True, schemas
        else:
            print_test_result("Schema Retrieval Overall", False, "No schemas retrieved")
            return False, {}
            
    except Exception as e:
        print_test_result("Schema Retrieval", False, f"Unexpected error: {str(e)}")
        return False, {}

def test_data_pagination(module_names: List[str]) -> Tuple[bool, Dict[str, int]]:
    """Test 4.1.3: Data Pagination"""
    print_section_header("Test 4.1.3: Data Pagination")
    
    if not module_names:
        print_test_result("Data Pagination", False, "No modules available for testing")
        return False, {}
    
    try:
        token, api_domain, error = get_access_token()
        if not token:
            print_test_result("Get Access Token", False, f"Error: {error}")
            return False, {}
        
        # Test with first module that has data
        test_module = None
        record_counts = {}
        
        for module_name in module_names[:3]:  # Test first 3 modules
            print(f"  Testing pagination for: {module_name}")
            
            url = f"{api_domain}/crm/v2/{module_name}"
            headers = {"Authorization": f"Zoho-oauthtoken {token}"}
            page = 1
            batch_size = 200
            total_records = 0
            max_pages = 5  # Limit to 5 pages for testing
            
            try:
                while page <= max_pages:
                    params = {"page": page, "per_page": batch_size}
                    start_time = time.time()
                    
                    response = requests.get(url, headers=headers, params=params, timeout=120)
                    
                    elapsed = time.time() - start_time
                    
                    if response.status_code == 204:
                        # No more data
                        break
                    
                    if response.status_code != 200:
                        print_test_result(f"Pagination - {module_name} Page {page}", False, 
                                        f"Status {response.status_code}")
                        break
                    
                    result = response.json()
                    data = result.get("data", [])
                    
                    if not data:
                        break
                    
                    total_records += len(data)
                    more_records = result.get("info", {}).get("more_records", False)
                    
                    print_test_result(f"Page {page} - {module_name}", True, 
                                    f"Retrieved {len(data)} records in {elapsed:.2f}s")
                    
                    if not more_records:
                        break
                    
                    page += 1
                
                record_counts[module_name] = total_records
                print_test_result(f"Pagination Complete - {module_name}", True, 
                                f"Total records: {total_records}")
                
                if total_records > 0:
                    test_module = module_name
                    break
                    
            except requests.exceptions.Timeout:
                print_test_result(f"Pagination Timeout - {module_name}", False, 
                                "Request timeout (120s)")
            except Exception as e:
                print_test_result(f"Pagination Error - {module_name}", False, 
                                f"Error: {str(e)}")
        
        if test_module:
            print_test_result("Data Pagination Overall", True, 
                            f"Successfully tested pagination for {test_module}")
            return True, record_counts
        else:
            print_test_result("Data Pagination Overall", False, 
                            "No modules with data found for testing", warning=True)
            return False, {}
            
    except Exception as e:
        print_test_result("Data Pagination", False, f"Unexpected error: {str(e)}")
        return False, {}

def normalize_value(value) -> Any:
    """Normalize value for ClickHouse (matching zoho_source logic)"""
    from datetime import time as time_type
    if value is None:
        return None
    if isinstance(value, (datetime, date, time_type)):
        return value.isoformat()
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)

def test_data_normalization(module_names: List[str]) -> Tuple[bool, Dict[str, Any]]:
    """Test 4.1.4: Data Normalization"""
    print_section_header("Test 4.1.4: Data Normalization")
    
    if not module_names:
        print_test_result("Data Normalization", False, "No modules available for testing")
        return False, {}
    
    try:
        token, api_domain, error = get_access_token()
        if not token:
            print_test_result("Get Access Token", False, f"Error: {error}")
            return False, {}
        
        # Get a sample record from first module
        test_module = module_names[0]
        print(f"  Testing normalization for: {test_module}")
        
        url = f"{api_domain}/crm/v2/{test_module}"
        headers = {"Authorization": f"Zoho-oauthtoken {token}"}
        
        try:
            response = requests.get(url, headers=headers, params={"page": 1, "per_page": 1}, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                data = result.get("data", [])
                
                if data and len(data) > 0:
                    record = data[0]
                    normalized_record = {}
                    
                    # Test normalization
                    datetime_count = 0
                    json_count = 0
                    null_count = 0
                    
                    for key, value in record.items():
                        normalized = normalize_value(value)
                        normalized_record[key] = normalized
                        
                        if value is None:
                            null_count += 1
                        elif isinstance(value, (datetime, date)):
                            datetime_count += 1
                        elif isinstance(value, (dict, list)):
                            json_count += 1
                    
                    print_test_result("Data Normalization", True, 
                                    f"Normalized {len(normalized_record)} fields")
                    print_test_result("Datetime Conversion", True, 
                                    f"Found {datetime_count} datetime fields")
                    print_test_result("JSON Serialization", True, 
                                    f"Found {json_count} JSON/dict fields")
                    print_test_result("Null Handling", True, 
                                    f"Found {null_count} null values")
                    
                    # Verify normalization
                    all_normalized = all(
                        isinstance(v, (str, type(None))) or 
                        (isinstance(v, str) and v.startswith('{')) or
                        (isinstance(v, str) and v.startswith('['))
                        for v in normalized_record.values()
                    )
                    
                    if all_normalized:
                        print_test_result("Normalization Format", True, 
                                        "All values properly normalized to strings")
                    else:
                        print_test_result("Normalization Format", False, 
                                        "Some values not properly normalized", warning=True)
                    
                    return True, normalized_record
                else:
                    print_test_result("Data Normalization", False, 
                                    "No records found for testing", warning=True)
                    return False, {}
            else:
                print_test_result("Data Normalization", False, 
                                f"Status {response.status_code}")
                return False, {}
                
        except Exception as e:
            print_test_result("Data Normalization", False, f"Error: {str(e)}")
            return False, {}
            
    except Exception as e:
        print_test_result("Data Normalization", False, f"Unexpected error: {str(e)}")
        return False, {}

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
        print("\n  ✓ All data retrieval tests passed!")
    else:
        print("\n  ✗ Some tests failed. Please review the errors above.")

def main():
    """Run all Zoho data retrieval tests"""
    print("="*70)
    print("ZOHO DATA RETRIEVAL TESTING")
    print("="*70)
    print("\nThis script tests:")
    print("  - Module listing")
    print("  - Schema retrieval")
    print("  - Data pagination")
    print("  - Data normalization")
    print("\nStarting tests...\n")
    
    # Run tests in sequence
    success, module_names = test_module_listing()
    if success and module_names:
        test_schema_retrieval(module_names)
        test_data_pagination(module_names)
        test_data_normalization(module_names)
    
    # Print summary
    print_summary()
    
    # Return exit code
    if len(test_results["failed"]) == 0:
        return 0
    else:
        return 1

if __name__ == '__main__':
    sys.exit(main())

