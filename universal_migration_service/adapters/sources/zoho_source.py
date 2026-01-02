"""
Zoho API Source Adapter
"""
import requests
import json
import re
import time
from typing import Iterator, Dict, List, Any
from datetime import datetime, date, time as time_type
import logging
from .base_source import BaseSourceAdapter

logger = logging.getLogger(__name__)


class ZohoSourceAdapter(BaseSourceAdapter):
    """Zoho CRM API source adapter"""
    
    def __init__(self):
        self.token = None
        self.api_domain = None
        self.config = None
    
    def connect(self, config: Dict[str, Any]) -> bool:
        """Connect to Zoho API (get access token)"""
        try:
            self.config = config
            token_result = self._get_access_token(
                config['refresh_token'],
                config['client_id'],
                config['client_secret'],
                config.get('api_domain', 'https://www.zohoapis.in')
            )
            
            if not token_result:
                raise ConnectionError("Failed to obtain Zoho access token")
            
            self.token = token_result["access_token"]
            self.api_domain = token_result.get("api_domain", config.get('api_domain', 'https://www.zohoapis.in'))
            logger.info("Connected to Zoho API successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Zoho API: {str(e)}")
            raise ConnectionError(f"Failed to connect to Zoho API: {str(e)}")
    
    def disconnect(self):
        """Disconnect from Zoho API"""
        self.token = None
        self.api_domain = None
    
    def test_connection(self, config: Dict[str, Any]) -> bool:
        """Test Zoho API connection"""
        try:
            token_result = self._get_access_token(
                config['refresh_token'],
                config['client_id'],
                config['client_secret'],
                config.get('api_domain', 'https://www.zohoapis.in')
            )
            return token_result is not None
        except:
            return False
    
    def _get_access_token(self, refresh_token: str, client_id: str, client_secret: str, api_domain: str):
        """Generate short-lived access token from refresh token"""
        import time
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
            start_time = time.time()
            logger.debug(f"Requesting access token from: {url}")
            resp = requests.post(url, data=data, timeout=30)
            elapsed = time.time() - start_time
            
            logger.debug(f"Token request completed in {elapsed:.2f}s, status: {resp.status_code}")
            resp.raise_for_status()
            result = resp.json()
            
            token = result.get("access_token")
            if not token:
                logger.error("No access token in response")
                return None
            
            expires_in = result.get("expires_in", 3600)
            logger.info(f"Access token obtained successfully (expires in {expires_in}s, request took {elapsed:.2f}s)")
            
            response_api_domain = result.get("api_domain")
            if response_api_domain:
                api_domain = response_api_domain
                logger.debug(f"API domain updated to: {api_domain}")
            
            return {
                "access_token": token,
                "expires_in": expires_in,
                "api_domain": api_domain,
                "token_type": result.get("token_type", "Bearer")
            }
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error getting access token: {e.response.status_code} - {e.response.text[:200]}")
            return None
        except Exception as e:
            logger.error(f"Error getting access token: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return None
    
    def list_tables(self) -> List[str]:
        """List all available Zoho CRM modules"""
        if not self.token:
            raise ConnectionError("Not connected to Zoho API")
        
        url = f"{self.api_domain}/crm/v8/settings/modules"
        headers = {"Authorization": f"Zoho-oauthtoken {self.token}"}
        
        try:
            import time
            start_time = time.time()
            logger.info(f"Fetching Zoho modules from: {url}")
            logger.debug(f"Request headers: Authorization=Zoho-oauthtoken ***")
            resp = requests.get(url, headers=headers, timeout=30)
            elapsed = time.time() - start_time
            
            logger.debug(f"Modules request completed in {elapsed:.2f}s, status: {resp.status_code}")
            if resp.status_code != 200:
                logger.error(f"Failed to fetch modules: {resp.status_code} - {resp.text[:500]}")
                return []
            
            result = resp.json()
            modules = result.get("modules", [])
            
            module_names = []
            for module in modules:
                api_name = module.get("api_name")
                if api_name:
                    module_names.append(api_name)
            
            logger.info(f"Found {len(module_names)} Zoho modules in {elapsed:.2f}s: {module_names[:10]}{'...' if len(module_names) > 10 else ''}")
            return sorted(module_names)
        except Exception as e:
            logger.error(f"Error fetching modules: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _get_module_field_names(self, module: str):
        """Retrieve all field API names for a module (matching working script)"""
        headers = {"Authorization": f"Zoho-oauthtoken {self.token}"}
        url = f"{self.api_domain}/crm/v2/settings/modules/{module}"
        
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code != 200:
                raise RuntimeError(f"Failed to fetch field metadata for {module}: {resp.status_code} - {resp.text}")

            payload = resp.json()
            fields = payload.get("modules", [{}])[0].get("fields", [])
            if not fields:
                fields = payload.get("fields", [])
            if not fields:
                raise RuntimeError(f"No fields returned for module {module}")
            
            field_names = {field.get("api_name") for field in fields if field.get("api_name")}
            field_names.add("id")
            return sorted(field_names)
        except Exception as e:
            logger.error(f"Error fetching field names for {module}: {e}")
            raise
    
    def get_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """Get module fields schema using field metadata (matching working script)"""
        if not self.token:
            raise ConnectionError("Not connected to Zoho API")
        
        try:
            # Try to get field names from module metadata (matching working script)
            field_names = self._get_module_field_names(table_name)
            
            # Build schema - all fields are String in ClickHouse for Zoho
            schema = []
            for field_name in field_names:
                schema.append({
                    "name": field_name,
                    "type": "string",
                    "nullable": True
                })
            
            return schema
        except Exception as e:
            logger.warning(f"Could not fetch field metadata for {table_name}: {e}, falling back to first record")
            
            # Fallback: fetch first record to determine schema
            url = f"{self.api_domain}/crm/v2/{table_name}"
            headers = {"Authorization": f"Zoho-oauthtoken {self.token}"}
            
            try:
                resp = requests.get(url, headers=headers, params={"page": 1, "per_page": 1}, timeout=30)
                if resp.status_code == 200:
                    result = resp.json()
                    data = result.get("data", [])
                    if data and len(data) > 0:
                        # Extract fields from first record
                        schema = []
                        seen_fields = set()
                        for key in data[0].keys():
                            # All Zoho fields are String in ClickHouse
                            schema.append({
                                "name": key,
                                "type": "string",
                                "nullable": True
                            })
                        return schema
            except Exception as e2:
                logger.warning(f"Could not fetch schema from first record: {e2}")
        
        # Final fallback: return basic schema
        return [
            {
                "name": "id",
                "type": "string",
                "nullable": False
            }
        ]
    
    def _normalize_value(self, value):
        """Prepare values for insertion into ClickHouse (matching working script)"""
        from datetime import time as time_type
        if value is None:
            return None
        if isinstance(value, (datetime, date, time_type)):
            return value.isoformat()
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)
    
    def read_data(self, table_name: str, batch_size: int = 200) -> Iterator[List[Dict[str, Any]]]:
        """Read data from Zoho CRM module in batches (matching working script logic with better error handling)"""
        if not self.token:
            raise ConnectionError("Not connected to Zoho API")
        
        url = f"{self.api_domain}/crm/v2/{table_name}"
        headers = {"Authorization": f"Zoho-oauthtoken {self.token}"}
        page = 1
        max_retries = 3
        retry_delay = 2
        
        while True:
            params = {"page": page, "per_page": batch_size}
            retry_count = 0
            success = False
            
            # Retry logic for failed requests
            while retry_count < max_retries and not success:
                try:
                    import time as time_module
                    request_start = time_module.time()
                    logger.debug(f"{table_name} page {page}: Requesting data from {url} with params {params}")
                    resp = requests.get(url, headers=headers, params=params, timeout=120)
                    request_elapsed = time_module.time() - request_start
                    
                    logger.debug(f"{table_name} page {page}: Response received in {request_elapsed:.2f}s, status: {resp.status_code}")
                    
                    if resp.status_code == 204:
                        logger.info(f"No records found for {table_name}")
                        return  # No more data
                    
                    if resp.status_code == 401:
                        # Token expired, try to refresh
                        logger.warning(f"Token expired for {table_name}, attempting to refresh...")
                        token_result = self._get_access_token(
                            self.config['refresh_token'],
                            self.config['client_id'],
                            self.config['client_secret'],
                            self.api_domain
                        )
                        if token_result:
                            self.token = token_result["access_token"]
                            self.api_domain = token_result.get("api_domain", self.api_domain)
                            headers = {"Authorization": f"Zoho-oauthtoken {self.token}"}
                            logger.info(f"Token refreshed successfully for {table_name}")
                            retry_count += 1
                            time.sleep(retry_delay)
                            continue
                        else:
                            raise ConnectionError("Failed to refresh Zoho access token")
                    
                    if resp.status_code != 200:
                        error_msg = f"{table_name} fetch failed: {resp.status_code} - {resp.text[:200]}"
                        if retry_count < max_retries - 1:
                            logger.warning(f"{error_msg}. Retrying... ({retry_count + 1}/{max_retries})")
                            retry_count += 1
                            time.sleep(retry_delay)
                            continue
                        else:
                            logger.error(error_msg)
                            raise RuntimeError(error_msg)
                    
                    result = resp.json()
                    data = result.get("data", [])
                    
                    if not data:
                        return  # No more data
                    
                    # Convert Zoho records to standard format (matching working script)
                    normalize_start = time_module.time()
                    records = []
                    for record in data:
                        # Normalize values for ClickHouse
                        normalized_record = {}
                        for key, value in record.items():
                            normalized_record[key] = self._normalize_value(value)
                        records.append(normalized_record)
                    normalize_elapsed = time_module.time() - normalize_start
                    
                    logger.info(f"{table_name}: Retrieved {len(data)} records (page {page}) in {request_elapsed:.2f}s (normalized in {normalize_elapsed:.2f}s)")
                    yield records
                    success = True
                    
                    # Check if there are more records
                    if not result.get("info", {}).get("more_records"):
                        logger.info(f"Completed fetching all records for {table_name}.")
                        return
                    
                    page += 1
                    break  # Success, move to next page
                    
                except requests.exceptions.Timeout:
                    retry_count += 1
                    if retry_count < max_retries:
                        logger.warning(f"Timeout fetching page {page} for {table_name}. Retrying... ({retry_count}/{max_retries})")
                        time.sleep(retry_delay)
                    else:
                        logger.error(f"Timeout after {max_retries} retries for {table_name} page {page}")
                        raise
                        
                except requests.exceptions.RequestException as e:
                    retry_count += 1
                    if retry_count < max_retries:
                        logger.warning(f"Request error for {table_name} page {page}: {e}. Retrying... ({retry_count}/{max_retries})")
                        time.sleep(retry_delay)
                    else:
                        logger.error(f"Request failed after {max_retries} retries for {table_name} page {page}: {e}")
                        raise
                        
                except Exception as e:
                    logger.error(f"Unexpected error fetching page {page} for {table_name}: {e}")
                    raise
    
    def read_incremental(self, table_name: str, last_sync_time: datetime, batch_size: int = 200) -> Iterator[List[Dict[str, Any]]]:
        """Read incremental changes (Zoho API doesn't support direct incremental, so we read all)"""
        # Zoho API doesn't have built-in incremental sync, so we read all data
        # In a real implementation, you'd need to track last sync time and filter
        logger.warning(f"Incremental sync for Zoho reads all data (no native incremental support)")
        yield from self.read_data(table_name, batch_size)
    
    def get_source_type(self) -> str:
        return "zoho"

