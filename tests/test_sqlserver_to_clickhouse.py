"""
Test SQL Server to ClickHouse migration
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'universal_migration_service'))

from pipeline_engine import UniversalPipelineEngine
from adapters.sources.sqlserver_source import SQLServerSourceAdapter
from adapters.destinations.clickhouse_dest import ClickHouseDestinationAdapter


class TestSQLServerToClickHouse(unittest.TestCase):
    """Test SQL Server to ClickHouse migration scenario"""
    
    def setUp(self):
        self.pipeline = UniversalPipelineEngine()
        self.pipeline.register_source("sqlserver", SQLServerSourceAdapter)
        self.pipeline.register_destination("clickhouse", ClickHouseDestinationAdapter)
    
    def test_sqlserver_clickhouse_registered(self):
        """Test that SQL Server and ClickHouse are registered"""
        self.assertIn("sqlserver", self.pipeline.get_available_sources())
        self.assertIn("clickhouse", self.pipeline.get_available_destinations())
    
    @patch('adapters.sources.sqlserver_source.pyodbc.connect')
    @patch('adapters.destinations.clickhouse_dest.clickhouse_connect.get_client')
    def test_sqlserver_to_clickhouse_migration_flow(self, mock_ch_client, mock_sql_connect):
        """Test SQL Server to ClickHouse migration flow"""
        # Mock SQL Server connection
        mock_sql_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ('master',), ('testdb',)
        ]
        mock_cursor.execute = MagicMock()
        mock_cursor.description = [('id',), ('name',)]
        mock_cursor.fetchall.side_effect = [
            [('master',), ('testdb',)],  # Databases
            [('dbo', 'users')],  # Tables
            [('id', 'int', None, None, None, 'NO'), ('name', 'varchar', 255, None, None, 'YES')],  # Schema
            [(1, 'Test')]  # Data
        ]
        mock_sql_conn.cursor.return_value = mock_cursor
        mock_sql_connect.return_value = mock_sql_conn
        
        # Mock ClickHouse client
        mock_ch = MagicMock()
        mock_ch.command.return_value = False  # Table doesn't exist
        mock_ch_client.return_value = mock_ch
        
        source_config = {
            'server': 'localhost',
            'username': 'sa',
            'password': 'pass'
        }
        
        dest_config = {
            'host': 'localhost',
            'port': 8123,
            'database': 'testdb',
            'username': 'default',
            'password': 'pass'
        }
        
        # This will fail at actual migration but should pass validation
        try:
            result = self.pipeline.migrate(
                source_config=source_config,
                dest_config=dest_config,
                source_type="sqlserver",
                dest_type="clickhouse",
                operation_type="full"
            )
            # Should not raise ValueError for unsupported types
            self.assertIsNotNone(result)
        except ValueError as e:
            self.fail(f"Should not raise ValueError for supported types: {e}")


if __name__ == '__main__':
    unittest.main()

