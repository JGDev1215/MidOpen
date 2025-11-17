"""
Price API Routes

GET /api/current-price/{ticker}
  Returns: Current market price with change indicators
"""

import logging
from flask import Blueprint, jsonify
from datetime import datetime, timedelta

from ...data.fetcher_live import LiveDataFetcher
from ...services.market_status_service import MarketStatusService
from ...utils.timezone import get_current_time_utc, ensure_et

logger = logging.getLogger(__name__)

price_bp = Blueprint('price', __name__, url_prefix='/api/current-price')


@price_bp.route('/<ticker>', methods=['GET'])
def get_current_price(ticker: str):
    """
    Get current price for a ticker with change indicators

    Args:
        ticker: Ticker symbol (NQ=F, ES=F, etc.)

    Returns:
        JSON with:
        {
            "success": true,
            "ticker": "NQ=F",
            "current_price": 17245.50,
            "change": 125.25,
            "change_percent": 0.73,
            "previous_close": 17120.25,
            "last_update_time": "2025-11-16T10:45:28-05:00",
            "last_update_time_utc": "2025-11-16T15:45:28+00:00",
            "is_live": true,
            "data_source": "yfinance"
        }
    """
    try:
        # Validate ticker
        if not ticker or len(ticker) < 2:
            return jsonify({
                "success": False,
                "error": "Invalid ticker symbol"
            }), 400

        # Get current time
        current_time_utc = get_current_time_utc()
        current_time_et = ensure_et(current_time_utc)

        # Check if market is open
        is_open = MarketStatusService.is_market_open(ticker, current_time_utc)

        # Fetch 1-minute data to get latest price
        logger.info(f"Fetching price for {ticker}")
        df_1m = LiveDataFetcher.fetch_data(ticker, interval='1m')

        if df_1m is None or df_1m.empty:
            logger.warning(f"No 1m data available for {ticker}")
            return jsonify({
                "success": False,
                "error": "Unable to fetch price data"
            }), 503

        # Get latest bar
        latest_bar = df_1m.iloc[-1]
        current_price = float(latest_bar['Close'])
        latest_time = df_1m.index[-1]

        # Get previous close (last close from previous market session)
        if len(df_1m) > 60:  # At least 1 hour of data
            # Get close from 1 hour ago
            one_hour_ago = df_1m.iloc[-60]['Close'] if len(df_1m) > 60 else None
        else:
            one_hour_ago = None

        # Calculate change
        if one_hour_ago is not None:
            change = current_price - one_hour_ago
            change_percent = (change / one_hour_ago) * 100 if one_hour_ago != 0 else 0
        else:
            # No prior data, use current as reference
            change = 0.0
            change_percent = 0.0
            one_hour_ago = current_price

        # Get high and low for today
        df_daily = LiveDataFetcher.fetch_data(ticker, interval='1d')
        daily_high = float(df_daily.iloc[-1]['High']) if df_daily is not None else None
        daily_low = float(df_daily.iloc[-1]['Low']) if df_daily is not None else None

        return jsonify({
            "success": True,
            "ticker": ticker,
            "current_price": round(current_price, 2),
            "change": round(change, 2),
            "change_percent": round(change_percent, 3),
            "previous_close": round(one_hour_ago, 2),
            "daily_high": round(daily_high, 2) if daily_high else None,
            "daily_low": round(daily_low, 2) if daily_low else None,
            "last_update_time": latest_time.isoformat(),
            "last_update_time_utc": latest_time.astimezone(
                __import__('pytz').UTC
            ).isoformat(),
            "is_live": is_open,
            "market_open": is_open,
            "data_source": "yfinance"
        }), 200

    except Exception as e:
        logger.error(f"Error fetching current price for {ticker}: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"Failed to fetch price: {str(e)}"
        }), 500


@price_bp.route('/<ticker>/ohlc', methods=['GET'])
def get_ohlc(ticker: str):
    """
    Get OHLC data for current minute

    Returns:
        JSON with:
        {
            "success": true,
            "ticker": "NQ=F",
            "open": 17240.0,
            "high": 17250.5,
            "low": 17235.0,
            "close": 17245.50,
            "volume": 12345,
            "timestamp": "2025-11-16T10:45:00-05:00"
        }
    """
    try:
        df_1m = LiveDataFetcher.fetch_data(ticker, interval='1m')

        if df_1m is None or df_1m.empty:
            return jsonify({
                "success": False,
                "error": "Unable to fetch OHLC data"
            }), 503

        latest_bar = df_1m.iloc[-1]

        return jsonify({
            "success": True,
            "ticker": ticker,
            "open": round(float(latest_bar['Open']), 2),
            "high": round(float(latest_bar['High']), 2),
            "low": round(float(latest_bar['Low']), 2),
            "close": round(float(latest_bar['Close']), 2),
            "volume": int(latest_bar['Volume']) if 'Volume' in latest_bar else None,
            "timestamp": df_1m.index[-1].isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Error fetching OHLC for {ticker}: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to fetch OHLC data"
        }), 500
