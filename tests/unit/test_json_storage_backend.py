"""
Unit tests for JSONStorageBackend
"""
import pytest
import json
import tempfile
from pathlib import Path
from src.infrastructure.storage.json_storage import JSONStorageBackend


@pytest.fixture
def temp_storage_path():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_save_prediction(temp_storage_path):
    """Test saving a prediction."""
    backend = JSONStorageBackend(temp_storage_path)

    prediction_data = {
        "instrument": "US100",
        "analysis": {"bias": "BULLISH", "confidence": 75.5},
        "timestamp": "2024-11-23T10:30:00"
    }

    result = backend.save("test_prediction_1", prediction_data)

    assert result is True
    saved_file = temp_storage_path / "test_prediction_1.json"
    assert saved_file.exists()


def test_load_prediction(temp_storage_path):
    """Test loading a saved prediction."""
    backend = JSONStorageBackend(temp_storage_path)

    prediction_data = {
        "instrument": "US100",
        "analysis": {"bias": "BULLISH", "confidence": 75.5}
    }

    backend.save("test_pred", prediction_data)
    loaded = backend.load("test_pred")

    assert loaded["instrument"] == "US100"
    assert loaded["analysis"]["bias"] == "BULLISH"


def test_load_nonexistent_prediction(temp_storage_path):
    """Test loading a non-existent prediction returns empty dict."""
    backend = JSONStorageBackend(temp_storage_path)
    loaded = backend.load("nonexistent")

    assert loaded == {}


def test_count_predictions(temp_storage_path):
    """Test counting total predictions."""
    backend = JSONStorageBackend(temp_storage_path)

    # Save multiple predictions
    for i in range(3):
        backend.save(f"pred_{i}", {"instrument": "US100", "id": i})

    count = backend.count()
    assert count == 3


def test_list_by_instrument(temp_storage_path):
    """Test listing predictions for a specific instrument."""
    backend = JSONStorageBackend(temp_storage_path)

    # Save predictions for different instruments
    backend.save("us100_1", {"instrument": "US100", "data": "test1"})
    backend.save("uk100_1", {"instrument": "UK100", "data": "test2"})
    backend.save("us100_2", {"instrument": "US100", "data": "test3"})

    us100_predictions = backend.list_by_instrument("US100")

    assert len(us100_predictions) == 2
    assert all(p["instrument"] == "US100" for p in us100_predictions)


def test_query_with_filters(temp_storage_path):
    """Test querying predictions with filters."""
    backend = JSONStorageBackend(temp_storage_path)

    # Save predictions
    backend.save("pred_1", {"instrument": "US100", "status": "DONE"})
    backend.save("pred_2", {"instrument": "UK100", "status": "DONE"})
    backend.save("pred_3", {"instrument": "US100", "status": "PENDING"})

    # Query with filter
    results = backend.query({"instrument": "US100"})

    assert len(results) == 2
    assert all(p["instrument"] == "US100" for p in results)


def test_query_with_limit(temp_storage_path):
    """Test querying with limit parameter."""
    backend = JSONStorageBackend(temp_storage_path)

    # Save multiple predictions
    for i in range(5):
        backend.save(f"pred_{i}", {"id": i, "instrument": "US100"})

    results = backend.query(limit=2)

    assert len(results) == 2


def test_delete_prediction(temp_storage_path):
    """Test deleting a prediction."""
    backend = JSONStorageBackend(temp_storage_path)

    # Save then delete
    backend.save("to_delete", {"data": "test"})
    assert (temp_storage_path / "to_delete.json").exists()

    result = backend.delete("to_delete")

    assert result is True
    assert not (temp_storage_path / "to_delete.json").exists()


def test_delete_nonexistent(temp_storage_path):
    """Test deleting a non-existent prediction returns False."""
    backend = JSONStorageBackend(temp_storage_path)
    result = backend.delete("nonexistent")

    assert result is False


def test_directory_creation(temp_storage_path):
    """Test that storage directory is created if needed."""
    deep_path = temp_storage_path / "sub1" / "sub2"
    backend = JSONStorageBackend(deep_path)

    assert deep_path.exists()


def test_save_load_roundtrip(temp_storage_path):
    """Test complete save and load roundtrip."""
    backend = JSONStorageBackend(temp_storage_path)

    original = {
        "instrument": "US100",
        "analysis": {
            "bias": "BEARISH",
            "confidence": 85.3,
            "bullish_weight": 0.25,
            "bearish_weight": 0.75
        },
        "timestamp": "2024-11-23T14:30:00+00:00",
        "data_length": 100,
        "current_price": 18500.50
    }

    backend.save("roundtrip_test", original)
    loaded = backend.load("roundtrip_test")

    assert loaded == original
    assert loaded["analysis"]["bias"] == "BEARISH"
    assert loaded["data_length"] == 100
