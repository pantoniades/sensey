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
    """Generate and display charts for a given client with time range selection."""
    time_range = request.args.get('range', '3d')
    df = sensey_data.get_latest_data(client_id, time_range)
    if df is None or df.empty:
        return render_template("charts.html", client_id=client_id, error="No data available", time_range=time_range)

    # Generate chart data for template
    charts = []
    colors = px.colors.qualitative.Set2
    
    for i, column in enumerate(df.select_dtypes(include=['number']).columns):
        if column != "timestamp":
            display_name = column.replace("_", " ").title()

            # Compute dynamic y-axis range
            y_min, y_max = df[column].min(), df[column].max()
            y_range_padding = (y_max - y_min) * 0.25 if y_max != y_min else y_max * 0.25
            y_range = [y_min - y_range_padding, y_max + y_range_padding]

            # Create line chart with a unique color
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["timestamp"], y=df[column], 
                                     mode='lines+markers', name=display_name, 
                                     line=dict(color=colors[i % len(colors)])))
            fig.update_layout(title=f"{display_name} Over Time",
                              xaxis_title="Timestamp",
                              yaxis_title=display_name,
                              yaxis=dict(range=y_range), 
                              template="plotly_dark",
                              height=350, width=500,
                              font=dict(family="Arial, sans-serif", size=14),
                              margin=dict(l=30, r=30, t=50, b=50))

            charts.append({
                'name': display_name,
                'html': fig.to_html(full_html=False, div_id=f"chart-{column}")
            })

    return render_template("charts.html", client_id=client_id, charts=charts, time_range=time_range)

if __name__ == "__main__":
    # Disable debug in production for security
    debug_mode = os.environ.get('SENSEY_DEBUG', 'False').lower() == 'true'
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)

