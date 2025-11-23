"""
PostgreSQL-based Storage Backend
Handles database operations for prediction storage
"""
import json
import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool

logger = logging.getLogger(__name__)


class PostgreSQLStorageBackend:
    """
    PostgreSQL-based storage backend for predictions.
    Implements the same interface as JSONStorageBackend.
    """

    def __init__(self, database_url: str = None):
        """
        Initialize PostgreSQL storage backend.

        Args:
            database_url: PostgreSQL connection URL (e.g., postgresql://user:pass@host:port/db)
                         If None, reads from DATABASE_URL environment variable
        """
        self.database_url = database_url or os.getenv('DATABASE_URL')

        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required for PostgreSQL backend")

        # Create connection pool
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                1,  # min connections
                10,  # max connections
                self.database_url
            )
            logger.info("PostgreSQL connection pool created successfully")
        except Exception as e:
            logger.error(f"Failed to create PostgreSQL connection pool: {e}")
            raise

        # Initialize database schema
        self._initialize_schema()
        logger.info("PostgreSQLStorageBackend initialized")

    def _get_connection(self):
        """Get a connection from the pool"""
        return self.connection_pool.getconn()

    def _release_connection(self, conn):
        """Release a connection back to the pool"""
        self.connection_pool.putconn(conn)

    def _initialize_schema(self):
        """Create the predictions table if it doesn't exist"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Create predictions table with JSONB column for flexible data storage
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    id SERIAL PRIMARY KEY,
                    key VARCHAR(255) UNIQUE NOT NULL,
                    instrument VARCHAR(50),
                    data_timestamp TIMESTAMP,
                    analysis_timestamp TIMESTAMP,
                    data JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Create indexes for better query performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_predictions_instrument
                ON predictions(instrument);
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_predictions_data_timestamp
                ON predictions(data_timestamp DESC);
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_predictions_key
                ON predictions(key);
            """)

            conn.commit()
            logger.info("PostgreSQL schema initialized successfully")

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to initialize schema: {e}")
            raise
        finally:
            if conn:
                cursor.close()
                self._release_connection(conn)

    def save(self, key: str, data: Dict[str, Any]) -> bool:
        """
        Save prediction data to PostgreSQL.

        Args:
            key: Unique key for the prediction
            data: Prediction data dictionary

        Returns:
            True if successful, False otherwise
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Extract metadata for indexed columns
            instrument = data.get('instrument')
            data_timestamp = data.get('data_timestamp')
            analysis_timestamp = data.get('analysis_timestamp')

            # Convert timestamps to datetime objects if they're strings
            if data_timestamp and isinstance(data_timestamp, str):
                try:
                    data_timestamp = datetime.fromisoformat(data_timestamp.replace('Z', '+00:00'))
                except:
                    data_timestamp = None

            if analysis_timestamp and isinstance(analysis_timestamp, str):
                try:
                    analysis_timestamp = datetime.fromisoformat(analysis_timestamp.replace('Z', '+00:00'))
                except:
                    analysis_timestamp = None

            # Insert or update using UPSERT
            cursor.execute("""
                INSERT INTO predictions (key, instrument, data_timestamp, analysis_timestamp, data, updated_at)
                VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (key)
                DO UPDATE SET
                    instrument = EXCLUDED.instrument,
                    data_timestamp = EXCLUDED.data_timestamp,
                    analysis_timestamp = EXCLUDED.analysis_timestamp,
                    data = EXCLUDED.data,
                    updated_at = CURRENT_TIMESTAMP;
            """, (key, instrument, data_timestamp, analysis_timestamp, json.dumps(data)))

            conn.commit()
            logger.info(f"Saved prediction with key: {key}")
            return True

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to save prediction: {e}")
            return False
        finally:
            if conn:
                cursor.close()
                self._release_connection(conn)

    def load(self, key: str) -> Dict[str, Any]:
        """
        Load prediction data from PostgreSQL.

        Args:
            key: Unique key for the prediction

        Returns:
            Prediction data dictionary or empty dict if not found
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("""
                SELECT data FROM predictions WHERE key = %s;
            """, (key,))

            result = cursor.fetchone()

            if result:
                logger.info(f"Loaded prediction with key: {key}")
                return result['data']
            else:
                logger.warning(f"Prediction not found with key: {key}")
                return {}

        except Exception as e:
            logger.error(f"Failed to load prediction: {e}")
            return {}
        finally:
            if conn:
                cursor.close()
                self._release_connection(conn)

    def query(self, filters: Dict[str, Any] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Query predictions from PostgreSQL with optional filters.

        Args:
            filters: Dictionary of filter criteria (e.g., {'instrument': 'US100'})
            limit: Maximum number of results to return

        Returns:
            List of matching predictions
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Build query with filters
            query = "SELECT data FROM predictions"
            params = []

            if filters:
                conditions = []
                for key, value in filters.items():
                    if key == 'instrument':
                        conditions.append("instrument = %s")
                        params.append(value)
                    else:
                        # For other filters, search in JSONB data
                        conditions.append(f"data->>{key} = %s")
                        params.append(str(value))

                if conditions:
                    query += " WHERE " + " AND ".join(conditions)

            # Order by data_timestamp descending (most recent first)
            query += " ORDER BY data_timestamp DESC NULLS LAST"

            # Add limit
            query += f" LIMIT %s"
            params.append(limit)

            cursor.execute(query, params)
            results = cursor.fetchall()

            predictions = [row['data'] for row in results]
            logger.info(f"Queried {len(predictions)} predictions")
            return predictions

        except Exception as e:
            logger.error(f"Failed to query predictions: {e}")
            return []
        finally:
            if conn:
                cursor.close()
                self._release_connection(conn)

    def count(self) -> int:
        """
        Count total number of saved predictions.

        Returns:
            Number of predictions
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM predictions;")
            count = cursor.fetchone()[0]

            logger.info(f"Prediction count: {count}")
            return count

        except Exception as e:
            logger.error(f"Failed to count predictions: {e}")
            return 0
        finally:
            if conn:
                cursor.close()
                self._release_connection(conn)

    def list_by_instrument(self, instrument: str) -> List[Dict[str, Any]]:
        """
        List all predictions for a specific instrument.

        Args:
            instrument: Instrument code (e.g., 'US100')

        Returns:
            List of predictions for the instrument
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("""
                SELECT data FROM predictions
                WHERE instrument = %s
                ORDER BY data_timestamp DESC NULLS LAST;
            """, (instrument,))

            results = cursor.fetchall()
            predictions = [row['data'] for row in results]

            logger.info(f"Found {len(predictions)} predictions for {instrument}")
            return predictions

        except Exception as e:
            logger.error(f"Failed to list predictions by instrument: {e}")
            return []
        finally:
            if conn:
                cursor.close()
                self._release_connection(conn)

    def delete(self, key: str) -> bool:
        """
        Delete a prediction from PostgreSQL.

        Args:
            key: Unique key for the prediction

        Returns:
            True if successful, False otherwise
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM predictions WHERE key = %s;
            """, (key,))

            deleted_count = cursor.rowcount
            conn.commit()

            if deleted_count > 0:
                logger.info(f"Deleted prediction with key: {key}")
                return True
            else:
                logger.warning(f"No prediction found with key: {key}")
                return False

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to delete prediction: {e}")
            return False
        finally:
            if conn:
                cursor.close()
                self._release_connection(conn)

    def close(self):
        """Close all database connections"""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("PostgreSQL connection pool closed")
