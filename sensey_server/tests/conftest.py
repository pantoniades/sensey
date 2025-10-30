"""
Pytest configuration and fixtures for sensey_server tests.

This module provides common fixtures and configuration for all tests.
"""

import pytest
import os
import tempfile
import shutil
from datetime import datetime, timedelta
import pandas as pd


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test data."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def test_config_csv(temp_dir):
    """Create a test configuration file for CSV storage."""
    config_path = os.path.join(temp_dir, "test_sensey.ini")
    config_content = f"""[storage]
backend = csv

[csv]
data_dir = {temp_dir}/data
"""
    with open(config_path, 'w') as f:
        f.write(config_content)
    return config_path


@pytest.fixture
def test_config_mysql():
    """Create a test configuration file for MySQL storage."""
    temp_path = tempfile.mkdtemp()
    config_path = os.path.join(temp_path, "test_sensey.ini")
    config_content = """[storage]
backend = mysql

[mysql]
host = localhost
port = 3306
user = test_sensey
password = test_password
database = test_sensey
pool_size = 2
"""
    with open(config_path, 'w') as f:
        f.write(config_content)

    yield config_path

    shutil.rmtree(temp_path)


@pytest.fixture
def sample_sensor_data():
    """Generate sample sensor data for testing."""
    return {
        'timestamp': datetime.now().isoformat(),
        'temperature': 23.5,
        'humidity': 65.2,
        'lux': 150.0,
        'soil_moisture': 32.5
    }


@pytest.fixture
def sample_sensor_data_batch():
    """Generate a batch of sample sensor data for testing."""
    base_time = datetime.now()
    data = []

    for i in range(10):
        timestamp = base_time - timedelta(minutes=i * 5)
        data.append({
            'timestamp': timestamp.isoformat(),
            'temperature': 20.0 + i * 0.5,
            'humidity': 60.0 + i * 1.0,
            'lux': 100.0 + i * 10.0,
            'soil_moisture': 30.0 + i * 0.5
        })

    return data


@pytest.fixture
def sample_dataframe():
    """Generate a sample pandas DataFrame for testing."""
    base_time = datetime.now()
    timestamps = [base_time - timedelta(hours=i) for i in range(24)]

    return pd.DataFrame({
        'timestamp': timestamps,
        'temperature': [20.0 + i * 0.5 for i in range(24)],
        'humidity': [60.0 + i * 1.0 for i in range(24)],
        'lux': [100.0 + i * 5.0 for i in range(24)]
    })


@pytest.fixture
def csv_storage_with_data(temp_dir, sample_sensor_data_batch):
    """Create a CSV storage backend with test data."""
    from storage import CSVStorage

    storage = CSVStorage(data_dir=temp_dir)
    storage.initialize()

    # Store test data
    for data in sample_sensor_data_batch:
        storage.store_data("test_client", data)

    yield storage

    storage.close()


@pytest.fixture
def flask_test_client(test_config_csv, monkeypatch):
    """Create a Flask test client with test configuration."""
    # Set the config path environment variable
    monkeypatch.setenv('SENSEY_CONFIG_PATH', test_config_csv)

    # Import app after setting env var
    # This ensures the app uses our test config
    import sys
    import importlib

    # Remove cached modules to force reload with test config
    modules_to_remove = [m for m in sys.modules.keys()
                         if m.startswith('storage') or m == 'config' or m == 'sensey_data' or m == 'app']
    for module in modules_to_remove:
        del sys.modules[module]

    # Now import app which will use test config
    import app as flask_app

    flask_app.app.config['TESTING'] = True
    client = flask_app.app.test_client()

    yield client

    # Cleanup storage
    import sensey_data
    sensey_data.close_storage()


@pytest.fixture
def mock_mysql_available(monkeypatch):
    """Mock MySQL availability for testing."""
    import storage.mysql_storage as mysql_module
    monkeypatch.setattr(mysql_module, 'MYSQL_AVAILABLE', True)


@pytest.fixture
def sample_nested_sensor_data():
    """Generate sample sensor data with nested readings."""
    return {
        'timestamp': datetime.now().isoformat(),
        'readings': {
            'temperature': 23.5,
            'humidity': 65.2,
            'lux': 150.0,
            'soil_moisture': 32.5
        }
    }
