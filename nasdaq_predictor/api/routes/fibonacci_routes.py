"""
Fibonacci Pivots API Routes

GET /api/fibonacci-pivots/{ticker}
  Returns: Weekly and daily Fibonacci pivot levels
"""

import logging
from flask import Blueprint, jsonify

from ...data.fetcher_live import LiveDataFetcher
from ...utils.timezone import get_current_time_utc

logger = logging.getLogger(__name__)

fibonacci_bp = Blueprint('fibonacci', __name__, url_prefix='/api/fibonacci-pivots')


def calculate_fibonacci_pivots(high, low, close):
    """
    Calculate Fibonacci pivot levels

    Formula: PP = (High + Low + Close) / 3

    Support/Resistance levels:
    - R3 = PP + 2 * (High - Low)
    - R2 = PP + 1.618 * (High - Low)
    - R1 = PP + 1.000 * (High - Low)
    - PP = (High + Low + Close) / 3
    - S1 = PP - 1.000 * (High - Low)
    - S2 = PP - 1.618 * (High - Low)
    - S3 = PP - 2.000 * (High - Low)
    """
    pp = (high + low + close) / 3
    range_val = high - low

    return {
        'R3': pp + 2.0 * range_val,
        'R2': pp + 1.618 * range_val,
        'R1': pp + 1.0 * range_val,
        'PP': pp,
        'S1': pp - 1.0 * range_val,
        'S2': pp - 1.618 * range_val,
        'S3': pp - 2.0 * range_val
    }


@fibonacci_bp.route('/<ticker>', methods=['GET'])
def get_fibonacci_pivots(ticker: str):
    """
    Get weekly and daily Fibonacci pivot levels

    Args:
        ticker: Ticker symbol (NQ=F, ES=F, etc.)

    Returns:
        JSON with:
        {
            "success": true,
            "ticker": "NQ=F",
            "current_price": 17245.50,
            "current_time_utc": "2025-11-16T15:45:28+00:00",
            "weekly_pivots": {
                "R3": 17400.0,
                "R2": 17320.0,
                "R1": 17270.0,
                "PP": 17220.0,
                "S1": 17170.0,
                "S2": 17120.0,
                "S3": 17040.0
            },
            "daily_pivots": {
                "R3": 17350.0,
                "R2": 17295.0,
                "R1": 17260.0,
                "PP": 17230.0,
                "S1": 17200.0,
                "S2": 17150.0,
                "S3": 17095.0
            },
            "distances": {
                "weekly": {
                    "R3": -154.5,
                    "R2": -74.5,
                    "R1": -24.5,
                    "PP": 25.5,
                    "S1": 75.5,
                    "S2": 125.5,
                    "S3": 205.5
                },
                "daily": {...}
            },
            "closest_pivot": {
                "timeframe": "daily",
                "level": "PP",
                "price": 17230.0,
                "distance": 15.5
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

        logger.info(f"Fetching Fibonacci pivots for {ticker}")

        # Get current price
        current_price = LiveDataFetcher.get_current_price(ticker)
        if current_price is None:
            logger.warning(f"Failed to get current price for {ticker}")
            return jsonify({
                "success": False,
                "error": "Unable to fetch current price"
            }), 503

        # Fetch daily and weekly data
        df_daily = LiveDataFetcher.fetch_data(ticker, interval='1d')
        df_weekly = LiveDataFetcher.fetch_data(ticker, interval='1wk')

        if df_daily is None or df_daily.empty or df_weekly is None or df_weekly.empty:
            logger.warning(f"Insufficient data for {ticker}")
            return jsonify({
                "success": False,
                "error": "Insufficient data to calculate pivots"
            }), 503

        # Get OHLC for pivot calculations
        daily_bar = df_daily.iloc[-1]
        daily_high = float(daily_bar['High'])
        daily_low = float(daily_bar['Low'])
        daily_close = float(daily_bar['Close'])

        weekly_bar = df_weekly.iloc[-1]
        weekly_high = float(weekly_bar['High'])
        weekly_low = float(weekly_bar['Low'])
        weekly_close = float(weekly_bar['Close'])

        # Calculate pivots
        daily_pivots = calculate_fibonacci_pivots(daily_high, daily_low, daily_close)
        weekly_pivots = calculate_fibonacci_pivots(weekly_high, weekly_low, weekly_close)

        # Calculate distances
        daily_distances = {k: round(current_price - v, 2) for k, v in daily_pivots.items()}
        weekly_distances = {k: round(current_price - v, 2) for k, v in weekly_pivots.items()}

        # Find closest pivot
        all_distances = {
            **{f"daily_{k}": v for k, v in daily_distances.items()},
            **{f"weekly_{k}": v for k, v in weekly_distances.items()}
        }

        closest_key = min(all_distances, key=lambda x: abs(all_distances[x]))
        closest_parts = closest_key.split('_')
        closest_timeframe = closest_parts[0]
        closest_level = closest_parts[1]
        closest_price = weekly_pivots[closest_level] if closest_timeframe == 'weekly' else daily_pivots[closest_level]

        return jsonify({
            "success": True,
            "ticker": ticker,
            "current_price": round(current_price, 2),
            "current_time_utc": get_current_time_utc().isoformat(),
            "weekly_pivots": {k: round(v, 2) for k, v in weekly_pivots.items()},
            "daily_pivots": {k: round(v, 2) for k, v in daily_pivots.items()},
            "distances": {
                "weekly": weekly_distances,
                "daily": daily_distances
            },
            "closest_pivot": {
                "timeframe": closest_timeframe,
                "level": closest_level,
                "price": round(closest_price, 2),
                "distance": all_distances[closest_key]
            }
        }), 200

    except Exception as e:
        logger.error(f"Error fetching Fibonacci pivots for {ticker}: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"Failed to fetch Fibonacci pivots: {str(e)}"
        }), 500


@fibonacci_bp.route('/<ticker>/daily', methods=['GET'])
def get_daily_pivots(ticker: str):
    """
    Get daily Fibonacci pivot levels only

    Returns:
        JSON with daily pivot levels
    """
    try:
        current_price = LiveDataFetcher.get_current_price(ticker)
        df_daily = LiveDataFetcher.fetch_data(ticker, interval='1d')

        if df_daily is None or df_daily.empty:
            return jsonify({
                "success": False,
                "error": "Unable to fetch daily data"
            }), 503

        daily_bar = df_daily.iloc[-1]
        daily_pivots = calculate_fibonacci_pivots(
            float(daily_bar['High']),
            float(daily_bar['Low']),
            float(daily_bar['Close'])
        )

        daily_distances = {k: round(current_price - v, 2) for k, v in daily_pivots.items()}

        return jsonify({
            "success": True,
            "ticker": ticker,
            "current_price": round(current_price, 2),
            "daily_pivots": {k: round(v, 2) for k, v in daily_pivots.items()},
            "distances": daily_distances
        }), 200

    except Exception as e:
        logger.error(f"Error fetching daily pivots: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to fetch daily pivots"
        }), 500


@fibonacci_bp.route('/<ticker>/weekly', methods=['GET'])
def get_weekly_pivots(ticker: str):
    """
    Get weekly Fibonacci pivot levels only

    Returns:
        JSON with weekly pivot levels
    """
    try:
        current_price = LiveDataFetcher.get_current_price(ticker)
        df_weekly = LiveDataFetcher.fetch_data(ticker, interval='1wk')

        if df_weekly is None or df_weekly.empty:
            return jsonify({
                "success": False,
                "error": "Unable to fetch weekly data"
            }), 503

        weekly_bar = df_weekly.iloc[-1]
        weekly_pivots = calculate_fibonacci_pivots(
            float(weekly_bar['High']),
            float(weekly_bar['Low']),
            float(weekly_bar['Close'])
        )

        weekly_distances = {k: round(current_price - v, 2) for k, v in weekly_pivots.items()}

        return jsonify({
            "success": True,
            "ticker": ticker,
            "current_price": round(current_price, 2),
            "weekly_pivots": {k: round(v, 2) for k, v in weekly_pivots.items()},
            "distances": weekly_distances
        }), 200

    except Exception as e:
        logger.error(f"Error fetching weekly pivots: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to fetch weekly pivots"
        }), 500
