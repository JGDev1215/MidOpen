"""
Unit tests for LoggingService
"""
import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from src.infrastructure.logging.file_log_store import FileLogStore
from src.services.logging_service import LoggingService


@pytest.fixture
def temp_log_path():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def log_store(temp_log_path):
    """Create a file log store instance."""
    return FileLogStore(temp_log_path)


@pytest.fixture
def logging_service(log_store):
    """Create a logging service instance."""
    return LoggingService(log_store)


def test_logging_service_initialization(logging_service):
    """Test LoggingService initializes correctly."""
    assert logging_service is not None
    assert logging_service.store is not None


def test_append_log_entry(logging_service):
    """Test appending a log entry."""
    entry = {
        'timestamp': datetime.now().isoformat(),
        'message': 'Test log entry',
        'level': 'INFO'
    }

    logging_service.append(entry)

    # Verify it was stored
    recent = logging_service.load_recent()
    assert len(recent) > 0
    assert recent[0]['message'] == 'Test log entry'


def test_log_weight_change(logging_service):
    """Test logging a weight change."""
    old_weights = {'level_1': 0.5, 'level_2': 0.5}
    new_weights = {'level_1': 0.6, 'level_2': 0.4}

    logging_service.log_weight_change(
        instrument='US100',
        old_weights=old_weights,
        new_weights=new_weights,
        user='test_user',
        reason='Testing'
    )

    # Verify it was logged
    history = logging_service.get_change_history(instrument='US100')
    assert len(history) > 0
    assert history[0]['instrument'] == 'US100'
    assert history[0]['user'] == 'test_user'
    assert len(history[0]['changes']) == 2


def test_no_change_detection(logging_service):
    """Test that no change is detected when weights are identical."""
    weights = {'level_1': 0.5, 'level_2': 0.5}

    logging_service.log_weight_change(
        instrument='US100',
        old_weights=weights,
        new_weights=weights,
        user='test_user',
        reason='Testing'
    )

    # Verify nothing was logged
    history = logging_service.get_change_history(instrument='US100')
    assert len(history) == 0


def test_load_recent_logs(logging_service):
    """Test loading recent logs."""
    # Add some entries
    for i in range(3):
        entry = {
            'timestamp': datetime.now().isoformat(),
            'message': f'Log entry {i}',
            'level': 'INFO'
        }
        logging_service.append(entry)

    # Load recent
    recent = logging_service.load_recent()
    assert len(recent) >= 3


def test_load_instrument_history(logging_service):
    """Test loading history for a specific instrument."""
    # Log changes for different instruments
    logging_service.log_weight_change(
        instrument='US100',
        old_weights={'a': 0.5, 'b': 0.5},
        new_weights={'a': 0.6, 'b': 0.4},
        user='user1'
    )

    logging_service.log_weight_change(
        instrument='UK100',
        old_weights={'a': 0.5, 'b': 0.5},
        new_weights={'a': 0.7, 'b': 0.3},
        user='user2'
    )

    # Load US100 history
    history = logging_service.load_instrument_history('US100')
    assert len(history) == 1
    assert history[0]['instrument'] == 'US100'


def test_get_latest_change(logging_service):
    """Test getting the latest change for an instrument."""
    # Log some changes
    for i in range(3):
        logging_service.log_weight_change(
            instrument='US100',
            old_weights={'a': 0.5, 'b': 0.5},
            new_weights={'a': 0.5 + i*0.1, 'b': 0.5 - i*0.1},
            user=f'user{i}'
        )

    # Get latest
    latest = logging_service.get_latest_change('US100')
    assert latest is not None
    assert latest['user'] == 'user2'  # Most recent


def test_get_summary_statistics(logging_service):
    """Test getting summary statistics for an instrument."""
    # Log a change
    logging_service.log_weight_change(
        instrument='US100',
        old_weights={'level_1': 0.5, 'level_2': 0.5},
        new_weights={'level_1': 0.6, 'level_2': 0.4},
        user='test_user'
    )

    # Get stats
    stats = logging_service.get_summary_statistics('US100')
    assert stats['total_changes'] == 1
    assert stats['unique_levels_modified'] == 2
    assert stats['most_adjusted_level'] in ['level_1', 'level_2']


def test_get_change_history_filtering(logging_service):
    """Test getting change history with filtering."""
    # Log changes for different instruments
    logging_service.log_weight_change(
        instrument='US100',
        old_weights={'a': 0.5, 'b': 0.5},
        new_weights={'a': 0.6, 'b': 0.4}
    )

    logging_service.log_weight_change(
        instrument='UK100',
        old_weights={'a': 0.5, 'b': 0.5},
        new_weights={'a': 0.7, 'b': 0.3}
    )

    # Get history for US100
    us100_history = logging_service.get_change_history(instrument='US100')
    assert all(log['instrument'] == 'US100' for log in us100_history)

    # Get all history
    all_history = logging_service.get_change_history(instrument=None)
    assert len(all_history) == 2
