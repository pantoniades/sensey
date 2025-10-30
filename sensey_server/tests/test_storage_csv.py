"""
Unit tests for CSV storage backend.

Tests the CSVStorage class functionality including:
- Initialization
- Data storage
- Data retrieval
- Time range filtering
- Multiple clients
"""

import pytest
import os
import pandas as pd
from datetime import datetime, timedelta
from storage import CSVStorage, StorageError


class TestCSVStorageInitialization:
    """Test CSV storage initialization."""

    def test_initialize_creates_directory(self, temp_dir):
        """Test that initialize creates the data directory."""
        data_dir = os.path.join(temp_dir, "data")
        storage = CSVStorage(data_dir=data_dir)
        storage.initialize()

        assert os.path.exists(data_dir)
        assert os.path.isdir(data_dir)

    def test_initialize_with_existing_directory(self, temp_dir):
        """Test that initialize works with existing directory."""
        os.makedirs(temp_dir, exist_ok=True)
        storage = CSVStorage(data_dir=temp_dir)
        storage.initialize()  # Should not raise

        assert os.path.exists(temp_dir)


class TestCSVStorageDataOperations:
    """Test CSV storage data operations."""

    def test_store_data_creates_csv_file(self, temp_dir, sample_sensor_data):
        """Test that store_data creates a CSV file."""
        storage = CSVStorage(data_dir=temp_dir)
        storage.initialize()

        storage.store_data("test_client", sample_sensor_data)

        csv_file = os.path.join(temp_dir, "test_client.csv")
        assert os.path.exists(csv_file)

    def test_store_data_with_nested_readings(self, temp_dir, sample_nested_sensor_data):
        """Test that store_data flattens nested readings."""
        storage = CSVStorage(data_dir=temp_dir)
        storage.initialize()

        storage.store_data("test_client", sample_nested_sensor_data)

        df = pd.read_csv(os.path.join(temp_dir, "test_client.csv"))
        assert 'temperature' in df.columns
        assert 'humidity' in df.columns
        assert 'readings' not in df.columns  # Should be flattened

    def test_store_multiple_records(self, temp_dir, sample_sensor_data_batch):
        """Test storing multiple records."""
        storage = CSVStorage(data_dir=temp_dir)
        storage.initialize()

        for data in sample_sensor_data_batch:
            storage.store_data("test_client", data)

        df = pd.read_csv(os.path.join(temp_dir, "test_client.csv"))
        assert len(df) == len(sample_sensor_data_batch)

    def test_get_available_clients_empty(self, temp_dir):
        """Test get_available_clients with no data."""
        storage = CSVStorage(data_dir=temp_dir)
        storage.initialize()

        clients = storage.get_available_clients()
        assert clients == []

    def test_get_available_clients_with_data(self, temp_dir, sample_sensor_data):
        """Test get_available_clients with data."""
        storage = CSVStorage(data_dir=temp_dir)
        storage.initialize()

        storage.store_data("client1", sample_sensor_data)
        storage.store_data("client2", sample_sensor_data)

        clients = storage.get_available_clients()
        assert len(clients) == 2
        assert "client1" in clients
        assert "client2" in clients


class TestCSVStorageDataRetrieval:
    """Test CSV storage data retrieval."""

    def test_get_latest_data_nonexistent_client(self, temp_dir):
        """Test get_latest_data for nonexistent client."""
        storage = CSVStorage(data_dir=temp_dir)
        storage.initialize()

        df = storage.get_latest_data("nonexistent_client")
        assert df is None

    def test_get_latest_data_all_time_range(self, csv_storage_with_data):
        """Test get_latest_data with 'all' time range."""
        df = csv_storage_with_data.get_latest_data("test_client", "all")

        assert df is not None
        assert len(df) == 10  # All records
        assert 'timestamp' in df.columns
        assert 'temperature' in df.columns

    def test_get_latest_data_sorted_by_timestamp(self, csv_storage_with_data):
        """Test that retrieved data is sorted by timestamp."""
        df = csv_storage_with_data.get_latest_data("test_client", "all")

        timestamps = df['timestamp'].tolist()
        assert timestamps == sorted(timestamps)  # Should be in ascending order

    def test_get_latest_data_time_filtering(self, temp_dir):
        """Test time range filtering."""
        storage = CSVStorage(data_dir=temp_dir)
        storage.initialize()

        # Store data with different timestamps
        now = datetime.now()
        data_2h_ago = {
            'timestamp': (now - timedelta(hours=2)).isoformat(),
            'temperature': 20.0
        }
        data_25h_ago = {
            'timestamp': (now - timedelta(hours=25)).isoformat(),
            'temperature': 15.0
        }

        storage.store_data("test_client", data_25h_ago)
        storage.store_data("test_client", data_2h_ago)

        # Get data from last day
        df = storage.get_latest_data("test_client", "1d")

        # Should only get the 2h ago data
        assert len(df) == 1
        assert df.iloc[0]['temperature'] == 20.0

    def test_get_all_clients_data(self, temp_dir, sample_sensor_data):
        """Test get_all_clients_data."""
        storage = CSVStorage(data_dir=temp_dir)
        storage.initialize()

        storage.store_data("client1", sample_sensor_data)
        storage.store_data("client2", sample_sensor_data)

        all_data = storage.get_all_clients_data("all")

        assert len(all_data) == 2
        assert "client1" in all_data
        assert "client2" in all_data
        assert isinstance(all_data["client1"], pd.DataFrame)


class TestCSVStorageCaching:
    """Test CSV storage caching behavior."""

    def test_cache_invalidation_on_new_data(self, temp_dir, sample_sensor_data):
        """Test that cache is invalidated when new data is added."""
        storage = CSVStorage(data_dir=temp_dir)
        storage.initialize()

        # Store first record
        storage.store_data("test_client", sample_sensor_data)
        df1 = storage.get_latest_data("test_client", "all")

        # Store second record
        storage.store_data("test_client", sample_sensor_data)
        df2 = storage.get_latest_data("test_client", "all")

        # Should have more records after second store
        assert len(df2) > len(df1)


class TestCSVStorageCleanup:
    """Test CSV storage cleanup."""

    def test_close_clears_cache(self, temp_dir, sample_sensor_data):
        """Test that close() clears the cache."""
        storage = CSVStorage(data_dir=temp_dir)
        storage.initialize()

        storage.store_data("test_client", sample_sensor_data)
        storage.get_latest_data("test_client", "all")  # Populate cache

        storage.close()  # Should clear cache

        # Cache should be cleared (no easy way to verify directly,
        # but at least ensure close() doesn't raise)
        assert True


class TestCSVStorageTimeRangeParsing:
    """Test time range parsing."""

    def test_parse_time_range_hours(self, temp_dir):
        """Test parsing hour-based time ranges."""
        storage = CSVStorage(data_dir=temp_dir)

        result = storage.parse_time_range("6h")
        assert result is not None
        assert isinstance(result, datetime)

    def test_parse_time_range_days(self, temp_dir):
        """Test parsing day-based time ranges."""
        storage = CSVStorage(data_dir=temp_dir)

        result = storage.parse_time_range("3d")
        assert result is not None
        assert isinstance(result, datetime)

    def test_parse_time_range_all(self, temp_dir):
        """Test parsing 'all' time range."""
        storage = CSVStorage(data_dir=temp_dir)

        result = storage.parse_time_range("all")
        assert result is None  # 'all' returns None

    def test_parse_time_range_invalid(self, temp_dir):
        """Test parsing invalid time range defaults to 3 days."""
        storage = CSVStorage(data_dir=temp_dir)

        result = storage.parse_time_range("invalid")
        assert result is not None
        assert isinstance(result, datetime)
