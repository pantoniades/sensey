"""
Ecowitt weather station integration for Sensey Server.

Receives data from Ecowitt GW3000 (and compatible) weather stations
via the Custom Server / Custom Push feature.

Protocol Details:
- HTTP POST with application/x-www-form-urlencoded data
- All values in imperial units (°F, inHg, mph, inches)
- Converts to metric if system_units=metric

Supported Devices:
- GW3000, GW1000, GW1100, GW2000
- Compatible Ecowitt/Froggit/Ambient Weather stations

TODO: Future enhancements
- Support multiple devices via PASSKEY mapping
- Configurable field mapping
- Battery level alerts
- Data validation and bounds checking
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from flask import request

logger = logging.getLogger(__name__)

# TODO: Move unit conversions to a shared utilities module
# Other sensors may need these conversions in the future


def register_routes(app, ecowitt_config, system_units: str):
    """
    Register Ecowitt routes with Flask app.

    Called from app.py if ecowitt is enabled.

    Args:
        app: Flask application instance
        ecowitt_config: ConfigParser section for [ecowitt]
        system_units: Global system units setting ('metric' or 'imperial')
    """
    # Import here to avoid circular dependency
    import sensey_data

    # Extract config
    url = ecowitt_config.get('url', '/ecowitt')
    client_name = ecowitt_config.get('client_name', None)

    # Convert to metric if system is configured for metric
    convert_to_metric = (system_units.lower() == 'metric')

    logger.info(f"Registering Ecowitt endpoint: {url}")
    logger.info(f"Unit conversion: {'imperial → metric' if convert_to_metric else 'imperial (no conversion)'}")

    @app.route(url, methods=['POST'])
    def receive_ecowitt():
        """
        Receive sensor data from Ecowitt device Custom Server push.

        Returns:
            HTTP 200 with "success" on successful data storage
            HTTP 400 on invalid data
            HTTP 500 on storage errors
        """
        try:
            # Parse form-encoded data
            raw_data = request.form.to_dict()

            if not raw_data:
                logger.warning("Received empty Ecowitt data")
                return "error: no data", 400

            logger.debug(f"Received Ecowitt data: {raw_data.keys()}")

            # Determine client ID
            device_id = _get_client_id(raw_data, client_name)

            # Transform Ecowitt format to Sensey format
            sensor_data = _parse_ecowitt_data(raw_data, convert_to_metric)

            # Store via sensey_data
            sensey_data.store_data(device_id, sensor_data)

            logger.info(f"Stored Ecowitt data from {device_id}")

            # Ecowitt expects simple success response
            return "success", 200

        except Exception as e:
            logger.error(f"Error processing Ecowitt data: {e}", exc_info=True)
            return "error", 500


def _get_client_id(raw_data: Dict[str, str], configured_name: Optional[str]) -> str:
    """
    Extract client ID from data or use configured name.

    Args:
        raw_data: Raw Ecowitt data dictionary
        configured_name: Configured client name from sensey.ini

    Returns:
        Client identifier string
    """
    if configured_name:
        return configured_name

    # Use PASSKEY if available, otherwise generic name
    passkey = raw_data.get('PASSKEY', 'unknown')
    return f"ecowitt-{passkey}"


def _parse_ecowitt_data(raw_data: Dict[str, str], convert_to_metric: bool) -> Dict[str, Any]:
    """
    Transform Ecowitt field names and units to Sensey format.

    Ecowitt sends:
    - All temperatures in °F
    - Pressure in inHg
    - Wind speed in mph
    - Rain in inches

    Args:
        raw_data: Raw form data from Ecowitt device
        convert_to_metric: Whether to convert to metric units

    Returns:
        Dictionary with standard Sensey sensor data format:
        {
            "timestamp": "2025-12-18 10:30:00",
            "temperature": 22.5,
            "humidity": 65.0,
            ...
        }
    """
    sensor_data = {}

    # Parse timestamp - Ecowitt sends as "dateutc" in format "2025-12-18 10:30:00"
    timestamp_str = raw_data.get('dateutc')
    if timestamp_str:
        sensor_data['timestamp'] = timestamp_str
    else:
        sensor_data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Outdoor temperature
    if 'tempf' in raw_data:
        temp = float(raw_data['tempf'])
        sensor_data['temperature'] = _fahrenheit_to_celsius(temp) if convert_to_metric else temp

    # Outdoor humidity
    if 'humidity' in raw_data:
        sensor_data['humidity'] = float(raw_data['humidity'])

    # Barometric pressure (relative)
    if 'baromrelin' in raw_data:
        pressure = float(raw_data['baromrelin'])
        sensor_data['pressure'] = _inhg_to_hpa(pressure) if convert_to_metric else pressure

    # Wind speed
    if 'windspeedmph' in raw_data:
        speed = float(raw_data['windspeedmph'])
        sensor_data['wind_speed'] = _mph_to_ms(speed) if convert_to_metric else speed

    # Wind direction
    if 'winddir' in raw_data:
        sensor_data['wind_direction'] = float(raw_data['winddir'])

    # Wind gust
    if 'windgustmph' in raw_data:
        gust = float(raw_data['windgustmph'])
        sensor_data['wind_gust'] = _mph_to_ms(gust) if convert_to_metric else gust

    # Max daily gust
    if 'maxdailygust' in raw_data:
        max_gust = float(raw_data['maxdailygust'])
        sensor_data['wind_gust_max_daily'] = _mph_to_ms(max_gust) if convert_to_metric else max_gust

    # Solar radiation
    if 'solarradiation' in raw_data:
        sensor_data['solar_radiation'] = float(raw_data['solarradiation'])

    # UV index
    if 'uv' in raw_data:
        sensor_data['uv_index'] = float(raw_data['uv'])

    # Rain rate (traditional rain gauge)
    if 'rainratein' in raw_data:
        rate = float(raw_data['rainratein'])
        sensor_data['rain_rate'] = _inches_to_mm(rate) if convert_to_metric else rate

    # Rain rate (piezo rain sensor)
    if 'rrain_piezo' in raw_data:
        rate = float(raw_data['rrain_piezo'])
        sensor_data['rain_rate'] = _inches_to_mm(rate) if convert_to_metric else rate

    # Daily rain (traditional rain gauge)
    if 'dailyrainin' in raw_data:
        rain = float(raw_data['dailyrainin'])
        sensor_data['rain_daily'] = _inches_to_mm(rain) if convert_to_metric else rain

    # Daily rain (piezo rain sensor)
    if 'drain_piezo' in raw_data:
        rain = float(raw_data['drain_piezo'])
        sensor_data['rain_daily'] = _inches_to_mm(rain) if convert_to_metric else rain

    # Hourly rain (piezo)
    if 'hrain_piezo' in raw_data:
        rain = float(raw_data['hrain_piezo'])
        sensor_data['rain_hourly'] = _inches_to_mm(rain) if convert_to_metric else rain

    # Weekly rain (piezo)
    if 'wrain_piezo' in raw_data:
        rain = float(raw_data['wrain_piezo'])
        sensor_data['rain_weekly'] = _inches_to_mm(rain) if convert_to_metric else rain

    # Monthly rain (piezo)
    if 'mrain_piezo' in raw_data:
        rain = float(raw_data['mrain_piezo'])
        sensor_data['rain_monthly'] = _inches_to_mm(rain) if convert_to_metric else rain

    # Yearly rain (piezo)
    if 'yrain_piezo' in raw_data:
        rain = float(raw_data['yrain_piezo'])
        sensor_data['rain_yearly'] = _inches_to_mm(rain) if convert_to_metric else rain

    # Indoor temperature (optional)
    if 'tempinf' in raw_data:
        temp_in = float(raw_data['tempinf'])
        sensor_data['temperature_indoor'] = _fahrenheit_to_celsius(temp_in) if convert_to_metric else temp_in

    # Indoor humidity (optional)
    if 'humidityin' in raw_data:
        sensor_data['humidity_indoor'] = float(raw_data['humidityin'])

    # Absolute pressure (optional)
    if 'baromabsin' in raw_data:
        pressure_abs = float(raw_data['baromabsin'])
        sensor_data['pressure_absolute'] = _inhg_to_hpa(pressure_abs) if convert_to_metric else pressure_abs

    # Battery voltage (WH90 sensor)
    if 'wh90batt' in raw_data:
        sensor_data['battery_wh90'] = float(raw_data['wh90batt'])

    # Battery voltage (WH65 sensor)
    if 'wh65batt' in raw_data:
        sensor_data['battery_wh65'] = float(raw_data['wh65batt'])

    # TODO: Add more fields as needed
    # - Soil moisture sensors (soilmoisture1-8)
    # - Additional temperature sensors (temp1f-temp8f)
    # - Additional humidity sensors (humidity1-8)
    # - PM2.5 air quality sensors
    # - Lightning detection

    return sensor_data


# Unit conversion functions
# TODO: Move these to a shared utils module for reuse across sensors

def _fahrenheit_to_celsius(fahrenheit: float) -> float:
    """Convert temperature from °F to °C"""
    return round((fahrenheit - 32) * 5 / 9, 2)


def _inhg_to_hpa(inhg: float) -> float:
    """Convert pressure from inHg to hPa (millibars)"""
    return round(inhg * 33.8639, 2)


def _mph_to_ms(mph: float) -> float:
    """Convert wind speed from mph to m/s"""
    return round(mph * 0.44704, 2)


def _inches_to_mm(inches: float) -> float:
    """Convert rainfall from inches to mm"""
    return round(inches * 25.4, 2)
