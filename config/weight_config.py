"""
Weight Configuration Manager
Manages adjustable weights for prediction levels
"""
from pathlib import Path
from typing import Dict, List, Any
import logging
from src.infrastructure.config.file_config_store import FileConfigStore

logger = logging.getLogger(__name__)


class WeightConfig:
    """Manages weight configurations for different instruments"""

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

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.store = FileConfigStore(config_path)
        self.weights = self._load_weights()

    def _load_weights(self) -> Dict[str, Dict[str, float]]:
        """Load weights from config file, or create defaults if not exists"""
        loaded = self.store.load()
        if loaded:
            logger.info(f"Loaded weights from {self.config_path}")
            return loaded

        # Create default weights file
        self._save_weights(self.DEFAULT_WEIGHTS.copy())
        return self.DEFAULT_WEIGHTS.copy()

    def _save_weights(self, weights: Dict[str, Dict[str, float]]):
        """Save weights to config file"""
        try:
            self.store.save(weights)
            logger.info(f"Saved weights to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save weights: {e}")

    def get_weights(self, instrument: str) -> Dict[str, float]:
        """Get current weights for an instrument"""
        return self.weights.get(instrument, self.DEFAULT_WEIGHTS.get(instrument, {}))

    def set_weights(self, instrument: str, weights: Dict[str, float]):
        """Set weights for an instrument (must sum to 1.0)"""
        # Validate weights sum to approximately 1.0
        total = sum(weights.values())
        if abs(total - 1.0) > 0.0001:
            raise ValueError(f"Weights must sum to 1.0, got {total}")

        self.weights[instrument] = weights
        self._save_weights(self.weights)
        logger.info(f"Updated weights for {instrument}")

    def reset_instrument_weights(self, instrument: str):
        """Reset weights for an instrument to defaults"""
        if instrument in self.DEFAULT_WEIGHTS:
            self.weights[instrument] = self.DEFAULT_WEIGHTS[instrument].copy()
            self._save_weights(self.weights)
            logger.info(f"Reset weights for {instrument} to defaults")
        else:
            logger.warning(f"No default weights available for {instrument}")

    def reset_all_weights(self):
        """Reset all weights to defaults"""
        self.weights = self.DEFAULT_WEIGHTS.copy()
        self._save_weights(self.weights)
        logger.info("Reset all weights to defaults")

    def validate_weights(self, weights: Dict[str, float]) -> tuple[bool, str]:
        """Validate weights (must sum to 1.0)"""
        total = sum(weights.values())
        if abs(total - 1.0) > 0.0001:
            return False, f"Weights sum to {total:.4f}, must be 1.0"
        return True, "Weights are valid"

    def get_all_instruments(self) -> List[str]:
        """Get list of all configured instruments"""
        return list(self.weights.keys())

    def get_weight_names(self, instrument: str) -> List[str]:
        """Get list of weight names for an instrument"""
        return list(self.weights.get(instrument, {}).keys())

    def export_weights(self) -> Dict[str, Dict[str, float]]:
        """Export all weights"""
        return self.weights.copy()

    def import_weights(self, weights_data: Dict[str, Dict[str, float]]):
        """Import weights from external source"""
        self.weights = weights_data.copy()
        self._save_weights(self.weights)
        logger.info("Imported weights from external source")
