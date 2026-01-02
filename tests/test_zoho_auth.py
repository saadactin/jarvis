#!/usr/bin/env python3
"""
Zoho Authentication Testing Script
Tests refresh token validation, API domain configuration, and token refresh mechanism
"""

import requests
import sys
import os
import time
from typing import Dict, Any, Tuple, Optional
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

def get_access_token(refresh_token: str, client_id: str, client_secret: str, api_domain: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Get access token from refresh token"""
    accounts_domain_map = {
        "https://www.zohoapis.in": "https://accounts.zoho.in",
        "https://www.zohoapis.com": "https://accounts.zoho.com",
        "https://www.zohoapis.eu": "https://accounts.zoho.eu",
        "https://www.zohoapis.com.au": "https://accounts.zoho.com.au",
        "https://www.zohoapis.jp": "https://accounts.zoho.jp",
    }
    
    accounts_domain = accounts_domain_map.get(api_domain, "https://accounts.zoho.in")
    url = f"{accounts_domain}/oauth/v2/token"
    
    data = {
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token"
    }
    
    try:
        response = requests.post(url, data=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        token = result.get("access_token")
        if not token:
            return None, "No access token in response"
        
        response_api_domain = result.get("api_domain")
        if response_api_domain:
            api_domain = response_api_domain
        
        return {
            "access_token": token,
            "expires_in": result.get("expires_in", 3600),
            "api_domain": api_domain,
            "token_type": result.get("token_type", "Bearer")
        }, None
    except requests.exceptions.HTTPError as e:
        return None, f"HTTP {e.response.status_code}: {e.response.text[:200]}"
    except Exception as e:
        return None, str(e)

def test_refresh_token_validation() -> Tuple[bool, str]:
    """Test 3.1.1: Refresh Token Validation"""
    print_section_header("Test 3.1.1: Refresh Token Validation")
    
    try:
        # Test with provided refresh token
        print(f"  Testing refresh token: {ZOHO_CONFIG['refresh_token'][:20]}...")
        
        token_result, error = get_access_token(
            ZOHO_CONFIG['refresh_token'],
            ZOHO_CONFIG['client_id'],
            ZOHO_CONFIG['client_secret'],
            ZOHO_CONFIG['api_domain']
        )
        
        if token_result:
            expires_in = token_result.get('expires_in', 0)
            print_test_result("Refresh Token Valid", True, 
                            f"Access token obtained (expires in {expires_in}s)")
            print_test_result("Access Token Format", True, 
                            f"Token length: {len(token_result['access_token'])} characters")
            return True, "Refresh token validation passed"
        else:
            print_test_result("Refresh Token Valid", False, f"Error: {error}")
            return False, f"Refresh token validation failed: {error}"
            
    except Exception as e:
        print_test_result("Refresh Token Validation", False, f"Unexpected error: {str(e)}")
        return False, f"Unexpected error: {str(e)}"

def test_api_domain_configuration() -> Tuple[bool, str]:
    """Test 3.1.2: API Domain Configuration"""
    print_section_header("Test 3.1.2: API Domain Configuration")
    
    try:
        api_domain = ZOHO_CONFIG['api_domain']
        print(f"  Testing API domain: {api_domain}")
        
        # Test India domain
        if api_domain == "https://www.zohoapis.in":
            print_test_result("India Domain", True, "Using India API domain")
        else:
            print_test_result("India Domain", False, f"Expected India domain, got: {api_domain}", warning=True)
        
        # Test token refresh with correct accounts domain
        accounts_domain_map = {
            "https://www.zohoapis.in": "https://accounts.zoho.in",
            "https://www.zohoapis.com": "https://accounts.zoho.com",
            "https://www.zohoapis.eu": "https://accounts.zoho.eu",
            "https://www.zohoapis.com.au": "https://accounts.zoho.com.au",
            "https://www.zohoapis.jp": "https://accounts.zoho.jp",
        }
        
        expected_accounts_domain = accounts_domain_map.get(api_domain)
        if expected_accounts_domain:
            print_test_result("Accounts Domain Mapping", True, 
                            f"Correctly mapped to {expected_accounts_domain}")
        else:
            print_test_result("Accounts Domain Mapping", False, 
                            f"Unknown API domain: {api_domain}", warning=True)
        
        # Test token refresh
        token_result, error = get_access_token(
            ZOHO_CONFIG['refresh_token'],
            ZOHO_CONFIG['client_id'],
            ZOHO_CONFIG['client_secret'],
            api_domain
        )
        
        if token_result:
            returned_api_domain = token_result.get('api_domain')
            if returned_api_domain:
                print_test_result("API Domain Returned", True, 
                                f"Server returned API domain: {returned_api_domain}")
                if returned_api_domain != api_domain:
                    print_test_result("API Domain Match", False, 
                                    f"Expected {api_domain}, got {returned_api_domain}", warning=True)
                else:
                    print_test_result("API Domain Match", True, "API domain matches")
            else:
                print_test_result("API Domain Returned", False, "No API domain in response", warning=True)
            
            return True, "API domain configuration test passed"
        else:
            print_test_result("Token Refresh", False, f"Error: {error}")
            return False, f"Token refresh failed: {error}"
            
    except Exception as e:
        print_test_result("API Domain Configuration", False, f"Unexpected error: {str(e)}")
        return False, f"Unexpected error: {str(e)}"

def test_token_refresh_during_migration() -> Tuple[bool, str]:
    """Test 3.1.3: Token Refresh During Migration"""
    print_section_header("Test 3.1.3: Token Refresh During Migration")
    
    try:
        # Get initial token
        print("  Getting initial access token...")
        token_result1, error1 = get_access_token(
            ZOHO_CONFIG['refresh_token'],
            ZOHO_CONFIG['client_id'],
            ZOHO_CONFIG['client_secret'],
            ZOHO_CONFIG['api_domain']
        )
        
        if not token_result1:
            print_test_result("Initial Token", False, f"Error: {error1}")
            return False, f"Failed to get initial token: {error1}"
        
        print_test_result("Initial Token", True, "Initial token obtained")
        initial_token = token_result1['access_token']
        
        # Test API call with token
        print("  Testing API call with token...")
        api_domain = token_result1.get('api_domain', ZOHO_CONFIG['api_domain'])
        url = f"{api_domain}/crm/v8/settings/modules"
        headers = {"Authorization": f"Zoho-oauthtoken {initial_token}"}
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                print_test_result("API Call with Token", True, "Successfully called Zoho API")
            elif response.status_code == 401:
                print_test_result("API Call with Token", False, "Token expired or invalid")
                # This is expected - test token refresh
                print("  Token expired, testing automatic refresh...")
            else:
                print_test_result("API Call with Token", False, 
                                f"Unexpected status: {response.status_code}")
        except Exception as e:
            print_test_result("API Call", False, f"Error: {str(e)}")
        
        # Simulate token expiration by getting a new token
        print("  Simulating token refresh...")
        token_result2, error2 = get_access_token(
            ZOHO_CONFIG['refresh_token'],
            ZOHO_CONFIG['client_id'],
            ZOHO_CONFIG['client_secret'],
            ZOHO_CONFIG['api_domain']
        )
        
        if not token_result2:
            print_test_result("Token Refresh", False, f"Error: {error2}")
            return False, f"Token refresh failed: {error2}"
        
        print_test_result("Token Refresh", True, "Token refreshed successfully")
        
        # Verify new token is different (usually)
        new_token = token_result2['access_token']
        if new_token != initial_token:
            print_test_result("Token Uniqueness", True, "New token is different from initial token")
        else:
            print_test_result("Token Uniqueness", False, "New token is same as initial token", warning=True)
        
        # Test API call with new token
        print("  Testing API call with refreshed token...")
        headers = {"Authorization": f"Zoho-oauthtoken {new_token}"}
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                print_test_result("API Call with Refreshed Token", True, "Successfully called Zoho API with refreshed token")
                return True, "Token refresh during migration test passed"
            else:
                print_test_result("API Call with Refreshed Token", False, 
                                f"Status: {response.status_code}")
                return False, f"API call failed with status {response.status_code}"
        except Exception as e:
            print_test_result("API Call with Refreshed Token", False, f"Error: {str(e)}")
            return False, f"API call error: {str(e)}"
            
    except Exception as e:
        print_test_result("Token Refresh During Migration", False, f"Unexpected error: {str(e)}")
        return False, f"Unexpected error: {str(e)}"

def test_client_credentials() -> Tuple[bool, str]:
    """Test client ID and secret validation"""
    print_section_header("Test: Client Credentials Validation")
    
    try:
        # Test with valid credentials
        token_result, error = get_access_token(
            ZOHO_CONFIG['refresh_token'],
            ZOHO_CONFIG['client_id'],
            ZOHO_CONFIG['client_secret'],
            ZOHO_CONFIG['api_domain']
        )
        
        if token_result:
            print_test_result("Client ID Valid", True, f"Client ID: {ZOHO_CONFIG['client_id'][:20]}...")
            print_test_result("Client Secret Valid", True, "Client secret accepted")
            return True, "Client credentials are valid"
        else:
            if "invalid_client" in str(error).lower() or "invalid" in str(error).lower():
                print_test_result("Client Credentials", False, "Invalid client ID or secret")
            else:
                print_test_result("Client Credentials", False, f"Error: {error}")
            return False, f"Client credentials validation failed: {error}"
            
    except Exception as e:
        print_test_result("Client Credentials", False, f"Unexpected error: {str(e)}")
        return False, f"Unexpected error: {str(e)}"

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
        print("\n  ✓ All authentication tests passed!")
    else:
        print("\n  ✗ Some tests failed. Please review the errors above.")

def main():
    """Run all Zoho authentication tests"""
    print("="*70)
    print("ZOHO AUTHENTICATION TESTING")
    print("="*70)
    print("\nThis script tests:")
    print("  - Refresh token validation")
    print("  - API domain configuration")
    print("  - Token refresh mechanism")
    print("  - Client credentials validation")
    print("\nStarting tests...\n")
    
    # Run all tests
    test_refresh_token_validation()
    test_api_domain_configuration()
    test_token_refresh_during_migration()
    test_client_credentials()
    
    # Print summary
    print_summary()
    
    # Return exit code
    if len(test_results["failed"]) == 0:
        return 0
    else:
        return 1

if __name__ == '__main__':
    sys.exit(main())

