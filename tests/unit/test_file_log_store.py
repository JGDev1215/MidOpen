"""
Unit tests for FileLogStore
"""
import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime
from src.infrastructure.logging.file_log_store import FileLogStore


@pytest.fixture
def temp_log_path():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_append_log_entry(temp_log_path):
    """Test appending a log entry to the log file."""
    store = FileLogStore(temp_log_path)

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "instrument": "US100",
        "user": "admin",
        "reason": "Manual adjustment"
    }

    store.append(log_entry)

    # Verify file was created and contains the entry
    log_files = list(temp_log_path.glob("*.json"))
    assert len(log_files) == 1

    with open(log_files[0], 'r') as f:
        logs = json.load(f)
    assert len(logs) == 1
    assert logs[0]["instrument"] == "US100"


def test_append_multiple_entries_same_day(temp_log_path):
    """Test appending multiple entries to the same day's log."""
    store = FileLogStore(temp_log_path)

    entries = [
        {"timestamp": datetime.now().isoformat(), "instrument": "US100"},
        {"timestamp": datetime.now().isoformat(), "instrument": "UK100"},
        {"timestamp": datetime.now().isoformat(), "instrument": "US500"}
    ]

    for entry in entries:
        store.append(entry)

    # Verify all entries are in the same file
    log_files = list(temp_log_path.glob("*.json"))
    assert len(log_files) == 1

    with open(log_files[0], 'r') as f:
        logs = json.load(f)
    assert len(logs) == 3


def test_load_recent_logs(temp_log_path):
    """Test loading recent log entries."""
    store = FileLogStore(temp_log_path)

    # Create entries
    entries = [
        {"timestamp": datetime.now().isoformat(), "instrument": "US100"},
        {"timestamp": datetime.now().isoformat(), "instrument": "UK100"}
    ]

    for entry in entries:
        store.append(entry)

    # Load and verify
    loaded = store.load_recent()
    assert len(loaded) >= 2
    instruments = [log["instrument"] for log in loaded]
    assert "US100" in instruments
    assert "UK100" in instruments


def test_load_instrument_history(temp_log_path):
    """Test loading history for a specific instrument."""
    store = FileLogStore(temp_log_path)

    # Create mixed entries
    entries = [
        {"timestamp": datetime.now().isoformat(), "instrument": "US100", "user": "admin1"},
        {"timestamp": datetime.now().isoformat(), "instrument": "UK100", "user": "admin2"},
        {"timestamp": datetime.now().isoformat(), "instrument": "US100", "user": "admin3"}
    ]

    for entry in entries:
        store.append(entry)

    # Load US100 history
    history = store.load_instrument_history("US100")
    assert len(history) == 2
    assert all(log["instrument"] == "US100" for log in history)


def test_load_empty_logs(temp_log_path):
    """Test loading from empty directory returns empty list."""
    store = FileLogStore(temp_log_path)
    loaded = store.load_recent()
    assert loaded == []


def test_directory_creation(temp_log_path):
    """Test that the log directory is created if it doesn't exist."""
    deep_path = temp_log_path / "sub1" / "sub2"
    store = FileLogStore(deep_path)

    # Should create parent directories
    assert deep_path.exists()
