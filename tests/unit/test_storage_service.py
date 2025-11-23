"""
Unit tests for StorageService
"""
import pytest
import tempfile
from pathlib import Path
from src.infrastructure.storage.json_storage import JSONStorageBackend
from src.services.storage_service import StorageService


@pytest.fixture
def temp_storage_path():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def storage_backend(temp_storage_path):
    """Create a JSON storage backend instance."""
    return JSONStorageBackend(temp_storage_path)


@pytest.fixture
def storage_service(storage_backend):
    """Create a storage service instance."""
    return StorageService(storage_backend)


def test_storage_service_initialization(storage_service):
    """Test StorageService initializes correctly."""
    assert storage_service is not None
    assert storage_service.backend is not None


def test_save_and_load_prediction(storage_service):
    """Test saving and loading a prediction."""
    prediction = {
        'instrument': 'US100',
        'bias': 'BULLISH',
        'confidence': 85.5,
        'timestamp': '2024-11-23T10:30:00'
    }

    # Save
    result = storage_service.save_prediction(prediction)
    assert result is True

    # Verify count
    count = storage_service.get_prediction_count()
    assert count == 1


def test_get_predictions_by_instrument(storage_service):
    """Test getting predictions for a specific instrument."""
    # Save predictions for different instruments
    storage_service.save_prediction({
        'instrument': 'US100',
        'bias': 'BULLISH',
        'timestamp': '2024-11-23T10:30:00'
    })

    storage_service.save_prediction({
        'instrument': 'UK100',
        'bias': 'BEARISH',
        'timestamp': '2024-11-23T10:30:00'
    })

    # Get US100 predictions
    us100_preds = storage_service.get_predictions_by_instrument('US100')
    assert len(us100_preds) == 1
    assert us100_preds[0]['instrument'] == 'US100'


def test_load_all_predictions(storage_service):
    """Test loading all predictions."""
    # Save multiple predictions
    for i in range(3):
        storage_service.save_prediction({
            'instrument': 'US100',
            'bias': 'BULLISH' if i % 2 == 0 else 'BEARISH',
            'timestamp': f'2024-11-23T{10+i}:30:00'
        })

    # Load all
    all_preds = storage_service.load_all_predictions()
    assert len(all_preds) == 3


def test_get_top_n_predictions(storage_service):
    """Test getting top N predictions by data timestamp."""
    # Save predictions
    for i in range(5):
        storage_service.save_prediction({
            'instrument': 'US100',
            'data_timestamp': f'2024-11-{20+i}T10:30:00',
            'timestamp': f'2024-11-23T{10+i}:30:00'
        })

    # Get top 3
    top_3 = storage_service.load_top_n_by_data_timestamp(n=3)
    assert len(top_3) == 3


def test_get_predictions_by_date_range(storage_service):
    """Test getting predictions within a date range."""
    # Save predictions on different dates
    storage_service.save_prediction({
        'instrument': 'US100',
        'data_timestamp': '2024-11-20T10:30:00',
        'timestamp': '2024-11-20T10:30:00'
    })

    storage_service.save_prediction({
        'instrument': 'US100',
        'data_timestamp': '2024-11-25T10:30:00',
        'timestamp': '2024-11-25T10:30:00'
    })

    # Get range
    range_preds = storage_service.get_predictions_by_date_range('2024-11-22', '2024-11-26')
    assert len(range_preds) == 1
    assert '2024-11-25' in range_preds[0]['data_timestamp']


def test_get_prediction_count(storage_service):
    """Test getting prediction count."""
    # Initially empty
    assert storage_service.get_prediction_count() == 0

    # Add some
    for i in range(5):
        storage_service.save_prediction({
            'instrument': 'US100',
            'timestamp': f'2024-11-23T{10+i}:30:00'
        })

    assert storage_service.get_prediction_count() == 5


def test_delete_prediction(storage_service):
    """Test deleting a prediction."""
    # Save
    storage_service.save_prediction({
        'instrument': 'US100',
        'timestamp': '2024-11-23T10:30:00'
    })

    initial_count = storage_service.get_prediction_count()
    assert initial_count == 1

    # Delete by filename
    all_preds = storage_service.load_all_predictions()
    filename = f"{all_preds[0]['instrument']}_2024-11-23_10-30-00.json"

    result = storage_service.delete_prediction(filename)
    assert result is True

    # Verify deleted
    final_count = storage_service.get_prediction_count()
    assert final_count == 0


def test_get_storage_info(storage_service):
    """Test getting storage information and statistics."""
    # Save predictions for different instruments
    for instrument in ['US100', 'UK100', 'US500']:
        for i in range(2):
            storage_service.save_prediction({
                'instrument': instrument,
                'timestamp': f'2024-11-23T{10+i}:30:00'
            })

    # Get info
    info = storage_service.get_storage_info()
    assert info['total_predictions'] == 6
    assert 'US100' in info['predictions_by_instrument']
    assert info['predictions_by_instrument']['US100'] == 2


def test_format_timestamp_for_filename(storage_service):
    """Test timestamp formatting for filenames."""
    # Valid ISO timestamp
    result = storage_service._format_timestamp_for_filename('2024-11-23T14:30:45')
    assert '2024-11-23' in result
    assert '14-30-45' in result

    # With timezone
    result = storage_service._format_timestamp_for_filename('2024-11-23T14:30:45-05:00')
    assert '2024-11-23' in result

    # Invalid timestamp (should use current time)
    result = storage_service._format_timestamp_for_filename('invalid')
    assert '_' in result


def test_storage_backend_delegation(storage_service):
    """Test that StorageService properly delegates to backend."""
    # Save via service
    storage_service.save('test_key', {'data': 'test_value'})

    # Load via service
    loaded = storage_service.load('test_key')
    assert loaded['data'] == 'test_value'

    # Delete via service
    result = storage_service.delete('test_key')
    assert result is True

    # Verify deleted
    loaded = storage_service.load('test_key')
    assert loaded == {}
