"""
Weight Change Logger
Logs all weight adjustments for audit trail and records
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from src.infrastructure.logging.file_log_store import FileLogStore

logger = logging.getLogger(__name__)


class WeightLogger:
    """Logs weight changes to JSON files organized by date"""

    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.store = FileLogStore(log_dir)

    def log_weight_change(self, instrument: str, old_weights: Dict[str, float],
                          new_weights: Dict[str, float], user: str = None, reason: str = None):
        """
        Log a weight adjustment

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

            if abs(old_value - new_value) > 0.00001:  # Account for floating point precision
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

        # Store the log entry using file log store
        self.store.append(log_entry)
        logger.info(f"Logged weight change for {instrument}: {len(changed_weights)} levels modified")

    def get_change_history(self, instrument: str = None, days: int = 30) -> list:
        """
        Get weight change history

        Args:
            instrument: Optional filter by instrument
            days: Number of days to look back

        Returns:
            List of log entries
        """
        # Load all logs from store
        if instrument:
            all_logs = self.store.load_instrument_history(instrument)
        else:
            all_logs = self.store.load_recent(days=days)

        return sorted(all_logs, key=lambda x: x.get('timestamp', ''), reverse=True)

    def get_latest_change(self, instrument: str) -> dict or None:
        """Get the most recent weight change for an instrument"""
        history = self.get_change_history(instrument=instrument, days=365)
        return history[0] if history else None

    def export_history_to_csv(self, output_file: Path, instrument: str = None):
        """Export weight change history to CSV"""
        import csv

        history = self.get_change_history(instrument=instrument)

        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)

            # Write header
            writer.writerow(['Timestamp', 'Instrument', 'User', 'Reason', 'Level', 'Old Weight', 'New Weight', 'Change'])

            # Write rows
            for entry in history:
                for level_name, changes in entry['changes'].items():
                    writer.writerow([
                        entry['timestamp'],
                        entry['instrument'],
                        entry['user'],
                        entry['reason'],
                        level_name,
                        f"{changes['old']:.6f}",
                        f"{changes['new']:.6f}",
                        f"{changes['change']:.6f}"
                    ])

        logger.info(f"Exported weight change history to {output_file}")

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
            for level_name in entry['changes']:
                level_adjustments[level_name] = level_adjustments.get(level_name, 0) + 1

        most_adjusted = max(level_adjustments.items(), key=lambda x: x[1], default=(None, 0))

        return {
            'total_changes': len(history),
            'last_change': history[0]['timestamp'] if history else None,
            'most_adjusted_level': most_adjusted[0],
            'most_adjusted_count': most_adjusted[1],
            'unique_levels_modified': len(level_adjustments)
        }
