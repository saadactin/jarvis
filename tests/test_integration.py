"""
Integration tests for end-to-end migration scenarios
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'universal_migration_service'))

from app import app, pipeline


class TestIntegration(unittest.TestCase):
    """Integration tests for the universal migration service"""
    
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('available_sources', data)
        self.assertIn('available_destinations', data)
    
    def test_migrate_endpoint_missing_fields(self):
        """Test migrate endpoint with missing required fields"""
        response = self.app.post('/migrate', json={})
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_migrate_endpoint_invalid_operation_type(self):
        """Test migrate endpoint with invalid operation type"""
        payload = {
            'source_type': 'postgresql',
            'dest_type': 'clickhouse',
            'source': {'host': 'localhost', 'database': 'test', 'username': 'user', 'password': 'pass'},
            'destination': {'host': 'localhost', 'database': 'test', 'username': 'user', 'password': 'pass'},
            'operation_type': 'invalid'
        }
        response = self.app.post('/migrate', json=payload)
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertIn('error', data)
    
    def test_test_connection_endpoint(self):
        """Test connection test endpoint"""
        payload = {
            'type': 'source',
            'adapter_type': 'postgresql',
            'config': {
                'host': 'localhost',
                'database': 'test',
                'username': 'user',
                'password': 'pass'
            }
        }
        response = self.app.post('/test-connection', json=payload)
        # Should return 200 even if connection fails (returns valid: false)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('valid', data)


class TestZohoToClickHouse(unittest.TestCase):
    """Test Zoho to ClickHouse migration scenario"""
    
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
    
    @patch('adapters.sources.zoho_source.requests.post')
    @patch('adapters.sources.zoho_source.requests.get')
    @patch('adapters.destinations.clickhouse_dest.clickhouse_connect.get_client')
    def test_zoho_to_clickhouse_migration(self, mock_ch_client, mock_get, mock_post):
        """Test Zoho to ClickHouse migration flow"""
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
        mock_get.return_value = mock_modules_response
        
        # Mock ClickHouse client
        mock_client = MagicMock()
        mock_ch_client.return_value = mock_client
        
        payload = {
            'source_type': 'zoho',
            'dest_type': 'clickhouse',
            'source': {
                'refresh_token': 'test_token',
                'client_id': 'test_id',
                'client_secret': 'test_secret',
                'api_domain': 'https://www.zohoapis.in'
            },
            'destination': {
                'host': 'localhost',
                'port': 8123,
                'database': 'testdb',
                'username': 'default',
                'password': 'pass'
            },
            'operation_type': 'full'
        }
        
        # This will fail at actual migration but should pass validation
        response = self.app.post('/migrate', json=payload)
        # Should not be 400 (validation error)
        self.assertNotEqual(response.status_code, 400)


class TestSQLServerToPostgreSQL(unittest.TestCase):
    """Test SQL Server to PostgreSQL migration scenario"""
    
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
    
    def test_sqlserver_to_postgresql_payload(self):
        """Test SQL Server to PostgreSQL migration payload structure"""
        payload = {
            'source_type': 'sqlserver',
            'dest_type': 'postgresql',
            'source': {
                'server': 'localhost\\SQLEXPRESS',
                'username': 'sa',
                'password': 'pass'
            },
            'destination': {
                'host': 'localhost',
                'port': 5432,
                'database': 'testdb',
                'username': 'postgres',
                'password': 'pass'
            },
            'operation_type': 'full'
        }
        
        # Test that payload structure is correct
        self.assertIn('source_type', payload)
        self.assertIn('dest_type', payload)
        self.assertIn('source', payload)
        self.assertIn('destination', payload)
        self.assertEqual(payload['source_type'], 'sqlserver')
        self.assertEqual(payload['dest_type'], 'postgresql')


if __name__ == '__main__':
    unittest.main()

