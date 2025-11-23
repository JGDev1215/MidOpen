"""
Service Layer Protocols (Interfaces)
Defines contracts for all application services using Python Protocols
"""
from typing import Protocol, Dict, List, Any, Optional, Tuple
from pathlib import Path


class ConfigService(Protocol):
    """
    Protocol for configuration management services.
    Handles loading and saving of configuration data.
    """

    def load(self) -> Dict[str, Any]:
        """
        Load configuration data.

        Returns:
            Configuration data dictionary, empty dict if not found
        """
        ...

    def save(self, data: Dict[str, Any]) -> None:
        """
        Save configuration data.

        Args:
            data: Configuration data to save
        """
        ...


class LogService(Protocol):
    """
    Protocol for audit logging services.
    Handles appending and retrieving audit log entries.
    """

    def append(self, log_entry: Dict[str, Any]) -> None:
        """
        Append a log entry to the audit log.

        Args:
            log_entry: Dictionary containing log data
        """
        ...

    def load_recent(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Load recent log entries from the last N days.

        Args:
            days: Number of days to look back

        Returns:
            List of log entries
        """
        ...

    def load_instrument_history(self, instrument: str) -> List[Dict[str, Any]]:
        """
        Load all log entries for a specific instrument.

        Args:
            instrument: Instrument name (e.g., 'US100')

        Returns:
            List of log entries for the instrument
        """
        ...


class StorageService(Protocol):
    """
    Protocol for prediction storage services.
    Handles saving, loading, and querying prediction data.
    """

    def save(self, key: str, data: Dict[str, Any]) -> bool:
        """
        Save data to storage.

        Args:
            key: Unique key for the data
            data: Data to save

        Returns:
            True if successful, False otherwise
        """
        ...

    def load(self, key: str) -> Dict[str, Any]:
        """
        Load data from storage.

        Args:
            key: Unique key for the data

        Returns:
            Data dictionary or empty dict if not found
        """
        ...

    def query(self, filters: Optional[Dict[str, Any]] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Query data from storage with optional filters.

        Args:
            filters: Dictionary of filter criteria
            limit: Maximum number of results to return

        Returns:
            List of matching data dictionaries
        """
        ...

    def count(self) -> int:
        """
        Count total number of stored items.

        Returns:
            Total count of items
        """
        ...

    def list_by_instrument(self, instrument: str) -> List[Dict[str, Any]]:
        """
        List all items for a specific instrument.

        Args:
            instrument: Instrument code (e.g., 'US100')

        Returns:
            List of items for the instrument
        """
        ...

    def delete(self, key: str) -> bool:
        """
        Delete an item from storage.

        Args:
            key: Unique key for the item

        Returns:
            True if deleted successfully, False otherwise
        """
        ...


class WeightManagementService(Protocol):
    """
    Protocol for weight management services.
    Handles weight configuration, validation, and adjustments.
    """

    def get_weights(self, instrument: str) -> Dict[str, float]:
        """
        Get current weights for an instrument.

        Args:
            instrument: Instrument code (e.g., 'US100')

        Returns:
            Dictionary of weight values
        """
        ...

    def set_weights(self, instrument: str, weights: Dict[str, float]) -> None:
        """
        Set weights for an instrument.

        Args:
            instrument: Instrument code
            weights: Dictionary of weight values (must sum to 1.0)

        Raises:
            ValueError: If weights don't sum to 1.0
        """
        ...

    def validate_weights(self, weights: Dict[str, float]) -> Tuple[bool, str]:
        """
        Validate weights (must sum to 1.0).

        Args:
            weights: Dictionary of weight values

        Returns:
            Tuple of (is_valid, message)
        """
        ...

    def get_all_instruments(self) -> List[str]:
        """
        Get list of all configured instruments.

        Returns:
            List of instrument codes
        """
        ...

    def reset_instrument_weights(self, instrument: str) -> None:
        """
        Reset weights for an instrument to defaults.

        Args:
            instrument: Instrument code
        """
        ...


class PredictionStorageService(Protocol):
    """
    Protocol for prediction storage services.
    Handles prediction persistence and retrieval.
    """

    def save_prediction(self, prediction_dict: Dict[str, Any]) -> bool:
        """
        Save a prediction result.

        Args:
            prediction_dict: Prediction data

        Returns:
            True if saved successfully
        """
        ...

    def load_all_predictions(self) -> List[Dict[str, Any]]:
        """
        Load all predictions from storage.

        Returns:
            List of prediction dictionaries
        """
        ...

    def get_prediction_count(self) -> int:
        """
        Get total number of saved predictions.

        Returns:
            Count of predictions
        """
        ...

    def get_predictions_by_instrument(self, instrument: str) -> List[Dict[str, Any]]:
        """
        Get all predictions for a specific instrument.

        Args:
            instrument: Instrument code

        Returns:
            List of predictions for the instrument
        """
        ...

    def delete_prediction(self, filename: str) -> bool:
        """
        Delete a specific prediction.

        Args:
            filename: Filename or key of the prediction

        Returns:
            True if deleted successfully
        """
        ...


class AnalysisService(Protocol):
    """
    Protocol for analysis services.
    Handles prediction analysis and market assessment.
    """

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform analysis on market data.

        Args:
            data: Market data to analyze

        Returns:
            Analysis results dictionary
        """
        ...

    def get_bias(self, analysis_result: Dict[str, Any]) -> str:
        """
        Get market bias from analysis result.

        Args:
            analysis_result: Result from analyze method

        Returns:
            Bias string (e.g., 'BULLISH', 'BEARISH')
        """
        ...

    def get_confidence(self, analysis_result: Dict[str, Any]) -> float:
        """
        Get confidence score from analysis result.

        Args:
            analysis_result: Result from analyze method

        Returns:
            Confidence score (0-100)
        """
        ...


class DataValidationService(Protocol):
    """
    Protocol for data validation services.
    Handles validation of various data types.
    """

    def validate_weights(self, weights: Dict[str, float]) -> Tuple[bool, str]:
        """
        Validate weight configuration.

        Args:
            weights: Weight dictionary to validate

        Returns:
            Tuple of (is_valid, message)
        """
        ...

    def validate_prediction_data(self, data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate prediction data structure.

        Args:
            data: Prediction data to validate

        Returns:
            Tuple of (is_valid, message)
        """
        ...

    def validate_instrument(self, instrument: str) -> bool:
        """
        Validate instrument code.

        Args:
            instrument: Instrument code to validate

        Returns:
            True if valid
        """
        ...


class FormattingService(Protocol):
    """
    Protocol for data formatting services.
    Handles formatting of various data types.
    """

    def format_timestamp(self, timestamp_str: str) -> str:
        """
        Format ISO timestamp to standard format.

        Args:
            timestamp_str: ISO format timestamp

        Returns:
            Formatted timestamp string
        """
        ...

    def format_weights(self, weights: Dict[str, float]) -> Dict[str, str]:
        """
        Format weight values for display.

        Args:
            weights: Weight dictionary

        Returns:
            Formatted weights dictionary
        """
        ...

    def format_confidence(self, confidence: float) -> str:
        """
        Format confidence score for display.

        Args:
            confidence: Confidence score (0-100)

        Returns:
            Formatted confidence string
        """
        ...
