"""
Configuration Service Implementation
Wraps configuration store and provides business logic for weight management
"""
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any
from src.infrastructure.config.file_config_store import FileConfigStore

logger = logging.getLogger(__name__)


class ConfigurationService:
    """
    Business logic service for configuration management.
    Implements ConfigService Protocol and WeightManagementService Protocol.
    """

    DEFAULT_WEIGHTS = {
        'US100': {
            'daily_midnight': 0.1339,
            'previous_hourly': 0.0822,
            '2h_open': 0.0520,
            '4h_open': 0.0650,
            'ny_open': 0.0779,
            'ny_preopen': 0.0391,
            'prev_day_high': 0.0260,
            'prev_day_low': 0.0260,
            'weekly_open': 0.0650,
            'weekly_high': 0.0260,
            'weekly_low': 0.0260,
            'prev_week_high': 0.0520,
            'prev_week_low': 0.0520,
            'monthly_open': 0.0391,
            'asian_range_high': 0.0279,
            'asian_range_low': 0.0279,
            'london_range_high': 0.0520,
            'london_range_low': 0.0520,
            'ny_range_high': 0.0391,
            'ny_range_low': 0.0391,
        },
        'US500': {
            'daily_midnight': 0.1339,
            'previous_hourly': 0.0822,
            '2h_open': 0.0520,
            '4h_open': 0.0650,
            'chicago_open': 0.0779,
            'chicago_preopen': 0.0391,
            'prev_day_high': 0.0260,
            'prev_day_low': 0.0260,
            'weekly_open': 0.0650,
            'weekly_high': 0.0260,
            'weekly_low': 0.0260,
            'prev_week_high': 0.0520,
            'prev_week_low': 0.0520,
            'monthly_open': 0.0391,
            'asian_range_high': 0.0279,
            'asian_range_low': 0.0279,
            'london_range_high': 0.0520,
            'london_range_low': 0.0520,
            'chicago_range_high': 0.0391,
            'chicago_range_low': 0.0391,
        },
        'UK100': {
            'daily_midnight': 0.1339,
            'previous_hourly': 0.0822,
            '2h_open': 0.0520,
            '4h_open': 0.0650,
            'london_open': 0.0779,
            'prev_day_high': 0.0260,
            'prev_day_low': 0.0260,
            'weekly_open': 0.0650,
            'weekly_high': 0.0260,
            'weekly_low': 0.0260,
            'prev_week_high': 0.0520,
            'prev_week_low': 0.0520,
            'monthly_open': 0.0391,
            'london_range_high': 0.0520,
            'london_range_low': 0.0520,
        }
    }

    def __init__(self, config_store: FileConfigStore):
        """
        Initialize configuration service with a config store dependency.

        Args:
            config_store: FileConfigStore instance for file I/O
        """
        self.store = config_store
        self.weights = self._load_weights()
        logger.info("ConfigurationService initialized")

    def _load_weights(self) -> Dict[str, Dict[str, float]]:
        """Load weights from store, or create defaults if not exists"""
        loaded = self.store.load()
        if loaded:
            logger.info("Loaded weights from configuration store")
            return loaded

        # Create default weights
        self._save_weights(self.DEFAULT_WEIGHTS.copy())
        return self.DEFAULT_WEIGHTS.copy()

    def _save_weights(self, weights: Dict[str, Dict[str, float]]):
        """Save weights to store"""
        try:
            self.store.save(weights)
            logger.info("Saved weights to configuration store")
        except Exception as e:
            logger.error(f"Failed to save weights: {e}")

    # ConfigService Protocol methods
    def load(self) -> Dict[str, Any]:
        """Load configuration data"""
        return self.weights.copy()

    def save(self, data: Dict[str, Any]) -> None:
        """Save configuration data"""
        self._save_weights(data)
        self.weights = data

    # WeightManagementService Protocol methods
    def get_weights(self, instrument: str) -> Dict[str, float]:
        """Get current weights for an instrument"""
        return self.weights.get(instrument, self.DEFAULT_WEIGHTS.get(instrument, {}))

    def set_weights(self, instrument: str, weights: Dict[str, float]) -> None:
        """Set weights for an instrument (must sum to 1.0)"""
        total = sum(weights.values())
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Weights must sum to 1.0, got {total}")

        self.weights[instrument] = weights
        self._save_weights(self.weights)
        logger.info(f"Updated weights for {instrument}")

    def validate_weights(self, weights: Dict[str, float]) -> Tuple[bool, str]:
        """Validate weights (must sum to 1.0, with tolerance for floating-point precision)"""
        total = sum(weights.values())
        if abs(total - 1.0) > 0.001:
            return False, f"Weights sum to {total:.4f}, must be 1.0"
        return True, "Weights are valid"

    def get_all_instruments(self) -> List[str]:
        """Get list of all configured instruments"""
        return list(self.weights.keys())

    def reset_instrument_weights(self, instrument: str) -> None:
        """Reset weights for an instrument to defaults"""
        if instrument in self.DEFAULT_WEIGHTS:
            self.weights[instrument] = self.DEFAULT_WEIGHTS[instrument].copy()
            self._save_weights(self.weights)
            logger.info(f"Reset weights for {instrument} to defaults")
        else:
            logger.warning(f"No default weights available for {instrument}")

    def reset_all_weights(self) -> None:
        """Reset all weights to defaults"""
        self.weights = self.DEFAULT_WEIGHTS.copy()
        self._save_weights(self.weights)
        logger.info("Reset all weights to defaults")

    def export_weights(self) -> Dict[str, Dict[str, float]]:
        """Export all weights"""
        return self.weights.copy()

    def import_weights(self, weights_data: Dict[str, Dict[str, float]]) -> None:
        """Import weights from external source"""
        self.weights = weights_data.copy()
        self._save_weights(self.weights)
        logger.info("Imported weights from external source")
