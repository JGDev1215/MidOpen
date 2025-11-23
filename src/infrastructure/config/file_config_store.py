"""
File-based Configuration Store
Handles JSON file I/O for weight configurations
"""
import json
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


class FileConfigStore:
    """
    Low-level JSON configuration file storage.
    Responsible only for file I/O operations.
    """

    def __init__(self, config_path: Path):
        """
        Initialize file config store.

        Args:
            config_path: Path to weights.json file
        """
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"FileConfigStore initialized with path: {self.config_path}")

    def load(self) -> Dict[str, Dict[str, float]]:
        """
        Load configuration from JSON file.

        Returns:
            Dictionary of instruments and their weights
        """
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    logger.info(f"Loaded config from {self.config_path}")
                    return data
            else:
                logger.warning(f"Config file not found: {self.config_path}")
                return {}
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}

    def save(self, data: Dict[str, Dict[str, float]]) -> None:
        """
        Save configuration to JSON file.

        Args:
            data: Dictionary of instruments and their weights
        """
        try:
            with open(self.config_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved config to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            raise
