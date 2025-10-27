import pandas as pd
import os
import glob
import logging
from datetime import datetime, timedelta
from functools import lru_cache



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

def _get_file_hash(file_path: str) -> str:
    """Get hash of file modification time for cache key."""
    if not os.path.exists(file_path):
        return "none"
    return str(int(os.path.getmtime(file_path)))

@lru_cache(maxsize=32)
def _cached_read_csv(file_path: str, file_hash: str) -> pd.DataFrame:
    """Cached CSV reading function."""
    if not os.path.exists(file_path):
        return None
    return pd.read_csv(file_path)

def get_latest_data(client_id: str, time_range: str = "3d") -> pd.DataFrame:
    """Read data for a client with flexible time range support.
    
    Args:
        client_id: Client identifier
        time_range: Time range in format like '1h', '6h', '1d', '3d', '7d', 'all'
    """
    file_path = os.path.join(DATA_DIR, f"{client_id}.csv")
    
    if not os.path.exists(file_path):
        return None

    # Use cached reading with file modification time as cache key
    file_hash = _get_file_hash(file_path)
    df = _cached_read_csv(file_path, file_hash)
    
    if df is None or df.empty:
        return None
    
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")
    
    # Parse time range and filter data
    if time_range != "all":
        cutoff_date = _parse_time_range(time_range)
        if cutoff_date:
            df = df[df["timestamp"] >= cutoff_date]
            logging.info(f"Returning data for last {time_range} of {client_id} sensors")
    
    return df

def _parse_time_range(time_range: str) -> datetime:
    """Parse time range string and return cutoff datetime."""
    now = datetime.now()
    
    if time_range.endswith('h'):
        hours = int(time_range[:-1])
        return now - timedelta(hours=hours)
    elif time_range.endswith('d'):
        days = int(time_range[:-1])
        return now - timedelta(days=days)
    elif time_range.endswith('w'):
        weeks = int(time_range[:-1])
        return now - timedelta(weeks=weeks)
    else:
        # Default to 3 days if invalid format
        return now - timedelta(days=3)

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

