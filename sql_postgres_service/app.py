"""
Flask Microservice for SQL Server to PostgreSQL Migration
Uses the scripts from Scripts/sql_postgres folder
Accepts credentials in request body and performs full or incremental migration
"""

from flask import Flask, request, jsonify
import sys
import os
import logging
import importlib.util
import tempfile
import yaml
from pathlib import Path

# Add Scripts directory to path
scripts_path = os.path.join(os.path.dirname(__file__), '..', 'Scripts', 'sql_postgres')
sys.path.insert(0, scripts_path)

app = Flask(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import the migration modules dynamically
full_migration_module = None
incremental_migration_module = None

try:
    # Import full migration module
    full_migration_path = os.path.join(scripts_path, 'final_full_sql_post.py')
    if os.path.exists(full_migration_path):
        spec_full = importlib.util.spec_from_file_location("final_full_sql_post", full_migration_path)
        full_migration_module = importlib.util.module_from_spec(spec_full)
        spec_full.loader.exec_module(full_migration_module)
        logger.info("Successfully loaded final_full_sql_post module")
    else:
        logger.error(f"Full migration script not found at: {full_migration_path}")
    
    # Import incremental migration module
    inc_migration_path = os.path.join(scripts_path, 'final_incre_sql_post.py')
    if os.path.exists(inc_migration_path):
        spec_inc = importlib.util.spec_from_file_location("final_incre_sql_post", inc_migration_path)
        incremental_migration_module = importlib.util.module_from_spec(spec_inc)
        spec_inc.loader.exec_module(incremental_migration_module)
        logger.info("Successfully loaded final_incre_sql_post module")
    else:
        logger.error(f"Incremental script not found at: {inc_migration_path}")
    
    if not full_migration_module or not incremental_migration_module:
        logger.warning("One or more migration modules failed to load")
        
except Exception as e:
    logger.error(f"Error loading migration modules: {str(e)}")
    logger.exception("Full error traceback:")


def create_temp_config(sql_config: dict, pg_config: dict) -> str:
    """Create a temporary YAML config file from request credentials"""
    config = {
        'sqlservers': {
            'temp_server': {
                'server': sql_config.get('server', sql_config.get('host', 'localhost')),
                'username': sql_config.get('username', ''),
                'password': sql_config.get('password', ''),
                'target_postgres_db': {
                    'host': pg_config.get('host', 'localhost'),
                    'port': pg_config.get('port', 5432),
                    'database': pg_config.get('database'),
                    'username': pg_config.get('username'),
                    'password': pg_config.get('password')
                }
            }
        },
        'postgresql': {
            'host': pg_config.get('host', 'localhost'),
            'port': pg_config.get('port', 5432),
            'database': pg_config.get('database'),
            'username': pg_config.get('username'),
            'password': pg_config.get('password')
        }
    }
    
    # Create temp config file
    temp_dir = tempfile.gettempdir()
    config_path = os.path.join(temp_dir, f'sql_postgres_config_{os.getpid()}.yaml')
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    return config_path


def perform_full_migration(sql_config: dict, pg_config: dict) -> dict:
    """Perform full migration using the final_full_sql_post script"""
    if not full_migration_module:
        return {
            "success": False,
            "databases_processed": [],
            "databases_failed": [],
            "total_databases": 0,
            "errors": ["Full migration module not loaded. Check server logs."]
        }
    
    results = {
        "success": True,
        "databases_processed": [],
        "databases_failed": [],
        "total_databases": 0,
        "errors": []
    }
    
    config_path = None
    try:
        # Create temporary config file
        config_path = create_temp_config(sql_config, pg_config)
        
        # Temporarily override CONFIG_PATH in the module
        original_config_path = full_migration_module.CONFIG_PATH
        full_migration_module.CONFIG_PATH = config_path
        
        # Create server config dict
        server_conf = {
            'server': sql_config.get('server', sql_config.get('host', 'localhost')),
            'username': sql_config.get('username', ''),
            'password': sql_config.get('password', ''),
            'target_postgres_db': {
                'host': pg_config.get('host', 'localhost'),
                'port': pg_config.get('port', 5432),
                'database': pg_config.get('database'),
                'username': pg_config.get('username'),
                'password': pg_config.get('password')
            }
        }
        
        # Perform migration
        logger.info("Starting full SQL Server to PostgreSQL migration")
        full_migration_module.process_sql_server_full('temp_server', server_conf)
        
        results["success"] = True
        results["databases_processed"] = ["All databases"]  # Script processes all databases
        logger.info("Full migration completed successfully")
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Full migration failed: {error_msg}")
        results["success"] = False
        results["errors"].append(error_msg)
    finally:
        # Restore original config path
        if full_migration_module and hasattr(full_migration_module, 'CONFIG_PATH'):
            full_migration_module.CONFIG_PATH = original_config_path
        
        # Clean up temp config file
        if config_path and os.path.exists(config_path):
            try:
                os.remove(config_path)
            except:
                pass
    
    return results


def perform_incremental_migration(sql_config: dict, pg_config: dict) -> dict:
    """Perform incremental migration using the final_incre_sql_post script"""
    if not incremental_migration_module:
        return {
            "success": False,
            "databases_processed": [],
            "databases_failed": [],
            "total_databases": 0,
            "errors": ["Incremental migration module not loaded. Check server logs."]
        }
    
    results = {
        "success": True,
        "databases_processed": [],
        "databases_failed": [],
        "total_databases": 0,
        "errors": []
    }
    
    config_path = None
    try:
        # Create temporary config file
        config_path = create_temp_config(sql_config, pg_config)
        
        # Temporarily override CONFIG_PATH in the module
        original_config_path = incremental_migration_module.CONFIG_PATH
        incremental_migration_module.CONFIG_PATH = config_path
        
        # Create server config dict
        server_conf = {
            'server': sql_config.get('server', sql_config.get('host', 'localhost')),
            'username': sql_config.get('username', ''),
            'password': sql_config.get('password', ''),
            'target_postgres_db': {
                'host': pg_config.get('host', 'localhost'),
                'port': pg_config.get('port', 5432),
                'database': pg_config.get('database'),
                'username': pg_config.get('username'),
                'password': pg_config.get('password')
            }
        }
        
        # Perform incremental migration
        logger.info("Starting incremental SQL Server to PostgreSQL migration")
        incremental_migration_module.process_sql_server_incremental('temp_server', server_conf)
        
        results["success"] = True
        results["databases_processed"] = ["All databases"]  # Script processes all databases
        logger.info("Incremental migration completed successfully")
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Incremental migration failed: {error_msg}")
        results["success"] = False
        results["errors"].append(error_msg)
    finally:
        # Restore original config path
        if incremental_migration_module and hasattr(incremental_migration_module, 'CONFIG_PATH'):
            incremental_migration_module.CONFIG_PATH = original_config_path
        
        # Clean up temp config file
        if config_path and os.path.exists(config_path):
            try:
                os.remove(config_path)
            except:
                pass
    
    return results


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "sql_postgres_migration",
        "modules_loaded": {
            "full_migration": full_migration_module is not None,
            "incremental_migration": incremental_migration_module is not None
        }
    }), 200


@app.route('/migrate/full', methods=['POST'])
def full_migration():
    """Full migration endpoint - accepts credentials in request body"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        # Validate SQL Server config
        sql_config = data.get('sql_server')
        if not sql_config:
            return jsonify({"error": "sql_server configuration is required"}), 400
        
        required_sql_fields = ['server', 'username', 'password']
        for field in required_sql_fields:
            if field not in sql_config:
                return jsonify({"error": f"sql_server.{field} is required"}), 400
        
        # Validate PostgreSQL config
        pg_config = data.get('postgres')
        if not pg_config:
            return jsonify({"error": "postgres configuration is required"}), 400
        
        required_pg_fields = ['host', 'database', 'username', 'password']
        for field in required_pg_fields:
            if field not in pg_config:
                return jsonify({"error": f"postgres.{field} is required"}), 400
        
        # Perform migration
        result = perform_full_migration(sql_config, pg_config)
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
        
    except Exception as e:
        logger.error(f"Error in full_migration endpoint: {str(e)}")
        return jsonify({"error": str(e), "success": False}), 500


@app.route('/migrate/incremental', methods=['POST'])
def incremental_migration():
    """Incremental migration endpoint - accepts credentials in request body"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        # Validate SQL Server config
        sql_config = data.get('sql_server')
        if not sql_config:
            return jsonify({"error": "sql_server configuration is required"}), 400
        
        required_sql_fields = ['server', 'username', 'password']
        for field in required_sql_fields:
            if field not in sql_config:
                return jsonify({"error": f"sql_server.{field} is required"}), 400
        
        # Validate PostgreSQL config
        pg_config = data.get('postgres')
        if not pg_config:
            return jsonify({"error": "postgres configuration is required"}), 400
        
        required_pg_fields = ['host', 'database', 'username', 'password']
        for field in required_pg_fields:
            if field not in pg_config:
                return jsonify({"error": f"postgres.{field} is required"}), 400
        
        # Perform incremental migration
        result = perform_incremental_migration(sql_config, pg_config)
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
        
    except Exception as e:
        logger.error(f"Error in incremental_migration endpoint: {str(e)}")
        return jsonify({"error": str(e), "success": False}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003, debug=True)
