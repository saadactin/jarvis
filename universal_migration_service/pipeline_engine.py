"""
Universal Pipeline Engine - Orchestrates migration from any source to any destination
"""
from adapters.sources.base_source import BaseSourceAdapter
from adapters.destinations.base_destination import BaseDestinationAdapter
from typing import Dict, Any, Type, Optional, List
from datetime import datetime
import logging
import time

logger = logging.getLogger(__name__)

# Try to import psutil for memory tracking, but don't fail if not available
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not available - memory tracking will be disabled")


class UniversalPipelineEngine:
    """Orchestrates migration from any source to any destination"""
    
    def __init__(self):
        self.source_registry: Dict[str, Type[BaseSourceAdapter]] = {}
        self.dest_registry: Dict[str, Type[BaseDestinationAdapter]] = {}
    
    def register_source(self, source_type: str, adapter_class: Type[BaseSourceAdapter]):
        """
        Register a source adapter
        
        Args:
            source_type: String identifier (e.g., "postgresql", "mysql")
            adapter_class: Class implementing BaseSourceAdapter
        """
        self.source_registry[source_type] = adapter_class
        logger.info(f"Registered source adapter: {source_type}")
    
    def register_destination(self, dest_type: str, adapter_class: Type[BaseDestinationAdapter]):
        """
        Register a destination adapter
        
        Args:
            dest_type: String identifier (e.g., "clickhouse", "postgresql")
            adapter_class: Class implementing BaseDestinationAdapter
        """
        self.dest_registry[dest_type] = adapter_class
        logger.info(f"Registered destination adapter: {dest_type}")
    
    def get_available_sources(self) -> List[str]:
        """Get list of registered source types"""
        return list(self.source_registry.keys())
    
    def get_available_destinations(self) -> List[str]:
        """Get list of registered destination types"""
        return list(self.dest_registry.keys())
    
    def migrate(self, source_config: Dict[str, Any], dest_config: Dict[str, Any], 
                source_type: str, dest_type: str, 
                operation_type: str = 'full',
                last_sync_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Execute migration from source to destination
        
        Args:
            source_config: Source connection configuration
            dest_config: Destination connection configuration
            source_type: Source type identifier
            dest_type: Destination type identifier
            operation_type: 'full' or 'incremental'
            last_sync_time: Timestamp for incremental sync (required if operation_type='incremental')
            
        Returns:
            Dictionary with migration results:
            {
                "success": bool,
                "tables_migrated": List[str],
                "tables_failed": List[Dict],
                "total_tables": int,
                "errors": List[str]
            }
        """
        # Validate source and destination are not the same
        if source_type == dest_type:
            raise ValueError(f"Cannot migrate from {source_type} to {source_type}. Source and destination cannot be the same.")
        
        # Get adapter classes
        SourceAdapter = self.source_registry.get(source_type)
        DestAdapter = self.dest_registry.get(dest_type)
        
        if not SourceAdapter:
            raise ValueError(f"Unsupported source type: {source_type}. Available: {list(self.source_registry.keys())}")
        if not DestAdapter:
            raise ValueError(f"Unsupported destination type: {dest_type}. Available: {list(self.dest_registry.keys())}")
        
        # Initialize adapters
        source = SourceAdapter()
        destination = DestAdapter()
        
        results = {
            "success": True,
            "tables_migrated": [],
            "tables_failed": [],
            "total_tables": 0,
            "errors": []
        }
        
        try:
            import os
            if PSUTIL_AVAILABLE:
                process = psutil.Process(os.getpid())
                initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            else:
                process = None
                initial_memory = 0
            
            # Connect to source and destination
            connect_start = time.time()
            logger.info(f"Connecting to source: {source_type}")
            if not source.connect(source_config):
                raise ConnectionError(f"Failed to connect to source: {source_type}")
            
            logger.info(f"Connecting to destination: {dest_type}")
            if not destination.connect(dest_config):
                raise ConnectionError(f"Failed to connect to destination: {dest_type}")
            connect_elapsed = time.time() - connect_start
            logger.info(f"Connections established in {connect_elapsed:.2f}s")
            
            # Get tables to migrate
            list_start = time.time()
            logger.info("Listing tables from source...")
            tables = source.list_tables()
            list_elapsed = time.time() - list_start
            results["total_tables"] = len(tables)
            logger.info(f"Found {len(tables)} tables to migrate in {list_elapsed:.2f}s: {tables[:10]}{'...' if len(tables) > 10 else ''}")
            
            if len(tables) == 0:
                logger.warning("No tables found in source")
                results["errors"].append("No tables/modules found in source")
                return results
            
            # Migrate each table with retry logic
            for table_name in tables:
                max_retries = 2
                retry_count = 0
                table_success = False
                
                while retry_count <= max_retries and not table_success:
                    try:
                        if retry_count > 0:
                            logger.info(f"Retrying migration for table {table_name} (attempt {retry_count + 1}/{max_retries + 1})")
                            time.sleep(2)  # Brief delay before retry
                        
                        table_start = time.time()
                        logger.info(f"Migrating table: {table_name}")
                        
                        # Get schema from source
                        schema_start = time.time()
                        schema = source.get_schema(table_name)
                        schema_elapsed = time.time() - schema_start
                        logger.debug(f"Table {table_name} has {len(schema)} columns (schema retrieved in {schema_elapsed:.2f}s)")
                        
                        # Extract constraints for PostgreSQL to MySQL migrations
                        primary_keys = []
                        foreign_keys = []
                        unique_constraints = []
                        indexes = []
                        
                        if source_type == 'postgresql' and hasattr(source, 'get_primary_key_columns'):
                            try:
                                primary_keys = source.get_primary_key_columns(table_name)
                                if primary_keys:
                                    logger.debug(f"Found primary keys for {table_name}: {primary_keys}")
                            except Exception as e:
                                logger.warning(f"Could not get primary keys for {table_name}: {e}")
                        
                        if source_type == 'postgresql' and hasattr(source, 'get_foreign_keys'):
                            try:
                                foreign_keys = source.get_foreign_keys(table_name)
                                if foreign_keys:
                                    logger.debug(f"Found {len(foreign_keys)} foreign keys for {table_name}")
                            except Exception as e:
                                logger.warning(f"Could not get foreign keys for {table_name}: {e}")
                        
                        if source_type == 'postgresql' and hasattr(source, 'get_unique_constraints'):
                            try:
                                unique_constraints = source.get_unique_constraints(table_name)
                                if unique_constraints:
                                    logger.debug(f"Found {len(unique_constraints)} unique constraints for {table_name}")
                            except Exception as e:
                                logger.warning(f"Could not get unique constraints for {table_name}: {e}")
                        
                        if source_type == 'postgresql' and hasattr(source, 'get_indexes'):
                            try:
                                indexes = source.get_indexes(table_name)
                                if indexes:
                                    logger.debug(f"Found {len(indexes)} indexes for {table_name}")
                            except Exception as e:
                                logger.warning(f"Could not get indexes for {table_name}: {e}")
                        
                        # Map types to destination
                        map_start = time.time()
                        dest_schema = destination.map_types(schema, source_type=source_type)
                        map_elapsed = time.time() - map_start
                        logger.debug(f"Type mapping completed in {map_elapsed:.2f}s")
                        
                        # Create destination table (pass source_type and constraints for PostgreSQL to MySQL)
                        create_start = time.time()
                        if source_type == 'postgresql' and dest_type == 'mysql':
                            destination.create_table(
                                table_name, dest_schema, 
                                source_type=source_type,
                                primary_keys=primary_keys,
                                foreign_keys=foreign_keys,
                                unique_constraints=unique_constraints,
                                indexes=indexes
                            )
                        else:
                            destination.create_table(table_name, dest_schema, source_type=source_type)
                        create_elapsed = time.time() - create_start
                        logger.debug(f"Table creation completed in {create_elapsed:.2f}s")
                        
                        # Migrate data
                        records_processed = 0
                        batch_count = 0
                        data_start = time.time()
                        
                        # Use appropriate batch size based on source type
                        # DevOps API has limits, so use smaller batches
                        if source_type == 'devops':
                            batch_size = 50  # Match test script batch size for DevOps
                        elif source_type == 'zoho':
                            batch_size = 200  # Zoho default
                        else:
                            batch_size = 1000  # Default for database sources
                        
                        if operation_type == 'full':
                            data_iterator = source.read_data(table_name, batch_size=batch_size)
                        elif operation_type == 'incremental':
                            if not last_sync_time:
                                raise ValueError("last_sync_time is required for incremental migration")
                            data_iterator = source.read_incremental(table_name, last_sync_time, batch_size=batch_size)
                        else:
                            raise ValueError(f"Invalid operation_type: {operation_type}")
                        
                        # Write data in batches (pass source_type for Zoho-specific handling)
                        # Wrap iterator in try-except to catch any exceptions during iteration
                        iterator_exception = None
                        try:
                            for batch in data_iterator:
                                batch_count += 1
                                if not batch or len(batch) == 0:
                                    logger.warning(f"{table_name}: Received empty batch {batch_count}, skipping")
                                    continue
                                
                                try:
                                    # Pass primary keys for upsert logic in PostgreSQL to MySQL migrations
                                    if source_type == 'postgresql' and dest_type == 'mysql' and primary_keys:
                                        destination.write_data(
                                            table_name, batch, 
                                            source_type=source_type,
                                            primary_keys=primary_keys
                                        )
                                    else:
                                        destination.write_data(table_name, batch, source_type=source_type)
                                    records_processed += len(batch)
                                    
                                    # Log progress more frequently for DevOps (every batch)
                                    if source_type == 'devops':
                                        logger.info(f"{table_name}: Batch {batch_count}: {len(batch)} records, Total: {records_processed:,} records")
                                    elif PSUTIL_AVAILABLE and process:
                                        current_memory = process.memory_info().rss / 1024 / 1024  # MB
                                        if batch_count % 10 == 0:  # Log every 10 batches
                                            logger.debug(f"{table_name}: Processed {records_processed} records, {batch_count} batches, memory: {current_memory:.1f}MB")
                                    elif batch_count % 10 == 0:
                                        logger.debug(f"{table_name}: Processed {records_processed} records, {batch_count} batches")
                                except Exception as write_error:
                                    logger.error(f"{table_name}: Error writing batch {batch_count}: {write_error}")
                                    # Continue with next batch instead of failing entire table
                                    import traceback
                                    logger.error(traceback.format_exc())
                                    # Re-raise to trigger retry logic
                                    raise
                        except StopIteration:
                            # Normal end of iterator
                            pass
                        except Exception as iter_error:
                            # Exception during iteration (reading from source)
                            iterator_exception = iter_error
                            logger.error(f"{table_name}: Exception during data iteration: {iter_error}")
                            import traceback
                            logger.error(traceback.format_exc())
                            # Re-raise to trigger retry logic
                            raise
                        
                        # Check if iterator ended prematurely due to exception
                        if iterator_exception:
                            raise iterator_exception
                        
                        data_elapsed = time.time() - data_start
                        
                        # Create indexes, unique constraints, and foreign keys after data migration
                        # (for PostgreSQL to MySQL migrations)
                        if source_type == 'postgresql' and dest_type == 'mysql':
                            if hasattr(destination, 'create_indexes') and indexes:
                                try:
                                    logger.info(f"Creating {len(indexes)} indexes for {table_name}...")
                                    destination.create_indexes(table_name, indexes)
                                except Exception as e:
                                    logger.warning(f"Could not create indexes for {table_name}: {e}")
                            
                            if hasattr(destination, 'create_unique_constraints') and unique_constraints:
                                try:
                                    logger.info(f"Creating {len(unique_constraints)} unique constraints for {table_name}...")
                                    destination.create_unique_constraints(table_name, unique_constraints)
                                except Exception as e:
                                    logger.warning(f"Could not create unique constraints for {table_name}: {e}")
                            
                            if hasattr(destination, 'create_foreign_keys') and foreign_keys:
                                try:
                                    logger.info(f"Creating {len(foreign_keys)} foreign keys for {table_name}...")
                                    destination.create_foreign_keys(table_name, foreign_keys)
                                except Exception as e:
                                    logger.warning(f"Could not create foreign keys for {table_name}: {e}")
                        
                        table_elapsed = time.time() - table_start
                        
                        # Warn if very few records were processed (might indicate early termination)
                        if records_processed > 0 and records_processed < 100 and source_type == 'devops':
                            logger.warning(f"{table_name}: Only {records_processed} records processed. This might indicate an early termination issue. Check logs for errors.")
                        
                        if PSUTIL_AVAILABLE and process:
                            current_memory = process.memory_info().rss / 1024 / 1024  # MB
                            memory_delta = current_memory - initial_memory
                            logger.info(f"Successfully migrated table {table_name}: {records_processed:,} records in {table_elapsed:.2f}s (data: {data_elapsed:.2f}s, {records_processed/data_elapsed:.1f} records/s, memory: {current_memory:.1f}MB, delta: {memory_delta:+.1f}MB)")
                        else:
                            logger.info(f"Successfully migrated table {table_name}: {records_processed:,} records in {table_elapsed:.2f}s (data: {data_elapsed:.2f}s, {records_processed/data_elapsed:.1f} records/s)")
                        results["tables_migrated"].append({
                            "table": table_name,
                            "records": records_processed
                        })
                        table_success = True
                        
                    except Exception as e:
                        error_msg = str(e)
                        retry_count += 1
                        
                        # Detailed error logging
                        import traceback
                        logger.error("="*60)
                        logger.error(f"TABLE MIGRATION ERROR: {table_name}")
                        logger.error(f"Attempt: {retry_count}/{max_retries + 1}")
                        logger.error(f"Error Type: {type(e).__name__}")
                        logger.error(f"Error Message: {error_msg}")
                        logger.error(f"Stack Trace:")
                        logger.error(traceback.format_exc())
                        logger.error("="*60)
                        
                        if retry_count > max_retries:
                            # Final failure after all retries
                            logger.error(f"Error migrating table {table_name} after {max_retries + 1} attempts: {error_msg}")
                            results["tables_failed"].append({
                                "table": table_name,
                                "error": error_msg,
                                "error_type": type(e).__name__
                            })
                            results["errors"].append(f"{table_name}: {error_msg}")
                        else:
                            logger.warning(f"Error migrating table {table_name} (attempt {retry_count}): {error_msg}. Will retry...")
            
            results["success"] = len(results["tables_failed"]) == 0
            total_elapsed = time.time() - connect_start
            if PSUTIL_AVAILABLE and process:
                final_memory = process.memory_info().rss / 1024 / 1024  # MB
                total_memory_delta = final_memory - initial_memory
                logger.info(f"Migration completed in {total_elapsed:.2f}s. Success: {results['success']}, "
                           f"Migrated: {len(results['tables_migrated'])}, "
                           f"Failed: {len(results['tables_failed'])}, "
                           f"Final memory: {final_memory:.1f}MB (delta: {total_memory_delta:+.1f}MB)")
            else:
                logger.info(f"Migration completed in {total_elapsed:.2f}s. Success: {results['success']}, "
                           f"Migrated: {len(results['tables_migrated'])}, "
                           f"Failed: {len(results['tables_failed'])}")
            
            return results
            
        except Exception as e:
            error_msg = str(e)
            import traceback
            logger.error("="*80)
            logger.error("MIGRATION FAILURE - Pipeline Engine Error")
            logger.error(f"Source Type: {source_type}")
            logger.error(f"Destination Type: {dest_type}")
            logger.error(f"Operation Type: {operation_type}")
            logger.error(f"Error Type: {type(e).__name__}")
            logger.error(f"Error Message: {error_msg}")
            logger.error(f"Stack Trace:")
            logger.error(traceback.format_exc())
            logger.error("="*80)
            
            results["success"] = False
            results["errors"].append(f"{type(e).__name__}: {error_msg}")
            return results
            
        finally:
            # Always disconnect
            try:
                source.disconnect()
            except:
                pass
            try:
                destination.disconnect()
            except:
                pass

