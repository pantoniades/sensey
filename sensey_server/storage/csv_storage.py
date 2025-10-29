"""
CSV file-based storage implementation for Sensey sensor data.

Each client gets its own CSV file in the data directory.
Includes caching for improved read performance.
"""

import os
import glob
import pandas as pd
from typing import List, Optional, Dict, Any
from functools import lru_cache
import logging

from .base import SenseyStorage, StorageError

logger = logging.getLogger(__name__)


class CSVStorage(SenseyStorage):
    """
    CSV file-based storage implementation.

    Features:
    - One CSV file per client (client_id.csv)
    - LRU cache for improved read performance
    - Automatic header management
    - Nested dictionary flattening support
    """

    def __init__(self, data_dir: str = "data"):
        """
        Initialize CSV storage backend.

        Args:
            data_dir: Directory path for storing CSV files (default: "data")
        """
        self.data_dir = data_dir

    def initialize(self) -> None:
        """Create data directory if it doesn't exist."""
        os.makedirs(self.data_dir, exist_ok=True)
        logger.info(f"CSV storage initialized at {self.data_dir}")

    def get_available_clients(self) -> List[str]:
        """Return list of clients based on CSV files in data directory."""
        if not os.path.exists(self.data_dir):
            return []

        csv_files = glob.glob(os.path.join(self.data_dir, "*.csv"))
        return sorted([os.path.basename(f).replace(".csv", "") for f in csv_files])

    def store_data(self, client_id: str, sensor_data: Dict[str, Any]) -> None:
        """
        Append sensor data to client's CSV file.

        Args:
            client_id: Unique identifier for the client
            sensor_data: Dictionary containing sensor readings and timestamp

        Raises:
            StorageError: If data cannot be stored
        """
        try:
            file_path = os.path.join(self.data_dir, f"{client_id}.csv")

            # Flatten nested dictionaries if present
            if 'readings' in sensor_data:
                sensor_data = self.flatten_dict(sensor_data)

            df = pd.DataFrame([sensor_data])

            # Write header only if file is new
            write_header = not os.path.exists(file_path)
            df.to_csv(file_path, mode="a", index=False, header=write_header)

            # Clear cache for this file since it's been modified
            self._cached_read_csv.cache_clear()

            logger.debug(f"Stored data for client {client_id}")

        except Exception as e:
            raise StorageError(f"Failed to store data for {client_id}: {e}")

    def get_latest_data(
        self,
        client_id: str,
        time_range: str = "3d"
    ) -> Optional[pd.DataFrame]:
        """
        Read and filter data for a specific client.

        Uses caching based on file modification time for performance.

        Args:
            client_id: Unique identifier for the client
            time_range: Time range string (e.g., '1h', '6h', '1d', '3d', 'all')

        Returns:
            DataFrame with sensor data, or None if no data exists
        """
        file_path = os.path.join(self.data_dir, f"{client_id}.csv")

        if not os.path.exists(file_path):
            logger.debug(f"No data file found for client {client_id}")
            return None

        try:
            # Use cached reading with file modification time as cache key
            file_hash = self._get_file_hash(file_path)
            df = self._cached_read_csv(file_path, file_hash)

            if df is None or df.empty:
                return None

            # Parse and sort by timestamp
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df = df.sort_values("timestamp")

            # Filter by time range
            cutoff_date = self.parse_time_range(time_range)
            if cutoff_date:
                df = df[df["timestamp"] >= cutoff_date]

            logger.debug(f"Retrieved {len(df)} records for {client_id} (range: {time_range})")
            return df

        except Exception as e:
            logger.error(f"Failed to read data for {client_id}: {e}")
            return None

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
        all_data = {}
        for client_id in self.get_available_clients():
            df = self.get_latest_data(client_id, time_range)
            if df is not None and not df.empty:
                all_data[client_id] = df

        logger.debug(f"Retrieved data for {len(all_data)} clients (range: {time_range})")
        return all_data

    def close(self) -> None:
        """Clear cache on shutdown."""
        self._cached_read_csv.cache_clear()
        logger.info("CSV storage closed and cache cleared")

    # Helper methods

    def _get_file_hash(self, file_path: str) -> str:
        """
        Get hash of file modification time for cache key.

        Args:
            file_path: Path to the CSV file

        Returns:
            String representation of modification timestamp
        """
        if not os.path.exists(file_path):
            return "none"
        return str(int(os.path.getmtime(file_path)))

    @lru_cache(maxsize=32)
    def _cached_read_csv(self, file_path: str, file_hash: str) -> Optional[pd.DataFrame]:
        """
        Cached CSV reading function.

        Cache key includes file_hash (mtime) to invalidate when file changes.

        Args:
            file_path: Path to the CSV file
            file_hash: File modification hash for cache invalidation

        Returns:
            DataFrame with CSV contents, or None if file doesn't exist
        """
        if not os.path.exists(file_path):
            return None
        return pd.read_csv(file_path)
