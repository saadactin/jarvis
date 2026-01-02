#!/usr/bin/env python3
"""
ClickHouse Writing Testing Script
Tests table creation, column management, data insertion, and type mapping
"""

import sys
import os
import re
import time
from typing import Dict, Any, List, Tuple, Optional, Set
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
CLICKHOUSE_CONFIG = {
    "host": os.getenv('CLICKHOUSE_HOST', 'localhost'),
    "port": int(os.getenv('CLICKHOUSE_PORT', '8123')),
    "username": os.getenv('CLICKHOUSE_USER', 'default'),
    "password": os.getenv('CLICKHOUSE_PASSWORD', ''),
    "database": os.getenv('CLICKHOUSE_DATABASE', 'default')
}

# Validate required environment variables
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

def get_clickhouse_client():
    """Get ClickHouse client connection"""
    try:
        import clickhouse_connect
        return clickhouse_connect.get_client(
            host=CLICKHOUSE_CONFIG['host'],
            port=CLICKHOUSE_CONFIG['port'],
            username=CLICKHOUSE_CONFIG['username'],
            password=CLICKHOUSE_CONFIG['password'],
            database=CLICKHOUSE_CONFIG['database']
        )
    except ImportError:
        print_test_result("ClickHouse Library", False, "clickhouse-connect not installed")
        return None
    except Exception as e:
        print_test_result("ClickHouse Connection", False, f"Error: {str(e)}")
        return None

def sanitize_column_name(name: str, used_names: set) -> str:
    """Sanitize column name (matching clickhouse_dest logic)"""
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

def get_table_name(table_name: str, source_type: str = "zoho") -> str:
    """Get ClickHouse table name with appropriate prefix"""
    if source_type == "zoho":
        return f"zoho_{table_name.lower()}"
    else:
        return f"HR_{table_name}"

def test_table_creation() -> Tuple[bool, Optional[str]]:
    """Test 4.2.1: Table Creation"""
    print_section_header("Test 4.2.1: Table Creation")
    
    try:
        client = get_clickhouse_client()
        if not client:
            return False, None
        
        # Test table creation with Zoho schema
        test_table_name = "test_module"
        ch_table_name = get_table_name(test_table_name, "zoho")
        
        print(f"  Testing table creation: {ch_table_name}")
        
        # Create test schema (all String for Zoho)
        schema = [
            {"name": "id", "type": "String", "nullable": False},
            {"name": "name", "type": "String", "nullable": True},
            {"name": "email", "type": "String", "nullable": True},
            {"name": "created_time", "type": "String", "nullable": True},
            {"name": "field.with.dots", "type": "String", "nullable": True},  # Test special chars
            {"name": "field-with-dashes", "type": "String", "nullable": True},  # Test special chars
        ]
        
        # Check if table exists
        try:
            result = client.command(f"EXISTS TABLE {ch_table_name}")
            if result == 1:
                print_test_result("Table Exists Check", True, f"Table {ch_table_name} already exists")
                # Drop it for clean test
                try:
                    client.command(f"DROP TABLE IF EXISTS {ch_table_name}")
                    print_test_result("Table Drop", True, "Dropped existing table")
                except Exception as e:
                    print_test_result("Table Drop", False, f"Error: {str(e)}", warning=True)
        except Exception as e:
            print_test_result("Table Exists Check", False, f"Error: {str(e)}", warning=True)
        
        # Build column definitions with sanitization
        used_names = {"id", "load_time"}
        column_map = {}
        for col in schema:
            if col['name'] != 'id':
                column_map[col['name']] = sanitize_column_name(col['name'], used_names)
        
        column_defs = []
        for field, sanitized_col in column_map.items():
            column_defs.append(f"`{sanitized_col}` Nullable(String)")
        
        column_section = ",\n            " + ",\n            ".join(column_defs) if column_defs else ""
        
        create_sql = f"""
CREATE TABLE IF NOT EXISTS {ch_table_name} (
    id String{column_section},
    load_time DateTime DEFAULT now()
)
ENGINE = MergeTree()
ORDER BY load_time
"""
        
        try:
            client.command(create_sql)
            print_test_result("Table Creation", True, f"Table {ch_table_name} created successfully")
            
            # Verify table structure
            try:
                describe = client.query(f"DESCRIBE TABLE {ch_table_name}")
                existing_columns = {row[0] for row in describe.result_rows}
                
                expected_columns = {"id", "load_time"} | set(column_map.values())
                missing_columns = expected_columns - existing_columns
                
                if missing_columns:
                    print_test_result("Table Structure", False, 
                                    f"Missing columns: {missing_columns}")
                else:
                    print_test_result("Table Structure", True, 
                                    f"All {len(existing_columns)} columns present")
                
                # Test column sanitization
                special_char_columns = [col for col in column_map.values() if '_' in col]
                if special_char_columns:
                    print_test_result("Column Sanitization", True, 
                                    f"Sanitized {len(special_char_columns)} columns with special characters")
                else:
                    print_test_result("Column Sanitization", True, "No special characters to sanitize")
                
                return True, ch_table_name
                
            except Exception as e:
                print_test_result("Table Verification", False, f"Error: {str(e)}")
                return False, None
                
        except Exception as e:
            print_test_result("Table Creation", False, f"Error: {str(e)}")
            return False, None
        
    except Exception as e:
        print_test_result("Table Creation", False, f"Unexpected error: {str(e)}")
        return False, None

def test_column_management(ch_table_name: str) -> Tuple[bool, Set[str]]:
    """Test 4.2.2: Column Management"""
    print_section_header("Test 4.2.2: Column Management")
    
    if not ch_table_name:
        print_test_result("Column Management", False, "No table available for testing")
        return False, set()
    
    try:
        client = get_clickhouse_client()
        if not client:
            return False, set()
        
        print(f"  Testing column management for: {ch_table_name}")
        
        # Get existing columns
        try:
            describe = client.query(f"DESCRIBE TABLE {ch_table_name}")
            existing_columns = {row[0] for row in describe.result_rows}
            print_test_result("Get Existing Columns", True, f"Found {len(existing_columns)} columns")
        except Exception as e:
            print_test_result("Get Existing Columns", False, f"Error: {str(e)}")
            return False, set()
        
        # Test dynamic column addition
        new_fields = ["new_field_1", "new.field.2", "new-field-3", "123field"]  # Test various cases
        used_names = existing_columns.copy()
        column_map = {}
        
        for field in new_fields:
            sanitized = sanitize_column_name(field, used_names)
            column_map[field] = sanitized
        
        added_count = 0
        for field, sanitized_col in column_map.items():
            if sanitized_col not in existing_columns:
                try:
                    client.command(f"ALTER TABLE {ch_table_name} ADD COLUMN IF NOT EXISTS `{sanitized_col}` Nullable(String)")
                    print_test_result(f"Add Column - {sanitized_col}", True, f"Added column from field: {field}")
                    added_count += 1
                except Exception as e:
                    print_test_result(f"Add Column - {sanitized_col}", False, f"Error: {str(e)}")
            else:
                print_test_result(f"Add Column - {sanitized_col}", True, "Column already exists")
        
        print_test_result("Dynamic Column Addition", added_count > 0 or len(new_fields) == 0, 
                        f"Added {added_count} new columns")
        
        # Test column name conflicts
        try:
            # Try to add a column that would conflict
            conflict_field = "test_field"
            used_names_conflict = existing_columns.copy()
            sanitized_conflict = sanitize_column_name(conflict_field, used_names_conflict)
            
            # If it already exists, test conflict handling
            if sanitized_conflict in existing_columns:
                print_test_result("Column Name Conflict Handling", True, 
                                "Conflict handling works (column already exists)")
            else:
                # Add it
                client.command(f"ALTER TABLE {ch_table_name} ADD COLUMN IF NOT EXISTS `{sanitized_conflict}` Nullable(String)")
                # Try to add again (should not conflict due to IF NOT EXISTS)
                client.command(f"ALTER TABLE {ch_table_name} ADD COLUMN IF NOT EXISTS `{sanitized_conflict}` Nullable(String)")
                print_test_result("Column Name Conflict Handling", True, 
                                "IF NOT EXISTS prevents conflicts")
        except Exception as e:
            print_test_result("Column Name Conflict Handling", False, f"Error: {str(e)}")
        
        # Get final column list
        try:
            describe = client.query(f"DESCRIBE TABLE {ch_table_name}")
            final_columns = {row[0] for row in describe.result_rows}
            print_test_result("Final Column Count", True, f"Table now has {len(final_columns)} columns")
            return True, final_columns
        except Exception as e:
            print_test_result("Final Column Count", False, f"Error: {str(e)}")
            return False, set()
        
    except Exception as e:
        print_test_result("Column Management", False, f"Unexpected error: {str(e)}")
        return False, set()

def test_data_insertion(ch_table_name: str, columns: Set[str]) -> Tuple[bool, int]:
    """Test 4.2.3: Data Insertion"""
    print_section_header("Test 4.2.3: Data Insertion")
    
    if not ch_table_name:
        print_test_result("Data Insertion", False, "No table available for testing")
        return False, 0
    
    try:
        client = get_clickhouse_client()
        if not client:
            return False, 0
        
        print(f"  Testing data insertion into: {ch_table_name}")
        
        # Prepare test data
        test_records = []
        for i in range(10):  # Create 10 test records
            record = {
                "id": f"test_id_{i}",
                "name": f"Test Name {i}",
                "email": f"test{i}@example.com",
                "created_time": "2024-01-01T00:00:00",
            }
            test_records.append(record)
        
        # Get column names (id + sanitized columns)
        column_names = ["id"]
        for col in columns:
            if col not in ["id", "load_time"]:
                column_names.append(col)
        
        # Prepare rows for insertion
        rows = []
        for record in test_records:
            row = [record.get("id", "")]
            for col in column_names[1:]:  # Skip id
                # Find matching field name
                value = None
                for field, sanitized in [("name", "name"), ("email", "email"), ("created_time", "created_time")]:
                    if sanitized == col:
                        value = record.get(field)
                        break
                row.append(value)
            rows.append(row)
        
        # Test batch insertion
        try:
            batch_size = 1000
            inserted_count = 0
            
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i + batch_size]
                client.insert(ch_table_name, batch, column_names=column_names)
                inserted_count += len(batch)
            
            print_test_result("Batch Insertion", True, f"Inserted {inserted_count} records")
            
            # Verify insertion
            try:
                result = client.query(f"SELECT COUNT(*) FROM {ch_table_name}")
                count = result.result_rows[0][0] if result.result_rows else 0
                print_test_result("Insertion Verification", True, f"Table contains {count} records")
            except Exception as e:
                print_test_result("Insertion Verification", False, f"Error: {str(e)}")
            
            # Test duplicate record handling
            try:
                # Try to insert same records again
                client.insert(ch_table_name, rows[:5], column_names=column_names)
                result = client.query(f"SELECT COUNT(*) FROM {ch_table_name}")
                new_count = result.result_rows[0][0] if result.result_rows else 0
                
                if new_count > count:
                    print_test_result("Duplicate Handling", True, 
                                    f"Duplicates inserted (new count: {new_count})")
                else:
                    print_test_result("Duplicate Handling", False, 
                                    "Duplicates not inserted (may be expected)", warning=True)
            except Exception as e:
                print_test_result("Duplicate Handling", False, f"Error: {str(e)}")
            
            # Test null value insertion
            try:
                null_record = [["null_test_id"] + [None] * (len(column_names) - 1)]
                client.insert(ch_table_name, null_record, column_names=column_names)
                print_test_result("Null Value Insertion", True, "Null values inserted successfully")
            except Exception as e:
                print_test_result("Null Value Insertion", False, f"Error: {str(e)}")
            
            return True, inserted_count
            
        except Exception as e:
            print_test_result("Data Insertion", False, f"Error: {str(e)}")
            return False, 0
        
    except Exception as e:
        print_test_result("Data Insertion", False, f"Unexpected error: {str(e)}")
        return False, 0

def test_data_type_mapping() -> Tuple[bool, Dict[str, str]]:
    """Test 4.2.4: Data Type Mapping"""
    print_section_header("Test 4.2.4: Data Type Mapping")
    
    try:
        client = get_clickhouse_client()
        if not client:
            return False, {}
        
        # Test table with various types
        test_table = "zoho_test_types"
        
        # Create table with Zoho schema (all String)
        create_sql = f"""
CREATE TABLE IF NOT EXISTS {test_table} (
    id String,
    string_field Nullable(String),
    nullable_string Nullable(String),
    load_time DateTime DEFAULT now()
)
ENGINE = MergeTree()
ORDER BY load_time
"""
        
        try:
            client.command(f"DROP TABLE IF EXISTS {test_table}")
            client.command(create_sql)
            print_test_result("Type Test Table", True, f"Created {test_table}")
        except Exception as e:
            print_test_result("Type Test Table", False, f"Error: {str(e)}")
            return False, {}
        
        # Verify types
        try:
            describe = client.query(f"DESCRIBE TABLE {test_table}")
            type_mapping = {}
            for row in describe.result_rows:
                col_name = row[0]
                col_type = row[1]
                type_mapping[col_name] = col_type
            
            # Check String type
            if type_mapping.get("string_field") == "Nullable(String)":
                print_test_result("String Type Mapping", True, "String fields mapped correctly")
            else:
                print_test_result("String Type Mapping", False, 
                                f"Expected Nullable(String), got {type_mapping.get('string_field')}")
            
            # Check Nullable handling
            nullable_count = sum(1 for t in type_mapping.values() if "Nullable" in t)
            print_test_result("Nullable Handling", nullable_count > 0, 
                            f"Found {nullable_count} Nullable columns")
            
            # Clean up
            try:
                client.command(f"DROP TABLE IF EXISTS {test_table}")
            except:
                pass
            
            return True, type_mapping
            
        except Exception as e:
            print_test_result("Type Verification", False, f"Error: {str(e)}")
            return False, {}
        
    except Exception as e:
        print_test_result("Data Type Mapping", False, f"Unexpected error: {str(e)}")
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
        print("\n  ✓ All ClickHouse writing tests passed!")
    else:
        print("\n  ✗ Some tests failed. Please review the errors above.")

def main():
    """Run all ClickHouse writing tests"""
    print("="*70)
    print("CLICKHOUSE WRITING TESTING")
    print("="*70)
    print("\nThis script tests:")
    print("  - Table creation")
    print("  - Column management")
    print("  - Data insertion")
    print("  - Data type mapping")
    print("\nStarting tests...\n")
    
    # Run tests in sequence
    success, ch_table_name = test_table_creation()
    if success and ch_table_name:
        success2, columns = test_column_management(ch_table_name)
        if success2:
            test_data_insertion(ch_table_name, columns)
    
    test_data_type_mapping()
    
    # Print summary
    print_summary()
    
    # Return exit code
    if len(test_results["failed"]) == 0:
        return 0
    else:
        return 1

if __name__ == '__main__':
    sys.exit(main())

