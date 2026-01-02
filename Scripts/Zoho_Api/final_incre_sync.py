"""
Final Incremental Sync Script - Complete standalone implementation
Migrates only MODIFIED/NEW data from Zoho CRM to ClickHouse (incremental synchronization)
All credentials, functions, and logic included in this single file.
"""

import requests
import json
import re
import time
import logging
from functools import lru_cache
from datetime import datetime, date, time as dt_time, timedelta
from clickhouse_connect import get_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# CREDENTIALS CONFIGURATION
# ============================================================================
# Update these values with your actual credentials

# Zoho CRM Credentials
ZOHO_REFRESH_TOKEN = "your_refresh_token_here"
ZOHO_CLIENT_ID = "your_client_id_here"
ZOHO_CLIENT_SECRET = "your_client_secret_here"
ZOHO_API_DOMAIN = "https://www.zohoapis.in"  # Options: .in, .com, .eu, .com.au, .jp

# ClickHouse Credentials
CLICKHOUSE_HOST = "localhost"
CLICKHOUSE_PORT = 8123
CLICKHOUSE_USER = "default"
CLICKHOUSE_PASSWORD = ""
CLICKHOUSE_DATABASE = "zoho_crm"

# Modules to sync (empty list = sync all modules)
SELECTED_MODULES = []  # Example: ["Accounts", "Contacts", "Deals"]

# ============================================================================
# ZOHO API FUNCTIONS
# ============================================================================

def get_access_token(refresh_token, client_id, client_secret, api_domain="https://www.zohoapis.in"):
    """
    Generate short-lived access token from refresh token.
    
    Args:
        refresh_token: Zoho refresh token
        client_id: Zoho client ID
        client_secret: Zoho client secret
        api_domain: Zoho API domain (default: https://www.zohoapis.in)
    
    Returns:
        dict with access_token, expires_in, api_domain, token_type or None if failed
    """
    # Determine accounts domain from API domain
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
    
    logger.info(f"Requesting new Zoho access token from {accounts_domain}...")
    try:
        resp = requests.post(url, data=data, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        
        token = result.get("access_token")
        if not token:
            logger.error("Failed to retrieve access token from response")
            return None
        
        # Extract API domain from response if available
        response_api_domain = result.get("api_domain")
        if response_api_domain:
            api_domain = response_api_domain
        
        logger.info("Access token retrieved successfully.")
        return {
            "access_token": token,
            "expires_in": result.get("expires_in", 3600),
            "api_domain": api_domain,
            "token_type": result.get("token_type", "Bearer")
        }
    except Exception as e:
        logger.error(f"Error getting access token: {e}")
        return None


def sanitize_column_name(name: str, used_names: set) -> str:
    """Convert Zoho field names into ClickHouse-safe identifiers."""
    sanitized = re.sub(r"[^0-9a-zA-Z_]", "_", name or "field")
    if sanitized and sanitized[0].isdigit():
        sanitized = f"_{sanitized}"
    sanitized = sanitized.lower()
    base = sanitized or "field"
    counter = 1
    candidate = base
    while candidate in used_names:
        candidate = f"{base}_{counter}"
        counter += 1
    used_names.add(candidate)
    return candidate


def normalize_value(value):
    """Prepare values for insertion into ClickHouse."""
    if value is None:
        return None
    if isinstance(value, (datetime, date, dt_time)):
        return value.isoformat()
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def fetch_modified_records(module, token, api_domain, last_sync_time=None, max_retries=3):
    """
    Fetch records modified after last_sync_time from Zoho CRM module.
    Uses Modified_Time field to filter records.
    
    Args:
        module: Zoho module API name
        token: Zoho access token
        api_domain: Zoho API domain
        last_sync_time: datetime object - only fetch records modified after this time
        max_retries: Maximum retry attempts for network errors
    
    Returns:
        List of modified/new records
    """
    url = f"{api_domain}/crm/v2/{module}"
    headers = {"Authorization": f"Zoho-oauthtoken {token}"}
    all_records = []
    page = 1
    
    # Build criteria for Modified_Time filter
    if last_sync_time:
        # Format: (Modified_Time:greater_than:2024-01-01T00:00:00+05:30)
        # Zoho expects ISO format with timezone
        try:
            modified_time_str = last_sync_time.strftime("%Y-%m-%dT%H:%M:%S")
            # Add timezone if not present (default to +05:30 for India)
            if not modified_time_str.endswith(('+', '-')):
                # Check if datetime has timezone info
                if last_sync_time.tzinfo is None:
                    modified_time_str = modified_time_str + "+05:30"
                else:
                    # Extract timezone offset
                    offset = last_sync_time.utcoffset()
                    if offset:
                        hours = int(offset.total_seconds() / 3600)
                        minutes = int((offset.total_seconds() % 3600) / 60)
                        sign = '+' if hours >= 0 else '-'
                        modified_time_str = modified_time_str + f"{sign}{abs(hours):02d}:{minutes:02d}"
                    else:
                        modified_time_str = modified_time_str + "+05:30"
            
            criteria = f"(Modified_Time:greater_than:{modified_time_str})"
            logger.info(f"{module}: Fetching records modified after {last_sync_time.strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            logger.warning(f"{module}: Error formatting Modified_Time criteria: {e}")
            logger.info(f"{module}: Will fetch all records and filter by ID comparison")
            criteria = None
    else:
        # If no last_sync_time, fetch all records (first sync)
        criteria = None
        logger.info(f"{module}: No last sync time - fetching all records (first sync)")
    
    while True:
        params = {"page": page, "per_page": 200}
        if criteria:
            params["criteria"] = criteria
        
        retry_count = 0
        success = False
        more_records = True
        
        while retry_count < max_retries and not success:
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=120)
                
                if resp.status_code == 204:
                    logger.info(f"{module}: No records found")
                    more_records = False
                    success = True
                    break
                
                if resp.status_code != 200:
                    if 400 <= resp.status_code < 500:
                        logger.error(f"{module} fetch failed: {resp.status_code} - {resp.text}")
                        more_records = False
                        success = True
                        break
                    else:
                        raise requests.exceptions.HTTPError(f"HTTP {resp.status_code}: {resp.text}")
                
                result = resp.json()
                data = result.get("data", [])
                
                if not data:
                    more_records = False
                    success = True
                    break
                
                all_records.extend(data)
                logger.info(f"{module}: Retrieved page {page} - {len(data)} records (total {len(all_records):,})")
                
                more_records = result.get("info", {}).get("more_records", False)
                success = True
                break
                
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, 
                    requests.exceptions.HTTPError) as e:
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = retry_count * 2
                    logger.warning(f"Network error fetching {module} page {page} (attempt {retry_count}/{max_retries}): {e}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to fetch {module} page {page} after {max_retries} retries: {e}")
                    raise
            except Exception as e:
                logger.error(f"Error fetching page {page} for {module}: {e}")
                raise
        
        if not success:
            logger.error(f"{module}: Failed to fetch page {page} after all retries")
            break
        
        if not more_records:
            logger.info(f"{module}: No more records, completed pagination")
            break
        
        page += 1
    
    logger.info(f"✅ Completed fetching {len(all_records)} modified/new records for {module}")
    return all_records


def get_available_modules(token, api_domain):
    """
    Fetch all available Zoho CRM modules.
    
    Args:
        token: Zoho access token
        api_domain: Zoho API domain
    
    Returns:
        list of module names or empty list if failed
    """
    url = f"{api_domain}/crm/v8/settings/modules"
    headers = {"Authorization": f"Zoho-oauthtoken {token}"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            logger.error(f"Failed to fetch modules: {resp.status_code} - {resp.text}")
            return []
        
        result = resp.json()
        modules = result.get("modules", [])
        
        # Extract module API names
        module_names = []
        for module in modules:
            api_name = module.get("api_name")
            if api_name:
                module_names.append({
                    "api_name": api_name,
                    "display_name": module.get("display_label", api_name),
                    "singular_label": module.get("singular_label", api_name),
                    "plural_label": module.get("plural_label", api_name)
                })
        
        return sorted(module_names, key=lambda x: x["display_name"])
    except Exception as e:
        logger.error(f"Error fetching modules: {e}")
        return []


# ============================================================================
# CLICKHOUSE FUNCTIONS
# ============================================================================

def recreate_clickhouse_client(clickhouse_host, clickhouse_user, clickhouse_password, database):
    """Recreate ClickHouse client to avoid session locks."""
    try:
        new_client = get_client(
            host=clickhouse_host,
            username=clickhouse_user,
            password=clickhouse_password,
            database=database,
        )
        return new_client
    except Exception as e:
        logger.error(f"   ❌ Failed to recreate client: {e}")
        return None


def is_session_lock_error(error_msg):
    """Check if error is a session lock error."""
    error_str = str(error_msg).lower()
    return 'session' in error_str and 'locked' in error_str


def is_timeout_error(error_msg):
    """Check if error is a timeout error."""
    error_str = str(error_msg).lower()
    return 'timeout' in error_str or 'timed out' in error_str


def get_last_sync_time(client, database, module):
    """
    Get the last sync time for a module from ClickHouse.
    Tries multiple methods:
    1. Modified_Time field (various formats)
    2. Created_Time field (fallback)
    3. load_time (last resort - when records were inserted)
    
    Returns the maximum time from the table, or None if table doesn't exist or is empty.
    """
    table = f"zoho_{module.lower()}"
    
    try:
        # Check if table exists
        exists_result = client.query(f"EXISTS TABLE {database}.{table}")
        if exists_result.result_rows[0][0] != 1:
            logger.info(f"{module}: Table {database}.{table} does not exist - will run full sync")
            return None
        
        # Get all column names to find Modified_Time variations
        try:
            describe_result = client.query(f"DESCRIBE TABLE {database}.{table}")
            column_names = [row[0] for row in describe_result.result_rows]
            
            # Try to find Modified_Time column (case-insensitive search)
            modified_time_col = None
            for col in column_names:
                col_lower = col.lower()
                if 'modified' in col_lower and 'time' in col_lower:
                    modified_time_col = col
                    logger.info(f"{module}: Found Modified_Time column: {col}")
                    break
            
            # Try Modified_Time field (various formats)
            if modified_time_col:
                try:
                    result = client.query(f"""
                        SELECT MAX(CAST(`{modified_time_col}` AS DateTime)) as max_time
                        FROM {database}.{table}
                        WHERE `{modified_time_col}` IS NOT NULL 
                        AND `{modified_time_col}` != ''
                        AND `{modified_time_col}` != 'None'
                    """)
                    if result.result_rows and result.result_rows[0][0]:
                        max_time = result.result_rows[0][0]
                        if isinstance(max_time, datetime):
                            logger.info(f"{module}: Last sync time from Modified_Time: {max_time}")
                            return max_time
                except Exception as e:
                    logger.debug(f"{module}: Could not parse Modified_Time: {e}")
            
            # Fallback 1: Try Created_Time
            created_time_col = None
            for col in column_names:
                col_lower = col.lower()
                if 'created' in col_lower and 'time' in col_lower:
                    created_time_col = col
                    break
            
            if created_time_col:
                try:
                    result = client.query(f"""
                        SELECT MAX(CAST(`{created_time_col}` AS DateTime)) as max_time
                        FROM {database}.{table}
                        WHERE `{created_time_col}` IS NOT NULL 
                        AND `{created_time_col}` != ''
                        AND `{created_time_col}` != 'None'
                    """)
                    if result.result_rows and result.result_rows[0][0]:
                        max_time = result.result_rows[0][0]
                        if isinstance(max_time, datetime):
                            logger.info(f"{module}: Using Created_Time as fallback: {max_time}")
                            return max_time
                except Exception as e:
                    logger.debug(f"{module}: Could not parse Created_Time: {e}")
            
            # Fallback 2: Use load_time (when records were inserted)
            if 'load_time' in column_names:
                try:
                    result = client.query(f"""
                        SELECT MAX(load_time) as max_time
                        FROM {database}.{table}
                    """)
                    if result.result_rows and result.result_rows[0][0]:
                        max_time = result.result_rows[0][0]
                        if isinstance(max_time, datetime):
                            logger.info(f"{module}: Using load_time as fallback: {max_time}")
                            # Subtract 1 hour to ensure we catch records that might have been modified
                            # but have the same load_time
                            fallback_time = max_time - timedelta(hours=1)
                            logger.info(f"{module}: Adjusted to {fallback_time} (1 hour before load_time)")
                            return fallback_time
                except Exception as e:
                    logger.debug(f"{module}: Could not use load_time: {e}")
            
        except Exception as e:
            logger.warning(f"{module}: Error getting column names: {e}")
        
        # If no time field found, check if table has any data
        count_result = client.query(f"SELECT COUNT() FROM {database}.{table}")
        count = count_result.result_rows[0][0] if count_result.result_rows else 0
        
        if count > 0:
            logger.warning(f"{module}: Table exists with {count} records but no time field found")
            logger.warning(f"{module}: Will use load_time -1 day as fallback to catch recent changes")
            # Use load_time minus 1 day as a safe fallback
            try:
                result = client.query(f"SELECT MAX(load_time) FROM {database}.{table}")
                if result.result_rows and result.result_rows[0][0]:
                    max_load_time = result.result_rows[0][0]
                    if isinstance(max_load_time, datetime):
                        fallback_time = max_load_time - timedelta(days=1)
                        logger.info(f"{module}: Using fallback time: {fallback_time} (1 day before last load)")
                        return fallback_time
            except:
                pass
            
            # Last resort: return None to trigger full sync check
            logger.warning(f"{module}: Cannot determine last sync time - will check if incremental is possible")
            return None
        else:
            logger.info(f"{module}: Table exists but is empty - will run full sync")
            return None
            
    except Exception as e:
        logger.warning(f"{module}: Error getting last sync time: {e} - will try fallback")
        # Try to get load_time as last resort
        try:
            result = client.query(f"SELECT MAX(load_time) FROM {database}.{table}")
            if result.result_rows and result.result_rows[0][0]:
                max_load_time = result.result_rows[0][0]
                if isinstance(max_load_time, datetime):
                    fallback_time = max_load_time - timedelta(days=1)
                    logger.info(f"{module}: Using load_time fallback: {fallback_time}")
                    return fallback_time
        except:
            pass
        return None


def check_zoho_tables_exist(client, database, modules):
    """
    Check which Zoho tables exist in ClickHouse.
    
    Returns:
        dict with module as key and bool (exists) as value
    """
    existing_tables = {}
    
    for module in modules:
        table = f"zoho_{module.lower()}"
        try:
            exists_result = client.query(f"EXISTS TABLE {database}.{table}")
            exists = exists_result.result_rows[0][0] == 1 if exists_result.result_rows else False
            existing_tables[module] = exists
        except:
            existing_tables[module] = False
    
    return existing_tables


def save_to_clickhouse_incremental(client, module, records, database, 
                                   clickhouse_host=None, clickhouse_user=None, 
                                   clickhouse_password=None):
    """
    Save records to ClickHouse with DELETE-then-INSERT for updates.
    This prevents duplicates by explicitly deleting old records before inserting new ones.
    
    Args:
        client: ClickHouse client connection
        module: Zoho module name
        records: List of records to insert
        database: ClickHouse database name
        clickhouse_host: ClickHouse host (for recreating client)
        clickhouse_user: ClickHouse username
        clickhouse_password: ClickHouse password
    
    Returns:
        dict with new_records and updated_records counts
    """
    table = f"zoho_{module.lower()}"
    
    if not records:
        logger.info(f"{module}: No records to save")
        return {"new_records": 0, "updated_records": 0}
    
    # Get existing IDs to determine new vs updated
    existing_ids = set()
    try:
        existing_result = client.query(f"SELECT DISTINCT id FROM {database}.{table}")
        existing_ids = {str(row[0]) for row in existing_result.result_rows}
        logger.info(f"   📊 Found {len(existing_ids):,} existing records in {database}.{table}")
    except Exception as e:
        logger.warning(f"   ⚠️  Could not fetch existing IDs: {e}")
        existing_ids = set()
    
    # Separate new and updated records
    new_records_list = []
    updated_record_ids = []
    
    for record in records:
        record_id = str(record.get("id", ""))
        if record_id in existing_ids:
            updated_record_ids.append(record_id)
        else:
            new_records_list.append(record)
    
    updated_count = len(updated_record_ids)
    new_count = len(new_records_list)
    
    logger.info(f"   📊 Analysis: {new_count:,} new records, {updated_count:,} records to update")
    
    # DELETE old records for updates (delete-then-insert pattern)
    if updated_record_ids:
        logger.info(f"   🗑️  Deleting {updated_count:,} old records before updating...")
        try:
            # Delete in batches to avoid query size limits
            batch_size = 1000
            total_deleted = 0
            
            for i in range(0, len(updated_record_ids), batch_size):
                batch_ids = updated_record_ids[i:i + batch_size]
                # Format IDs for SQL IN clause
                ids_str = "', '".join(batch_ids)
                delete_query = f"ALTER TABLE {database}.{table} DELETE WHERE id IN ('{ids_str}')"
                
                try:
                    client.command(delete_query)
                    total_deleted += len(batch_ids)
                    logger.info(f"   ✓ Deleted batch {i//batch_size + 1} ({len(batch_ids)} records, total: {total_deleted}/{updated_count})")
                except Exception as e:
                    if is_session_lock_error(e) or is_timeout_error(e):
                        logger.warning(f"   ⚠️  Session lock/timeout during delete, recreating client...")
                        new_client = recreate_clickhouse_client(clickhouse_host, clickhouse_user, clickhouse_password, database)
                        if new_client:
                            client = new_client
                            client.command(delete_query)
                            total_deleted += len(batch_ids)
                        else:
                            logger.error(f"   ❌ Could not delete records: {e}")
                    else:
                        logger.error(f"   ❌ Error deleting records: {e}")
            
            logger.info(f"   ✅ Deleted {total_deleted:,} old records")
            
            # Wait a moment for deletion to complete
            time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"   ❌ Error during delete operation: {e}")
            logger.warning(f"   ⚠️  Continuing with insert - duplicates may occur")
    
    # Now insert all records (new + updated)
    # Extract all fields from records
    all_fields = set()
    for record in records:
        all_fields.update(record.keys())
    
    fields = sorted([f for f in all_fields if f != "id"])
    
    used_names = {"id", "load_time"}
    column_map = {field: sanitize_column_name(field, used_names) for field in fields}
    
    # Ensure all columns exist
    try:
        describe = client.query(f"DESCRIBE TABLE {database}.{table}")
        existing_columns = {row[0] for row in describe.result_rows}
    except Exception as e:
        existing_columns = {"id", "load_time"}
    
    for column in column_map.values():
        if column not in existing_columns:
            try:
                client.command(f"ALTER TABLE {database}.{table} ADD COLUMN `{column}` Nullable(String)")
                logger.info(f"   ➕ Added column: {column}")
            except Exception as e:
                logger.warning(f"   ⚠️  Could not add column {column}: {e}")
    
    # Prepare rows for insertion
    column_names = ["id"] + [column_map[field] for field in fields]
    rows_to_insert = []
    
    for record in records:
        record_id = str(record.get("id", ""))
        row = [record_id]
        for field in fields:
            row.append(normalize_value(record.get(field)))
        rows_to_insert.append(row)
    
    # Insert records in batches
    if rows_to_insert:
        batch_size = 5000
        total_inserted = 0
        max_retries = 3
        
        for i in range(0, len(rows_to_insert), batch_size):
            batch = rows_to_insert[i:i + batch_size]
            batch_num = i//batch_size + 1
            retry_count = 0
            batch_success = False
            
            while retry_count < max_retries and not batch_success:
                try:
                    client.insert(f"{database}.{table}", batch, column_names=column_names)
                    total_inserted += len(batch)
                    logger.info(f"   ✓ Inserted batch {batch_num} ({len(batch)} records, total: {total_inserted}/{len(rows_to_insert)})")
                    batch_success = True
                except Exception as e:
                    error_str = str(e)
                    retry_count += 1
                    
                    if is_session_lock_error(error_str) or is_timeout_error(error_str):
                        if retry_count < max_retries:
                            wait_time = retry_count * 3
                            logger.warning(f"   ⚠️  Batch {batch_num} failed, retrying in {wait_time}s...")
                            time.sleep(wait_time)
                            new_client = recreate_clickhouse_client(clickhouse_host, clickhouse_user, clickhouse_password, database)
                            if new_client:
                                client = new_client
                        else:
                            logger.error(f"   ❌ Batch {batch_num} failed after {max_retries} retries")
                            batch_success = True  # Mark as handled
                    else:
                        logger.error(f"   ❌ Error inserting batch {batch_num}: {error_str[:200]}")
                        batch_success = True  # Mark as handled
        
        logger.info(f"   ✅ Inserted {total_inserted:,} records ({new_count:,} new, {updated_count:,} updated)")
    
    return {
        "new_records": new_count,
        "updated_records": updated_count,
        "total_inserted": len(rows_to_insert) if rows_to_insert else 0
    }


# ============================================================================
# MAIN SYNC FUNCTION
# ============================================================================

def sync_zoho_incremental(refresh_token, client_id, client_secret, api_domain,
                          clickhouse_host, clickhouse_user, clickhouse_password,
                          clickhouse_database, selected_modules=None):
    """
    Incremental Zoho CRM sync - only fetches modified/new records.
    
    Args:
        refresh_token: Zoho refresh token
        client_id: Zoho client ID
        client_secret: Zoho client secret
        api_domain: Zoho API domain
        clickhouse_host: ClickHouse host
        clickhouse_user: ClickHouse username
        clickhouse_password: ClickHouse password
        clickhouse_database: ClickHouse database name
        selected_modules: List of module API names to sync (optional, syncs all if None)
    
    Returns:
        dict with sync results
    """
    logger.info("="*70)
    logger.info("🔄 ZOHO INCREMENTAL SYNC STARTED")
    logger.info("="*70)
    
    results = {
        "success": True,
        "synced_modules": [],
        "failed_modules": [],
        "total_records": 0,
        "new_records": 0,
        "updated_records": 0,
        "full_sync_modules": [],
        "errors": []
    }
    
    # Get access token
    token_result = get_access_token(refresh_token, client_id, client_secret, api_domain)
    if not token_result:
        results["success"] = False
        results["errors"].append("Failed to obtain access token")
        return results
    
    token = token_result["access_token"]
    api_domain = token_result.get("api_domain", api_domain)
    
    # Connect to ClickHouse
    try:
        client = get_client(
            host=clickhouse_host,
            username=clickhouse_user,
            password=clickhouse_password,
            database=clickhouse_database,
        )
        logger.info(f"✅ Connected to ClickHouse database: {clickhouse_database}")
    except Exception as e:
        results["success"] = False
        results["errors"].append(f"Failed to connect to ClickHouse: {str(e)}")
        logger.error(f"❌ ClickHouse connection error: {str(e)}")
        return results
    
    # Get modules to sync
    if not selected_modules:
        logger.info("No modules specified, fetching all available modules...")
        modules = get_available_modules(token, api_domain)
        if not modules:
            results["success"] = False
            results["errors"].append("No modules found in Zoho CRM")
            return results
        selected_modules = [module["api_name"] for module in modules]
        logger.info(f"Found {len(selected_modules)} modules: {', '.join(selected_modules[:5])}...")
    
    # Check which tables exist
    logger.info("\n📋 Checking which tables exist in ClickHouse...")
    existing_tables = check_zoho_tables_exist(client, clickhouse_database, selected_modules)
    
    modules_needing_full_sync = []
    modules_for_incremental = []
    
    for module in selected_modules:
        if existing_tables.get(module, False):
            modules_for_incremental.append(module)
            logger.info(f"   ✓ {module}: Table exists - will run incremental sync")
        else:
            modules_needing_full_sync.append(module)
            logger.info(f"   ⚠️  {module}: Table does not exist - skipping (run full sync first)")
    
    # Note: For incremental sync, we skip modules without tables
    # User should run full sync first to create tables
    if modules_needing_full_sync:
        logger.warning(f"\n⚠️  {len(modules_needing_full_sync)} modules need full sync first:")
        for module in modules_needing_full_sync:
            logger.warning(f"   - {module}")
        logger.warning("   Please run final_full_sync.py for these modules first.\n")
    
    # Run incremental sync for existing tables
    if modules_for_incremental:
        logger.info(f"\n🔄 Running INCREMENTAL sync for {len(modules_for_incremental)} modules...")
        logger.info("="*70)
        
        for idx, module in enumerate(modules_for_incremental, 1):
            try:
                logger.info(f"\n[{idx}/{len(modules_for_incremental)}] Processing module: {module}")
                
                # Get last sync time for this module
                last_sync_time = get_last_sync_time(client, clickhouse_database, module)
                
                # If no last_sync_time, try to use a very conservative fallback
                if last_sync_time is None:
                    # Check if table exists and has data
                    table = f"zoho_{module.lower()}"
                    try:
                        count_result = client.query(f"SELECT COUNT() FROM {clickhouse_database}.{table}")
                        count = count_result.result_rows[0][0] if count_result.result_rows else 0
                        
                        if count > 0:
                            # Table has data but we can't determine last sync time
                            # Use a conservative approach: fetch records from last 7 days
                            logger.warning(f"   ⚠️  {module}: Cannot determine last sync time")
                            logger.info(f"   💡 Using conservative fallback: fetching records from last 7 days")
                            last_sync_time = datetime.now() - timedelta(days=7)
                        else:
                            # Table is empty, skip incremental
                            logger.info(f"   ✓ {module}: Table is empty - skipping incremental")
                            continue
                    except Exception as e:
                        logger.warning(f"   ⚠️  {module}: Error checking table: {e} - skipping incremental")
                        continue
                
                # Fetch modified records (ONLY records modified after last_sync_time)
                modified_records = fetch_modified_records(
                    module=module,
                    token=token,
                    api_domain=api_domain,
                    last_sync_time=last_sync_time
                )
                
                if not modified_records:
                    logger.info(f"   ✓ {module}: No new or modified records since last sync")
                    results["synced_modules"].append({
                        "module": module,
                        "record_count": 0,
                        "new_records": 0,
                        "updated_records": 0
                    })
                    continue
                
                if last_sync_time:
                    logger.info(f"   📊 {module}: Found {len(modified_records)} records modified after {last_sync_time.strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    logger.info(f"   📊 {module}: Found {len(modified_records)} records (using fallback method)")
                
                # Save to ClickHouse with delete-then-insert for updates
                sync_result = save_to_clickhouse_incremental(
                    client, module, modified_records, clickhouse_database,
                    clickhouse_host=clickhouse_host,
                    clickhouse_user=clickhouse_user,
                    clickhouse_password=clickhouse_password
                )
                
                # Track results
                new_count = sync_result.get('new_records', 0)
                updated_count = sync_result.get('updated_records', 0)
                total_count = new_count + updated_count
                
                results["synced_modules"].append({
                    "module": module,
                    "record_count": total_count,
                    "new_records": new_count,
                    "updated_records": updated_count
                })
                results["total_records"] += total_count
                results["new_records"] += new_count
                results["updated_records"] += updated_count
                
                logger.info(f"   ✅ {module}: {new_count:,} new, {updated_count:,} updated records")
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"   ❌ {module}: Error - {error_msg}")
                results["failed_modules"].append({
                    "module": module,
                    "error": error_msg
                })
                continue
    
    logger.info("\n" + "="*70)
    logger.info("🔄 ZOHO INCREMENTAL SYNC COMPLETED")
    logger.info("="*70)
    logger.info(f"   Total records synced: {results['total_records']:,}")
    logger.info(f"   ✨ New records added: {results['new_records']:,}")
    logger.info(f"   🔄 Records updated: {results['updated_records']:,}")
    logger.info(f"   Modules synced: {len(results['synced_modules'])}")
    logger.info(f"   Modules failed: {len(results['failed_modules'])}")
    if modules_needing_full_sync:
        logger.info(f"   Modules needing full sync: {len(modules_needing_full_sync)}")
    logger.info("="*70)
    
    results["success"] = len(results["failed_modules"]) == 0
    return results


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point for the script."""
    logger.info("="*70)
    logger.info("ZOHO CRM INCREMENTAL SYNC TO CLICKHOUSE")
    logger.info("="*70)
    logger.info("")
    
    # Use credentials from the configuration section
    result = sync_zoho_incremental(
        refresh_token=ZOHO_REFRESH_TOKEN,
        client_id=ZOHO_CLIENT_ID,
        client_secret=ZOHO_CLIENT_SECRET,
        api_domain=ZOHO_API_DOMAIN,
        clickhouse_host=CLICKHOUSE_HOST,
        clickhouse_user=CLICKHOUSE_USER,
        clickhouse_password=CLICKHOUSE_PASSWORD,
        clickhouse_database=CLICKHOUSE_DATABASE,
        selected_modules=SELECTED_MODULES if SELECTED_MODULES else None
    )
    
    if result["success"]:
        logger.info("✅ Incremental sync completed successfully!")
        return 0
    else:
        logger.error("❌ Incremental sync completed with errors")
        return 1


if __name__ == "__main__":
    exit(main())

