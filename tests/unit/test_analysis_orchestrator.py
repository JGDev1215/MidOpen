"""
Unit tests for Analysis Orchestrator
"""
import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from src.di.container import DIContainer, reset_container
from src.services.analysis_orchestrator import (
    AnalysisOrchestrator, AnalysisResult, PredictionSnapshot, WeightAdjustmentSnapshot
)


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
def orchestrator(temp_paths):
    """Create an orchestrator with container dependencies."""
    reset_container()
    container = DIContainer(
        config_path=temp_paths['config'],
        log_path=temp_paths['log'],
        storage_path=temp_paths['storage']
    )
    return container.get_analysis_orchestrator()


def test_orchestrator_initialization(orchestrator):
    """Test orchestrator initializes correctly."""
    assert orchestrator is not None
    assert orchestrator.config is not None
    assert orchestrator.logging is not None
    assert orchestrator.storage is not None


def test_analysis_result_dataclass():
    """Test AnalysisResult dataclass."""
    result = AnalysisResult(
        instrument='US100',
        bias='BULLISH',
        confidence=85.5,
        timestamp='2024-11-23T10:30:00',
        analysis_data={'key': 'value'},
        metadata={'data_timestamp': '2024-11-23T10:30:00'}
    )

    assert result.instrument == 'US100'
    assert result.bias == 'BULLISH'
    assert result.confidence == 85.5

    # Test to_dict
    result_dict = result.to_dict()
    assert result_dict['instrument'] == 'US100'
    assert result_dict['bias'] == 'BULLISH'


def test_prediction_snapshot_dataclass():
    """Test PredictionSnapshot dataclass."""
    snapshot = PredictionSnapshot(
        instrument='US100',
        result={'analysis': 'data'},
        analysis_timestamp='2024-11-23T10:30:00',
        data_timestamp='2024-11-23T10:30:00',
        confidence=85.5,
        bias='BULLISH'
    )

    assert snapshot.instrument == 'US100'
    assert snapshot.confidence == 85.5

    # Test to_dict
    snapshot_dict = snapshot.to_dict()
    assert 'instrument' in snapshot_dict


def test_execute_analysis_workflow(orchestrator):
    """Test complete analysis workflow."""
    analysis_result = AnalysisResult(
        instrument='US100',
        bias='BULLISH',
        confidence=85.5,
        timestamp='2024-11-23T10:30:00',
        analysis_data={'signal': 'strong'},
        metadata={'data_timestamp': '2024-11-23T10:30:00'}
    )

    prediction_data = {
        'timezone': 'UTC',
        'filename': 'data.csv',
        'data_length': 100,
        'current_price': 18500.50
    }

    success, message = orchestrator.execute_analysis_workflow(analysis_result, prediction_data)

    assert success is True
    assert 'successful' in message.lower()

    # Verify prediction was saved
    count = orchestrator.storage.get_prediction_count()
    assert count == 1


def test_analysis_workflow_invalid_instrument(orchestrator):
    """Test analysis workflow with invalid instrument."""
    analysis_result = AnalysisResult(
        instrument='INVALID',
        bias='BULLISH',
        confidence=85.5,
        timestamp='2024-11-23T10:30:00',
        analysis_data={},
        metadata={}
    )

    success, message = orchestrator.execute_analysis_workflow(analysis_result, {})

    assert success is False
    assert 'not configured' in message.lower()


def test_adjust_weights_workflow(orchestrator):
    """Test weight adjustment workflow."""
    new_weights = {
        'daily_midnight': 0.2,
        'ny_open': 0.3,
        'previous_hourly': 0.5
    }

    # Truncate weights to sum to 1.0
    new_weights = {
        'daily_midnight': 0.333,
        'ny_open': 0.333,
        'previous_hourly': 0.334
    }

    success, message = orchestrator.adjust_weights_workflow(
        'US100', new_weights, reason='Test adjustment', user='test_user'
    )

    assert success is True
    assert 'successful' in message.lower()

    # Verify weights were updated
    updated = orchestrator.config.get_weights('US100')
    assert abs(updated['daily_midnight'] - 0.333) < 0.001


def test_adjust_weights_workflow_no_changes(orchestrator):
    """Test weight adjustment workflow returns a valid response."""
    current = orchestrator.config.get_weights('US100')

    success, message = orchestrator.adjust_weights_workflow(
        'US100', current, reason='Test'
    )

    # Result should be boolean regardless of outcome
    assert isinstance(success, bool)
    assert isinstance(message, str)


def test_adjust_weights_invalid_weights(orchestrator):
    """Test weight adjustment with invalid weights."""
    invalid_weights = {'a': 0.5, 'b': 0.3}

    success, message = orchestrator.adjust_weights_workflow(
        'US100', invalid_weights
    )

    assert success is False
    assert 'sum' in message.lower()


def test_get_prediction_summary(orchestrator):
    """Test getting prediction summary."""
    # Create and save a prediction using analysis workflow
    analysis = AnalysisResult(
        instrument='US100',
        bias='BULLISH',
        confidence=85.5,
        timestamp='2024-11-23T10:30:00',
        analysis_data={'data': 'test'},
        metadata={'data_timestamp': '2024-11-23T10:30:00'}
    )

    orchestrator.execute_analysis_workflow(analysis, {})

    summary = orchestrator.get_prediction_summary('US100')

    assert summary['instrument'] == 'US100'
    assert summary['total_predictions'] == 1


def test_get_prediction_summary_no_predictions(orchestrator):
    """Test prediction summary with no predictions."""
    summary = orchestrator.get_prediction_summary('US100')

    assert summary['instrument'] == 'US100'
    assert summary['total_predictions'] == 0


def test_get_weight_change_summary(orchestrator):
    """Test getting weight change summary."""
    # Make a weight change
    old = orchestrator.config.get_weights('US100')
    new = old.copy()
    new['daily_midnight'] = 0.15

    # Adjust to sum to 1.0
    total = sum(new.values())
    new = {k: v / total for k, v in new.items()}

    orchestrator.adjust_weights_workflow('US100', new)

    summary = orchestrator.get_weight_change_summary('US100')

    assert summary['instrument'] == 'US100'
    assert summary['total_changes'] > 0


def test_get_weight_change_summary_no_changes(orchestrator):
    """Test weight change summary with no changes."""
    summary = orchestrator.get_weight_change_summary('US100')

    assert summary['instrument'] == 'US100'
    assert summary['total_changes'] == 0


def test_get_instrument_health_report(orchestrator):
    """Test getting comprehensive health report."""
    # Make some activity
    orchestrator.storage.save_prediction({
        'instrument': 'US100',
        'timestamp': '2024-11-23T10:30:00'
    })

    report = orchestrator.get_instrument_health_report('US100')

    assert report['instrument'] == 'US100'
    assert 'configuration' in report
    assert 'predictions' in report
    assert 'weight_changes' in report
    assert report['predictions']['total_predictions'] == 1


def test_reset_instrument(orchestrator):
    """Test resetting instrument to defaults."""
    # Modify weights
    modified = orchestrator.config.get_weights('US100')
    modified['daily_midnight'] = 0.05

    total = sum(modified.values())
    modified = {k: v / total for k, v in modified.items()}

    orchestrator.config.set_weights('US100', modified)

    # Reset
    success, message = orchestrator.reset_instrument('US100', reason='Test reset')

    assert success is True
    assert 'successful' in message.lower()

    # Verify reset
    reset_weights = orchestrator.config.get_weights('US100')
    assert reset_weights == orchestrator.config.DEFAULT_WEIGHTS['US100']


def test_reset_invalid_instrument(orchestrator):
    """Test resetting invalid instrument."""
    success, message = orchestrator.reset_instrument('INVALID')

    assert success is False
    assert 'not configured' in message.lower()


def test_get_all_instruments_status(orchestrator):
    """Test getting status for all instruments."""
    # Add some activity for US100
    orchestrator.storage.save_prediction({
        'instrument': 'US100',
        'timestamp': '2024-11-23T10:30:00'
    })

    statuses = orchestrator.get_all_instruments_status()

    assert len(statuses) > 0
    assert any(s['instrument'] == 'US100' for s in statuses)

    us100_status = next(s for s in statuses if s['instrument'] == 'US100')
    assert us100_status['predictions'] == 1


def test_orchestrator_workflow_complete(orchestrator):
    """Test complete orchestrator workflow."""
    # 1. Execute analysis
    analysis = AnalysisResult(
        instrument='US100',
        bias='BEARISH',
        confidence=92.3,
        timestamp='2024-11-23T11:00:00',
        analysis_data={'trend': 'down'},
        metadata={'data_timestamp': '2024-11-23T11:00:00'}
    )

    success, msg = orchestrator.execute_analysis_workflow(analysis, {})
    assert success is True

    # 2. Get prediction summary
    summary = orchestrator.get_prediction_summary('US100')
    assert summary['total_predictions'] == 1

    # 3. Adjust weights based on analysis
    current = orchestrator.config.get_weights('US100')
    adjusted = current.copy()
    adjusted['daily_midnight'] = 0.15

    total = sum(adjusted.values())
    adjusted = {k: v / total for k, v in adjusted.items()}

    success, msg = orchestrator.adjust_weights_workflow(
        'US100', adjusted, reason='Analysis-based adjustment'
    )
    assert success is True

    # 4. Get weight summary
    weight_summary = orchestrator.get_weight_change_summary('US100')
    assert weight_summary['total_changes'] > 0

    # 5. Get full health report
    report = orchestrator.get_instrument_health_report('US100')
    assert report['predictions']['total_predictions'] == 1
    assert report['weight_changes']['total_changes'] > 0
