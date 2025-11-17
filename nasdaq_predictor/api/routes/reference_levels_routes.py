"""
Reference Levels API Routes

GET /api/reference-levels/{ticker}
  Returns: All 16 reference levels with price comparison and signals
"""

import logging
from flask import Blueprint, jsonify

from ...services.reference_level_service import ReferenceLevelService
from ...data.fetcher_live import LiveDataFetcher

logger = logging.getLogger(__name__)

reference_levels_bp = Blueprint('reference_levels', __name__, url_prefix='/api/reference-levels')


@reference_levels_bp.route('/<ticker>', methods=['GET'])
def get_reference_levels(ticker: str):
    """
    Get all 16 reference levels with signals

    Args:
        ticker: Ticker symbol (NQ=F, ES=F, etc.)

    Returns:
        JSON with all reference levels, signals, and closest level
        {
            "success": true,
            "ticker": "NQ=F",
            "current_price": 17245.50,
            "current_time_utc": "2025-11-16T15:45:28+00:00",
            "reference_levels": {
                "weekly_open": 17200.0,
                "monthly_open": 17180.5,
                ...all 16 levels
            },
            "signals": {
                "weekly_open": {
                    "price": 17200.0,
                    "distance": 45.50,
                    "distance_pct": 0.264,
                    "proximity": "ABOVE",
                    "signal": 1
                },
                ...signals for all levels
            },
            "closest_level": {
                "level": "fourh_open",
                "price": 17244.0,
                "distance": 1.5,
                "proximity": "NEAR"
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

        logger.info(f"Fetching reference levels for {ticker}")

        # Get current price
        current_price = LiveDataFetcher.get_current_price(ticker)
        if current_price is None:
            logger.warning(f"Failed to get current price for {ticker}")
            return jsonify({
                "success": False,
                "error": "Unable to fetch current price"
            }), 503

        # Calculate all reference levels
        result = ReferenceLevelService.calculate_all_levels(
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
        logger.error(f"Error fetching reference levels for {ticker}: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"Failed to fetch reference levels: {str(e)}"
        }), 500


@reference_levels_bp.route('/<ticker>/summary', methods=['GET'])
def get_reference_levels_summary(ticker: str):
    """
    Get summary of key reference levels (for dashboard display)

    Returns:
        JSON with key levels only:
        {
            "success": true,
            "ticker": "NQ=F",
            "current_price": 17245.50,
            "current_time": "2025-11-16T15:45:28+00:00",
            "levels": {
                "weekly_open": {...},
                "daily_open_midnight": {...},
                "ny_open_0830": {...},
                ...key levels
            }
        }
    """
    try:
        current_price = LiveDataFetcher.get_current_price(ticker)
        if current_price is None:
            return jsonify({
                "success": False,
                "error": "Unable to fetch current price"
            }), 503

        result = ReferenceLevelService.get_level_summary(ticker, current_price)

        if "error" in result:
            return jsonify({
                "success": False,
                "error": result["error"]
            }), 503

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error fetching reference levels summary: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to fetch reference levels summary"
        }), 500


@reference_levels_bp.route('/<ticker>/closest', methods=['GET'])
def get_closest_reference_level(ticker: str):
    """
    Get the closest reference level to current price

    Returns:
        JSON with:
        {
            "success": true,
            "ticker": "NQ=F",
            "current_price": 17245.50,
            "closest_level": {
                "level": "fourh_open",
                "price": 17244.0,
                "distance": 1.5,
                "proximity": "NEAR"
            }
        }
    """
    try:
        current_price = LiveDataFetcher.get_current_price(ticker)
        if current_price is None:
            return jsonify({
                "success": False,
                "error": "Unable to fetch current price"
            }), 503

        result = ReferenceLevelService.calculate_all_levels(ticker, current_price)

        if "error" in result:
            return jsonify({
                "success": False,
                "error": result["error"]
            }), 503

        return jsonify({
            "success": True,
            "ticker": ticker,
            "current_price": result.get("current_price"),
            "closest_level": result.get("closest_level")
        }), 200

    except Exception as e:
        logger.error(f"Error fetching closest reference level: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to fetch closest reference level"
        }), 500
