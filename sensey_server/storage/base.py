"""
Abstract base class for Sensey sensor data storage backends.

This module defines the interface that all storage implementations must follow.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import pandas as pd
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class SenseyStorage(ABC):
    """
    Abstract base class for Sensey sensor data storage backends.

    All storage implementations must provide methods to:
    - Store incoming sensor data from clients
    - Retrieve available clients
    - Query historical data with time range filtering
    """

    @abstractmethod
    def initialize(self) -> None:
        """
        Initialize the storage backend (create directories, tables, connections, etc.)
        Called once during application startup.
        """
        pass

    @abstractmethod
    def get_available_clients(self) -> List[str]:
        """
        Return a list of client IDs that have stored data.

        Returns:
            List of client identifier strings
        """
        pass

    @abstractmethod
    def store_data(self, client_id: str, sensor_data: Dict[str, Any]) -> None:
        """
        Store sensor data for a specific client.

        Args:
            client_id: Unique identifier for the client
            sensor_data: Dictionary containing sensor readings and timestamp

        Raises:
            StorageError: If data cannot be stored
        """
        pass

    @abstractmethod
    def get_latest_data(
        self,
        client_id: str,
        time_range: str = "3d"
    ) -> Optional[pd.DataFrame]:
        """
        Retrieve sensor data for a client within a specified time range.

        Args:
            client_id: Unique identifier for the client
            time_range: Time range string (e.g., '1h', '6h', '1d', '3d', 'all')

        Returns:
            DataFrame with timestamp and sensor columns, or None if no data exists
        """
        pass

    @abstractmethod
    def get_all_clients_data(
        self,
        time_range: str = "3d"
    ) -> Dict[str, pd.DataFrame]:
        """
        Retrieve data for all clients within a specified time range.

        Args:
            time_range: Time range string (e.g., '1h', '6h', '1d', '3d', 'all')

        Returns:
            Dictionary mapping client_id to DataFrame of sensor data
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Close connections and cleanup resources.
        Called during application shutdown.
        """
        pass

    # Utility methods available to all implementations

    def parse_time_range(self, time_range: str) -> Optional[datetime]:
        """
        Parse time range string and return cutoff datetime.

        Args:
            time_range: Time range string (e.g., '1h', '6h', '1d', '3d', 'all')

        Returns:
            datetime object representing the cutoff time, or None for 'all'
        """
        if time_range == "all":
            return None

        now = datetime.now()

        try:
            if time_range.endswith('h'):
                hours = int(time_range[:-1])
                return now - timedelta(hours=hours)
            elif time_range.endswith('d'):
                days = int(time_range[:-1])
                return now - timedelta(days=days)
            elif time_range.endswith('w'):
                weeks = int(time_range[:-1])
                return now - timedelta(weeks=weeks)
        except (ValueError, IndexError):
            logger.warning(f"Invalid time range format: {time_range}, defaulting to 3 days")
            return now - timedelta(days=3)

        # Default to 3 days if format not recognized
        return now - timedelta(days=3)

    def flatten_dict(self, d: Dict[str, Any]) -> Dict[str, Any]:
        """
        Flatten nested dictionaries (e.g., {'readings': {'temp': 20}} -> {'temp': 20}).

        Args:
            d: Dictionary to flatten

        Returns:
            Flattened dictionary
        """
        flattened = {}
        for k, v in d.items():
            if isinstance(v, dict):
                for inner_k, inner_v in v.items():
                    flattened[inner_k] = inner_v
            else:
                flattened[k] = v
        return flattened


class StorageError(Exception):
    """Exception raised for storage operation failures."""
    pass
