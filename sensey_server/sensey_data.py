import pandas as pd
import os
import glob
import logging
from datetime import datetime, timedelta


DATA_DIR = "data"  # Directory where CSV files are stored

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def get_available_clients():
    """Return a list of client hostnames based on available CSV files."""
    if not os.path.exists(DATA_DIR):
        return []

    csv_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
    return [os.path.basename(f).replace(".csv", "") for f in csv_files]

def store_data(client_id: str, sensor_data: dict):
    """Append new sensor data to the client's CSV file."""
    os.makedirs(DATA_DIR, exist_ok=True)
    file_path = os.path.join(DATA_DIR, f"{client_id}.csv")

    if 'readings' in sensor_data:
        sensor_data = flatten_dict( sensor_data )

    df = pd.DataFrame([sensor_data])

    # Write header only if the file is new
    write_header = not os.path.exists(file_path)
    df.to_csv(file_path, mode="a", index=False, header=write_header)

def get_latest_data(client_id: str, days: int | None = 3) -> pd.DataFrame:
    """Read the latest week's worth of data for a client."""
    file_path = os.path.join(DATA_DIR, f"{client_id}.csv")
    
    if not os.path.exists(file_path):
        return None

    df = pd.read_csv(file_path)
    
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")
    
    if days is not None:
            cutoff_date = datetime.now() - timedelta(days=days)
            df = df[df["timestamp"] >= cutoff_date]
            logging.info( f"Returning data for last {days} days of {client_id} sensors" )
    
    return df

def flatten_dict(d: dict )->dict:
    """
    Flattens a dictionary by unpacking any nested dictionaries.
    """
    flattened = {}
    for k, v in d.items():
        if isinstance(v, dict):
            for inner_k, inner_v in v.items():
                flattened[f"{inner_k}"] = inner_v
        else:
            flattened[k] = v
    return flattened

