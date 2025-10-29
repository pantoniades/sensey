"""
MySQL database storage implementation for Sensey sensor data.

Uses official Oracle MySQL Connector (mysql-connector-python) optimized for MySQL 8.4+.
Features connection pooling, hybrid schema (fixed columns + JSON), and efficient querying.

Hybrid Schema Design:
- Fixed columns for common measurements (temperature, humidity)
- JSON column for additional/variable measurements
- Leverages MySQL 8.4+ JSON features for flexibility
"""

import json
import pandas as pd
from typing import List, Optional, Dict, Any, Set
from datetime import datetime
import logging

from .base import SenseyStorage, StorageError

logger = logging.getLogger(__name__)

# Try to import mysql-connector-python
try:
    import mysql.connector
    from mysql.connector import Error as MySQLError
    from mysql.connector.pooling import MySQLConnectionPool
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    logger.warning("mysql-connector-python not installed, MySQL storage unavailable")


class MySQLStorage(SenseyStorage):
    """
    MySQL database storage implementation using official Oracle connector.

    Features:
    - Optimized for MySQL 8.4+
    - Hybrid schema: fixed columns (temp/humidity) + JSON (other sensors)
    - Connection pooling for better performance
    - Proper indexing for fast queries
    - Microsecond timestamp precision (DATETIME(3))

    Schema Design:
    --------------
    Table: sensor_data
    - id (PK, auto-increment)
    - client_id (VARCHAR, indexed)
    - timestamp (DATETIME(3), indexed)
    - temperature (DOUBLE, nullable) - common measurement
    - humidity (DOUBLE, nullable) - common measurement
    - readings (JSON, nullable) - all other measurements
    - created_at (DATETIME(3), audit field)

    Compound index on (client_id, timestamp) for efficient time-range queries.
    """

    # Define which fields get their own columns vs going into JSON
    FIXED_COLUMNS = {'temperature', 'humidity'}

    def __init__(
        self,
        host: str = "localhost",
        port: int = 3306,
        user: str = "sensey",
        password: str = "",
        database: str = "sensey",
        table_name: str = "sensor_data",
        pool_name: str = "sensey_pool",
        pool_size: int = 5
    ):
        """
        Initialize MySQL storage backend.

        Args:
            host: MySQL server hostname
            port: MySQL server port
            user: Database username
            password: Database password
            database: Database name
            table_name: Table name for sensor data
            pool_name: Connection pool name
            pool_size: Number of connections in the pool (default: 5)
        """
        if not MYSQL_AVAILABLE:
            raise StorageError(
                "mysql-connector-python not installed. "
                "Install with: pip install mysql-connector-python"
            )

        self.config = {
            'host': host,
            'port': port,
            'user': user,
            'password': password,
            'database': database,
            'charset': 'utf8mb4',
            'use_unicode': True,
            'autocommit': False,
            'pool_name': pool_name,
            'pool_size': pool_size,
            'pool_reset_session': True
        }
        self.database = database
        self.table_name = table_name
        self.pool: Optional[MySQLConnectionPool] = None

    def initialize(self) -> None:
        """
        Create database, connection pool, and ensure table exists.

        Raises:
            StorageError: If initialization fails
        """
        try:
            # First, connect without database to create it if needed
            config_without_db = self.config.copy()
            config_without_db.pop('database')
            config_without_db.pop('pool_name')
            config_without_db.pop('pool_size')
            config_without_db.pop('pool_reset_session')

            conn = mysql.connector.connect(**config_without_db)
            cursor = conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{self.database}`")
            cursor.close()
            conn.close()

            # Create connection pool
            self.pool = mysql.connector.pooling.MySQLConnectionPool(**self.config)

            # Create table with hybrid schema
            self._create_table()

            logger.info(
                f"MySQL storage initialized: {self.config['host']}/{self.database} "
                f"(pool: {self.config['pool_size']} connections, hybrid schema)"
            )

        except MySQLError as e:
            raise StorageError(f"Failed to initialize MySQL storage: {e}")

    def _create_table(self) -> None:
        """
        Create sensor data table with hybrid schema optimized for MySQL 8.4+.

        Fixed columns for common measurements, JSON for everything else.
        """
        conn = self.pool.get_connection()
        cursor = conn.cursor()

        try:
            # Create table with hybrid schema
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS `{self.table_name}` (
                    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    client_id VARCHAR(255) NOT NULL,
                    timestamp DATETIME(3) NOT NULL,
                    temperature DOUBLE DEFAULT NULL,
                    humidity DOUBLE DEFAULT NULL,
                    readings JSON DEFAULT NULL,
                    created_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
                    INDEX idx_client_timestamp (client_id, timestamp),
                    INDEX idx_timestamp (timestamp)
                ) ENGINE=InnoDB
                  DEFAULT CHARSET=utf8mb4
                  COLLATE=utf8mb4_unicode_ci
                  ROW_FORMAT=DYNAMIC
                  COMMENT='Hybrid schema: fixed columns for temp/humidity, JSON for other sensors'
            """)
            conn.commit()
            logger.debug(f"Table {self.table_name} created or verified (hybrid schema)")

        except MySQLError as e:
            conn.rollback()
            raise StorageError(f"Failed to create table: {e}")
        finally:
            cursor.close()
            conn.close()

    def get_available_clients(self) -> List[str]:
        """
        Return list of unique client IDs in database.

        Returns:
            Sorted list of client identifiers
        """
        conn = self.pool.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                f"SELECT DISTINCT client_id FROM `{self.table_name}` ORDER BY client_id"
            )
            clients = [row[0] for row in cursor.fetchall()]
            logger.debug(f"Found {len(clients)} clients in database")
            return clients

        except MySQLError as e:
            logger.error(f"Failed to get available clients: {e}")
            return []
        finally:
            cursor.close()
            conn.close()

    def store_data(self, client_id: str, sensor_data: Dict[str, Any]) -> None:
        """
        Insert sensor data into database using hybrid schema.

        Temperature and humidity go into dedicated columns.
        All other measurements go into the JSON 'readings' column.

        Args:
            client_id: Unique identifier for the client
            sensor_data: Dictionary containing sensor readings and timestamp

        Raises:
            StorageError: If data cannot be stored
        """
        conn = self.pool.get_connection()
        cursor = conn.cursor()

        try:
            # Flatten nested dictionaries
            if 'readings' in sensor_data:
                sensor_data = self.flatten_dict(sensor_data)

            # Prepare timestamp
            if 'timestamp' not in sensor_data:
                timestamp = datetime.now()
            elif isinstance(sensor_data['timestamp'], str):
                timestamp = pd.to_datetime(sensor_data['timestamp']).to_pydatetime()
            else:
                timestamp = sensor_data['timestamp']

            # Split data into fixed columns and JSON
            fixed_data = {}
            json_data = {}

            for key, value in sensor_data.items():
                if key == 'timestamp':
                    continue  # handled separately
                elif key in self.FIXED_COLUMNS:
                    fixed_data[key] = value
                else:
                    json_data[key] = value

            # Build INSERT query
            columns = ['client_id', 'timestamp']
            values = [client_id, timestamp]

            # Add fixed columns
            for col in self.FIXED_COLUMNS:
                if col in fixed_data:
                    columns.append(col)
                    values.append(fixed_data[col])

            # Add JSON column if there's additional data
            if json_data:
                columns.append('readings')
                values.append(json.dumps(json_data))

            placeholders = ', '.join(['%s'] * len(columns))
            column_names = ', '.join([f"`{col}`" for col in columns])

            query = f"INSERT INTO `{self.table_name}` ({column_names}) VALUES ({placeholders})"

            cursor.execute(query, values)
            conn.commit()
            logger.debug(f"Stored data for client {client_id} (fixed: {list(fixed_data.keys())}, json: {list(json_data.keys())})")

        except MySQLError as e:
            conn.rollback()
            raise StorageError(f"Failed to store data for {client_id}: {e}")
        finally:
            cursor.close()
            conn.close()

    def get_latest_data(
        self,
        client_id: str,
        time_range: str = "3d"
    ) -> Optional[pd.DataFrame]:
        """
        Query sensor data for a specific client.

        Merges fixed columns and JSON data into a single DataFrame.

        Args:
            client_id: Unique identifier for the client
            time_range: Time range string (e.g., '1h', '6h', '1d', '3d', 'all')

        Returns:
            DataFrame with sensor data, or None if no data exists
        """
        conn = self.pool.get_connection()

        try:
            cutoff_date = self.parse_time_range(time_range)

            if cutoff_date:
                query = f"""
                    SELECT timestamp, temperature, humidity, readings
                    FROM `{self.table_name}`
                    WHERE client_id = %s AND timestamp >= %s
                    ORDER BY timestamp ASC
                """
                df = pd.read_sql(query, conn, params=(client_id, cutoff_date))
            else:
                query = f"""
                    SELECT timestamp, temperature, humidity, readings
                    FROM `{self.table_name}`
                    WHERE client_id = %s
                    ORDER BY timestamp ASC
                """
                df = pd.read_sql(query, conn, params=(client_id,))

            if df.empty:
                logger.debug(f"No data found for client {client_id}")
                return None

            # Expand JSON column into separate columns
            df = self._expand_json_column(df)

            # Convert timestamp to datetime if needed
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])

            logger.debug(f"Retrieved {len(df)} records for {client_id} (range: {time_range})")
            return df

        except MySQLError as e:
            logger.error(f"Failed to read data for {client_id}: {e}")
            return None
        finally:
            conn.close()

    def get_all_clients_data(
        self,
        time_range: str = "3d"
    ) -> Dict[str, pd.DataFrame]:
        """
        Retrieve data for all clients efficiently in a single query.

        Args:
            time_range: Time range string (e.g., '1h', '6h', '1d', '3d', 'all')

        Returns:
            Dictionary mapping client_id to DataFrame of sensor data
        """
        conn = self.pool.get_connection()

        try:
            cutoff_date = self.parse_time_range(time_range)

            if cutoff_date:
                query = f"""
                    SELECT client_id, timestamp, temperature, humidity, readings
                    FROM `{self.table_name}`
                    WHERE timestamp >= %s
                    ORDER BY client_id, timestamp ASC
                """
                df = pd.read_sql(query, conn, params=(cutoff_date,))
            else:
                query = f"""
                    SELECT client_id, timestamp, temperature, humidity, readings
                    FROM `{self.table_name}`
                    ORDER BY client_id, timestamp ASC
                """
                df = pd.read_sql(query, conn)

            if df.empty:
                logger.debug("No data found for any clients")
                return {}

            # Expand JSON column
            df = self._expand_json_column(df)

            # Convert timestamp to datetime
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])

            # Split by client_id
            all_data = {}
            for client_id in df['client_id'].unique():
                client_df = df[df['client_id'] == client_id].drop('client_id', axis=1).reset_index(drop=True)
                all_data[client_id] = client_df

            logger.debug(f"Retrieved data for {len(all_data)} clients (range: {time_range})")
            return all_data

        except MySQLError as e:
            logger.error(f"Failed to read all clients data: {e}")
            return {}
        finally:
            conn.close()

    def close(self) -> None:
        """
        Close connection pool.

        Note: mysql-connector-python connection pools don't have explicit close method.
        Connections are automatically closed when returned to pool and pool is garbage collected.
        """
        if self.pool:
            logger.info("MySQL storage closed (connection pool will be garbage collected)")

    # Helper methods

    def _expand_json_column(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Expand the JSON 'readings' column into separate columns.

        Args:
            df: DataFrame with 'readings' JSON column

        Returns:
            DataFrame with JSON data expanded into columns
        """
        if 'readings' not in df.columns:
            return df

        # Parse JSON and expand into columns
        json_expanded = []
        for idx, row in df.iterrows():
            if pd.notna(row['readings']) and row['readings']:
                try:
                    if isinstance(row['readings'], str):
                        json_data = json.loads(row['readings'])
                    else:
                        json_data = row['readings']
                    json_expanded.append(json_data)
                except (json.JSONDecodeError, TypeError):
                    json_expanded.append({})
            else:
                json_expanded.append({})

        # Convert to DataFrame and merge
        if json_expanded:
            json_df = pd.DataFrame(json_expanded)
            # Drop the original readings column
            df = df.drop('readings', axis=1)
            # Concatenate with expanded JSON data
            df = pd.concat([df, json_df], axis=1)

        return df
