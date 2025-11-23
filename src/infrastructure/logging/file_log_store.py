"""
File-based Audit Log Store
Handles JSON file I/O for audit logging of weight changes
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class FileLogStore:
    """
    Low-level JSON audit log file storage.
    Responsible only for file I/O operations for audit logs.
    """

    def __init__(self, log_path: Path):
        """
        Initialize file log store.

        Args:
            log_path: Path to weight_changes directory
        """
        self.log_path = Path(log_path)
        self.log_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"FileLogStore initialized with path: {self.log_path}")

    def append(self, log_entry: Dict[str, Any]) -> None:
        """
        Append a log entry to the audit log.

        Args:
            log_entry: Dictionary containing log data
        """
        try:
            # Create log file with current date
            log_date = datetime.now().strftime("%Y-%m-%d")
            log_file = self.log_path / f"{log_date}.json"

            # Load existing logs or create empty list
            logs = []
            if log_file.exists():
                with open(log_file, 'r') as f:
                    logs = json.load(f)

            # Append new entry
            logs.append(log_entry)

            # Save updated logs
            with open(log_file, 'w') as f:
                json.dump(logs, f, indent=2)

            logger.info(f"Appended log entry to {log_file}")
        except Exception as e:
            logger.error(f"Failed to append log entry: {e}")
            raise

    def load_recent(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Load recent log entries from the last N days.

        Args:
            days: Number of days to look back

        Returns:
            List of log entries
        """
        try:
            logs = []
            # Get all JSON files in log directory
            for log_file in sorted(self.log_path.glob("*.json"), reverse=True):
                try:
                    with open(log_file, 'r') as f:
                        file_logs = json.load(f)
                        logs.extend(file_logs)
                except Exception as e:
                    logger.warning(f"Failed to load {log_file}: {e}")

            logger.info(f"Loaded {len(logs)} log entries")
            return logs
        except Exception as e:
            logger.error(f"Failed to load recent logs: {e}")
            return []

    def load_instrument_history(self, instrument: str) -> List[Dict[str, Any]]:
        """
        Load all log entries for a specific instrument.

        Args:
            instrument: Instrument name (e.g., 'US100')

        Returns:
            List of log entries for the instrument
        """
        try:
            all_logs = self.load_recent()
            instrument_logs = [
                log for log in all_logs
                if log.get('instrument') == instrument
            ]
            logger.info(f"Loaded {len(instrument_logs)} logs for {instrument}")
            return instrument_logs
        except Exception as e:
            logger.error(f"Failed to load instrument history: {e}")
            return []
