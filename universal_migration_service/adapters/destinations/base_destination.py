"""
Base Destination Adapter - Abstract interface for all destination adapters
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseDestinationAdapter(ABC):
    """Abstract base class for all destination adapters"""
    
    @abstractmethod
    def connect(self, config: Dict[str, Any]) -> bool:
        """
        Establish connection to destination database/API
        
        Args:
            config: Connection configuration dictionary
            
        Returns:
            bool: True if connection successful
            
        Raises:
            ConnectionError: If connection fails
        """
        pass
    
    @abstractmethod
    def disconnect(self):
        """Close connection to destination"""
        pass
    
    @abstractmethod
    def test_connection(self, config: Dict[str, Any]) -> bool:
        """
        Test if connection configuration is valid
        
        Args:
            config: Connection configuration dictionary
            
        Returns:
            bool: True if connection test successful
        """
        pass
    
    @abstractmethod
    def create_table(self, table_name: str, schema: List[Dict[str, Any]]):
        """
        Create table if it doesn't exist
        
        Args:
            table_name: Name of the table to create
            schema: List of column definitions:
            [{"name": "column_name", "type": "data_type", ...}, ...]
        """
        pass
    
    @abstractmethod
    def write_data(self, table_name: str, data: List[Dict[str, Any]], batch_size: int = 1000):
        """
        Write data to destination in batches
        
        Args:
            table_name: Name of the table
            data: List of dictionaries representing rows/records
            batch_size: Number of records per batch (for optimization)
        """
        pass
    
    @abstractmethod
    def map_types(self, source_schema: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Map source data types to destination data types
        
        Args:
            source_schema: Source schema with source types
            
        Returns:
            Schema with destination types:
            [{"name": "column_name", "type": "destination_type", ...}, ...]
        """
        pass
    
    @abstractmethod
    def get_destination_type(self) -> str:
        """
        Return destination type identifier
        
        Returns:
            String identifier (e.g., "clickhouse", "postgresql", "mysql")
        """
        pass

