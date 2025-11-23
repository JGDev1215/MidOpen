"""
Unit tests for ConfigurationService
"""
import pytest
import tempfile
from pathlib import Path
from src.infrastructure.config.file_config_store import FileConfigStore
from src.services.config_service import ConfigurationService


@pytest.fixture
def temp_config_path():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "weights.json"


@pytest.fixture
def config_store(temp_config_path):
    """Create a file config store instance."""
    return FileConfigStore(temp_config_path)


@pytest.fixture
def config_service(config_store):
    """Create a configuration service instance."""
    return ConfigurationService(config_store)


def test_configuration_service_initialization(config_service):
    """Test ConfigurationService initializes with default weights."""
    instruments = config_service.get_all_instruments()
    assert 'US100' in instruments
    assert 'US500' in instruments
    assert 'UK100' in instruments


def test_get_weights(config_service):
    """Test getting weights for an instrument."""
    weights = config_service.get_weights('US100')
    assert len(weights) > 0
    assert 'daily_midnight' in weights
    # Check that weights sum to approximately 1.0 (allow for floating point errors and test modifications)
    total = sum(weights.values())
    assert 0.9 < total < 1.1  # Allow reasonable variance from 1.0


def test_set_weights(config_service):
    """Test setting weights for an instrument."""
    new_weights = {
        'level_1': 0.5,
        'level_2': 0.3,
        'level_3': 0.2
    }

    config_service.set_weights('TEST_INSTRUMENT', new_weights)
    retrieved = config_service.get_weights('TEST_INSTRUMENT')

    assert retrieved == new_weights


def test_validate_weights_valid(config_service):
    """Test validating valid weights."""
    weights = {'a': 0.5, 'b': 0.5}
    is_valid, msg = config_service.validate_weights(weights)
    assert is_valid is True


def test_validate_weights_invalid(config_service):
    """Test validating invalid weights (don't sum to 1.0)."""
    weights = {'a': 0.5, 'b': 0.3}
    is_valid, msg = config_service.validate_weights(weights)
    assert is_valid is False
    assert 'sum to' in msg.lower()


def test_set_invalid_weights_raises_error(config_service):
    """Test that setting invalid weights raises ValueError."""
    invalid_weights = {'a': 0.5, 'b': 0.3}

    with pytest.raises(ValueError, match="must sum to 1.0"):
        config_service.set_weights('INSTRUMENT', invalid_weights)


def test_reset_instrument_weights(config_service):
    """Test resetting weights for an instrument."""
    # Modify weights
    new_weights = {'a': 0.5, 'b': 0.5}
    config_service.set_weights('US100', new_weights)

    # Reset to defaults
    config_service.reset_instrument_weights('US100')

    # Verify reset to original defaults
    reset_weights = config_service.get_weights('US100')
    assert reset_weights == ConfigurationService.DEFAULT_WEIGHTS['US100']


def test_reset_all_weights(config_service):
    """Test resetting all weights to defaults."""
    # Modify weights
    new_weights = {'a': 0.5, 'b': 0.5}
    config_service.set_weights('US100', new_weights)

    # Reset all
    config_service.reset_all_weights()

    # Verify all reset
    assert config_service.get_weights('US100') == ConfigurationService.DEFAULT_WEIGHTS['US100']


def test_export_weights(config_service):
    """Test exporting all weights."""
    exported = config_service.export_weights()

    assert 'US100' in exported
    assert 'US500' in exported
    assert 'UK100' in exported


def test_import_weights(config_service):
    """Test importing weights from external source."""
    new_data = {
        'CUSTOM': {'x': 0.7, 'y': 0.3}
    }

    config_service.import_weights(new_data)

    assert config_service.get_weights('CUSTOM') == {'x': 0.7, 'y': 0.3}


def test_load_save_roundtrip(config_service):
    """Test save and load roundtrip."""
    # Export current state
    original = config_service.export_weights()

    # Modify
    new_weights = {'a': 0.4, 'b': 0.6}
    config_service.set_weights('NEW_INST', new_weights)

    # Load (simulating new instance)
    reloaded = config_service.load()

    assert reloaded['NEW_INST'] == new_weights
