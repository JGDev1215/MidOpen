"""
Dependency Injection Container
Manages service instantiation, lifecycle, and dependency resolution
"""
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dotenv import load_dotenv
from src.infrastructure.config.file_config_store import FileConfigStore
from src.infrastructure.logging.file_log_store import FileLogStore
from src.infrastructure.storage.json_storage import JSONStorageBackend
from src.infrastructure.storage.postgresql_storage import PostgreSQLStorageBackend
from src.services.config_service import ConfigurationService
from src.services.logging_service import LoggingService
from src.services.storage_service import StorageService
from src.services.analysis_orchestrator import AnalysisOrchestrator

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


class ServiceLifetime:
    """Enumeration for service lifetimes"""
    SINGLETON = "singleton"  # Single instance for entire application
    TRANSIENT = "transient"  # New instance for each request


class DIContainer:
    """
    Dependency Injection Container
    Manages service instantiation and caching with different lifetimes.
    """

    def __init__(self, config_path: Path = None, log_path: Path = None, storage_path: Path = None):
        """
        Initialize the DI container.

        Args:
            config_path: Path to configuration file (defaults to config/weights.json)
            log_path: Path to log directory (defaults to logs/weight_changes)
            storage_path: Path to storage directory (defaults to data/prediction_history)
        """
        # Set default paths
        self.config_path = config_path or Path("config/weights.json")
        self.log_path = log_path or Path("logs/weight_changes")
        self.storage_path = storage_path or Path("data/prediction_history")

        # Singleton instance cache
        self._singletons: Dict[str, Any] = {}

        # Service registry for lazy initialization
        self._services: Dict[str, Dict[str, Any]] = {
            'FileConfigStore': {'lifetime': ServiceLifetime.SINGLETON},
            'FileLogStore': {'lifetime': ServiceLifetime.SINGLETON},
            'StorageBackend': {'lifetime': ServiceLifetime.SINGLETON},
            'ConfigurationService': {'lifetime': ServiceLifetime.SINGLETON},
            'LoggingService': {'lifetime': ServiceLifetime.SINGLETON},
            'StorageService': {'lifetime': ServiceLifetime.SINGLETON},
            'AnalysisOrchestrator': {'lifetime': ServiceLifetime.SINGLETON},
        }

        # Determine storage backend type
        self.database_url = os.getenv('DATABASE_URL')
        if self.database_url:
            self.storage_backend_type = 'postgresql'
            logger.info("Using PostgreSQL storage backend (DATABASE_URL found)")
        else:
            self.storage_backend_type = 'json'
            logger.info("Using JSON file storage backend (DATABASE_URL not found)")

        logger.info(f"DIContainer initialized with paths:")
        logger.info(f"  Config: {self.config_path}")
        logger.info(f"  Logs: {self.log_path}")
        logger.info(f"  Storage: {self.storage_path}")
        logger.info(f"  Backend: {self.storage_backend_type}")

    def get_file_config_store(self) -> FileConfigStore:
        """Get or create FileConfigStore (singleton)"""
        if 'FileConfigStore' not in self._singletons:
            logger.info("Creating FileConfigStore singleton")
            self._singletons['FileConfigStore'] = FileConfigStore(self.config_path)
        return self._singletons['FileConfigStore']

    def get_file_log_store(self) -> FileLogStore:
        """Get or create FileLogStore (singleton)"""
        if 'FileLogStore' not in self._singletons:
            logger.info("Creating FileLogStore singleton")
            self._singletons['FileLogStore'] = FileLogStore(self.log_path)
        return self._singletons['FileLogStore']

    def get_storage_backend(self) -> Union[JSONStorageBackend, PostgreSQLStorageBackend]:
        """Get or create storage backend (singleton) - PostgreSQL or JSON based on config"""
        if 'StorageBackend' not in self._singletons:
            if self.storage_backend_type == 'postgresql':
                logger.info("Creating PostgreSQLStorageBackend singleton")
                self._singletons['StorageBackend'] = PostgreSQLStorageBackend(self.database_url)
            else:
                logger.info("Creating JSONStorageBackend singleton")
                self._singletons['StorageBackend'] = JSONStorageBackend(self.storage_path)
        return self._singletons['StorageBackend']

    def get_configuration_service(self) -> ConfigurationService:
        """Get or create ConfigurationService (singleton)"""
        if 'ConfigurationService' not in self._singletons:
            logger.info("Creating ConfigurationService singleton")
            store = self.get_file_config_store()
            self._singletons['ConfigurationService'] = ConfigurationService(store)
        return self._singletons['ConfigurationService']

    def get_logging_service(self) -> LoggingService:
        """Get or create LoggingService (singleton)"""
        if 'LoggingService' not in self._singletons:
            logger.info("Creating LoggingService singleton")
            store = self.get_file_log_store()
            self._singletons['LoggingService'] = LoggingService(store)
        return self._singletons['LoggingService']

    def get_storage_service(self) -> StorageService:
        """Get or create StorageService (singleton)"""
        if 'StorageService' not in self._singletons:
            logger.info("Creating StorageService singleton")
            backend = self.get_storage_backend()
            self._singletons['StorageService'] = StorageService(backend)
        return self._singletons['StorageService']

    def get_analysis_orchestrator(self) -> AnalysisOrchestrator:
        """Get or create AnalysisOrchestrator (singleton)"""
        if 'AnalysisOrchestrator' not in self._singletons:
            logger.info("Creating AnalysisOrchestrator singleton")
            config_service = self.get_configuration_service()
            logging_service = self.get_logging_service()
            storage_service = self.get_storage_service()
            self._singletons['AnalysisOrchestrator'] = AnalysisOrchestrator(
                config_service, logging_service, storage_service
            )
        return self._singletons['AnalysisOrchestrator']

    def clear(self):
        """Clear all singleton instances (useful for testing)"""
        logger.info("Clearing all singleton instances")
        self._singletons.clear()

    def get_service_info(self) -> Dict[str, Any]:
        """Get information about registered services"""
        return {
            'config_path': str(self.config_path),
            'log_path': str(self.log_path),
            'storage_path': str(self.storage_path),
            'singletons_created': list(self._singletons.keys()),
            'total_services': len(self._services)
        }


# Global container instance
_global_container: Optional[DIContainer] = None


def get_container(config_path: Path = None, log_path: Path = None,
                  storage_path: Path = None) -> DIContainer:
    """
    Get or create the global DI container.

    Args:
        config_path: Path to configuration file (optional, defaults to config/weights.json)
        log_path: Path to log directory (optional, defaults to logs/weight_changes)
        storage_path: Path to storage directory (optional, defaults to data/prediction_history)

    Returns:
        Global DIContainer instance
    """
    global _global_container

    if _global_container is None:
        _global_container = DIContainer(config_path, log_path, storage_path)

    return _global_container


def reset_container():
    """Reset the global container (useful for testing)"""
    global _global_container
    if _global_container:
        _global_container.clear()
    _global_container = None
    logger.info("Global container reset")
