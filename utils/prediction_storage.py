"""
Prediction Storage Utility
Handles persistent storage of prediction results to JSON files
"""
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from src.infrastructure.storage.json_storage import JSONStorageBackend

logger = logging.getLogger(__name__)


class PredictionStorage:
    """Manages persistent storage of prediction results"""

    def __init__(self, storage_path: Path):
        """
        Initialize storage manager

        Args:
            storage_path: Path to prediction_history folder
        """
        self.storage_path = Path(storage_path)
        self.backend = JSONStorageBackend(self.storage_path)
        logger.info(f"Prediction storage initialized at {self.storage_path}")

    def _format_timestamp_for_filename(self, timestamp_str: str) -> str:
        """
        Convert ISO timestamp to filename format

        Args:
            timestamp_str: ISO format timestamp (e.g., '2024-11-23T14:30:00-05:00')

        Returns:
            Formatted string (e.g., '2024-11-23_14-30-00')
        """
        try:
            # Parse ISO timestamp
            dt = datetime.fromisoformat(timestamp_str)
            # Format as YYYY-MM-DD_HH-MM-SS
            return dt.strftime("%Y-%m-%d_%H-%M-%S")
        except Exception as e:
            logger.warning(f"Could not parse timestamp {timestamp_str}: {e}")
            # Fallback to current time
            return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    def save_prediction(self, prediction_dict: Dict[str, Any]) -> bool:
        """
        Save a prediction result to JSON file

        Args:
            prediction_dict: Prediction result containing:
                - result: Full prediction engine output
                - instrument: US100, ES, UK100
                - timezone: Timezone string
                - timestamp: When analysis was executed
                - filename: Original CSV filename
                - data_length: Number of OHLC candles
                - current_price: Latest close price

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Extract data timestamp from result for sorting
            result = prediction_dict.get('result', {})
            metadata = result.get('metadata', {})
            data_timestamp = metadata.get('timestamp', prediction_dict.get('timestamp'))

            # Create filename from data timestamp
            filename_timestamp = self._format_timestamp_for_filename(data_timestamp)
            instrument = prediction_dict.get('instrument', 'UNKNOWN')
            filename_key = f"{instrument}_{filename_timestamp}"

            # Prepare data for storage
            storage_data = {
                'result': result,
                'instrument': instrument,
                'timezone': prediction_dict.get('timezone'),
                'analysis_timestamp': prediction_dict.get('timestamp'),
                'data_timestamp': data_timestamp,
                'filename': prediction_dict.get('filename'),
                'data_length': prediction_dict.get('data_length'),
                'current_price': prediction_dict.get('current_price')
            }

            # Save using backend
            return self.backend.save(filename_key, storage_data)

        except Exception as e:
            logger.error(f"Failed to save prediction: {e}")
            return False

    def load_all_predictions(self) -> List[Dict[str, Any]]:
        """
        Load all predictions from storage

        Returns:
            List of prediction dictionaries
        """
        # Load all predictions using backend with high limit
        predictions = self.backend.query(limit=10000)
        logger.info(f"Loaded {len(predictions)} predictions from storage")
        return predictions

    def load_top_n_by_data_timestamp(self, n: int = 50) -> List[Dict[str, Any]]:
        """
        Load top N predictions sorted by data timestamp (most recent first)

        Args:
            n: Number of predictions to return

        Returns:
            List of top N predictions sorted by data timestamp
        """
        all_predictions = self.load_all_predictions()

        # Sort by data_timestamp (most recent first)
        sorted_predictions = sorted(
            all_predictions,
            key=lambda x: x.get('data_timestamp', ''),
            reverse=True
        )

        return sorted_predictions[:n]

    def get_prediction_count(self) -> int:
        """
        Get total number of saved predictions

        Returns:
            Count of JSON files in storage
        """
        return self.backend.count()

    def get_predictions_by_instrument(self, instrument: str) -> List[Dict[str, Any]]:
        """
        Get all predictions for a specific instrument

        Args:
            instrument: US100, ES, or UK100

        Returns:
            List of predictions for the instrument
        """
        return self.backend.list_by_instrument(instrument)

    def get_predictions_by_date_range(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Get predictions within date range (by data timestamp)

        Args:
            start_date: Start date string (YYYY-MM-DD)
            end_date: End date string (YYYY-MM-DD)

        Returns:
            List of predictions in date range
        """
        all_predictions = self.load_all_predictions()
        filtered = []

        for pred in all_predictions:
            data_timestamp = pred.get('data_timestamp', '')
            if data_timestamp:
                # Extract date from timestamp
                pred_date = data_timestamp.split('T')[0]
                if start_date <= pred_date <= end_date:
                    filtered.append(pred)

        # Sort by data timestamp
        return sorted(filtered, key=lambda x: x.get('data_timestamp', ''), reverse=True)

    def delete_prediction(self, filename: str) -> bool:
        """
        Delete a specific prediction file

        Args:
            filename: Filename to delete (e.g., 'US100_2024-11-23_14-30-00.json')

        Returns:
            True if deleted successfully
        """
        # Extract key from filename (remove .json extension if present)
        key = filename.replace('.json', '') if filename.endswith('.json') else filename
        return self.backend.delete(key)

    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get storage information and statistics

        Returns:
            Dictionary with storage stats
        """
        try:
            all_preds = self.load_all_predictions()
            instruments = {}

            for pred in all_preds:
                instrument = pred.get('instrument', 'UNKNOWN')
                if instrument not in instruments:
                    instruments[instrument] = 0
                instruments[instrument] += 1

            return {
                'total_predictions': len(all_preds),
                'predictions_by_instrument': instruments,
                'storage_path': str(self.storage_path),
                'last_updated': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get storage info: {e}")
            return {'error': str(e)}


# Global storage instance
_storage_instance = None


def get_storage(storage_path: Path = None) -> PredictionStorage:
    """
    Get or create global prediction storage instance

    Args:
        storage_path: Path to prediction_history folder (optional)

    Returns:
        PredictionStorage instance
    """
    global _storage_instance

    if _storage_instance is None:
        if storage_path is None:
            from scheduler.config import config
            storage_path = config.PREDICTION_HISTORY_PATH
        _storage_instance = PredictionStorage(storage_path)

    return _storage_instance
