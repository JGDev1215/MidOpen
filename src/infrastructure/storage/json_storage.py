"""
JSON-based Storage Backend
Handles file I/O for prediction storage
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class JSONStorageBackend:
    """
    JSON file-based storage backend for predictions.
    Responsible only for file I/O operations.
    """

    def __init__(self, storage_path: Path):
        """
        Initialize JSON storage backend.

        Args:
            storage_path: Path to prediction_history directory
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"JSONStorageBackend initialized with path: {self.storage_path}")

    def save(self, key: str, data: Dict[str, Any]) -> bool:
        """
        Save prediction data to JSON file.

        Args:
            key: Filename key (without extension)
            data: Prediction data dictionary

        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = self.storage_path / f"{key}.json"
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved prediction to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save prediction: {e}")
            return False

    def load(self, key: str) -> Dict[str, Any]:
        """
        Load prediction data from JSON file.

        Args:
            key: Filename key (without extension)

        Returns:
            Prediction data dictionary or empty dict if not found
        """
        try:
            file_path = self.storage_path / f"{key}.json"
            if file_path.exists():
                with open(file_path, 'r') as f:
                    data = json.load(f)
                logger.info(f"Loaded prediction from {file_path}")
                return data
            else:
                logger.warning(f"File not found: {file_path}")
                return {}
        except Exception as e:
            logger.error(f"Failed to load prediction: {e}")
            return {}

    def query(self, filters: Dict[str, Any] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Query predictions from storage.

        Args:
            filters: Dictionary of filter criteria (e.g., {'instrument': 'US100'})
            limit: Maximum number of results to return

        Returns:
            List of matching predictions
        """
        try:
            predictions = []
            for json_file in sorted(self.storage_path.glob("*.json"), reverse=True):
                try:
                    with open(json_file, 'r') as f:
                        pred = json.load(f)

                        # Apply filters
                        if filters:
                            match = True
                            for key, value in filters.items():
                                if pred.get(key) != value:
                                    match = False
                                    break
                            if not match:
                                continue

                        predictions.append(pred)

                        # Check limit
                        if len(predictions) >= limit:
                            break
                except Exception as e:
                    logger.warning(f"Failed to load {json_file.name}: {e}")

            logger.info(f"Queried {len(predictions)} predictions")
            return predictions
        except Exception as e:
            logger.error(f"Failed to query predictions: {e}")
            return []

    def count(self) -> int:
        """
        Count total number of saved predictions.

        Returns:
            Number of prediction files
        """
        try:
            count = len(list(self.storage_path.glob("*.json")))
            logger.info(f"Prediction count: {count}")
            return count
        except Exception as e:
            logger.error(f"Failed to count predictions: {e}")
            return 0

    def list_by_instrument(self, instrument: str) -> List[Dict[str, Any]]:
        """
        List all predictions for a specific instrument.

        Args:
            instrument: Instrument code (e.g., 'US100')

        Returns:
            List of predictions for the instrument
        """
        try:
            predictions = []
            for json_file in sorted(self.storage_path.glob("*.json"), reverse=True):
                try:
                    with open(json_file, 'r') as f:
                        pred = json.load(f)
                        if pred.get('instrument') == instrument:
                            predictions.append(pred)
                except Exception as e:
                    logger.warning(f"Failed to load {json_file.name}: {e}")

            logger.info(f"Found {len(predictions)} predictions for {instrument}")
            return predictions
        except Exception as e:
            logger.error(f"Failed to list predictions by instrument: {e}")
            return []

    def delete(self, key: str) -> bool:
        """
        Delete a prediction file.

        Args:
            key: Filename key (without extension)

        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = self.storage_path / f"{key}.json"
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted {file_path}")
                return True
            else:
                logger.warning(f"File not found: {file_path}")
                return False
        except Exception as e:
            logger.error(f"Failed to delete prediction: {e}")
            return False
