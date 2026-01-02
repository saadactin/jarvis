"""
Unit tests for source and destination adapters
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'universal_migration_service'))

from adapters.sources.base_source import BaseSourceAdapter
from adapters.destinations.base_destination import BaseDestinationAdapter
from adapters.sources.postgresql_source import PostgreSQLSourceAdapter
from adapters.sources.zoho_source import ZohoSourceAdapter
from adapters.sources.sqlserver_source import SQLServerSourceAdapter
from adapters.destinations.clickhouse_dest import ClickHouseDestinationAdapter
from adapters.destinations.postgresql_dest import PostgreSQLDestinationAdapter


class TestPostgreSQLSourceAdapter(unittest.TestCase):
    """Test PostgreSQL source adapter"""
    
    def setUp(self):
        self.adapter = PostgreSQLSourceAdapter()
        self.config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'testdb',
            'username': 'testuser',
            'password': 'testpass'
        }
    
    @patch('adapters.sources.postgresql_source.psycopg2.connect')
    def test_connect_success(self, mock_connect):
        """Test successful connection"""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        
        result = self.adapter.connect(self.config)
        
        self.assertTrue(result)
        self.assertEqual(self.adapter.conn, mock_conn)
        mock_connect.assert_called_once()
    
    def test_get_source_type(self):
        """Test source type identifier"""
        self.assertEqual(self.adapter.get_source_type(), "postgresql")


class TestZohoSourceAdapter(unittest.TestCase):
    """Test Zoho source adapter"""
    
    def setUp(self):
        self.adapter = ZohoSourceAdapter()
        self.config = {
            'refresh_token': 'test_refresh_token',
            'client_id': 'test_client_id',
            'client_secret': 'test_client_secret',
            'api_domain': 'https://www.zohoapis.in'
        }
    
    @patch('adapters.sources.zoho_source.requests.post')
    def test_get_access_token_success(self, mock_post):
        """Test successful access token retrieval"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'access_token': 'test_token',
            'expires_in': 3600,
            'api_domain': 'https://www.zohoapis.in'
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response
        
        token_result = self.adapter._get_access_token(
            'refresh_token', 'client_id', 'client_secret', 'https://www.zohoapis.in'
        )
        
        self.assertIsNotNone(token_result)
        self.assertEqual(token_result['access_token'], 'test_token')
    
    def test_get_source_type(self):
        """Test source type identifier"""
        self.assertEqual(self.adapter.get_source_type(), "zoho")


class TestSQLServerSourceAdapter(unittest.TestCase):
    """Test SQL Server source adapter"""
    
    def setUp(self):
        self.adapter = SQLServerSourceAdapter()
        self.config = {
            'server': 'localhost',
            'username': 'sa',
            'password': 'testpass'
        }
    
    def test_get_source_type(self):
        """Test source type identifier"""
        self.assertEqual(self.adapter.get_source_type(), "sqlserver")


class TestClickHouseDestinationAdapter(unittest.TestCase):
    """Test ClickHouse destination adapter"""
    
    def setUp(self):
        self.adapter = ClickHouseDestinationAdapter()
        self.config = {
            'host': 'localhost',
            'port': 8123,
            'database': 'testdb',
            'username': 'default',
            'password': 'testpass'
        }
    
    def test_map_types(self):
        """Test type mapping"""
        source_schema = [
            {'name': 'id', 'type': 'integer', 'nullable': False},
            {'name': 'name', 'type': 'varchar', 'nullable': True},
            {'name': 'price', 'type': 'decimal', 'nullable': False}
        ]
        
        dest_schema = self.adapter.map_types(source_schema)
        
        self.assertEqual(len(dest_schema), 3)
        self.assertEqual(dest_schema[0]['type'], 'Int32')
        self.assertEqual(dest_schema[1]['type'], 'Nullable(String)')
        self.assertEqual(dest_schema[2]['type'], 'Decimal64(2)')
    
    def test_get_destination_type(self):
        """Test destination type identifier"""
        self.assertEqual(self.adapter.get_destination_type(), "clickhouse")


class TestPostgreSQLDestinationAdapter(unittest.TestCase):
    """Test PostgreSQL destination adapter"""
    
    def setUp(self):
        self.adapter = PostgreSQLDestinationAdapter()
        self.config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'testdb',
            'username': 'testuser',
            'password': 'testpass'
        }
    
    def test_map_types(self):
        """Test type mapping"""
        source_schema = [
            {'name': 'id', 'type': 'integer', 'nullable': False},
            {'name': 'name', 'type': 'varchar', 'max_length': 255, 'nullable': True}
        ]
        
        dest_schema = self.adapter.map_types(source_schema)
        
        self.assertEqual(len(dest_schema), 2)
        self.assertEqual(dest_schema[0]['type'], 'INTEGER')
        self.assertEqual(dest_schema[1]['type'], 'VARCHAR(255)')
    
    def test_get_destination_type(self):
        """Test destination type identifier"""
        self.assertEqual(self.adapter.get_destination_type(), "postgresql")


if __name__ == '__main__':
    unittest.main()

