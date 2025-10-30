"""
Unit tests for configuration loading and validation.

Tests the config module functionality including:
- Configuration file loading
- Validation
- Error handling
- Storage config extraction
"""

import pytest
import os
import tempfile
from config import SenseyConfig, ConfigurationError


class TestConfigFileResolution:
    """Test configuration file path resolution."""

    def test_explicit_config_path(self, test_config_csv):
        """Test loading config from explicit path."""
        config = SenseyConfig(config_path=test_config_csv)
        assert config.config_path == test_config_csv

    def test_missing_config_file_raises_error(self):
        """Test that missing config file raises clear error."""
        with pytest.raises(ConfigurationError) as exc_info:
            SenseyConfig(config_path="/nonexistent/path/sensey.ini")

        assert "not found" in str(exc_info.value).lower()

    def test_config_from_env_var(self, test_config_csv, monkeypatch):
        """Test loading config from SENSEY_CONFIG_PATH env var."""
        monkeypatch.setenv('SENSEY_CONFIG_PATH', test_config_csv)
        config = SenseyConfig()

        assert config.config_path == test_config_csv


class TestConfigValidation:
    """Test configuration validation."""

    def test_valid_csv_config(self, test_config_csv):
        """Test validation of valid CSV configuration."""
        config = SenseyConfig(config_path=test_config_csv)
        assert config.get_storage_backend() == 'csv'

    def test_missing_storage_section(self, temp_dir):
        """Test validation fails with missing [storage] section."""
        config_path = os.path.join(temp_dir, "bad_config.ini")
        with open(config_path, 'w') as f:
            f.write("[csv]\ndata_dir = /tmp\n")

        with pytest.raises(ConfigurationError) as exc_info:
            SenseyConfig(config_path=config_path)

        assert "storage" in str(exc_info.value).lower()

    def test_invalid_backend_type(self, temp_dir):
        """Test validation fails with invalid backend type."""
        config_path = os.path.join(temp_dir, "bad_config.ini")
        with open(config_path, 'w') as f:
            f.write("[storage]\nbackend = invalid_backend\n")

        with pytest.raises(ConfigurationError) as exc_info:
            SenseyConfig(config_path=config_path)

        assert "invalid" in str(exc_info.value).lower()

    def test_csv_missing_data_dir(self, temp_dir):
        """Test validation fails when CSV backend missing data_dir."""
        config_path = os.path.join(temp_dir, "bad_config.ini")
        with open(config_path, 'w') as f:
            f.write("[storage]\nbackend = csv\n[csv]\n")

        with pytest.raises(ConfigurationError) as exc_info:
            SenseyConfig(config_path=config_path)

        assert "data_dir" in str(exc_info.value).lower()

    def test_mysql_missing_required_params(self, temp_dir):
        """Test validation fails when MySQL backend missing required params."""
        config_path = os.path.join(temp_dir, "bad_config.ini")
        with open(config_path, 'w') as f:
            f.write("[storage]\nbackend = mysql\n[mysql]\nhost = localhost\n")

        with pytest.raises(ConfigurationError) as exc_info:
            SenseyConfig(config_path=config_path)

        assert "mysql" in str(exc_info.value).lower()

    def test_mysql_invalid_port(self, temp_dir):
        """Test validation fails with invalid MySQL port."""
        config_path = os.path.join(temp_dir, "bad_config.ini")
        with open(config_path, 'w') as f:
            f.write("""[storage]
backend = mysql

[mysql]
host = localhost
port = not_a_number
user = test
database = test
""")

        with pytest.raises(ConfigurationError) as exc_info:
            SenseyConfig(config_path=config_path)

        assert "port" in str(exc_info.value).lower()


class TestConfigAccess:
    """Test configuration value access."""

    def test_get_storage_backend_csv(self, test_config_csv):
        """Test getting CSV storage backend."""
        config = SenseyConfig(config_path=test_config_csv)
        assert config.get_storage_backend() == 'csv'

    def test_get_storage_config_csv(self, test_config_csv):
        """Test getting CSV storage configuration."""
        config = SenseyConfig(config_path=test_config_csv)
        storage_config = config.get_storage_config()

        assert 'data_dir' in storage_config
        assert storage_config['data_dir'].endswith('/data')

    def test_get_storage_config_mysql(self, test_config_mysql):
        """Test getting MySQL storage configuration."""
        config = SenseyConfig(config_path=test_config_mysql)
        storage_config = config.get_storage_config()

        assert storage_config['host'] == 'localhost'
        assert storage_config['port'] == 3306
        assert storage_config['user'] == 'test_sensey'
        assert storage_config['database'] == 'test_sensey'
        assert storage_config['pool_size'] == 2

    def test_get_storage_config_mysql_default_pool_size(self, temp_dir):
        """Test MySQL config uses default pool_size if not specified."""
        config_path = os.path.join(temp_dir, "mysql_config.ini")
        with open(config_path, 'w') as f:
            f.write("""[storage]
backend = mysql

[mysql]
host = localhost
port = 3306
user = test
password = pass
database = test
""")

        config = SenseyConfig(config_path=config_path)
        storage_config = config.get_storage_config()

        # pool_size should not be in config if not specified in INI
        assert 'pool_size' not in storage_config


class TestConfigGlobal:
    """Test global config functions."""

    def test_get_config_singleton(self, test_config_csv):
        """Test that get_config returns singleton."""
        from config import get_config, reload_config

        # Clear any existing config
        reload_config(test_config_csv)

        config1 = get_config()
        config2 = get_config()

        assert config1 is config2  # Same instance

    def test_reload_config(self, test_config_csv, temp_dir):
        """Test that reload_config creates new instance."""
        from config import get_config, reload_config

        config1 = reload_config(test_config_csv)

        # Create different config
        config_path2 = os.path.join(temp_dir, "config2.ini")
        with open(config_path2, 'w') as f:
            f.write("[storage]\nbackend = csv\n[csv]\ndata_dir = /other\n")

        config2 = reload_config(config_path2)

        assert config1 is not config2  # Different instances
        assert config1.config_path != config2.config_path
