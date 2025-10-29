"""
Configuration loader for Sensey Server.

Reads configuration from sensey.ini file and provides validated settings
for the storage backend and other application parameters.
"""

import os
import configparser
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Exception raised for configuration-related errors."""
    pass


class SenseyConfig:
    """
    Sensey server configuration loader and validator.

    Loads configuration from sensey.ini (or path specified by SENSEY_CONFIG_PATH).
    Validates configuration and provides type-safe access to settings.
    """

    DEFAULT_CONFIG_FILENAME = "sensey.ini"
    EXAMPLE_CONFIG_FILENAME = "sensey.ini.example"

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration loader.

        Args:
            config_path: Path to config file. If None, looks for sensey.ini
                        in current directory, then checks SENSEY_CONFIG_PATH env var.

        Raises:
            ConfigurationError: If config file not found or invalid
        """
        self.config_path = self._resolve_config_path(config_path)
        self.config = configparser.ConfigParser()
        self._load_config()
        self._validate_config()

    def _resolve_config_path(self, config_path: Optional[str]) -> str:
        """
        Resolve the configuration file path.

        Priority:
        1. Explicitly provided config_path parameter
        2. SENSEY_CONFIG_PATH environment variable
        3. sensey.ini in current working directory
        4. sensey.ini in script directory

        Args:
            config_path: Explicit config file path (optional)

        Returns:
            Resolved config file path

        Raises:
            ConfigurationError: If config file not found
        """
        # Priority 1: Explicit parameter
        if config_path and os.path.exists(config_path):
            logger.info(f"Using config from parameter: {config_path}")
            return config_path

        # Priority 2: Environment variable
        env_path = os.environ.get('SENSEY_CONFIG_PATH')
        if env_path and os.path.exists(env_path):
            logger.info(f"Using config from SENSEY_CONFIG_PATH: {env_path}")
            return env_path

        # Priority 3: Current working directory
        cwd_path = os.path.join(os.getcwd(), self.DEFAULT_CONFIG_FILENAME)
        if os.path.exists(cwd_path):
            logger.info(f"Using config from current directory: {cwd_path}")
            return cwd_path

        # Priority 4: Script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(script_dir, self.DEFAULT_CONFIG_FILENAME)
        if os.path.exists(script_path):
            logger.info(f"Using config from script directory: {script_path}")
            return script_path

        # Not found - provide helpful error message
        example_path = os.path.join(script_dir, self.EXAMPLE_CONFIG_FILENAME)
        error_msg = f"""
Configuration file not found!

Sensey Server requires a configuration file named '{self.DEFAULT_CONFIG_FILENAME}'.

Please create it by copying the example configuration:
    cp {example_path} {script_path}

Then edit {script_path} to configure your storage backend (CSV or MySQL).

Alternatively, set the SENSEY_CONFIG_PATH environment variable to point
to your configuration file.
"""
        raise ConfigurationError(error_msg.strip())

    def _load_config(self):
        """
        Load configuration from INI file.

        Raises:
            ConfigurationError: If config file cannot be read
        """
        try:
            self.config.read(self.config_path)
            logger.info(f"Configuration loaded from: {self.config_path}")
        except Exception as e:
            raise ConfigurationError(f"Failed to read config file {self.config_path}: {e}")

    def _validate_config(self):
        """
        Validate configuration completeness and correctness.

        Raises:
            ConfigurationError: If configuration is invalid or incomplete
        """
        # Check for [storage] section
        if 'storage' not in self.config:
            raise ConfigurationError("Missing [storage] section in configuration")

        # Validate storage backend
        backend = self.get_storage_backend()
        if backend not in ['csv', 'mysql']:
            raise ConfigurationError(
                f"Invalid storage backend: '{backend}'. Must be 'csv' or 'mysql'"
            )

        # Validate backend-specific configuration
        if backend == 'csv':
            self._validate_csv_config()
        elif backend == 'mysql':
            self._validate_mysql_config()

        logger.info(f"Configuration validated successfully (backend: {backend})")

    def _validate_csv_config(self):
        """
        Validate CSV storage configuration.

        Raises:
            ConfigurationError: If CSV configuration is invalid
        """
        if 'csv' not in self.config:
            raise ConfigurationError("Missing [csv] section for CSV backend")

        if 'data_dir' not in self.config['csv']:
            raise ConfigurationError("Missing 'data_dir' in [csv] section")

        data_dir = self.config['csv']['data_dir']
        if not data_dir:
            raise ConfigurationError("'data_dir' in [csv] section cannot be empty")

    def _validate_mysql_config(self):
        """
        Validate MySQL storage configuration.

        Raises:
            ConfigurationError: If MySQL configuration is invalid or incomplete
        """
        if 'mysql' not in self.config:
            raise ConfigurationError(
                "Missing [mysql] section for MySQL backend.\n"
                "Please add MySQL connection parameters to sensey.ini"
            )

        required_params = ['host', 'port', 'user', 'database']
        missing = []

        for param in required_params:
            if param not in self.config['mysql'] or not self.config['mysql'][param]:
                missing.append(param)

        if missing:
            raise ConfigurationError(
                f"Missing or empty MySQL parameters in [mysql] section: {', '.join(missing)}\n"
                f"Please configure these parameters in {self.config_path}"
            )

        # Validate port is a number
        try:
            int(self.config['mysql']['port'])
        except ValueError:
            raise ConfigurationError(
                f"Invalid MySQL port: '{self.config['mysql']['port']}'. Must be a number."
            )

        # Validate pool_size if present
        if 'pool_size' in self.config['mysql']:
            try:
                pool_size = int(self.config['mysql']['pool_size'])
                if pool_size < 1 or pool_size > 100:
                    raise ValueError("Pool size must be between 1 and 100")
            except ValueError as e:
                raise ConfigurationError(f"Invalid MySQL pool_size: {e}")

        # Warn if password is empty (not an error, but worth noting)
        if not self.config['mysql'].get('password'):
            logger.warning("MySQL password is empty - connecting without password")

    def get_storage_backend(self) -> str:
        """
        Get the configured storage backend type.

        Returns:
            Storage backend type ('csv' or 'mysql')
        """
        return self.config['storage']['backend'].lower()

    def get_storage_config(self) -> Dict[str, Any]:
        """
        Get storage backend configuration parameters.

        Returns:
            Dictionary of configuration parameters for the selected backend

        Raises:
            ConfigurationError: If configuration is invalid
        """
        backend = self.get_storage_backend()

        if backend == 'csv':
            return {
                'data_dir': self.config['csv']['data_dir']
            }
        elif backend == 'mysql':
            config = {
                'host': self.config['mysql']['host'],
                'port': int(self.config['mysql']['port']),
                'user': self.config['mysql']['user'],
                'password': self.config['mysql'].get('password', ''),
                'database': self.config['mysql']['database'],
            }

            # Add optional parameters if present
            if 'pool_size' in self.config['mysql']:
                config['pool_size'] = int(self.config['mysql']['pool_size'])

            return config
        else:
            raise ConfigurationError(f"Unknown storage backend: {backend}")


# Global configuration instance
_config: Optional[SenseyConfig] = None


def get_config(config_path: Optional[str] = None) -> SenseyConfig:
    """
    Get the global configuration instance.

    Loads configuration on first call. Subsequent calls return the cached instance.

    Args:
        config_path: Path to config file (only used on first call)

    Returns:
        SenseyConfig instance

    Raises:
        ConfigurationError: If configuration is invalid
    """
    global _config

    if _config is None:
        _config = SenseyConfig(config_path)

    return _config


def reload_config(config_path: Optional[str] = None) -> SenseyConfig:
    """
    Reload configuration from file.

    Useful for testing or runtime configuration changes.

    Args:
        config_path: Path to config file

    Returns:
        New SenseyConfig instance

    Raises:
        ConfigurationError: If configuration is invalid
    """
    global _config
    _config = SenseyConfig(config_path)
    return _config
