"""
Integration tests for Flask application.

Tests the Flask app endpoints and integration with storage backend.
"""

import pytest
import json
from datetime import datetime


class TestDataReceival:
    """Test the /data/<client_id> endpoint."""

    def test_receive_data_success(self, flask_test_client, sample_sensor_data):
        """Test receiving sensor data successfully."""
        response = flask_test_client.post(
            '/data/test_client',
            data=json.dumps(sample_sensor_data),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'

    def test_receive_data_invalid_json(self, flask_test_client):
        """Test receiving invalid JSON."""
        response = flask_test_client.post(
            '/data/test_client',
            data='not json',
            content_type='application/json'
        )

        assert response.status_code == 400

    def test_receive_data_stores_in_backend(self, flask_test_client, sample_sensor_data):
        """Test that received data is stored in backend."""
        # Send data
        flask_test_client.post(
            '/data/test_client',
            data=json.dumps(sample_sensor_data),
            content_type='application/json'
        )

        # Verify it's stored
        import sensey_data
        clients = sensey_data.get_available_clients()
        assert 'test_client' in clients


class TestIndexPage:
    """Test the index page endpoint."""

    def test_index_no_clients(self, flask_test_client):
        """Test index page with no clients."""
        response = flask_test_client.get('/')

        assert response.status_code == 200
        assert b'No data available' in response.data

    def test_index_with_clients(self, flask_test_client, sample_sensor_data):
        """Test index page with clients."""
        # Add some data first
        flask_test_client.post(
            '/data/test_client',
            data=json.dumps(sample_sensor_data),
            content_type='application/json'
        )

        response = flask_test_client.get('/')

        assert response.status_code == 200
        assert b'test_client' in response.data


class TestChartsPage:
    """Test the charts page endpoint."""

    def test_charts_nonexistent_client(self, flask_test_client):
        """Test charts for nonexistent client."""
        response = flask_test_client.get('/charts/nonexistent_client')

        assert response.status_code == 200
        assert b'No data available' in response.data

    def test_charts_with_data(self, flask_test_client, sample_sensor_data_batch):
        """Test charts page with data."""
        # Add batch of data
        for data in sample_sensor_data_batch:
            flask_test_client.post(
                '/data/test_client',
                data=json.dumps(data),
                content_type='application/json'
            )

        response = flask_test_client.get('/charts/test_client')

        assert response.status_code == 200
        assert b'test_client' in response.data

    def test_charts_time_range_selection(self, flask_test_client, sample_sensor_data_batch):
        """Test charts with different time ranges."""
        # Add data
        for data in sample_sensor_data_batch:
            flask_test_client.post(
                '/data/test_client',
                data=json.dumps(data),
                content_type='application/json'
            )

        # Test different time ranges
        for time_range in ['1h', '6h', '1d', '3d', '7d', 'all']:
            response = flask_test_client.get(f'/charts/test_client?range={time_range}')
            assert response.status_code == 200


class TestMultipleClients:
    """Test handling multiple clients."""

    def test_multiple_clients_data_isolation(self, flask_test_client):
        """Test that data from different clients is isolated."""
        data1 = {
            'timestamp': datetime.now().isoformat(),
            'temperature': 20.0,
            'humidity': 60.0
        }
        data2 = {
            'timestamp': datetime.now().isoformat(),
            'temperature': 25.0,
            'humidity': 70.0
        }

        # Store data for two clients
        flask_test_client.post('/data/client1', data=json.dumps(data1), content_type='application/json')
        flask_test_client.post('/data/client2', data=json.dumps(data2), content_type='application/json')

        # Verify both clients exist
        import sensey_data
        clients = sensey_data.get_available_clients()
        assert 'client1' in clients
        assert 'client2' in clients

        # Verify data isolation
        df1 = sensey_data.get_latest_data('client1', 'all')
        df2 = sensey_data.get_latest_data('client2', 'all')

        assert len(df1) == 1
        assert len(df2) == 1
        assert df1.iloc[0]['temperature'] == 20.0
        assert df2.iloc[0]['temperature'] == 25.0
