"""
Unit tests for FileConfigStore
"""
import pytest
import json
import tempfile
from pathlib import Path
from src.infrastructure.config.file_config_store import FileConfigStore


@pytest.fixture
def temp_config_path():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "weights.json"


def test_load_existing_config_file(temp_config_path):
    """Test loading an existing configuration file."""
    # Create a test config file
    test_data = {
        "US100": {"daily_midnight": 0.1339, "ny_open": 0.0779},
        "UK100": {"london_open": 0.0779}
    }
    temp_config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(temp_config_path, 'w') as f:
        json.dump(test_data, f)

    # Load and verify
    store = FileConfigStore(temp_config_path)
    loaded = store.load()

    assert loaded == test_data
    assert "US100" in loaded
    assert loaded["US100"]["daily_midnight"] == 0.1339


def test_save_config_file(temp_config_path):
    """Test saving configuration to file."""
    test_data = {
        "US100": {"daily_midnight": 0.1339},
        "US500": {"chicago_open": 0.0779}
    }

    store = FileConfigStore(temp_config_path)
    store.save(test_data)

    # Verify file was created and contains correct data
    assert temp_config_path.exists()
    with open(temp_config_path, 'r') as f:
        saved_data = json.load(f)
    assert saved_data == test_data


def test_load_nonexistent_file(temp_config_path):
    """Test loading from a non-existent file returns empty dict."""
    store = FileConfigStore(temp_config_path)
    loaded = store.load()

    assert loaded == {}


def test_directory_creation(temp_config_path):
    """Test that parent directories are created if they don't exist."""
    deep_path = temp_config_path.parent / "sub1" / "sub2" / "weights.json"
    store = FileConfigStore(deep_path)

    # Should create parent directories
    assert deep_path.parent.exists()


def test_save_and_load_roundtrip(temp_config_path):
    """Test saving and loading data roundtrip."""
    original_data = {
        "US100": {
            "daily_midnight": 0.1339,
            "ny_open": 0.0779,
            "ny_preopen": 0.0391
        },
        "US500": {
            "chicago_open": 0.0779,
            "chicago_preopen": 0.0391
        }
    }

    # Save
    store = FileConfigStore(temp_config_path)
    store.save(original_data)

    # Load
    loaded_data = store.load()

    # Verify
    assert loaded_data == original_data
    assert len(loaded_data["US100"]) == 3
    assert loaded_data["US500"]["chicago_open"] == 0.0779
