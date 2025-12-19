# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Sensey is a distributed sensor monitoring system with two main components:
- **sensey_client**: Raspberry Pi clients that collect sensor data and send it to a central server
- **sensey_server**: Flask web server that receives, stores, and visualizes sensor data

## Commands

### Development Setup (Unified Environment)

For development work on both server and client:

```bash
# From project root
cd /path/to/sensey

# Create virtual environment (if not exists)
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install server dependencies
pip install -r sensey_server/requirements.txt

# Install client dependencies (when available)
# pip install -r sensey_client/requirements.txt

# Copy and configure server
cp sensey_server/sensey.ini.example sensey_server/sensey.ini
# Edit sensey_server/sensey.ini to choose CSV or MySQL storage

# For MySQL storage, also install:
# pip install mysql-connector-python

# Run tests (from project root)
pytest

# Run server
cd sensey_server
python app.py
```

Server runs on http://0.0.0.0:5000

### Production Deployment (Raspberry Pi)

For production deployment with isolated environments:

```bash
# Server installation
./install-server.sh
sudo systemctl start sensey-server

# Client installation
./install-client.sh --garden  # or --sensehat
```

Production installs create isolated virtual environments in `/home/pi/sensey/`.

### Client Setup and Running
```bash
cd sensey_client
# Edit sensey.ini to configure server connection
python garden_sensey.py    # For garden sensors (BH1750, HTU21D, moisture)
python pi_sense_hat_sensey.py  # For Raspberry Pi Sense HAT
```

### Service Installation (Production)
For running as systemd services on Raspbian:

#### Server Installation
```bash
./install-server.sh
sudo systemctl start sensey-server
```

#### Client Installation
```bash
# For garden sensors
./install-client.sh --garden

# For Sense HAT
./install-client.sh --sensehat
```

#### Service Management
```bash
# Start/stop/restart services
./manage-services.sh start server
./manage-services.sh status all
./manage-services.sh logs garden

# Enable/disable auto-start
./manage-services.sh enable server
./manage-services.sh disable garden
```

## Architecture

### Client Architecture
- **Abstract Base Classes**: `EnvironmentSensor` and `SenseEvent` define the sensor interface
- **Sensor Implementations**: 
  - `BH1750LightSensor` - I2C light sensor
  - `H2UT1DLightHumiditySensor` - I2C temperature/humidity sensor  
  - `MoistureSensor` - SPI soil moisture sensor
  - `SenseHatReader` - Raspberry Pi Sense HAT integration
- **CSVLogger**: Handles data collection, local CSV logging, and HTTP transmission to server
- **Error Handling**: Implements retry logic with exponential backoff and local caching for failed transmissions

### Server Architecture
- **Flask Routes**:
  - `POST /data/<client_id>` - Receives sensor data from clients
  - `POST /ecowitt` - Receives data from Ecowitt weather stations (optional, configurable)
  - `GET /` - Dashboard showing available clients
  - `GET /charts/<client_id>` - Interactive Plotly charts for client data
- **Storage Abstraction Layer** (`storage/` package):
  - **Abstract Base**: `base.py` defines `SenseyStorage` interface
  - **CSV Backend**: `csv_storage.py` - File-based storage (default, no extra dependencies)
  - **MySQL Backend**: `mysql_storage.py` - Database storage for MySQL 8.4+ with hybrid schema:
    - Fixed columns for common measurements (temperature, humidity)
    - JSON column for additional/variable sensors (lux, soil_moisture, etc.)
  - **Factory**: `create_storage_from_config()` creates backend from `sensey.ini`
  - **Easy extensibility**: Add PostgreSQL, InfluxDB, etc. by implementing `SenseyStorage`
- **Configuration**: `config.py` loads and validates `sensey.ini` with fail-fast behavior
- **Data Access**: `sensey_data.py` provides backward-compatible API wrapping storage backends
- **Ecowitt Integration** (`ecowitt.py`): Optional module for receiving data from Ecowitt weather stations
  - Supports GW3000, GW1000, GW1100, GW2000 and compatible devices
  - Receives data via Custom Server / Custom Push feature
  - Auto-converts imperial units (°F, inHg, mph, inches) to metric based on system_units setting
  - Disabled by default, enabled via `sensey.ini` configuration

### Key Design Patterns
- **Plugin Architecture**:
  - Sensors extend abstract base classes for easy addition of new sensor types
  - Storage backends implement `SenseyStorage` interface for pluggable data persistence
- **Asynchronous Processing**: Client uses asyncio for non-blocking sensor polling
- **Resilient Communication**: Client caches unsent data locally and retries with backoff
- **Dynamic Configuration**:
  - Client reads `sensey.ini` for server endpoints and polling intervals
  - Server reads `sensey.ini` for storage backend selection and configuration
- **Factory Pattern**: `create_storage_from_config()` instantiates appropriate storage backend
- **Fail-Fast**: Server validates configuration at startup and refuses to run with invalid config
- **Backward Compatibility**: `sensey_data.py` maintains legacy API while using new storage layer

### Configuration

#### Server Configuration (`sensey_server/sensey.ini`)
- **System Units**: Global unit preference (`metric` or `imperial`, default: `metric`)
- **Storage Backend**: Choose between CSV or MySQL
- **CSV Settings**: Data directory path (default: `data/`)
- **MySQL Settings**: Host, port, user, password, database, connection pool size
- **Ecowitt Integration** (optional):
  - `enabled`: Enable/disable Ecowitt weather station integration (default: `false`)
  - `url`: Custom endpoint URL (default: `/ecowitt`)
  - `client_name`: Friendly name for dashboard (default: uses device PASSKEY)
  - Configure GW3000 Custom Server to push to: `http://your-server:5000/ecowitt`
- **Validation**: Application fails fast if `sensey.ini` is missing or invalid
- **Template**: Use `sensey.ini.example` as starting point
- **Environment Override**: `SENSEY_CONFIG_PATH` can specify alternate config location

#### Client Configuration (`sensey_client/sensey.ini`)
- Server endpoint URL and polling interval
- Sensor-specific settings

#### Data Retention
- Time range selectable in UI (1h, 6h, 1d, 3d, 7d, all)
- Storage backend handles time-based filtering efficiently

## TODO / Future Work

### Data Model Refactoring (HIGH PRIORITY)
- **Issue**: Currently MySQL uses hybrid schema (dedicated temp/humidity columns + JSON for other sensors)
- **Goal**: Consolidate to single unified table structure across all storage backends
- **Options**:
  - All sensors stored in JSON column (flexible but slower queries)
  - Normalized `sensor_readings` table with sensor_type, value columns
  - Wide table with common columns for all sensor types
- **Impact**: Breaking change, requires migration script

### Global Settings Expansion
- **Current**: Only `system_units` in `[server]` section
- **Needed**:
  - `host` - Server bind address (default: 0.0.0.0)
  - `port` - Server port (default: 5000)
  - `debug` - Debug mode flag
  - `log_level` - Logging verbosity (DEBUG, INFO, WARNING, ERROR)
  - Centralized configuration management via `config.py`

### Ecowitt Enhancements
- **Multi-device support**: Map PASSKEY to friendly names (e.g., `{"ABC123": "backyard", "DEF456": "frontyard"}`)
- **Additional sensor fields**: Soil moisture, extra temp sensors (temp1f-temp8f), lightning detection
- **Battery monitoring**: Alert/display battery levels for wireless sensors
- **Data validation**: Bounds checking and anomaly detection

### Web UI Improvements
- **Client labeling**: Edit client names through web UI instead of config file
- **Unit display**: Show units on charts based on system_units setting
- **Settings page**: Configure server settings via web interface