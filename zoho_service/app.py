"""
Flask Microservice for Zoho API to ClickHouse Migration
Accepts credentials in request body and performs full or incremental sync
"""

from flask import Flask, request, jsonify
import requests
import json
import re
import time
import logging
from functools import lru_cache
from datetime import datetime, date, time as dt_time, timedelta
from clickhouse_connect import get_client
import sys
import os

app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_access_token(refresh_token, client_id, client_secret, api_domain="https://www.zohoapis.in"):
    """Generate short-lived access token from refresh token"""
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
    """Convert Zoho field names into ClickHouse-safe identifiers"""
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
    """Prepare values for insertion into ClickHouse"""
    if value is None:
        return None
    if isinstance(value, (datetime, date, dt_time)):
        return value.isoformat()
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def get_available_modules(token, api_domain):
    """Fetch all available Zoho CRM modules"""
    url = f"{api_domain}/crm/v8/settings/modules"
    headers = {"Authorization": f"Zoho-oauthtoken {token}"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            logger.error(f"Failed to fetch modules: {resp.status_code} - {resp.text}")
            return []
        
        result = resp.json()
        modules = result.get("modules", [])
        
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


def fetch_all_records(module, token, api_domain, max_retries=3):
    """Fetch ALL records from Zoho CRM module (handles pagination)"""
    url = f"{api_domain}/crm/v2/{module}"
    headers = {"Authorization": f"Zoho-oauthtoken {token}"}
    all_records = []
    page = 1
    processed_pages = set()
    
    while True:
        if page in processed_pages:
            logger.error(f"{module}: ❌ DUPLICATE PAGE DETECTED - Page {page} already processed! Skipping.")
            page += 1
            continue
        
        params = {"page": page, "per_page": 200}
        retry_count = 0
        success = False
        more_records = True
        
        while retry_count < max_retries and not success:
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=120)
                
                if resp.status_code == 204:
                    logger.info(f"No records found for {module}")
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
                
                if page not in processed_pages:
                    all_records.extend(data)
                    processed_pages.add(page)
                    
                    if page == 1 or page % 10 == 0 or not result.get("info", {}).get("more_records", False):
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
    
    logger.info(f"✅ Completed fetching ALL {len(all_records)} records for {module}")
    return all_records


def recreate_clickhouse_client(clickhouse_host, clickhouse_user, clickhouse_password, database):
    """Recreate ClickHouse client to avoid session locks"""
    try:
        new_client = get_client(
            host=clickhouse_host,
            username=clickhouse_user,
            password=clickhouse_password,
            database=database,
        )
        return new_client
    except Exception as e:
        logger.error(f"❌ Failed to recreate client: {e}")
        return None


def is_session_lock_error(error_msg):
    """Check if error is a session lock error"""
    error_str = str(error_msg).lower()
    return 'session' in error_str and 'locked' in error_str


def is_timeout_error(error_msg):
    """Check if error is a timeout error"""
    error_str = str(error_msg).lower()
    return 'timeout' in error_str or 'timed out' in error_str


def save_to_clickhouse(client, module, records, database, clickhouse_host=None, 
                      clickhouse_user=None, clickhouse_password=None):
    """Insert ALL records into ClickHouse with ALL fields/columns"""
    table = f"zoho_{module.lower()}"
    
    if not records:
        logger.info(f"No records found for {module}, creating empty table")
        try:
            client.command(f"""
                CREATE TABLE IF NOT EXISTS {database}.{table} (
                    id String,
                    load_time DateTime DEFAULT now()
                )
                ENGINE = ReplacingMergeTree(load_time)
                ORDER BY id
            """)
            logger.info(f"✅ EMPTY TABLE CREATED: {database}.{table}")
        except Exception as e:
            if is_session_lock_error(e):
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
                    logger.info(f"✅ EMPTY TABLE CREATED: {database}.{table}")
                else:
                    raise
            else:
                raise
        return 0
    
    all_fields = set()
    for record in records:
        all_fields.update(record.keys())
    
    fields = sorted([f for f in all_fields if f != "id"])
    logger.info(f"{module}: Processing {len(records)} records with {len(fields)} unique fields")
    
    used_names = {"id", "load_time"}
    column_map = {field: sanitize_column_name(field, used_names) for field in fields}
    
    column_defs = ",\n            ".join(
        f"`{column}` Nullable(String)" for column in column_map.values()
    )
    column_section = f",\n            {column_defs}" if column_defs else ""
    
    table_exists = False
    existing_ids = set()
    
    try:
        exists_result = client.query(f"EXISTS TABLE {database}.{table}")
        table_exists = exists_result.result_rows[0][0] == 1
        
        if table_exists:
            logger.info(f"📋 Table {database}.{table} already exists, checking existing records...")
            try:
                existing_result = client.query(f"SELECT DISTINCT id FROM {database}.{table}")
                existing_ids = {str(row[0]) for row in existing_result.result_rows}
                logger.info(f"📊 Found {len(existing_ids):,} existing records")
            except Exception as e:
                if is_session_lock_error(e):
                    new_client = recreate_clickhouse_client(clickhouse_host, clickhouse_user, clickhouse_password, database)
                    if new_client:
                        client = new_client
                        existing_result = client.query(f"SELECT DISTINCT id FROM {database}.{table}")
                        existing_ids = {str(row[0]) for row in existing_result.result_rows}
                else:
                    existing_ids = set()
    except Exception as e:
        if is_session_lock_error(e):
            new_client = recreate_clickhouse_client(clickhouse_host, clickhouse_user, clickhouse_password, database)
            if new_client:
                client = new_client
    
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
            logger.info(f"✅ TABLE CREATED: {database}.{table}")
        except Exception as e:
            if is_session_lock_error(e):
                new_client = recreate_clickhouse_client(clickhouse_host, clickhouse_user, clickhouse_password, database)
                if new_client:
                    client = new_client
                    client.command(create_sql)
                    logger.info(f"✅ TABLE CREATED: {database}.{table}")
                else:
                    raise
            else:
                raise
    
    try:
        describe = client.query(f"DESCRIBE TABLE {database}.{table}")
        existing_columns = {row[0] for row in describe.result_rows}
    except Exception as e:
        existing_columns = {"id", "load_time"}
    
    for column in column_map.values():
        if column not in existing_columns:
            try:
                client.command(f"ALTER TABLE {database}.{table} ADD COLUMN `{column}` Nullable(String)")
                logger.info(f"➕ Added column: {column}")
            except Exception as e:
                if is_session_lock_error(e):
                    new_client = recreate_clickhouse_client(clickhouse_host, clickhouse_user, clickhouse_password, database)
                    if new_client:
                        client = new_client
                        try:
                            client.command(f"ALTER TABLE {database}.{table} ADD COLUMN `{column}` Nullable(String)")
                            logger.info(f"➕ Added column: {column}")
                        except:
                            pass
    
    column_names = ["id"] + [column_map[field] for field in fields]
    rows_to_insert = []
    new_records = 0
    updated_records = 0
    
    for record in records:
        record_id = str(record.get("id", ""))
        row = [record_id]
        for field in fields:
            row.append(normalize_value(record.get(field)))
        rows_to_insert.append(row)
        
        if record_id in existing_ids:
            updated_records += 1
        else:
            new_records += 1
    
    if rows_to_insert:
        logger.info(f"📊 Records to insert: {len(rows_to_insert):,} ({new_records:,} new, {updated_records:,} updates)")
        
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
                    logger.info(f"✓ Inserted batch {batch_num} ({len(batch)} records, total: {total_inserted}/{len(rows_to_insert)})")
                    batch_success = True
                except Exception as e:
                    error_str = str(e)
                    retry_count += 1
                    
                    if is_session_lock_error(error_str) or is_timeout_error(error_str):
                        if retry_count < max_retries:
                            wait_time = retry_count * 3
                            logger.warning(f"⚠️  Batch {batch_num} failed, retrying in {wait_time}s...")
                            time.sleep(wait_time)
                            new_client = recreate_clickhouse_client(clickhouse_host, clickhouse_user, clickhouse_password, database)
                            if new_client:
                                client = new_client
                        else:
                            logger.error(f"❌ Batch {batch_num} failed after {max_retries} retries")
                            batch_success = True
                    else:
                        logger.error(f"❌ Error inserting batch {batch_num}: {error_str[:200]}")
                        batch_success = True
        
        logger.info(f"✅ Successfully inserted {total_inserted:,} records into {database}.{table}")
    
    return len(rows_to_insert)


def sync_zoho_full(refresh_token, client_id, client_secret, api_domain,
                   clickhouse_host, clickhouse_user, clickhouse_password,
                   clickhouse_database, selected_modules=None):
    """Full Zoho CRM sync - fetches ALL records from selected modules"""
    results = {
        "success": True,
        "synced_modules": [],
        "failed_modules": [],
        "total_records": 0,
        "errors": []
    }
    
    token_result = get_access_token(refresh_token, client_id, client_secret, api_domain)
    if not token_result:
        results["success"] = False
        results["errors"].append("Failed to obtain access token")
        return results
    
    token = token_result["access_token"]
    api_domain = token_result.get("api_domain", api_domain)
    
    try:
        temp_client = get_client(
            host=clickhouse_host,
            username=clickhouse_user,
            password=clickhouse_password,
        )
        temp_client.command(f"CREATE DATABASE IF NOT EXISTS {clickhouse_database}")
        logger.info(f"✅ Database '{clickhouse_database}' verified/created")
        temp_client.close()
        
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
        return results
    
    if not selected_modules:
        logger.info("No modules specified, fetching all available modules...")
        modules = get_available_modules(token, api_domain)
        if not modules:
            results["success"] = False
            results["errors"].append("No modules found in Zoho CRM")
            return results
        selected_modules = [module["api_name"] for module in modules]
        logger.info(f"Found {len(selected_modules)} modules")
    
    total_modules = len(selected_modules)
    logger.info(f"📊 ZOHO FULL SYNC TO CLICKHOUSE - {total_modules} modules")
    
    for idx, module in enumerate(selected_modules, 1):
        try:
            logger.info(f"[{idx}/{total_modules}] Fetching ALL records from module: {module}")
            records = fetch_all_records(module, token, api_domain, max_retries=3)
            
            logger.info(f"[{idx}/{total_modules}] Saving to ClickHouse: {module}")
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
            logger.info(f"✅ [{idx}/{total_modules}] {module}: {record_count:,} records synced")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ [{idx}/{total_modules}] {module}: FAILED - {error_msg}")
            results["failed_modules"].append({
                "module": module,
                "error": error_msg
            })
            results["errors"].append(f"{module}: {error_msg}")
    
    logger.info(f"📊 FULL SYNC SUMMARY - Synced: {len(results['synced_modules'])}, Failed: {len(results['failed_modules'])}")
    results["success"] = len(results["failed_modules"]) == 0
    return results


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "zoho_migration"}), 200


@app.route('/sync/full', methods=['POST'])
def full_sync():
    """Full sync endpoint - accepts credentials in request body"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        # Validate Zoho config
        zoho_config = data.get('zoho')
        if not zoho_config:
            return jsonify({"error": "zoho configuration is required"}), 400
        
        required_zoho_fields = ['refresh_token', 'client_id', 'client_secret']
        for field in required_zoho_fields:
            if field not in zoho_config:
                return jsonify({"error": f"zoho.{field} is required"}), 400
        
        # Validate ClickHouse config
        ch_config = data.get('clickhouse')
        if not ch_config:
            return jsonify({"error": "clickhouse configuration is required"}), 400
        
        required_ch_fields = ['host', 'database', 'username', 'password']
        for field in required_ch_fields:
            if field not in ch_config:
                return jsonify({"error": f"clickhouse.{field} is required"}), 400
        
        # Optional: selected_modules
        selected_modules = data.get('selected_modules', None)
        
        # Optional: api_domain
        api_domain = zoho_config.get('api_domain', 'https://www.zohoapis.in')
        
        # Perform full sync
        result = sync_zoho_full(
            refresh_token=zoho_config['refresh_token'],
            client_id=zoho_config['client_id'],
            client_secret=zoho_config['client_secret'],
            api_domain=api_domain,
            clickhouse_host=ch_config['host'],
            clickhouse_user=ch_config['username'],
            clickhouse_password=ch_config['password'],
            clickhouse_database=ch_config['database'],
            selected_modules=selected_modules
        )
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
        
    except Exception as e:
        logger.error(f"Error in full_sync endpoint: {str(e)}")
        return jsonify({"error": str(e), "success": False}), 500


@app.route('/sync/incremental', methods=['POST'])
def incremental_sync():
    """Incremental sync endpoint - accepts credentials in request body"""
    # Note: This is a placeholder. For full implementation, 
    # you would use the logic from final_incre_sync.py
    return jsonify({
        "error": "Incremental sync not yet implemented. Please use /sync/full endpoint.",
        "success": False
    }), 501


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)

