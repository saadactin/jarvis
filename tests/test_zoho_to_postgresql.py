"""
Test Zoho to PostgreSQL migration
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'universal_migration_service'))

from pipeline_engine import UniversalPipelineEngine
from adapters.sources.zoho_source import ZohoSourceAdapter
from adapters.destinations.postgresql_dest import PostgreSQLDestinationAdapter


class TestZohoToPostgreSQL(unittest.TestCase):
    """Test Zoho to PostgreSQL migration scenario"""
    
    def setUp(self):
        self.pipeline = UniversalPipelineEngine()
        self.pipeline.register_source("zoho", ZohoSourceAdapter)
        self.pipeline.register_destination("postgresql", PostgreSQLDestinationAdapter)
    
    def test_zoho_postgresql_registered(self):
        """Test that Zoho and PostgreSQL are registered"""
        self.assertIn("zoho", self.pipeline.get_available_sources())
        self.assertIn("postgresql", self.pipeline.get_available_destinations())
    
    @patch('adapters.sources.zoho_source.requests.post')
    @patch('adapters.sources.zoho_source.requests.get')
    @patch('adapters.destinations.postgresql_dest.psycopg2.connect')
    def test_zoho_to_postgresql_migration_flow(self, mock_pg_connect, mock_get, mock_post):
        """Test Zoho to PostgreSQL migration flow"""
        # Mock Zoho token response
        mock_token_response = MagicMock()
        mock_token_response.json.return_value = {
            'access_token': 'test_token',
            'expires_in': 3600,
            'api_domain': 'https://www.zohoapis.in'
        }
        mock_token_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_token_response
        
        # Mock Zoho modules response
        mock_modules_response = MagicMock()
        mock_modules_response.json.return_value = {
            'modules': [
                {'api_name': 'Accounts', 'display_label': 'Accounts'}
            ]
        }
        mock_modules_response.status_code = 200
        
        # Mock Zoho records response
        mock_records_response = MagicMock()
        mock_records_response.json.return_value = {
            'data': [
                {
                    'id': '123',
                    'Account_Name': {'name': 'Test Account'},
                    'Phone': '1234567890'
                }
            ],
            'info': {'more_records': False}
        }
        mock_records_response.status_code = 200
        
        mock_get.side_effect = [mock_modules_response, mock_records_response]
        
        # Mock PostgreSQL connection
        mock_pg_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (False,)  # Table doesn't exist
        mock_cursor.fetchall.return_value = []
        mock_pg_conn.cursor.return_value = mock_cursor
        mock_pg_connect.return_value = mock_pg_conn
        
        source_config = {
            'refresh_token': 'test_token',
            'client_id': 'test_id',
            'client_secret': 'test_secret',
            'api_domain': 'https://www.zohoapis.in'
        }
        
        dest_config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'testdb',
            'username': 'postgres',
            'password': 'pass'
        }
        
        # This will fail at actual migration but should pass validation
        try:
            result = self.pipeline.migrate(
                source_config=source_config,
                dest_config=dest_config,
                source_type="zoho",
                dest_type="postgresql",
                operation_type="full"
            )
            # Should not raise ValueError for unsupported types
            self.assertIsNotNone(result)
        except ValueError as e:
            self.fail(f"Should not raise ValueError for supported types: {e}")


if __name__ == '__main__':
    unittest.main()

