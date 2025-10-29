"""
Sensey Storage Abstraction Layer

This package provides a pluggable storage backend system for Sensey sensor data.

Supported Backends:
- CSV: File-based storage (default, no additional dependencies)
- MySQL: Database storage (requires mysql-connector-python)

Configuration:
--------------
Storage backend is configured via sensey.ini file.
See sensey.ini.example for configuration options.

Usage:
------
from storage import create_storage_from_config

# Create storage from configuration file
storage = create_storage_from_config()

# Or create directly with parameters
from storage import create_storage
storage = create_storage("csv", data_dir="./data")

# Initialize and use
storage.initialize()
storage.store_data("client1", {"timestamp": "2025-01-01 12:00:00", "temperature": 23.5})
df = storage.get_latest_data("client1", "3d")
"""

import logging
from typing import Optional

# Import base classes
from .base import SenseyStorage, StorageError

# Import CSV storage (always available)
from .csv_storage import CSVStorage

# Try to import MySQL storage (optional dependency)
try:
    from .mysql_storage import MySQLStorage
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    MySQLStorage = None

logger = logging.getLogger(__name__)


def create_storage(storage_type: str, **kwargs) -> SenseyStorage:
    """
    Factory function to create storage backend instances.

    Args:
        storage_type: Type of storage ("csv" or "mysql")
        **kwargs: Configuration parameters for the storage backend

    Returns:
        Instance of SenseyStorage implementation

    Raises:
        ValueError: If storage_type is not recognized
        StorageError: If required dependencies are missing

    Examples:
    ---------
    # CSV storage
    storage = create_storage("csv", data_dir="/var/sensey/data")

    # MySQL storage
    storage = create_storage(
        "mysql",
        host="db.example.com",
        port=3306,
        user="sensey_user",
        password="secret123",
        database="sensey_prod",
        pool_size=10
    )
    """
    storage_type = storage_type.lower()

    if storage_type == "csv":
        logger.info(f"Creating CSV storage with data_dir={kwargs.get('data_dir', 'data')}")
        return CSVStorage(**kwargs)
    elif storage_type == "mysql":
        if not MYSQL_AVAILABLE:
            raise StorageError(
                "MySQL storage requested but mysql-connector-python is not installed. "
                "Install with: pip install mysql-connector-python"
            )
        logger.info(
            f"Creating MySQL storage: {kwargs.get('user', 'sensey')}@"
            f"{kwargs.get('host', 'localhost')}:{kwargs.get('port', 3306)}/"
            f"{kwargs.get('database', 'sensey')}"
        )
        return MySQLStorage(**kwargs)
    else:
        raise ValueError(
            f"Unknown storage type: '{storage_type}'. "
            f"Supported types: csv, mysql"
        )


def create_storage_from_config(config_path: Optional[str] = None) -> SenseyStorage:
    """
    Create storage backend from configuration file.

    Reads sensey.ini (or path specified by config_path/SENSEY_CONFIG_PATH)
    and creates the appropriate storage backend with validated parameters.

    Args:
        config_path: Path to config file (optional). If not provided,
                    searches for sensey.ini in standard locations.

    Returns:
        Initialized storage backend instance

    Raises:
        ConfigurationError: If config file is missing or invalid
        StorageError: If storage backend cannot be created

    Examples:
    ---------
    # Use default config file (sensey.ini)
    storage = create_storage_from_config()

    # Use specific config file
    storage = create_storage_from_config("/etc/sensey/sensey.ini")

    # Then initialize and use
    storage.initialize()
    """
    from config import get_config, ConfigurationError

    try:
        # Load and validate configuration
        config = get_config(config_path)

        # Get storage backend type and parameters
        backend = config.get_storage_backend()
        storage_config = config.get_storage_config()

        # Create storage backend
        logger.info(f"Creating {backend} storage from configuration")
        return create_storage(backend, **storage_config)

    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        raise
    except Exception as e:
        raise StorageError(f"Failed to create storage from config: {e}")


# Public API exports
__all__ = [
    'SenseyStorage',
    'StorageError',
    'CSVStorage',
    'MySQLStorage',
    'create_storage',
    'create_storage_from_config',
]
