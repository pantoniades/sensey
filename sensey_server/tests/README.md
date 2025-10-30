# Sensey Server Test Suite

Comprehensive test suite for the sensey_server application using pytest.

## Test Structure

```
tests/
├── __init__.py           # Package initialization
├── conftest.py           # Pytest fixtures and configuration
├── test_config.py        # Configuration loading and validation tests
├── test_storage_csv.py   # CSV storage backend unit tests
├── test_storage_mysql.py # MySQL storage backend unit tests (TODO)
├── test_app.py           # Flask application integration tests
└── README.md             # This file
```

## Installation

Install test dependencies:

```bash
cd sensey_server
pip install -r requirements.txt
pip install pytest pytest-cov
```

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Specific Test File

```bash
pytest tests/test_storage_csv.py
pytest tests/test_config.py
pytest tests/test_app.py
```

### Run Specific Test Class or Function

```bash
# Run a specific test class
pytest tests/test_storage_csv.py::TestCSVStorageInitialization

# Run a specific test function
pytest tests/test_storage_csv.py::TestCSVStorageInitialization::test_initialize_creates_directory
```

### Run Tests with Verbose Output

```bash
pytest -v
```

### Run Tests with Coverage Report

```bash
pytest --cov=storage --cov=config --cov=sensey_data --cov-report=html
```

Coverage report will be generated in `htmlcov/index.html`

## Test Categories

Tests are organized into categories:

### Unit Tests
- **test_config.py**: Configuration loading, validation, error handling
- **test_storage_csv.py**: CSV storage backend functionality
  - Initialization
  - Data storage and retrieval
  - Time range filtering
  - Caching behavior
  - Multi-client support

### Integration Tests
- **test_app.py**: Flask application endpoints
  - Data receiving endpoint
  - Index page
  - Charts page
  - Multi-client scenarios

## Fixtures

Common test fixtures are defined in `conftest.py`:

- **temp_dir**: Temporary directory for test data
- **test_config_csv**: Test configuration for CSV storage
- **test_config_mysql**: Test configuration for MySQL storage
- **sample_sensor_data**: Single sensor reading
- **sample_sensor_data_batch**: Batch of sensor readings
- **csv_storage_with_data**: Pre-populated CSV storage
- **flask_test_client**: Flask test client with test configuration

## Test Data

Test data includes realistic sensor measurements:
- Temperature (Celsius)
- Humidity (%)
- Light level (lux)
- Soil moisture (%)
- Timestamps (ISO format)

## MySQL Tests

MySQL tests require:
- MySQL 8.4+ server running
- Test database and user configured
- `mysql-connector-python` installed

To run MySQL tests:

```bash
# Set up test database
mysql -u root -p <<EOF
CREATE DATABASE IF NOT EXISTS test_sensey;
CREATE USER IF NOT EXISTS 'test_sensey'@'localhost' IDENTIFIED BY 'test_password';
GRANT ALL PRIVILEGES ON test_sensey.* TO 'test_sensey'@'localhost';
FLUSH PRIVILEGES;
EOF

# Run MySQL tests
pytest tests/test_storage_mysql.py
```

**Note**: MySQL tests are currently marked as TODO and not yet implemented.

## Continuous Integration

Tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    pip install pytest pytest-cov
    pytest --cov=storage --cov=config --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
```

## Writing New Tests

### Test Naming Conventions

- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`

### Example Test

```python
def test_example_feature(temp_dir, sample_sensor_data):
    """Test description here."""
    # Arrange
    storage = CSVStorage(data_dir=temp_dir)
    storage.initialize()

    # Act
    storage.store_data("client1", sample_sensor_data)

    # Assert
    clients = storage.get_available_clients()
    assert "client1" in clients
```

### Using Fixtures

```python
def test_with_fixtures(csv_storage_with_data):
    """Test using pre-populated storage."""
    df = csv_storage_with_data.get_latest_data("test_client", "all")
    assert len(df) == 10  # Fixture provides 10 records
```

## Troubleshooting

### Import Errors

If you see import errors, ensure you're running pytest from the `sensey_server` directory:

```bash
cd sensey_server
pytest
```

### Configuration Errors

If tests fail due to configuration, check that test fixtures are properly setting `SENSEY_CONFIG_PATH`:

```python
def test_example(test_config_csv, monkeypatch):
    monkeypatch.setenv('SENSEY_CONFIG_PATH', test_config_csv)
    # Your test code
```

### MySQL Connection Errors

If MySQL tests fail:
1. Verify MySQL server is running: `systemctl status mysql`
2. Check test database exists: `mysql -u test_sensey -p test_sensey`
3. Verify credentials in test configuration

## Future Enhancements

- [ ] Implement MySQL storage backend tests
- [ ] Add performance/benchmark tests
- [ ] Add client-side integration tests
- [ ] Mock external dependencies for faster tests
- [ ] Add mutation testing for robustness
- [ ] Add property-based testing with Hypothesis

## Contributing

When adding new tests:
1. Follow existing test structure and naming conventions
2. Use fixtures for common setup
3. Include docstrings explaining what each test validates
4. Ensure tests are isolated and don't depend on execution order
5. Clean up resources in fixtures (use `yield` pattern)

## References

- [Pytest Documentation](https://docs.pytest.org/)
- [Flask Testing](https://flask.palletsprojects.com/en/latest/testing/)
- [Pandas Testing Utilities](https://pandas.pydata.org/docs/reference/general_utility_functions.html#testing-functions)
