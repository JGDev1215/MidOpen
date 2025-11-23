"""
Unit tests for DI Container
"""
import pytest
import tempfile
from pathlib import Path
from src.di.container import DIContainer, get_container, reset_container
from src.services.config_service import ConfigurationService
from src.services.logging_service import LoggingService
from src.services.storage_service import StorageService


@pytest.fixture
def temp_paths():
    """Create temporary paths for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        yield {
            'config': tmpdir_path / 'weights.json',
            'log': tmpdir_path / 'logs',
            'storage': tmpdir_path / 'storage'
        }


@pytest.fixture
def container(temp_paths):
    """Create a DI container for testing."""
    return DIContainer(
        config_path=temp_paths['config'],
        log_path=temp_paths['log'],
        storage_path=temp_paths['storage']
    )


def test_container_initialization(container):
    """Test container initializes with correct paths."""
    assert container.config_path is not None
    assert container.log_path is not None
    assert container.storage_path is not None


def test_get_file_config_store(container):
    """Test retrieving FileConfigStore."""
    store = container.get_file_config_store()
    assert store is not None


def test_get_file_log_store(container):
    """Test retrieving FileLogStore."""
    store = container.get_file_log_store()
    assert store is not None


def test_get_json_storage_backend(container):
    """Test retrieving JSONStorageBackend."""
    backend = container.get_json_storage_backend()
    assert backend is not None


def test_get_configuration_service(container):
    """Test retrieving ConfigurationService."""
    service = container.get_configuration_service()
    assert service is not None
    assert isinstance(service, ConfigurationService)


def test_get_logging_service(container):
    """Test retrieving LoggingService."""
    service = container.get_logging_service()
    assert service is not None
    assert isinstance(service, LoggingService)


def test_get_storage_service(container):
    """Test retrieving StorageService."""
    service = container.get_storage_service()
    assert service is not None
    assert isinstance(service, StorageService)


def test_singleton_pattern_config_service(container):
    """Test that ConfigurationService is singleton."""
    service1 = container.get_configuration_service()
    service2 = container.get_configuration_service()

    assert service1 is service2  # Same instance


def test_singleton_pattern_logging_service(container):
    """Test that LoggingService is singleton."""
    service1 = container.get_logging_service()
    service2 = container.get_logging_service()

    assert service1 is service2  # Same instance


def test_singleton_pattern_storage_service(container):
    """Test that StorageService is singleton."""
    service1 = container.get_storage_service()
    service2 = container.get_storage_service()

    assert service1 is service2  # Same instance


def test_service_dependencies_injected(container):
    """Test that services have dependencies properly injected."""
    config_service = container.get_configuration_service()
    assert config_service.store is not None

    logging_service = container.get_logging_service()
    assert logging_service.store is not None

    storage_service = container.get_storage_service()
    assert storage_service.backend is not None


def test_container_clear(container):
    """Test clearing container singletons."""
    service1 = container.get_configuration_service()
    container.clear()
    service2 = container.get_configuration_service()

    assert service1 is not service2  # Different instances after clear


def test_container_get_service_info(container):
    """Test getting container service info."""
    info = container.get_service_info()

    assert 'config_path' in info
    assert 'log_path' in info
    assert 'storage_path' in info
    assert 'singletons_created' in info
    assert 'total_services' in info


def test_global_container_singleton(temp_paths):
    """Test global container singleton pattern."""
    reset_container()

    container1 = get_container(
        config_path=temp_paths['config'],
        log_path=temp_paths['log'],
        storage_path=temp_paths['storage']
    )

    container2 = get_container()

    assert container1 is container2  # Same global instance


def test_global_container_reset(temp_paths):
    """Test resetting global container."""
    reset_container()

    container1 = get_container(
        config_path=temp_paths['config'],
        log_path=temp_paths['log'],
        storage_path=temp_paths['storage']
    )

    reset_container()

    container2 = get_container(
        config_path=temp_paths['config'],
        log_path=temp_paths['log'],
        storage_path=temp_paths['storage']
    )

    assert container1 is not container2  # Different instances after reset


def test_services_work_together(container):
    """Test that services work together properly."""
    # Get services
    config_service = container.get_configuration_service()
    logging_service = container.get_logging_service()
    storage_service = container.get_storage_service()

    # Test config service
    instruments = config_service.get_all_instruments()
    assert len(instruments) > 0

    # Test logging service
    logging_service.log_weight_change(
        instrument='US100',
        old_weights={'a': 0.5, 'b': 0.5},
        new_weights={'a': 0.6, 'b': 0.4}
    )

    # Test storage service
    storage_service.save_prediction({
        'instrument': 'US100',
        'timestamp': '2024-11-23T10:30:00'
    })

    # Verify
    count = storage_service.get_prediction_count()
    assert count == 1


def test_container_default_paths():
    """Test container uses default paths when not provided."""
    reset_container()
    container = DIContainer()

    assert 'config/weights.json' in str(container.config_path)
    assert 'logs/weight_changes' in str(container.log_path)
    assert 'data/prediction_history' in str(container.storage_path)

    reset_container()
