# Sensey - Distributed Sensor Monitoring System

A flexible, distributed environmental sensor monitoring system for Raspberry Pi devices with a centralized web-based visualization server.

## Overview

Sensey consists of two main components:

- **sensey_server**: Flask web server that receives, stores, and visualizes sensor data
- **sensey_client**: Raspberry Pi client applications that collect sensor data and transmit to the server
- **Ecowitt Integration**: Optional support for Ecowitt weather stations (GW3000, GW1000, etc.)

### Key Features

- 📊 **Pluggable Storage**: Choose between CSV files or MySQL 8.4+ database
- 🔄 **Resilient Communication**: Automatic retry with exponential backoff and local caching
- 📈 **Interactive Visualizations**: Real-time Plotly charts with configurable time ranges
- 🔌 **Sensor Abstraction**: Easy to add new sensor types via plugin architecture
- 🌦️ **Weather Station Support**: Optional Ecowitt GW3000/GW1000 integration with auto unit conversion
- 🧪 **Comprehensive Testing**: 40+ tests with pytest
- ⚙️ **Configuration-Driven**: INI-based configuration with validation
- 🚀 **Production Ready**: Systemd service files and installation scripts included
- 🐳 **Containerized Deployment**: Podman/Docker support with secrets management

## Quick Start

### Development Setup

```bash
# Clone the repository
cd /path/to/sensey

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r sensey_server/requirements.txt

# Configure server
cp sensey_server/sensey.ini.example sensey_server/sensey.ini
# Edit sensey.ini to choose storage backend (CSV or MySQL)

# Run tests
pytest

# Start server
cd sensey_server
python app.py
```

Server runs at http://localhost:5000

### Production Deployment (Raspberry Pi)

**Native systemd deployment:**
```bash
# Install server
./install-server.sh
sudo systemctl start sensey-server

# Install client (choose one)
./install-client.sh --garden      # For garden sensors (BH1750, HTU21D, moisture)
./install-client.sh --sensehat    # For Raspberry Pi Sense HAT

# Manage services
./manage-services.sh status all
./manage-services.sh logs server
```

### Containerized Deployment (Podman)

**For portable, containerized server deployment:**

```bash
# CSV storage (simple, file-based)
./install-server-podman.sh --csv

# MySQL storage (production, external database)
./install-server-podman.sh --mysql
```

**Features:**
- 🐳 **Portable**: Run anywhere Podman/Docker is available
- 🔒 **Isolated**: No conflicts with system packages
- 🔑 **Secure**: Podman secrets for password management
- 📦 **Self-contained**: All dependencies bundled in image

**Management:**
```bash
# Using Podman directly
podman ps                              # View containers
podman logs -f sensey-server-csv       # View logs
podman restart sensey-server-mysql     # Restart

# Using manage-services.sh
./manage-services.sh status server-podman-csv
./manage-services.sh logs server-podman-mysql
./manage-services.sh restart server-podman-csv
```

**Documentation:** See [sensey_server/podman/README.md](sensey_server/podman/README.md) for complete Podman deployment guide.

**Note:** Clients always run natively on edge devices (not containerized) for hardware sensor access.

## Architecture

### Server Architecture

```
sensey_server/
├── app.py              # Flask application entry point
├── config.py           # Configuration loader with validation
├── sensey_data.py      # Backward-compatible data access layer
├── ecowitt.py          # Ecowitt weather station integration (optional)
├── storage/            # Pluggable storage backends
│   ├── base.py         # Abstract base class
│   ├── csv_storage.py  # CSV file storage
│   └── mysql_storage.py # MySQL 8.4+ with hybrid schema
└── tests/              # Pytest test suite (40+ tests)
```

**Storage Backends:**

1. **CSV Storage** (default):
   - One file per client in `data/` directory
   - No additional dependencies
   - Simple and reliable

2. **MySQL Storage**:
   - Hybrid schema for optimal performance
   - Fixed columns for common measurements (temperature, humidity)
   - JSON column for additional/variable sensors
   - Connection pooling and caching
   - Requires MySQL 8.4+ and `mysql-connector-python`

### Client Architecture

```
sensey_client/
├── sensey.py           # Core abstractions (EnvironmentSensor, CSVLogger)
├── garden_sensey.py    # BH1750 light + HTU21D temp/humidity + moisture sensors
├── pi_sense_hat_sensey.py # Raspberry Pi Sense HAT integration
└── enviroplus_sensey.py    # Pimoroni Enviro+ device support
```

**Design Patterns:**

- **Abstract Base Classes**: `EnvironmentSensor` and `SenseEvent` define sensor interface
- **Plugin Architecture**: Easy to add new sensor types
- **Asynchronous Polling**: Non-blocking sensor data collection
- **Resilient Communication**: Local caching and retry logic for unreliable networks
- **Factory Pattern**: Storage backend instantiation via configuration

## Configuration

### Server Configuration (sensey.ini)

Located in `sensey_server/sensey.ini`:

```ini
[server]
# System-wide unit preference (metric or imperial)
system_units = metric

[storage]
# Storage backend: csv or mysql
backend = csv

[csv]
# Directory for CSV files
data_dir = data

[mysql]
# MySQL connection parameters (only if backend=mysql)
host = localhost
port = 3306
user = sensey
password =
database = sensey
pool_size = 5

[ecowitt]
# Ecowitt weather station integration (optional)
enabled = false
url = /ecowitt
client_name = ecowitt-weather
```

**Configuration Rules:**
- Application fails fast if `sensey.ini` is missing or invalid
- Use `sensey.ini.example` as template
- Environment variable override: `SENSEY_CONFIG_PATH`

**Podman/Container Secrets (MySQL only):**
- `SENSEY_MYSQL_PASSWORD` - Direct environment variable
- `SENSEY_MYSQL_PASSWORD_FILE` - Path to secret file (Podman secrets)
- Priority: ENV VAR > SECRET FILE > CONFIG FILE

### Client Configuration (sensey.ini)

Located in `sensey_client/sensey.ini`:

```ini
[server]
url = http://your-server:5000/data/{hostname}

[polling]
interval = 300  # Seconds between sensor readings
```

## API Endpoints

### POST /data/\<client_id\>

Receive sensor data from a client.

**Request:**
```json
{
  "timestamp": "2025-01-01T12:00:00",
  "temperature": 23.5,
  "humidity": 65.2,
  "lux": 150.0
}
```

**Response:**
```json
{
  "status": "success"
}
```

### POST /ecowitt

Receive data from Ecowitt weather stations (optional, configurable).

**Protocol:** HTTP POST with form-encoded data (imperial units)
**Auto-converts** to metric if `system_units=metric`

**Supported fields:**
- Outdoor: `tempf`, `humidity`, `baromrelin`
- Wind: `windspeedmph`, `winddir`, `windgustmph`
- Solar: `solarradiation`, `uv`
- Rain: `rainratein`, `dailyrainin`
- Indoor: `tempinf`, `humidityin` (optional)

**Response:** `"success"` (HTTP 200)

**Configuration:** Enable in `sensey.ini`:
```ini
[ecowitt]
enabled = true
url = /ecowitt
client_name = backyard-weather
```

Configure GW3000 Custom Server to: `http://your-server:5000/ecowitt`

### GET /

Dashboard showing available clients and client selector.

### GET /health

Health check endpoint for monitoring and container orchestration.

**Response (healthy):**
```json
{
  "status": "healthy",
  "storage": "accessible"
}
```

**Response (unhealthy):** HTTP 503
```json
{
  "status": "unhealthy",
  "error": "error details"
}
```

Used by Podman/Docker HEALTHCHECK and monitoring tools.

### GET /charts/\<client_id\>?range=\<timerange\>

Interactive charts for a specific client.

**Time Range Options:** `1h`, `6h`, `1d`, `3d` (default), `7d`, `all`

## Testing

### Run All Tests

```bash
# From project root
pytest

# With verbose output
pytest -v

# With coverage report
pytest --cov=sensey_server/storage --cov=sensey_server/config --cov-report=html
```

### Test Organization

- **Unit Tests**: Storage backends, configuration loading
- **Integration Tests**: Flask endpoints, multi-client scenarios
- **Fixtures**: Common test data and configurations in `conftest.py`

See [sensey_server/tests/README.md](sensey_server/tests/README.md) for detailed testing documentation.

## Supported Sensors

### Currently Implemented

| Sensor Type | Model | Measurements | Interface |
|-------------|-------|--------------|-----------|
| Light | BH1750 | Lux | I2C |
| Temperature/Humidity | HTU21D | °C, % | I2C |
| Soil Moisture | Generic analog | Voltage, % | SPI/ADC |
| Raspberry Pi Sense HAT | All sensors | Temp, humidity, pressure, etc. | Built-in |
| Pimoroni Enviro+ | All sensors | Temp, humidity, pressure, gas, PM | I2C |
| **Weather Stations** | **Ecowitt GW3000/GW1000/GW1100/GW2000** | **Temp, humidity, pressure, wind, rain, solar, UV** | **HTTP (Custom Server)** |

### Adding New Sensors

1. Create a sensor class extending `EnvironmentSensor`
2. Implement `poll()` method returning a `SenseEvent`
3. Define `sensor_names` property with measurement field names
4. Instantiate in your client script

Example:

```python
class MySensor(EnvironmentSensor):
    def poll(self) -> SenseEvent:
        # Read sensor
        reading = self.read_hardware()
        return MySenseEvent(reading)

    @property
    def sensor_names(self) -> List[str]:
        return ["my_measurement"]
```

## Development

### Project Structure

```
sensey/
├── .venv/                      # Unified development environment
├── pytest.ini                  # Test configuration
├── CLAUDE.md                   # AI assistant context
├── README.md                   # This file
├── sensey_server/              # Server application
│   ├── storage/                # Storage abstraction layer
│   ├── tests/                  # Server tests
│   ├── templates/              # Flask templates
│   ├── data/                   # CSV data files (gitignored)
│   ├── app.py                  # Flask app
│   ├── config.py               # Configuration loader
│   ├── sensey_data.py          # Data access compatibility layer
│   ├── sensey.ini.example      # Configuration template
│   └── requirements.txt        # Python dependencies
├── sensey_client/              # Client applications
│   ├── sensey.py               # Core abstractions
│   ├── garden_sensey.py        # Garden sensor implementation
│   ├── pi_sense_hat_sensey.py  # Sense HAT implementation
│   └── sensey.ini.example      # Client configuration template
└── services/                   # Systemd service files
    ├── sensey-server.service
    ├── sensey-client-garden.service
    └── sensey-client-sensehat.service
```

### Development vs Production

**Development:**
- Use root `.venv/` for unified environment
- Run apps directly: `python app.py`
- Easier testing and debugging

**Production:**
- Isolated venvs per component (`/home/pi/sensey/`)
- Systemd services for automatic startup
- Process management via `manage-services.sh`

### Branching Strategy

- `main`: Stable production-ready code
- `feature/*`: Feature development branches
- Create PR from feature branch to `main` for review

## Troubleshooting

### Server Won't Start

```
ConfigurationError: config.ini not found!
```

**Solution:** Copy `sensey.ini.example` to `sensey.ini` and configure.

### MySQL Connection Errors

```
StorageError: Failed to connect to MySQL
```

**Solution:**
1. Verify MySQL server is running: `systemctl status mysql`
2. Check credentials in `sensey.ini`
3. Ensure database exists: `mysql -u sensey -p sensey`
4. Install driver: `pip install mysql-connector-python`

### Client Can't Reach Server

```
ConnectionError: Failed to send data to server
```

**Solution:**
1. Check server URL in `sensey_client/sensey.ini`
2. Verify server is running: `curl http://server:5000/`
3. Check firewall rules on server
4. Review client logs: `./manage-services.sh logs garden`

### Import Errors in Tests

```
ModuleNotFoundError: No module named 'storage'
```

**Solution:** Run pytest from project root, not subdirectory.

## Contributing

### Code Style

- Follow PEP 8 guidelines
- Use type hints for function signatures
- Write docstrings for all public functions/classes
- Add tests for new features

### Pull Request Process

1. Create feature branch: `git checkout -b feature/my-feature`
2. Make changes and commit: `git commit -m "Add feature"`
3. Run tests: `pytest`
4. Push branch: `git push origin feature/my-feature`
5. Create PR to `main` branch

### Testing Requirements

- All new features must have tests
- Maintain >90% test coverage
- Tests must pass before merge

## License

[Add your license here]

## Credits

Developed by Philip

Built with:
- [Flask](https://flask.palletsprojects.com/) - Web framework
- [Plotly](https://plotly.com/python/) - Interactive visualizations
- [Pandas](https://pandas.pydata.org/) - Data processing
- [pytest](https://pytest.org/) - Testing framework

## Related Documentation

- [Server Tests Documentation](sensey_server/tests/README.md)
- [CLAUDE.md](CLAUDE.md) - AI assistant context and architecture details
- [Storage Backend Documentation](sensey_server/storage/)

## Roadmap

### High Priority
- [ ] **Data model refactoring**: Consolidate to single unified table (MySQL hybrid schema → normalized structure)
- [ ] **Global settings expansion**: Add server section for host, port, debug, log_level
- [ ] **Web UI for client labeling**: Edit client names through web interface

### Ecowitt Enhancements
- [ ] Multi-device PASSKEY mapping
- [ ] Additional sensor fields (soil moisture, extra temp sensors, lightning)
- [ ] Battery level monitoring and alerts
- [ ] Data validation and bounds checking

### Future Features
- [ ] PostgreSQL storage backend
- [ ] InfluxDB time-series storage backend
- [ ] Email/SMS alerts for sensor thresholds
- [ ] Mobile app for monitoring
- [ ] Historical data export (CSV, JSON, Excel)
- [ ] Multi-user authentication
- [ ] Sensor calibration interface

## Support

For issues, questions, or contributions:
- GitHub Issues: [Create an issue](https://github.com/yourusername/sensey/issues)
- Documentation: [See CLAUDE.md](CLAUDE.md) for detailed architecture
