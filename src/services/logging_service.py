"""
Logging Service Implementation
Wraps logging store and provides business logic for audit trail management
"""
import logging
from typing import Dict, List, Any
from datetime import datetime
from src.infrastructure.logging.file_log_store import FileLogStore

logger = logging.getLogger(__name__)


class LoggingService:
    """
    Business logic service for audit logging.
    Implements LogService Protocol and provides weight change tracking.
    """

    def __init__(self, log_store: FileLogStore):
        """
        Initialize logging service with a log store dependency.

        Args:
            log_store: FileLogStore instance for file I/O
        """
        self.store = log_store
        logger.info("LoggingService initialized")

    # LogService Protocol methods
    def append(self, log_entry: Dict[str, Any]) -> None:
        """
        Append a log entry to the audit log.

        Args:
            log_entry: Dictionary containing log data
        """
        self.store.append(log_entry)

    def load_recent(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Load recent log entries from the last N days.

        Args:
            days: Number of days to look back

        Returns:
            List of log entries
        """
        return self.store.load_recent(days=days)

    def load_instrument_history(self, instrument: str) -> List[Dict[str, Any]]:
        """
        Load all log entries for a specific instrument.

        Args:
            instrument: Instrument name (e.g., 'US100')

        Returns:
            List of log entries for the instrument
        """
        return self.store.load_instrument_history(instrument)

    # Weight change tracking methods
    def log_weight_change(self, instrument: str, old_weights: Dict[str, float],
                          new_weights: Dict[str, float], user: str = None, reason: str = None):
        """
        Log a weight adjustment.

        Args:
            instrument: The instrument being modified
            old_weights: Dictionary of old weight values
            new_weights: Dictionary of new weight values
            user: Optional user who made the change
            reason: Optional reason for the change
        """
        timestamp = datetime.now()

        # Identify which weights changed
        changed_weights = {}
        for level_name in new_weights:
            old_value = old_weights.get(level_name, 0.0)
            new_value = new_weights.get(level_name, 0.0)

            if abs(old_value - new_value) > 0.00001:
                changed_weights[level_name] = {
                    'old': old_value,
                    'new': new_value,
                    'change': new_value - old_value
                }

        if not changed_weights:
            logger.info(f"No weight changes detected for {instrument}")
            return

        # Create log entry
        log_entry = {
            'timestamp': timestamp.isoformat(),
            'instrument': instrument,
            'user': user or 'admin',
            'reason': reason or 'Manual adjustment',
            'changes': changed_weights,
            'old_total': sum(old_weights.values()),
            'new_total': sum(new_weights.values()),
            'num_changed_levels': len(changed_weights)
        }

        # Store using the store
        self.store.append(log_entry)
        logger.info(f"Logged weight change for {instrument}: {len(changed_weights)} levels modified")

    def get_change_history(self, instrument: str = None, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get weight change history.

        Args:
            instrument: Optional filter by instrument
            days: Number of days to look back

        Returns:
            List of log entries sorted by timestamp (newest first)
        """
        if instrument:
            all_logs = self.load_instrument_history(instrument)
        else:
            all_logs = self.load_recent(days=days)

        return sorted(all_logs, key=lambda x: x.get('timestamp', ''), reverse=True)

    def get_latest_change(self, instrument: str) -> Dict[str, Any] | None:
        """Get the most recent weight change for an instrument"""
        history = self.get_change_history(instrument=instrument, days=365)
        return history[0] if history else None

    def get_summary_statistics(self, instrument: str) -> Dict[str, Any]:
        """Get summary statistics for weight changes"""
        history = self.get_change_history(instrument=instrument, days=365)

        if not history:
            return {
                'total_changes': 0,
                'last_change': None,
                'most_adjusted_level': None
            }

        # Count adjustments per level
        level_adjustments = {}
        for entry in history:
            for level_name in entry.get('changes', {}):
                level_adjustments[level_name] = level_adjustments.get(level_name, 0) + 1

        most_adjusted = max(level_adjustments.items(), key=lambda x: x[1], default=(None, 0))

        return {
            'total_changes': len(history),
            'last_change': history[0].get('timestamp') if history else None,
            'most_adjusted_level': most_adjusted[0],
            'most_adjusted_count': most_adjusted[1],
            'unique_levels_modified': len(level_adjustments)
        }
