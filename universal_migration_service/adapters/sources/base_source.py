"""
Base Source Adapter - Abstract interface for all source adapters
"""
from abc import ABC, abstractmethod
from typing import Iterator, Dict, List, Any
from datetime import datetime


class BaseSourceAdapter(ABC):
    """Abstract base class for all source adapters"""
    
    @abstractmethod
    def connect(self, config: Dict[str, Any]) -> bool:
        """
        Establish connection to source database/API
        
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
        """Close connection to source"""
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
    def get_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get table/collection schema information
        
        Args:
            table_name: Name of the table/collection
            
        Returns:
            List of dictionaries with column/field information:
            [{"name": "column_name", "type": "data_type", ...}, ...]
        """
        pass
    
    @abstractmethod
    def list_tables(self) -> List[str]:
        """
        List all tables/collections in the source
        
        Returns:
            List of table/collection names
        """
        pass
    
    @abstractmethod
    def read_data(self, table_name: str, batch_size: int = 1000) -> Iterator[List[Dict[str, Any]]]:
        """
        Read data from source in batches (generator)
        
        Args:
            table_name: Name of the table/collection
            batch_size: Number of records per batch
            
        Yields:
            List of dictionaries representing rows/records
        """
        pass
    
    @abstractmethod
    def read_incremental(self, table_name: str, last_sync_time: datetime, batch_size: int = 1000) -> Iterator[List[Dict[str, Any]]]:
        """
        Read incremental changes since last sync
        
        Args:
            table_name: Name of the table/collection
            last_sync_time: Timestamp of last sync
            batch_size: Number of records per batch
            
        Yields:
            List of dictionaries representing new/updated rows
        """
        pass
    
    @abstractmethod
    def get_source_type(self) -> str:
        """
        Return source type identifier
        
        Returns:
            String identifier (e.g., "postgresql", "mysql", "cassandra")
        """
        pass

