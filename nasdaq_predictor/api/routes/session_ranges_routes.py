"""
Session Ranges API Routes

GET /api/session-ranges/{ticker}
  Returns: Current and previous day session ranges (Asian, London, NY AM, NY PM)
"""

import logging
from flask import Blueprint, jsonify

from ...services.session_range_service import SessionRangeService
from ...data.fetcher_live import LiveDataFetcher

logger = logging.getLogger(__name__)

session_ranges_bp = Blueprint('session_ranges', __name__, url_prefix='/api/session-ranges')


@session_ranges_bp.route('/<ticker>', methods=['GET'])
def get_session_ranges(ticker: str):
    """
    Get current and previous day session ranges

    Args:
        ticker: Ticker symbol (NQ=F, ES=F, etc.)

    Returns:
        JSON with:
        {
            "success": true,
            "ticker": "NQ=F",
            "current_price": 17245.50,
            "current_session_ranges": {
                "asian": {
                    "name": "Asian (18:00-02:00 ET)",
                    "high": 17255.0,
                    "low": 17200.0,
                    "range": 55.0,
                    "bars_in_session": 42,
                    "is_active": false,
                    "current_price": 17245.50,
                    "within_range": true,
                    "above_range": false,
                    "below_range": false
                },
                "london": {...},
                "ny_am": {...},
                "ny_pm": {...}
            },
            "previous_day_session_ranges": {
                "asian": {...},
                ...
            }
        }
    """
    try:
        # Validate ticker
        if not ticker or len(ticker) < 2:
            return jsonify({
                "success": False,
                "error": "Invalid ticker symbol"
            }), 400

        logger.info(f"Fetching session ranges for {ticker}")

        # Get current price
        current_price = LiveDataFetcher.get_current_price(ticker)
        if current_price is None:
            logger.warning(f"Failed to get current price for {ticker}")
            return jsonify({
                "success": False,
                "error": "Unable to fetch current price"
            }), 503

        # Get all session ranges
        result = SessionRangeService.get_all_session_ranges(
            ticker=ticker,
            current_price=current_price
        )

        if "error" in result:
            return jsonify({
                "success": False,
                "error": result["error"]
            }), 503

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error fetching session ranges for {ticker}: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"Failed to fetch session ranges: {str(e)}"
        }), 500


@session_ranges_bp.route('/<ticker>/current', methods=['GET'])
def get_current_session_ranges(ticker: str):
    """
    Get current session ranges only

    Returns:
        JSON with current session ranges for Asian, London, NY AM, NY PM
    """
    try:
        result = SessionRangeService.get_current_session_ranges(ticker=ticker)

        if "error" in result:
            return jsonify({
                "success": False,
                "error": result["error"]
            }), 503

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error fetching current session ranges: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to fetch current session ranges"
        }), 500


@session_ranges_bp.route('/<ticker>/previous', methods=['GET'])
def get_previous_session_ranges(ticker: str):
    """
    Get previous day's session ranges

    Returns:
        JSON with previous day's session ranges
    """
    try:
        result = SessionRangeService.get_previous_day_session_ranges(ticker=ticker)

        if "error" in result:
            return jsonify({
                "success": False,
                "error": result["error"]
            }), 503

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error fetching previous session ranges: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to fetch previous session ranges"
        }), 500
