"""
Universal Migration Service - Single service for all database migrations
"""
from flask import Flask, request, jsonify
from pipeline_engine import UniversalPipelineEngine
from adapters.sources.postgresql_source import PostgreSQLSourceAdapter
from adapters.sources.mysql_source import MySQLSourceAdapter
from adapters.sources.zoho_source import ZohoSourceAdapter
from adapters.sources.sqlserver_source import SQLServerSourceAdapter
from adapters.sources.devops_source import DevOpsSourceAdapter
from adapters.destinations.clickhouse_dest import ClickHouseDestinationAdapter
from adapters.destinations.postgresql_dest import PostgreSQLDestinationAdapter
from adapters.destinations.mysql_dest import MySQLDestinationAdapter
from datetime import datetime
import logging
import os
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path, encoding='utf-8')
else:
    load_dotenv(encoding='utf-8')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize pipeline engine
pipeline = UniversalPipelineEngine()

# Register all source adapters
pipeline.register_source("postgresql", PostgreSQLSourceAdapter)
pipeline.register_source("mysql", MySQLSourceAdapter)
pipeline.register_source("zoho", ZohoSourceAdapter)
pipeline.register_source("sqlserver", SQLServerSourceAdapter)
pipeline.register_source("devops", DevOpsSourceAdapter)
# Add more source adapters here as they are created
# pipeline.register_source("mongodb", MongoDBSourceAdapter)
# pipeline.register_source("cassandra", CassandraSourceAdapter)

# Register all destination adapters
pipeline.register_destination("clickhouse", ClickHouseDestinationAdapter)
pipeline.register_destination("postgresql", PostgreSQLDestinationAdapter)
pipeline.register_destination("mysql", MySQLDestinationAdapter)
# Add more destination adapters here as they are created
# pipeline.register_destination("sqlserver", SQLServerDestinationAdapter)


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "universal_migration_service",
        "available_sources": pipeline.get_available_sources(),
        "available_destinations": pipeline.get_available_destinations()
    }), 200


@app.route('/migrate', methods=['POST'])
def migrate():
    """
    Universal migration endpoint
    
    Request body:
    {
        "source_type": "postgresql",
        "dest_type": "clickhouse",
        "source": {
            "host": "...",
            "port": 5432,
            "database": "...",
            "username": "...",
            "password": "..."
        },
        "destination": {
            "host": "...",
            "port": 8123,
            "database": "...",
            "username": "...",
            "password": "..."
        },
        "operation_type": "full" | "incremental",
        "last_sync_time": "2024-01-01T00:00:00"  // Optional, required for incremental
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        # Validate required fields
        required_fields = ['source_type', 'dest_type', 'source', 'destination']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"{field} is required"}), 400
        
        source_type = data['source_type']
        dest_type = data['dest_type']
        source_config = data['source']
        dest_config = data['destination']
        operation_type = data.get('operation_type', 'full')
        
        # Validate operation type
        if operation_type not in ['full', 'incremental']:
            return jsonify({"error": "operation_type must be 'full' or 'incremental'"}), 400
        
        # Parse last_sync_time for incremental
        last_sync_time = None
        if operation_type == 'incremental':
            if 'last_sync_time' not in data:
                return jsonify({"error": "last_sync_time is required for incremental migration"}), 400
            try:
                last_sync_time = datetime.fromisoformat(data['last_sync_time'].replace('Z', '+00:00'))
            except ValueError as e:
                return jsonify({"error": f"Invalid last_sync_time format: {str(e)}"}), 400
        
        # Execute migration with comprehensive error handling
        logger.info(f"Starting migration: {source_type} → {dest_type} ({operation_type})")
        logger.info(f"Source config keys: {list(source_config.keys())}")
        logger.info(f"Destination config keys: {list(dest_config.keys())}")
        
        try:
            result = pipeline.migrate(
                source_config=source_config,
                dest_config=dest_config,
                source_type=source_type,
                dest_type=dest_type,
                operation_type=operation_type,
                last_sync_time=last_sync_time
            )
            
            # Log detailed results
            logger.info(f"Migration completed. Success: {result.get('success')}, "
                       f"Total tables: {result.get('total_tables')}, "
                       f"Migrated: {len(result.get('tables_migrated', []))}, "
                       f"Failed: {len(result.get('tables_failed', []))}")
            
            if result.get('tables_migrated'):
                migrated_tables = [t.get('table') for t in result.get('tables_migrated', [])]
                logger.info(f"Successfully migrated {len(migrated_tables)} tables: {migrated_tables[:10]}{'...' if len(migrated_tables) > 10 else ''}")
            if result.get('tables_failed'):
                failed_tables = [t.get('table') for t in result.get('tables_failed', [])]
                logger.warning(f"Failed {len(failed_tables)} tables: {failed_tables[:10]}{'...' if len(failed_tables) > 10 else ''}")
            
            status_code = 200 if result['success'] else 500
            return jsonify(result), status_code
            
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            # Check if it's a same source/destination error
            if "cannot be the same" in str(e).lower():
                return jsonify({"error": str(e), "success": False}), 400
            return jsonify({"error": str(e), "success": False}), 400
        except Exception as e:
            import traceback
            logger.error("="*80)
            logger.error("MIGRATION ENDPOINT ERROR")
            logger.error(f"Source Type: {source_type}")
            logger.error(f"Destination Type: {dest_type}")
            logger.error(f"Operation Type: {operation_type}")
            logger.error(f"Error Type: {type(e).__name__}")
            logger.error(f"Error Message: {str(e)}")
            logger.error(f"Stack Trace:")
            logger.error(traceback.format_exc())
            logger.error("="*80)
            
            logger.exception(f"Unexpected error during migration: {str(e)}")
            return jsonify({
                "error": str(e),
                "error_type": type(e).__name__,
                "success": False,
                "tables_migrated": [],
                "tables_failed": [],
                "total_tables": 0,
                "errors": [f"{type(e).__name__}: {str(e)}"]
            }), 500
    
    except Exception as e:
        logger.exception(f"Error in migrate endpoint: {str(e)}")
        return jsonify({
            "error": str(e),
            "success": False
        }), 500


@app.route('/test-connection', methods=['POST'])
def test_connection():
    """
    Test connection to source or destination
    
    Request body:
    {
        "type": "source" | "destination",
        "adapter_type": "postgresql",
        "config": {
            "host": "...",
            ...
        }
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        conn_type = data.get('type')  # 'source' or 'destination'
        adapter_type = data.get('adapter_type')
        config = data.get('config')
        
        if not all([conn_type, adapter_type, config]):
            return jsonify({"error": "type, adapter_type, and config are required"}), 400
        
        if conn_type == 'source':
            adapter_class = pipeline.source_registry.get(adapter_type)
        elif conn_type == 'destination':
            adapter_class = pipeline.dest_registry.get(adapter_type)
        else:
            return jsonify({"error": "type must be 'source' or 'destination'"}), 400
        
        if not adapter_class:
            return jsonify({"error": f"Unknown adapter type: {adapter_type}"}), 400
        
        # Test connection
        adapter = adapter_class()
        try:
            is_valid = adapter.test_connection(config)
            return jsonify({"valid": is_valid}), 200
        except Exception as e:
            return jsonify({"valid": False, "error": str(e)}), 200
        
    except Exception as e:
        logger.error(f"Connection test error: {str(e)}")
        return jsonify({"error": str(e), "valid": False}), 500


if __name__ == '__main__':
    # Get port from environment variable, default to 5011
    service_port = int(os.getenv('UNIVERSAL_MIGRATION_SERVICE_PORT', 5011))
    service_host = os.getenv('UNIVERSAL_MIGRATION_SERVICE_HOST', '0.0.0.0')
    
    logger.info("Starting Universal Migration Service...")
    logger.info(f"Available sources: {pipeline.get_available_sources()}")
    logger.info(f"Available destinations: {pipeline.get_available_destinations()}")
    logger.info(f"Service will run on {service_host}:{service_port}")
    # Use threaded mode for long-running migrations
    # Note: For production, use a WSGI server (gunicorn, waitress) with proper timeout configuration
    app.run(host=service_host, port=service_port, debug=True, threaded=True)

