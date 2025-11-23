"""
Service Accessor Functions
Convenient functions for UI layer to access services without needing container knowledge
"""
import logging
from src.di.container import get_container
from src.services.config_service import ConfigurationService
from src.services.logging_service import LoggingService
from src.services.storage_service import StorageService

logger = logging.getLogger(__name__)


def get_config_service() -> ConfigurationService:
    """
    Get the ConfigurationService instance.

    Returns:
        ConfigurationService for managing weights and configuration
    """
    container = get_container()
    return container.get_configuration_service()


def get_logging_service() -> LoggingService:
    """
    Get the LoggingService instance.

    Returns:
        LoggingService for managing audit logs and weight change history
    """
    container = get_container()
    return container.get_logging_service()


def get_storage_service() -> StorageService:
    """
    Get the StorageService instance.

    Returns:
        StorageService for managing prediction storage and retrieval
    """
    container = get_container()
    return container.get_storage_service()


def get_weights(instrument: str) -> dict:
    """
    Get weights for an instrument.

    Args:
        instrument: Instrument code (e.g., 'US100')

    Returns:
        Dictionary of weight values
    """
    service = get_config_service()
    return service.get_weights(instrument)


def set_weights(instrument: str, weights: dict) -> None:
    """
    Set weights for an instrument.

    Args:
        instrument: Instrument code
        weights: Dictionary of weight values (must sum to 1.0)
    """
    service = get_config_service()
    service.set_weights(instrument, weights)


def validate_weights(weights: dict) -> tuple:
    """
    Validate weights.

    Args:
        weights: Dictionary of weight values

    Returns:
        Tuple of (is_valid, message)
    """
    service = get_config_service()
    return service.validate_weights(weights)


def get_all_instruments() -> list:
    """
    Get all configured instruments.

    Returns:
        List of instrument codes
    """
    service = get_config_service()
    return service.get_all_instruments()


def log_weight_change(instrument: str, old_weights: dict, new_weights: dict,
                      user: str = None, reason: str = None) -> None:
    """
    Log a weight change.

    Args:
        instrument: Instrument code
        old_weights: Previous weight values
        new_weights: New weight values
        user: Optional user who made the change
        reason: Optional reason for the change
    """
    service = get_logging_service()
    service.log_weight_change(instrument, old_weights, new_weights, user, reason)


def get_weight_change_history(instrument: str = None, days: int = 30) -> list:
    """
    Get weight change history.

    Args:
        instrument: Optional filter by instrument
        days: Number of days to look back

    Returns:
        List of change history entries
    """
    service = get_logging_service()
    return service.get_change_history(instrument, days)


def get_latest_weight_change(instrument: str) -> dict:
    """
    Get the most recent weight change for an instrument.

    Args:
        instrument: Instrument code

    Returns:
        Latest change entry or None
    """
    service = get_logging_service()
    return service.get_latest_change(instrument)


def save_prediction(prediction_dict: dict) -> bool:
    """
    Save a prediction.

    Args:
        prediction_dict: Prediction data

    Returns:
        True if saved successfully
    """
    service = get_storage_service()
    return service.save_prediction(prediction_dict)


def load_all_predictions() -> list:
    """
    Load all predictions.

    Returns:
        List of prediction dictionaries
    """
    service = get_storage_service()
    return service.load_all_predictions()


def get_prediction_count() -> int:
    """
    Get total number of predictions.

    Returns:
        Count of predictions
    """
    service = get_storage_service()
    return service.get_prediction_count()


def get_predictions_by_instrument(instrument: str) -> list:
    """
    Get predictions for a specific instrument.

    Args:
        instrument: Instrument code

    Returns:
        List of predictions for the instrument
    """
    service = get_storage_service()
    return service.get_predictions_by_instrument(instrument)


def get_top_predictions(n: int = 50) -> list:
    """
    Get top N predictions by data timestamp.

    Args:
        n: Number of predictions to return

    Returns:
        List of top N predictions
    """
    service = get_storage_service()
    return service.load_top_n_by_data_timestamp(n)


def delete_prediction(filename: str) -> bool:
    """
    Delete a prediction.

    Args:
        filename: Filename or key of the prediction

    Returns:
        True if deleted successfully
    """
    service = get_storage_service()
    return service.delete_prediction(filename)


def get_storage_info() -> dict:
    """
    Get storage statistics.

    Returns:
        Dictionary with storage information
    """
    service = get_storage_service()
    return service.get_storage_info()


def get_summary_statistics(instrument: str) -> dict:
    """
    Get summary statistics for weight changes.

    Args:
        instrument: Instrument code

    Returns:
        Dictionary with summary statistics
    """
    service = get_logging_service()
    return service.get_summary_statistics(instrument)
