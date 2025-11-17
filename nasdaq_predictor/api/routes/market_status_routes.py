"""
Market Status API Routes

GET /api/market-status/{ticker}
  Returns: Market open/closed status, current time, countdown to next event
"""

import logging
from flask import Blueprint, jsonify, request
from datetime import datetime
import pytz

from ...services.market_status_service import MarketStatusService
from ...utils.timezone import get_current_time_utc

logger = logging.getLogger(__name__)

market_status_bp = Blueprint('market_status', __name__, url_prefix='/api/market-status')


@market_status_bp.route('/<ticker>', methods=['GET'])
def get_market_status(ticker: str):
    """
    Get current market status for a ticker

    Args:
        ticker: Ticker symbol (NQ=F, ES=F, etc.)

    Returns:
        JSON with:
        {
            "success": true,
            "ticker": "NQ=F",
            "status": "OPEN|CLOSED|MAINTENANCE",
            "is_open": boolean,
            "is_closed": boolean,
            "is_maintenance": boolean,
            "current_time_et": "2025-11-16T10:45:30-05:00",
            "current_time_utc": "2025-11-16T15:45:30+00:00",
            "next_event": {
                "type": "close",
                "time_et": "2025-11-21T17:00:00-05:00",
                "time_utc": "2025-11-21T22:00:00+00:00",
                "countdown_seconds": 432000,
                "countdown_display": "120h 0m"
            },
            "hours_of_operation": "Sunday 6 PM ET - Friday 5 PM ET",
            "daily_maintenance": "5 PM - 6 PM ET"
        }
    """
    try:
        # Validate ticker
        if not ticker or len(ticker) < 2:
            return jsonify({
                "success": False,
                "error": "Invalid ticker symbol"
            }), 400

        # Get market info
        market_info = MarketStatusService.get_market_info(ticker=ticker)

        return jsonify(market_info), 200

    except Exception as e:
        logger.error(f"Error fetching market status for {ticker}: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"Failed to fetch market status: {str(e)}"
        }), 500


@market_status_bp.route('/<ticker>/is-open', methods=['GET'])
def is_market_open(ticker: str):
    """
    Quick check if market is currently open

    Returns:
        JSON with:
        {
            "ticker": "NQ=F",
            "is_open": true,
            "status": "OPEN"
        }
    """
    try:
        is_open = MarketStatusService.is_market_open(ticker)
        status = "OPEN" if is_open else "CLOSED"

        return jsonify({
            "success": True,
            "ticker": ticker,
            "is_open": is_open,
            "status": status
        }), 200

    except Exception as e:
        logger.error(f"Error checking if market is open: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to check market status"
        }), 500


@market_status_bp.route('/<ticker>/next-event', methods=['GET'])
def get_next_event(ticker: str):
    """
    Get next market event (open or close)

    Returns:
        JSON with:
        {
            "success": true,
            "ticker": "NQ=F",
            "next_event": {
                "type": "close",
                "time_et": "2025-11-21T17:00:00-05:00",
                "time_utc": "2025-11-21T22:00:00+00:00",
                "countdown_seconds": 432000,
                "countdown_display": "120h 0m"
            }
        }
    """
    try:
        next_event = MarketStatusService.get_next_event(ticker)

        return jsonify({
            "success": True,
            "ticker": ticker,
            "next_event": next_event
        }), 200

    except Exception as e:
        logger.error(f"Error fetching next event: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to fetch next event"
        }), 500
