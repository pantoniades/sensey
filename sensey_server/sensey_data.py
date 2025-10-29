"""
Sensey data access layer - Compatibility wrapper around storage backends.

DEPRECATED MODULE:
This module is maintained for backward compatibility with existing code.
It provides the same API as before but delegates to the new storage abstraction layer.

New code should import directly from the storage package:
    from storage import create_storage_from_config
    storage = create_storage_from_config()
    storage.initialize()

Migration Guide:
    Old: sensey_data.get_available_clients()
    New: storage.get_available_clients()

    Old: sensey_data.store_data(client_id, data)
    New: storage.store_data(client_id, data)

    Old: sensey_data.get_latest_data(client_id, "3d")
    New: storage.get_latest_data(client_id, "3d")
"""

import pandas as pd
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# Module-level storage instance (singleton)
# Will be initialized on first use or by set_storage()
_storage = None


def set_storage(storage_instance):
    """
    Set the storage backend instance to use for all operations.

    This should be called once at application startup, before any data operations.
    If not called, storage will be auto-initialized from config on first use.

    Args:
        storage_instance: Initialized SenseyStorage instance

    Example:
        from storage import create_storage_from_config
        storage = create_storage_from_config()
        storage.initialize()
        sensey_data.set_storage(storage)
    """
    global _storage
    _storage = storage_instance
    logger.info(f"Storage backend set: {type(storage_instance).__name__}")


def _get_storage():
    """
    Get the storage instance, initializing it if necessary.

    Returns:
        Storage instance

    Raises:
        RuntimeError: If storage initialization fails
    """
    global _storage

    if _storage is None:
        # Auto-initialize from config (fallback behavior)
        logger.warning(
            "Storage not explicitly initialized. Auto-initializing from config. "
            "Consider calling set_storage() at application startup."
        )
        try:
            from storage import create_storage_from_config
            _storage = create_storage_from_config()
            _storage.initialize()
            logger.info("Auto-initialized storage from configuration")
        except Exception as e:
            logger.error(f"Failed to auto-initialize storage: {e}")
            raise RuntimeError(
                "Storage not initialized and auto-initialization failed. "
                "Please ensure sensey.ini exists and call set_storage() at startup."
            ) from e

    return _storage


def get_available_clients() -> List[str]:
    """
    Return a list of client hostnames that have stored data.

    Returns:
        List of client identifier strings
    """
    storage = _get_storage()
    return storage.get_available_clients()


def store_data(client_id: str, sensor_data: Dict[str, Any]):
    """
    Store new sensor data for a client.

    Args:
        client_id: Unique identifier for the client
        sensor_data: Dictionary containing sensor readings and timestamp

    Raises:
        StorageError: If data cannot be stored
    """
    storage = _get_storage()
    storage.store_data(client_id, sensor_data)


def get_latest_data(client_id: str, time_range: str = "3d") -> Optional[pd.DataFrame]:
    """
    Read data for a client with flexible time range support.

    Args:
        client_id: Client identifier
        time_range: Time range in format like '1h', '6h', '1d', '3d', '7d', 'all'

    Returns:
        DataFrame with sensor data, or None if no data exists
    """
    storage = _get_storage()
    return storage.get_latest_data(client_id, time_range)


def get_all_clients_data(time_range: str = "3d") -> Dict[str, pd.DataFrame]:
    """
    Retrieve data for all clients within a specified time range.

    Args:
        time_range: Time range string (e.g., '1h', '6h', '1d', '3d', 'all')

    Returns:
        Dictionary mapping client_id to DataFrame of sensor data
    """
    storage = _get_storage()
    return storage.get_all_clients_data(time_range)


def close_storage():
    """
    Close storage backend and cleanup resources.

    Should be called during application shutdown.
    """
    global _storage

    if _storage is not None:
        _storage.close()
        logger.info("Storage closed via sensey_data compatibility layer")
        _storage = None

