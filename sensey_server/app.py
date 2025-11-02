"""
Sensey Server - Flask Web Application

This module provides the main Flask web server for the Sensey distributed sensor
monitoring system. It receives sensor data from remote Raspberry Pi clients,
stores it using a pluggable storage backend, and provides web-based visualization.

Routes:
    POST /data/<client_id>  - Receive sensor data from clients
    GET  /                  - Dashboard with client selector
    GET  /charts/<client_id> - Interactive charts for a specific client

Storage:
    The application uses a pluggable storage backend (CSV or MySQL) configured
    via sensey.ini. The storage is initialized at startup and cleanly closed
    on shutdown.

Usage:
    # Development (with .venv activated)
    python app.py

    # Production (via systemd)
    systemctl start sensey-server

Configuration:
    sensey.ini must exist in the same directory. See sensey.ini.example for
    configuration options.

Environment Variables:
    SENSEY_DEBUG: Set to 'true' to enable Flask debug mode (default: false)
    SENSEY_CONFIG_PATH: Override path to sensey.ini (optional)
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import atexit
from flask import Flask, jsonify, request, render_template
import logging
import sensey_data  # Data handling module

app = Flask(__name__)

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize storage backend from configuration
def initialize_storage():
    """Initialize storage backend from sensey.ini configuration file."""
    try:
        from storage import create_storage_from_config
        from config import ConfigurationError

        storage = create_storage_from_config()
        storage.initialize()
        sensey_data.set_storage(storage)

        logger.info("Storage backend initialized successfully")

    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Application cannot start without valid configuration")
        raise
    except Exception as e:
        logger.error(f"Failed to initialize storage: {e}")
        raise

# Initialize storage on application startup
try:
    initialize_storage()
except Exception as e:
    logger.critical(f"FATAL: Storage initialization failed: {e}")
    logger.critical("Please check sensey.ini configuration and try again")
    # Let the exception propagate - app should not start without storage
    raise

# Register shutdown handler to close storage cleanly
@atexit.register
def shutdown_storage():
    """Close storage backend on application shutdown."""
    logger.info("Application shutting down, closing storage...")
    sensey_data.close_storage()

@app.route("/data/<client_id>", methods=["POST"])
def receive_data(client_id):
    """Receive sensor data from a remote Raspberry Pi."""
    try:
        sensor_data = request.get_json()
        if not sensor_data:
            return jsonify({"error": "Invalid JSON"}), 400

        logger.info(f"Received data from {client_id}: {sensor_data}")

        # Save data using sensey_data
        sensey_data.store_data(client_id, sensor_data)

        return jsonify({"status": "success"}), 200

    except Exception as e:
        logger.error(f"Error processing data from {client_id}: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/health")
def health():
    """
    Health check endpoint for container orchestration and monitoring.

    Returns 200 OK if the application is running and storage is accessible.
    Used by Podman/Docker HEALTHCHECK and monitoring tools.
    """
    try:
        # Verify storage is accessible by checking for clients
        # This is a lightweight check that exercises the storage layer
        _ = sensey_data.get_available_clients()
        return jsonify({"status": "healthy", "storage": "accessible"}), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 503

@app.route("/")
def index():
    """Show a dropdown to select a client and display charts for the selected client."""
    clients = sensey_data.get_available_clients()

    if not clients:
        return "<h2>No data available.</h2>"

    # Default to first client if none is selected
    return render_template("index.html", clients=clients)

@app.route("/charts/<client_id>")
def display_charts_for_client(client_id):
    """
    Generate and display interactive charts for a specific client.

    Creates one Plotly chart for each numeric column in the client's sensor data.
    Charts are displayed in a responsive grid layout with time range filtering.

    Args:
        client_id (str): Unique identifier for the client (typically hostname)

    Query Parameters:
        range (str): Time range for data (1h, 6h, 1d, 3d, 7d, all). Default: 3d

    Returns:
        Rendered HTML template with charts or error message

    Chart Features:
        - Dynamic y-axis scaling with 25% padding for better visibility
        - Dark theme for reduced eye strain
        - Responsive sizing for different screen sizes
        - Unique colors for each measurement type
    """
    # Get time range from query parameter (default: 3 days)
    time_range = request.args.get('range', '3d')

    # Fetch sensor data from storage backend
    df = sensey_data.get_latest_data(client_id, time_range)
    if df is None or df.empty:
        return render_template("charts.html", client_id=client_id,
                             error="No data available", time_range=time_range)

    # Generate one chart for each numeric column (temperature, humidity, etc.)
    charts = []
    colors = px.colors.qualitative.Set2  # Color palette for visual distinction

    # Iterate through all numeric columns (excluding timestamp)
    for i, column in enumerate(df.select_dtypes(include=['number']).columns):
        if column != "timestamp":
            # Convert column name to human-readable format (e.g., "soil_moisture" -> "Soil Moisture")
            display_name = column.replace("_", " ").title()

            # Calculate dynamic y-axis range with 25% padding above and below data range
            # This prevents data points from touching the chart edges
            y_min, y_max = df[column].min(), df[column].max()
            y_range_padding = (y_max - y_min) * 0.25 if y_max != y_min else y_max * 0.25
            y_range = [y_min - y_range_padding, y_max + y_range_padding]

            # Create Plotly line chart with markers for data points
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df["timestamp"],
                y=df[column],
                mode='lines+markers',  # Show both line and individual data points
                name=display_name,
                line=dict(color=colors[i % len(colors)])  # Cycle through color palette
            ))

            # Configure chart layout and styling
            fig.update_layout(
                title=f"{display_name} Over Time",
                xaxis_title="Timestamp",
                yaxis_title=display_name,
                yaxis=dict(range=y_range),  # Apply calculated range
                template="plotly_dark",      # Dark theme
                height=350,
                width=500,
                font=dict(family="Arial, sans-serif", size=14),
                margin=dict(l=30, r=30, t=50, b=50)  # Compact margins
            )

            # Convert chart to HTML and add to collection
            charts.append({
                'name': display_name,
                'html': fig.to_html(full_html=False, div_id=f"chart-{column}")
            })

    return render_template("charts.html", client_id=client_id,
                         charts=charts, time_range=time_range)

if __name__ == "__main__":
    # Disable debug in production for security
    debug_mode = os.environ.get('SENSEY_DEBUG', 'False').lower() == 'true'
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)

