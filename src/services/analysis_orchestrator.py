"""
Analysis Orchestrator Service
High-level service that orchestrates analysis workflows across multiple services
"""
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from src.services.config_service import ConfigurationService
from src.services.logging_service import LoggingService
from src.services.storage_service import StorageService

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """Result of an analysis operation"""
    instrument: str
    bias: str  # BULLISH, BEARISH, NEUTRAL
    confidence: float  # 0-100
    timestamp: str
    analysis_data: Dict[str, Any]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class PredictionSnapshot:
    """Snapshot of a prediction with metadata"""
    instrument: str
    result: Dict[str, Any]
    analysis_timestamp: str
    data_timestamp: str
    confidence: float
    bias: str
    timezone: Optional[str] = None
    filename: Optional[str] = None
    data_length: Optional[int] = None
    current_price: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class WeightAdjustmentSnapshot:
    """Snapshot of a weight adjustment operation"""
    instrument: str
    old_weights: Dict[str, float]
    new_weights: Dict[str, float]
    changed_levels: Dict[str, Dict[str, float]]
    timestamp: str
    reason: str
    user: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class AnalysisOrchestrator:
    """
    High-level orchestrator for analysis workflows.
    Coordinates operations across Configuration, Logging, and Storage services.
    """

    def __init__(self, config_service: ConfigurationService,
                 logging_service: LoggingService,
                 storage_service: StorageService):
        """
        Initialize the analysis orchestrator with service dependencies.

        Args:
            config_service: ConfigurationService instance
            logging_service: LoggingService instance
            storage_service: StorageService instance
        """
        self.config = config_service
        self.logging = logging_service
        self.storage = storage_service
        logger.info("AnalysisOrchestrator initialized")

    def execute_analysis_workflow(self, analysis_result: AnalysisResult,
                                  prediction_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Execute complete analysis workflow:
        1. Validate analysis result
        2. Save prediction to storage
        3. Log analysis completion
        4. Update metrics

        Args:
            analysis_result: Result from analysis
            prediction_data: Additional prediction data

        Returns:
            Tuple of (success, message)
        """
        try:
            # Validate input
            if not analysis_result or not analysis_result.instrument:
                return False, "Invalid analysis result: missing instrument"

            instrument = analysis_result.instrument

            # Verify instrument is configured
            if instrument not in self.config.get_all_instruments():
                return False, f"Instrument {instrument} not configured"

            # Prepare prediction snapshot
            snapshot = PredictionSnapshot(
                instrument=instrument,
                result=analysis_result.analysis_data,
                analysis_timestamp=analysis_result.timestamp,
                data_timestamp=analysis_result.metadata.get('data_timestamp', analysis_result.timestamp),
                confidence=analysis_result.confidence,
                bias=analysis_result.bias,
                timezone=prediction_data.get('timezone'),
                filename=prediction_data.get('filename'),
                data_length=prediction_data.get('data_length'),
                current_price=prediction_data.get('current_price')
            )

            # Save prediction to storage
            save_success = self.storage.save_prediction(snapshot.to_dict())
            if not save_success:
                return False, "Failed to save prediction to storage"

            # Log analysis completion
            try:
                self.logging.append({
                    'timestamp': datetime.now().isoformat(),
                    'event_type': 'analysis_complete',
                    'instrument': instrument,
                    'bias': analysis_result.bias,
                    'confidence': analysis_result.confidence
                })
            except Exception as e:
                logger.warning(f"Failed to log analysis completion: {e}")

            logger.info(f"Analysis workflow completed for {instrument}")
            return True, f"Analysis completed successfully for {instrument}"

        except Exception as e:
            logger.error(f"Analysis workflow failed: {e}")
            return False, f"Analysis workflow error: {str(e)}"

    def adjust_weights_workflow(self, instrument: str, new_weights: Dict[str, float],
                                reason: str = None, user: str = None) -> Tuple[bool, str]:
        """
        Execute weight adjustment workflow:
        1. Validate new weights
        2. Get current weights
        3. Apply changes
        4. Log weight change
        5. Update configuration

        Args:
            instrument: Instrument to adjust
            new_weights: New weight values
            reason: Reason for adjustment
            user: User making the adjustment

        Returns:
            Tuple of (success, message)
        """
        try:
            # Validate instrument
            if instrument not in self.config.get_all_instruments():
                return False, f"Instrument {instrument} not configured"

            # Validate new weights
            is_valid, msg = self.config.validate_weights(new_weights)
            if not is_valid:
                return False, msg

            # Get current weights
            old_weights = self.config.get_weights(instrument)

            # Check if any changes
            has_changes = any(
                abs(old_weights.get(k, 0) - new_weights.get(k, 0)) > 0.00001
                for k in new_weights.keys()
            )

            if not has_changes:
                return True, f"No weight changes detected for {instrument}"

            # Identify changed levels
            changed_levels = {}
            for level_name in new_weights:
                old_value = old_weights.get(level_name, 0.0)
                new_value = new_weights.get(level_name, 0.0)

                if abs(old_value - new_value) > 0.00001:
                    changed_levels[level_name] = {
                        'old': old_value,
                        'new': new_value,
                        'change': new_value - old_value
                    }

            # Apply changes
            self.config.set_weights(instrument, new_weights)

            # Log weight change
            self.logging.log_weight_change(
                instrument=instrument,
                old_weights=old_weights,
                new_weights=new_weights,
                user=user,
                reason=reason
            )

            logger.info(f"Weight adjustment completed for {instrument}: {len(changed_levels)} levels changed")
            return True, f"Weight adjustment successful for {instrument}"

        except ValueError as e:
            logger.error(f"Weight validation failed: {e}")
            return False, str(e)
        except Exception as e:
            logger.error(f"Weight adjustment workflow failed: {e}")
            return False, f"Weight adjustment error: {str(e)}"

    def get_prediction_summary(self, instrument: str) -> Dict[str, Any]:
        """
        Get summary of predictions for an instrument.

        Args:
            instrument: Instrument code

        Returns:
            Summary dictionary with prediction stats
        """
        try:
            predictions = self.storage.get_predictions_by_instrument(instrument)

            if not predictions:
                return {
                    'instrument': instrument,
                    'total_predictions': 0,
                    'latest_prediction': None,
                    'bias_distribution': {},
                    'average_confidence': 0
                }

            # Calculate statistics
            biases = {}
            confidences = []

            for pred in predictions:
                bias = pred.get('bias', 'UNKNOWN')
                biases[bias] = biases.get(bias, 0) + 1

                confidence = pred.get('confidence', 0)
                if confidence:
                    confidences.append(confidence)

            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            return {
                'instrument': instrument,
                'total_predictions': len(predictions),
                'latest_prediction': predictions[0] if predictions else None,
                'bias_distribution': biases,
                'average_confidence': round(avg_confidence, 2),
                'prediction_count_by_bias': {
                    bias: count for bias, count in biases.items()
                }
            }

        except Exception as e:
            logger.error(f"Failed to get prediction summary: {e}")
            return {'error': str(e), 'instrument': instrument}

    def get_weight_change_summary(self, instrument: str, days: int = 30) -> Dict[str, Any]:
        """
        Get summary of weight changes for an instrument.

        Args:
            instrument: Instrument code
            days: Number of days to look back

        Returns:
            Summary dictionary with weight change stats
        """
        try:
            history = self.logging.get_change_history(instrument=instrument, days=days)

            if not history:
                return {
                    'instrument': instrument,
                    'total_changes': 0,
                    'latest_change': None,
                    'most_adjusted_level': None
                }

            # Get summary statistics
            stats = self.logging.get_summary_statistics(instrument)

            return {
                'instrument': instrument,
                'total_changes': stats['total_changes'],
                'latest_change': history[0] if history else None,
                'most_adjusted_level': stats['most_adjusted_level'],
                'unique_levels_modified': stats['unique_levels_modified'],
                'most_adjusted_count': stats['most_adjusted_count']
            }

        except Exception as e:
            logger.error(f"Failed to get weight change summary: {e}")
            return {'error': str(e), 'instrument': instrument}

    def get_instrument_health_report(self, instrument: str) -> Dict[str, Any]:
        """
        Get comprehensive health report for an instrument.

        Args:
            instrument: Instrument code

        Returns:
            Comprehensive health report
        """
        try:
            # Get configuration
            weights = self.config.get_weights(instrument)

            # Get prediction summary
            pred_summary = self.get_prediction_summary(instrument)

            # Get weight change summary
            weight_summary = self.get_weight_change_summary(instrument)

            return {
                'instrument': instrument,
                'configuration': {
                    'num_weights': len(weights),
                    'weights': weights
                },
                'predictions': pred_summary,
                'weight_changes': weight_summary,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to get health report: {e}")
            return {'error': str(e), 'instrument': instrument}

    def reset_instrument(self, instrument: str, reason: str = None) -> Tuple[bool, str]:
        """
        Reset instrument to default weights.

        Args:
            instrument: Instrument code
            reason: Reason for reset

        Returns:
            Tuple of (success, message)
        """
        try:
            if instrument not in self.config.get_all_instruments():
                return False, f"Instrument {instrument} not configured"

            # Log the reset
            old_weights = self.config.get_weights(instrument)

            # Reset weights
            self.config.reset_instrument_weights(instrument)

            # Log reset
            new_weights = self.config.get_weights(instrument)
            self.logging.log_weight_change(
                instrument=instrument,
                old_weights=old_weights,
                new_weights=new_weights,
                user='system',
                reason=reason or 'System reset'
            )

            logger.info(f"Reset weights for {instrument}")
            return True, f"Reset successful for {instrument}"

        except Exception as e:
            logger.error(f"Reset failed: {e}")
            return False, f"Reset error: {str(e)}"

    def get_all_instruments_status(self) -> List[Dict[str, Any]]:
        """
        Get status for all configured instruments.

        Returns:
            List of instrument status dictionaries
        """
        try:
            instruments = self.config.get_all_instruments()
            statuses = []

            for instrument in instruments:
                try:
                    status = {
                        'instrument': instrument,
                        'predictions': len(self.storage.get_predictions_by_instrument(instrument)),
                        'weight_changes': len(self.logging.get_change_history(instrument=instrument)),
                        'latest_prediction': self.storage.get_predictions_by_instrument(instrument)[0]
                        if self.storage.get_predictions_by_instrument(instrument) else None
                    }
                    statuses.append(status)
                except Exception as e:
                    logger.warning(f"Failed to get status for {instrument}: {e}")

            return statuses

        except Exception as e:
            logger.error(f"Failed to get all instruments status: {e}")
            return []
