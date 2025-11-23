"""
Unit tests for Service Accessors
"""
import pytest
import tempfile
from pathlib import Path
from src.di.container import DIContainer, reset_container, get_container
from src.di.accessors import (
    get_config_service,
    get_logging_service,
    get_storage_service,
    get_weights,
    set_weights,
    validate_weights,
    get_all_instruments,
    log_weight_change,
    get_weight_change_history,
    get_latest_weight_change,
    save_prediction,
    load_all_predictions,
    get_prediction_count,
    get_predictions_by_instrument,
    get_top_predictions,
    delete_prediction,
    get_storage_info,
)


@pytest.fixture(autouse=True)
def setup_teardown():
    """Set up and tear down container for each test."""
    reset_container()

    # Create temporary paths
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        get_container(
            config_path=tmpdir_path / 'weights.json',
            log_path=tmpdir_path / 'logs',
            storage_path=tmpdir_path / 'storage'
        )
        yield

    reset_container()


def test_get_config_service():
    """Test getting configuration service."""
    service = get_config_service()
    assert service is not None


def test_get_logging_service():
    """Test getting logging service."""
    service = get_logging_service()
    assert service is not None


def test_get_storage_service():
    """Test getting storage service."""
    service = get_storage_service()
    assert service is not None


def test_get_weights():
    """Test getting weights for an instrument."""
    weights = get_weights('US100')
    assert len(weights) > 0
    assert isinstance(weights, dict)


def test_set_weights():
    """Test setting weights for an instrument."""
    new_weights = {'level_1': 0.5, 'level_2': 0.5}
    set_weights('TEST_INST', new_weights)

    retrieved = get_weights('TEST_INST')
    assert retrieved == new_weights


def test_validate_weights_valid():
    """Test validating valid weights."""
    is_valid, msg = validate_weights({'a': 0.5, 'b': 0.5})
    assert is_valid is True


def test_validate_weights_invalid():
    """Test validating invalid weights."""
    is_valid, msg = validate_weights({'a': 0.5, 'b': 0.3})
    assert is_valid is False


def test_get_all_instruments():
    """Test getting all instruments."""
    instruments = get_all_instruments()
    assert len(instruments) > 0
    assert 'US100' in instruments


def test_log_weight_change():
    """Test logging weight change."""
    old_weights = {'a': 0.5, 'b': 0.5}
    new_weights = {'a': 0.6, 'b': 0.4}

    log_weight_change('US100', old_weights, new_weights, user='test')

    history = get_weight_change_history(instrument='US100')
    assert len(history) > 0


def test_get_weight_change_history():
    """Test getting weight change history."""
    # Log a change
    log_weight_change(
        'US100',
        {'a': 0.5, 'b': 0.5},
        {'a': 0.6, 'b': 0.4}
    )

    history = get_weight_change_history()
    assert len(history) > 0


def test_get_weight_change_history_filtered():
    """Test getting weight change history with instrument filter."""
    # Log changes for different instruments
    log_weight_change(
        'US100',
        {'a': 0.5, 'b': 0.5},
        {'a': 0.6, 'b': 0.4}
    )

    log_weight_change(
        'UK100',
        {'a': 0.5, 'b': 0.5},
        {'a': 0.7, 'b': 0.3}
    )

    # Get US100 history
    us100_history = get_weight_change_history(instrument='US100')
    assert all(log['instrument'] == 'US100' for log in us100_history)


def test_get_latest_weight_change():
    """Test getting latest weight change."""
    log_weight_change(
        'US100',
        {'a': 0.5, 'b': 0.5},
        {'a': 0.6, 'b': 0.4}
    )

    latest = get_latest_weight_change('US100')
    assert latest is not None
    assert latest['instrument'] == 'US100'


def test_save_prediction():
    """Test saving prediction."""
    result = save_prediction({
        'instrument': 'US100',
        'timestamp': '2024-11-23T10:30:00'
    })
    assert result is True


def test_load_all_predictions():
    """Test loading all predictions."""
    # Save some
    for i in range(3):
        save_prediction({
            'instrument': 'US100',
            'timestamp': f'2024-11-23T{10+i}:30:00'
        })

    # Load all
    predictions = load_all_predictions()
    assert len(predictions) == 3


def test_get_prediction_count():
    """Test getting prediction count."""
    # Save some
    for i in range(5):
        save_prediction({
            'instrument': 'US100',
            'timestamp': f'2024-11-23T{10+i}:30:00'
        })

    count = get_prediction_count()
    assert count == 5


def test_get_predictions_by_instrument():
    """Test getting predictions by instrument."""
    # Save for different instruments
    save_prediction({'instrument': 'US100', 'timestamp': '2024-11-23T10:30:00'})
    save_prediction({'instrument': 'UK100', 'timestamp': '2024-11-23T10:30:00'})

    us100_preds = get_predictions_by_instrument('US100')
    assert len(us100_preds) == 1
    assert us100_preds[0]['instrument'] == 'US100'


def test_get_top_predictions():
    """Test getting top N predictions."""
    # Save some
    for i in range(10):
        save_prediction({
            'instrument': 'US100',
            'data_timestamp': f'2024-11-{20+i}T10:30:00',
            'timestamp': f'2024-11-23T{10+i}:30:00'
        })

    top_5 = get_top_predictions(5)
    assert len(top_5) == 5


def test_delete_prediction():
    """Test deleting prediction."""
    # Save
    save_prediction({
        'instrument': 'US100',
        'timestamp': '2024-11-23T10:30:00'
    })

    # Get filename
    all_preds = load_all_predictions()
    filename = f"{all_preds[0]['instrument']}_2024-11-23_10-30-00.json"

    # Delete
    result = delete_prediction(filename)
    assert result is True

    # Verify deleted
    count = get_prediction_count()
    assert count == 0


def test_get_storage_info():
    """Test getting storage information."""
    # Save some predictions
    save_prediction({'instrument': 'US100', 'timestamp': '2024-11-23T10:30:00'})
    save_prediction({'instrument': 'UK100', 'timestamp': '2024-11-23T10:30:00'})

    info = get_storage_info()
    assert info['total_predictions'] == 2
    assert 'US100' in info['predictions_by_instrument']


def test_accessor_caching():
    """Test that accessors use same service instances."""
    service1 = get_config_service()
    service2 = get_config_service()

    assert service1 is service2


def test_accessor_integration():
    """Test that accessors work together."""
    # Use accessors for complete workflow
    instruments = get_all_instruments()
    instrument = instruments[0]

    # Get weights
    weights = get_weights(instrument)
    assert len(weights) > 0

    # Log change
    log_weight_change(
        instrument,
        weights,
        weights  # Same weights, should not log
    )

    # Save prediction
    save_prediction({
        'instrument': instrument,
        'timestamp': '2024-11-23T10:30:00'
    })

    # Get info
    count = get_prediction_count()
    assert count == 1

    info = get_storage_info()
    assert info['total_predictions'] == 1
