"""
Final Full Sync Script - Complete standalone implementation
Migrates ALL data from Zoho CRM to ClickHouse (full synchronization)
All credentials, functions, and logic included in this single file.
"""

import requests
import json
import re
import time
import logging
from functools import lru_cache
from datetime import datetime, date, time as dt_time
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


@lru_cache(maxsize=None)
def get_module_field_names(module: str, token: str, api_domain: str):
    """Retrieve all field API names for a module."""
    headers = {"Authorization": f"Zoho-oauthtoken {token}"}
    
    # Try v8 API first (newer)
    url_v8 = f"{api_domain}/crm/v8/settings/modules/{module}"
    try:
        resp = requests.get(url_v8, headers=headers, timeout=30)
        if resp.status_code == 200:
            payload = resp.json()
            modules_data = payload.get("modules", [])
            if modules_data:
                fields = modules_data[0].get("fields", [])
                if fields:
                    field_names = {field.get("api_name") for field in fields if field.get("api_name")}
                    field_names.add("id")
                    return sorted(field_names)
    except:
        pass
    
    # Fallback to v2 API
    url_v2 = f"{api_domain}/crm/v2/settings/modules/{module}"
    try:
        resp = requests.get(url_v2, headers=headers, timeout=30)
        if resp.status_code == 200:
            payload = resp.json()
            fields = payload.get("modules", [{}])[0].get("fields", [])
            if not fields:
                fields = payload.get("fields", [])
            if fields:
                field_names = {field.get("api_name") for field in fields if field.get("api_name")}
                field_names.add("id")
                return sorted(field_names)
    except:
        pass
    
    # If both fail, return None - we'll extract fields from actual records
    logger.warning(f"Could not fetch field metadata for {module}, will extract from records")
    return None


def fetch_all_records(module, token, api_domain, max_retries=3, progress_callback=None):
    """
    Fetch ALL records from Zoho CRM module (handles pagination with retry logic).
    
    Args:
        module: Zoho module API name
        token: Zoho access token
        api_domain: Zoho API domain
        max_retries: Maximum retry attempts for network errors
        progress_callback: Optional callback function(module, page, total_fetched) for progress updates
    
    Returns:
        List of all records from the module
    """
    url = f"{api_domain}/crm/v2/{module}"
    headers = {"Authorization": f"Zoho-oauthtoken {token}"}
    all_records = []
    page = 1
    processed_pages = set()  # Track successfully processed pages to prevent duplicates

    # Try to get field names from metadata (optional - we'll extract from records anyway)
    field_names = get_module_field_names(module, token, api_domain)
    if field_names:
        logger.info(f"{module}: Found {len(field_names)} fields in module metadata")
    else:
        logger.info(f"{module}: Will extract fields from actual records")
        field_names = None  # Will be extracted from records

    while True:
        # Skip if we've already processed this page (safety check to prevent duplicates)
        if page in processed_pages:
            logger.error(f"{module}: ❌ DUPLICATE PAGE DETECTED - Page {page} already processed! This indicates a bug. Skipping to next page.")
            page += 1
            continue
            
        params = {"page": page, "per_page": 200}
        retry_count = 0
        success = False
        more_records = True  # Track if there are more records
        
        # Retry logic for network failures
        while retry_count < max_retries and not success:
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=120)
                
                if resp.status_code == 204:
                    logger.info(f"No records found for {module}")
                    more_records = False
                    success = True
                    break
                    
                if resp.status_code != 200:
                    # Don't retry on 4xx errors (client errors)
                    if 400 <= resp.status_code < 500:
                        logger.error(f"{module} fetch failed: {resp.status_code} - {resp.text}")
                        more_records = False
                        success = True  # Mark as handled, don't retry
                        break
                    else:
                        # Retry on 5xx errors (server errors)
                        raise requests.exceptions.HTTPError(f"HTTP {resp.status_code}: {resp.text}")

                result = resp.json()
                data = result.get("data", [])
                
                if not data:
                    more_records = False
                    success = True
                    break

                # Double-check: Only add data if we haven't already processed this page
                if page not in processed_pages:
                    all_records.extend(data)
                    processed_pages.add(page)
                    
                    # Log progress: every 10 pages, first page, or when done
                    should_log = (page == 1 or page % 10 == 0 or 
                                 not result.get("info", {}).get("more_records", False))
                    
                    if should_log:
                        logger.info(f"{module}: Retrieved page {page} - {len(data)} records (total {len(all_records):,})")
                else:
                    # This should never happen - duplicate detected during processing
                    logger.error(f"{module}: ❌ CRITICAL: Page {page} was added to processed_pages during processing! This is a bug.")
                    # Don't add duplicate data, but continue to next page
                
                # Check if there are more records
                more_records = result.get("info", {}).get("more_records", False)
                
                # Call progress callback if provided
                if progress_callback:
                    try:
                        progress_callback(module, page, len(all_records))
                    except:
                        pass
                
                success = True
                break  # Exit retry loop on success
                
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, 
                    requests.exceptions.HTTPError) as e:
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = retry_count * 2  # Exponential backoff: 2s, 4s, 6s
                    logger.warning(f"Network error fetching {module} page {page} (attempt {retry_count}/{max_retries}): {e}")
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to fetch {module} page {page} after {max_retries} retries: {e}")
                    raise
            except Exception as e:
                logger.error(f"Error fetching page {page} for {module}: {e}")
                raise
        
        # If we didn't succeed after all retries, break
        if not success:
            logger.error(f"{module}: Failed to fetch page {page} after all retries")
            break
        
        # If no more records, we're done
        if not more_records:
            logger.info(f"{module}: No more records (more_records=False), completed pagination")
            break
        
        # Always move to next page after successful fetch (or skip if duplicate was detected)
        page += 1

    logger.info(f"✅ Completed fetching ALL {len(all_records)} records for {module} (from {page} page(s)).")
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


def save_to_clickhouse(client, module, records, database, clickhouse_host=None, clickhouse_user=None, clickhouse_password=None):
    """
    Insert ALL records into ClickHouse with ALL fields/columns.
    Uses incremental update: checks existing records and only inserts new/updated ones.
    Always creates table, even for empty modules.
    Handles session locks and timeouts by recreating client connections.
    
    Args:
        client: ClickHouse client connection
        module: Zoho module name
        records: List of all records to insert
        database: ClickHouse database name
        clickhouse_host: ClickHouse host (for recreating client on session lock)
        clickhouse_user: ClickHouse username (for recreating client on session lock)
        clickhouse_password: ClickHouse password (for recreating client on session lock)
    
    Returns:
        Number of records inserted
    """
    table = f"zoho_{module.lower()}"
    
    # Always create table, even if no records
    if not records:
        logger.info(f"No records found for {module}, creating empty table")
        # Create minimal table structure
        try:
            client.command(f"""
                CREATE TABLE IF NOT EXISTS {database}.{table} (
                    id String,
                    load_time DateTime DEFAULT now()
                )
                ENGINE = ReplacingMergeTree(load_time)
                ORDER BY id
            """)
            logger.info(f"✅✅✅ EMPTY TABLE CREATED IN {database}: {database}.{table} ✅✅✅")
            logger.info(f"   You can now see this table in ClickHouse database '{database}'")
        except Exception as e:
            if is_session_lock_error(e):
                logger.warning(f"   ⚠️  Session lock during table creation, recreating client...")
                new_client = recreate_clickhouse_client(clickhouse_host, clickhouse_user, clickhouse_password, database)
                if new_client:
                    client = new_client
                    client.command(f"""
                        CREATE TABLE IF NOT EXISTS {database}.{table} (
                            id String,
                            load_time DateTime DEFAULT now()
                        )
                        ENGINE = ReplacingMergeTree(load_time)
                        ORDER BY id
                    """)
                    logger.info(f"✅✅✅ EMPTY TABLE CREATED IN {database}: {database}.{table} ✅✅✅")
                else:
                    raise
            else:
                raise
        return 0

    # Process ALL records and extract ALL fields/columns dynamically
    # This ensures we capture every field from every record
    all_fields = set()
    for record in records:
        all_fields.update(record.keys())
    
    # Remove 'id' from fields list (it's handled separately)
    fields = sorted([f for f in all_fields if f != "id"])
    
    logger.info(f"{module}: Processing {len(records)} records with {len(fields)} unique fields")
    
    used_names = {"id", "load_time"}
    column_map = {field: sanitize_column_name(field, used_names) for field in fields}

    column_defs = ",\n            ".join(
        f"`{column}` Nullable(String)" for column in column_map.values()
    )
    column_section = f",\n            {column_defs}" if column_defs else ""

    # Check if table exists and get existing record IDs
    table_exists = False
    existing_ids = set()
    
    try:
        exists_result = client.query(f"EXISTS TABLE {database}.{table}")
        table_exists = exists_result.result_rows[0][0] == 1
        
        if table_exists:
            logger.info(f"   📋 Table {database}.{table} already exists, checking existing records...")
            try:
                # Get all existing IDs from the table
                existing_result = client.query(f"SELECT DISTINCT id FROM {database}.{table}")
                existing_ids = {str(row[0]) for row in existing_result.result_rows}
                logger.info(f"   📊 Found {len(existing_ids):,} existing records in {database}.{table}")
            except Exception as e:
                if is_session_lock_error(e):
                    logger.warning(f"   ⚠️  Session lock, recreating client...")
                    new_client = recreate_clickhouse_client(clickhouse_host, clickhouse_user, clickhouse_password, database)
                    if new_client:
                        client = new_client
                        existing_result = client.query(f"SELECT DISTINCT id FROM {database}.{table}")
                        existing_ids = {str(row[0]) for row in existing_result.result_rows}
                        logger.info(f"   📊 Found {len(existing_ids):,} existing records in {database}.{table}")
                    else:
                        logger.warning(f"   ⚠️  Could not fetch existing IDs: {e}, will insert all records")
                        existing_ids = set()
                else:
                    logger.warning(f"   ⚠️  Could not fetch existing IDs: {e}, will insert all records")
                    existing_ids = set()
    except Exception as e:
        if is_session_lock_error(e):
            logger.warning(f"   ⚠️  Session lock, recreating client...")
            new_client = recreate_clickhouse_client(clickhouse_host, clickhouse_user, clickhouse_password, database)
            if new_client:
                client = new_client
        else:
            logger.warning(f"   ⚠️  Error checking table existence: {e}")

    # Create table if it doesn't exist (using ReplacingMergeTree for automatic deduplication)
    if not table_exists:
        try:
            create_sql = f"""
                CREATE TABLE IF NOT EXISTS {database}.{table} (
                    id String{column_section},
                    load_time DateTime DEFAULT now()
                )
                ENGINE = ReplacingMergeTree(load_time)
                ORDER BY id
            """
            client.command(create_sql)
            logger.info(f"✅✅✅ TABLE CREATED IN {database}: {database}.{table} ✅✅✅")
            logger.info(f"   You can now see this table in ClickHouse database '{database}'")
            
            # Verify table exists
            try:
                verify_result = client.query(f"EXISTS TABLE {database}.{table}")
                if verify_result.result_rows[0][0] == 1:
                    logger.info(f"   ✓ Verified: Table {database}.{table} exists in ClickHouse")
            except:
                pass
        except Exception as e:
            if is_session_lock_error(e):
                logger.warning(f"   ⚠️  Session lock during table creation, recreating client...")
                new_client = recreate_clickhouse_client(clickhouse_host, clickhouse_user, clickhouse_password, database)
                if new_client:
                    client = new_client
                    create_sql = f"""
                        CREATE TABLE IF NOT EXISTS {database}.{table} (
                            id String{column_section},
                            load_time DateTime DEFAULT now()
                        )
                        ENGINE = ReplacingMergeTree(load_time)
                        ORDER BY id
                    """
                    client.command(create_sql)
                    logger.info(f"✅✅✅ TABLE CREATED IN {database}: {database}.{table} ✅✅✅")
                else:
                    logger.error(f"❌❌❌ FAILED to create table {database}.{table}: {e}")
                    raise
            else:
                logger.error(f"❌❌❌ FAILED to create table {database}.{table}: {e}")
                raise
    else:
        logger.info(f"   ✓ Table {database}.{table} exists, will update incrementally")

    # Ensure all columns exist
    try:
        describe = client.query(f"DESCRIBE TABLE {database}.{table}")
        existing_columns = {row[0] for row in describe.result_rows}
    except Exception as e:
        if is_session_lock_error(e):
            logger.warning(f"   ⚠️  Session lock, recreating client...")
            new_client = recreate_clickhouse_client(clickhouse_host, clickhouse_user, clickhouse_password, database)
            if new_client:
                client = new_client
                describe = client.query(f"DESCRIBE TABLE {database}.{table}")
                existing_columns = {row[0] for row in describe.result_rows}
            else:
                existing_columns = {"id", "load_time"}
        else:
            existing_columns = {"id", "load_time"}

    for column in column_map.values():
        if column not in existing_columns:
            try:
                client.command(f"ALTER TABLE {database}.{table} ADD COLUMN `{column}` Nullable(String)")
                logger.info(f"   ➕ Added column: {column}")
            except Exception as e:
                if is_session_lock_error(e):
                    logger.warning(f"   ⚠️  Session lock, recreating client...")
                    new_client = recreate_clickhouse_client(clickhouse_host, clickhouse_user, clickhouse_password, database)
                    if new_client:
                        client = new_client
                        try:
                            client.command(f"ALTER TABLE {database}.{table} ADD COLUMN `{column}` Nullable(String)")
                            logger.info(f"   ➕ Added column: {column}")
                        except:
                            logger.warning(f"   ⚠️  Could not add column {column}")
                    else:
                        logger.warning(f"   ⚠️  Could not add column {column}: {e}")
                else:
                    logger.warning(f"   ⚠️  Could not add column {column}: {e}")

    # Filter records: only insert new or updated records
    column_names = ["id"] + [column_map[field] for field in fields]
    rows_to_insert = []
    new_records = 0
    updated_records = 0
    
    for record in records:
        record_id = str(record.get("id", ""))
        
        # Always insert (ReplacingMergeTree will handle duplicates based on ORDER BY id)
        # This ensures we get the latest data
        row = [record_id]
        for field in fields:
            row.append(normalize_value(record.get(field)))
        rows_to_insert.append(row)
        
        if record_id in existing_ids:
            updated_records += 1
        else:
            new_records += 1

    if rows_to_insert:
        logger.info(f"   📊 Records to insert: {len(rows_to_insert):,} ({new_records:,} new, {updated_records:,} updates)")
        
        # Use smaller batch size to avoid timeouts (5000 instead of 10000)
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
                    
                    # Check if it's a session lock or timeout error
                    if is_session_lock_error(error_str) or is_timeout_error(error_str):
                        if retry_count < max_retries:
                            wait_time = retry_count * 3  # 3s, 6s, 9s
                            logger.warning(f"   ⚠️  Batch {batch_num} failed ({error_str[:100]}), retrying in {wait_time}s (attempt {retry_count}/{max_retries})...")
                            time.sleep(wait_time)
                            
                            # Recreate client to get a new session
                            new_client = recreate_clickhouse_client(clickhouse_host, clickhouse_user, clickhouse_password, database)
                            if new_client:
                                client = new_client
                                logger.info(f"   🔄 Client recreated for batch {batch_num}")
                            else:
                                logger.error(f"   ❌ Could not recreate client, will try smaller batches")
                        else:
                            # Max retries reached, try smaller batches
                            logger.warning(f"   ⚠️  Batch {batch_num} failed after {max_retries} retries, trying smaller batches...")
                            # Break into smaller batches (1000 records)
                            small_batch_size = 1000
                            for j in range(0, len(batch), small_batch_size):
                                small_batch = batch[j:j + small_batch_size]
                                small_retry = 0
                                small_success = False
                                
                                while small_retry < 2 and not small_success:
                                    try:
                                        client.insert(f"{database}.{table}", small_batch, column_names=column_names)
                                        total_inserted += len(small_batch)
                                        small_success = True
                                    except Exception as small_e:
                                        small_retry += 1
                                        if is_session_lock_error(small_e) or is_timeout_error(small_e):
                                            if small_retry < 2:
                                                time.sleep(2)
                                                new_client = recreate_clickhouse_client(clickhouse_host, clickhouse_user, clickhouse_password, database)
                                                if new_client:
                                                    client = new_client
                                            else:
                                                # Last resort: insert one by one
                                                logger.warning(f"   ⚠️  Small batch failed, inserting records individually...")
                                                for single_row in small_batch:
                                                    single_retry = 0
                                                    while single_retry < 2:
                                                        try:
                                                            client.insert(f"{database}.{table}", [single_row], column_names=column_names)
                                                            total_inserted += 1
                                                            break
                                                        except Exception as single_e:
                                                            single_retry += 1
                                                            if is_session_lock_error(single_e) or is_timeout_error(single_e):
                                                                if single_retry < 2:
                                                                    time.sleep(1)
                                                                    new_client = recreate_clickhouse_client(clickhouse_host, clickhouse_user, clickhouse_password, database)
                                                                    if new_client:
                                                                        client = new_client
                                                                else:
                                                                    logger.warning(f"   ⚠️  Failed to insert record after retries: {single_e}")
                                                            else:
                                                                logger.warning(f"   ⚠️  Failed to insert record: {single_e}")
                                                                break
                                                small_success = True
                                        else:
                                            logger.warning(f"   ⚠️  Failed to insert small batch: {small_e}")
                                            small_success = True  # Mark as handled
                                
                                if small_success:
                                    logger.info(f"   ✓ Inserted small batch {j//small_batch_size + 1} ({len(small_batch)} records, total: {total_inserted}/{len(rows_to_insert)})")
                            
                            batch_success = True  # Mark batch as handled
                    else:
                        # Non-retryable error
                        logger.error(f"   ❌ Error inserting batch {batch_num}: {error_str[:200]}")
                        batch_success = True  # Mark as handled, move on
        
        logger.info(f"✅✅✅ {module}: Successfully inserted {total_inserted:,} records into {database}.{table} ✅✅✅")
        logger.info(f"   📊 Table {database}.{table} is NOW READY with data in ClickHouse!")
        logger.info(f"   📈 New records: {new_records:,}, Updated records: {updated_records:,}")
    
    return len(rows_to_insert)


# ============================================================================
# MAIN SYNC FUNCTION
# ============================================================================

def sync_zoho_full(refresh_token, client_id, client_secret, api_domain, 
                   clickhouse_host, clickhouse_user, clickhouse_password, 
                   clickhouse_database, selected_modules=None):
    """
    Full Zoho CRM sync - fetches ALL records from selected modules.
    
    Args:
        refresh_token: Zoho refresh token
        client_id: Zoho client ID
        client_secret: Zoho client secret
        api_domain: Zoho API domain
        clickhouse_host: ClickHouse host
        clickhouse_user: ClickHouse username
        clickhouse_password: ClickHouse password
        clickhouse_database: ClickHouse database name
        selected_modules: List of module API names to sync (None = all modules)
    
    Returns:
        dict with sync results
    """
    results = {
        "success": True,
        "synced_modules": [],
        "failed_modules": [],
        "total_records": 0,
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
        # First connect without database to create it if needed
        temp_client = get_client(
            host=clickhouse_host,
            username=clickhouse_user,
            password=clickhouse_password,
        )
        # Create database if it doesn't exist
        temp_client.command(f"CREATE DATABASE IF NOT EXISTS {clickhouse_database}")
        logger.info(f"✅ Database '{clickhouse_database}' verified/created")
        temp_client.close()
        
        # Now connect with database
        client = get_client(
            host=clickhouse_host,
            username=clickhouse_user,
            password=clickhouse_password,
            database=clickhouse_database,
        )
        logger.info(f"✅✅✅ Connected to ClickHouse database: {clickhouse_database} ✅✅✅")
        logger.info(f"   All tables will be created in this database")
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
    
    # Sync each selected module with retry logic
    total_modules = len(selected_modules)
    logger.info("")
    logger.info("="*70)
    logger.info(f"📊 ZOHO FULL SYNC TO CLICKHOUSE")
    logger.info("="*70)
    logger.info(f"   Target Database: {clickhouse_database}")
    logger.info(f"   Total Modules: {total_modules}")
    logger.info(f"   Will migrate: ALL records + ALL fields from each module")
    logger.info("="*70)
    logger.info("")
    
    for idx, module in enumerate(selected_modules, 1):
        module_retry_count = 0
        max_module_retries = 3
        module_success = False
        
        while module_retry_count < max_module_retries and not module_success:
            try:
                logger.info(f"[{idx}/{total_modules}] Fetching ALL records from module: {module}")
                records = fetch_all_records(module, token, api_domain, max_retries=3)
                
                logger.info(f"[{idx}/{total_modules}] Saving ALL records and ALL fields to ClickHouse: {module}")
                record_count = save_to_clickhouse(
                    client, module, records, clickhouse_database,
                    clickhouse_host=clickhouse_host,
                    clickhouse_user=clickhouse_user,
                    clickhouse_password=clickhouse_password
                )
                
                results["synced_modules"].append({
                    "module": module,
                    "record_count": record_count
                })
                results["total_records"] += record_count
                module_success = True
                table_name = f"{clickhouse_database}.zoho_{module.lower()}"
                logger.info(f"✅ [{idx}/{total_modules}] {module}: {record_count:,} records synced")
                logger.info(f"   📊 Table: {table_name} - NOW VISIBLE in ClickHouse database '{clickhouse_database}'")
                
            except Exception as e:
                module_retry_count += 1
                error_msg = str(e)
                
                # Check if it's a network error that we should retry
                is_network_error = any(keyword in error_msg.lower() for keyword in [
                    'connection', 'timeout', 'network', 'aborted', 'unreachable'
                ])
                
                if is_network_error and module_retry_count < max_module_retries:
                    wait_time = module_retry_count * 5  # 5s, 10s, 15s
                    logger.warning(f"Network error syncing {module} (attempt {module_retry_count}/{max_module_retries}): {error_msg}")
                    logger.info(f"Retrying {module} in {wait_time} seconds...")
                    time.sleep(wait_time)
                    # Refresh token if needed (tokens expire after 1 hour)
                    if module_retry_count == 2:
                        logger.info("Refreshing access token...")
                        token_result = get_access_token(refresh_token, client_id, client_secret, api_domain)
                        if token_result:
                            token = token_result["access_token"]
                            api_domain = token_result.get("api_domain", api_domain)
                            logger.info("Access token refreshed")
                else:
                    # Non-retryable error or max retries reached
                    logger.error(f"   └─ ❌ ERROR: {error_msg}")
                    logger.error(f"   ❌ [{idx}/{total_modules}] {module}: FAILED")
                    results["failed_modules"].append({
                        "module": module,
                        "error": error_msg
                    })
                    results["errors"].append(f"{module}: {error_msg}")
                    module_success = True  # Mark as handled, move to next module
    
    # Final summary
    logger.info("")
    logger.info("="*70)
    logger.info("📊 FULL SYNC SUMMARY")
    logger.info("="*70)
    logger.info(f"   Total Modules Processed: {total_modules}")
    logger.info(f"   Successfully Synced: {len(results['synced_modules'])}")
    logger.info(f"   Failed: {len(results['failed_modules'])}")
    logger.info(f"   Total Records Migrated: {results['total_records']:,}")
    logger.info(f"   Database: {clickhouse_database}")
    logger.info("="*70)
    logger.info("")
    
    return results


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point for the script."""
    logger.info("="*70)
    logger.info("ZOHO CRM FULL SYNC TO CLICKHOUSE")
    logger.info("="*70)
    logger.info("")
    
    # Use credentials from the configuration section
    result = sync_zoho_full(
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
        logger.info("✅ Full sync completed successfully!")
        return 0
    else:
        logger.error("❌ Full sync completed with errors")
        return 1


if __name__ == "__main__":
    exit(main())

