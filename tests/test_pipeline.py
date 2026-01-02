"""
Integration tests for universal pipeline engine
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'universal_migration_service'))

from pipeline_engine import UniversalPipelineEngine
from adapters.sources.postgresql_source import PostgreSQLSourceAdapter
from adapters.destinations.clickhouse_dest import ClickHouseDestinationAdapter


class TestUniversalPipelineEngine(unittest.TestCase):
    """Test universal pipeline engine"""
    
    def setUp(self):
        self.pipeline = UniversalPipelineEngine()
        self.pipeline.register_source("postgresql", PostgreSQLSourceAdapter)
        self.pipeline.register_destination("clickhouse", ClickHouseDestinationAdapter)
    
    def test_register_source(self):
        """Test source registration"""
        self.assertIn("postgresql", self.pipeline.source_registry)
    
    def test_register_destination(self):
        """Test destination registration"""
        self.assertIn("clickhouse", self.pipeline.dest_registry)
    
    def test_get_available_sources(self):
        """Test getting available sources"""
        sources = self.pipeline.get_available_sources()
        self.assertIn("postgresql", sources)
    
    def test_get_available_destinations(self):
        """Test getting available destinations"""
        destinations = self.pipeline.get_available_destinations()
        self.assertIn("clickhouse", destinations)
    
    def test_migrate_unsupported_source(self):
        """Test migration with unsupported source"""
        with self.assertRaises(ValueError) as context:
            self.pipeline.migrate(
                source_config={},
                dest_config={},
                source_type="unknown",
                dest_type="clickhouse"
            )
        self.assertIn("Unsupported source type", str(context.exception))
    
    def test_migrate_unsupported_destination(self):
        """Test migration with unsupported destination"""
        with self.assertRaises(ValueError) as context:
            self.pipeline.migrate(
                source_config={},
                dest_config={},
                source_type="postgresql",
                dest_type="unknown"
            )
        self.assertIn("Unsupported destination type", str(context.exception))


if __name__ == '__main__':
    unittest.main()

