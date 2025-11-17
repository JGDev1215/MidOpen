"""
Hourly Block Segmentation API Routes

GET /api/hourly-blocks/{ticker}
  Returns: 7-block hourly segmentation with OHLC for each block
"""

import logging
from flask import Blueprint, jsonify
from datetime import datetime, timedelta
import pytz

from ...data.fetcher_live import LiveDataFetcher
from ...utils.timezone import get_current_time_utc, ensure_et

logger = logging.getLogger(__name__)

block_bp = Blueprint('blocks', __name__, url_prefix='/api/hourly-blocks')

# Constants for hourly block segmentation
BLOCKS_PER_HOUR = 7
MINUTES_PER_BLOCK = 60 / BLOCKS_PER_HOUR  # ~8.57 minutes


def calculate_block_boundaries(current_time_et):
    """
    Calculate the 7 block boundaries for the current hour

    Args:
        current_time_et: Current time in ET timezone

    Returns:
        List of 7 tuples: (block_num, start_time, end_time, is_complete)
    """
    hour_start = current_time_et.replace(minute=0, second=0, microsecond=0)

    blocks = []
    for i in range(BLOCKS_PER_HOUR):
        block_num = i + 1
        start_offset = i * MINUTES_PER_BLOCK
        end_offset = (i + 1) * MINUTES_PER_BLOCK

        block_start = hour_start + timedelta(minutes=start_offset)
        block_end = hour_start + timedelta(minutes=end_offset)

        # Block is complete if current time is past the block end
        is_complete = current_time_et >= block_end

        blocks.append({
            'block_num': block_num,
            'start_time': block_start,
            'end_time': block_end,
            'is_complete': is_complete
        })

    return blocks


def extract_block_ohlc(df, block_start, block_end):
    """
    Extract OHLC data for a specific block time range

    Args:
        df: DataFrame with OHLC data (1-minute bars)
        block_start: Block start time (ET)
        block_end: Block end time (ET)

    Returns:
        dict with O, H, L, C, Volume or None if no data
    """
    if df is None or df.empty:
        return None

    # Filter bars within block time range
    mask = (df.index >= block_start) & (df.index < block_end)
    block_data = df[mask]

    if block_data.empty:
        return None

    # Calculate OHLC for the block
    open_price = float(block_data.iloc[0]['Open'])
    high_price = float(block_data['High'].max())
    low_price = float(block_data['Low'].min())
    close_price = float(block_data.iloc[-1]['Close'])
    volume = int(block_data['Volume'].sum()) if 'Volume' in block_data.columns else 0

    return {
        'open': round(open_price, 2),
        'high': round(high_price, 2),
        'low': round(low_price, 2),
        'close': round(close_price, 2),
        'volume': volume,
        'bar_count': len(block_data)
    }


@block_bp.route('/<ticker>', methods=['GET'])
def get_hourly_blocks(ticker: str):
    """
    Get 7-block hourly segmentation with OHLC data for each block

    Args:
        ticker: Ticker symbol (NQ=F, ES=F, etc.)

    Returns:
        JSON with:
        {
            "success": true,
            "ticker": "NQ=F",
            "current_price": 17245.50,
            "current_time_utc": "2025-11-16T15:45:28+00:00",
            "current_time_et": "2025-11-16T10:45:28-05:00",
            "current_hour": "10:00-11:00 ET",
            "current_block": 3,
            "blocks_completed": 2,
            "blocks_total": 7,
            "progress_percent": 28.6,
            "blocks": [
                {
                    "block_num": 1,
                    "start_time": "2025-11-16T10:00:00-05:00",
                    "end_time": "2025-11-16T10:08:34-05:00",
                    "is_complete": true,
                    "ohlc": {
                        "open": 17240.0,
                        "high": 17250.5,
                        "low": 17235.0,
                        "close": 17245.50,
                        "volume": 1234,
                        "bar_count": 8
                    }
                },
                ...7 blocks total
            ],
            "current_block": {
                "block_num": 3,
                "start_time": "2025-11-16T10:17:08-05:00",
                "end_time": "2025-11-16T10:25:42-05:00",
                "ohlc": {...}
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

        logger.info(f"Fetching hourly blocks for {ticker}")

        # Get current time
        current_time_utc = get_current_time_utc()
        current_time_et = ensure_et(current_time_utc)

        # Get current price
        current_price = LiveDataFetcher.get_current_price(ticker)
        if current_price is None:
            logger.warning(f"Failed to get current price for {ticker}")
            return jsonify({
                "success": False,
                "error": "Unable to fetch current price"
            }), 503

        # Fetch 1-minute data for the current day
        logger.info(f"Fetching 1m data for {ticker}")
        df_1m = LiveDataFetcher.fetch_data(ticker, interval='1m')

        if df_1m is None or df_1m.empty:
            logger.warning(f"No 1m data available for {ticker}")
            return jsonify({
                "success": False,
                "error": "Unable to fetch 1-minute data"
            }), 503

        # Calculate block boundaries
        blocks_info = calculate_block_boundaries(current_time_et)

        # Extract OHLC for each block
        blocks_data = []
        blocks_completed = 0
        current_block_num = None
        current_block_data = None

        for block_info in blocks_info:
            block_ohlc = extract_block_ohlc(
                df_1m,
                block_info['start_time'],
                block_info['end_time']
            )

            block_dict = {
                "block_num": block_info['block_num'],
                "start_time": block_info['start_time'].isoformat(),
                "end_time": block_info['end_time'].isoformat(),
                "is_complete": block_info['is_complete']
            }

            if block_ohlc:
                block_dict["ohlc"] = block_ohlc

            blocks_data.append(block_dict)

            if block_info['is_complete']:
                blocks_completed += 1
            elif current_block_num is None:
                current_block_num = block_info['block_num']
                current_block_data = block_dict

        # If no current block found (all complete), current is the last one
        if current_block_num is None:
            current_block_num = BLOCKS_PER_HOUR
            if blocks_data:
                current_block_data = blocks_data[-1]

        # Calculate progress
        progress_percent = round((blocks_completed / BLOCKS_PER_HOUR) * 100, 1)

        # Format current hour
        hour_start = current_time_et.replace(minute=0, second=0, microsecond=0)
        hour_end = (hour_start + timedelta(hours=1)).replace(second=0, microsecond=0)
        current_hour_str = f"{hour_start.strftime('%H:%M')}-{hour_end.strftime('%H:%M')} ET"

        return jsonify({
            "success": True,
            "ticker": ticker,
            "current_price": round(current_price, 2),
            "current_time_utc": current_time_utc.isoformat(),
            "current_time_et": current_time_et.isoformat(),
            "current_hour": current_hour_str,
            "current_block": current_block_num,
            "blocks_completed": blocks_completed,
            "blocks_total": BLOCKS_PER_HOUR,
            "progress_percent": progress_percent,
            "blocks": blocks_data,
            "current_block": current_block_data  # Add current block object for UI
        }), 200

    except Exception as e:
        logger.error(f"Error fetching hourly blocks for {ticker}: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"Failed to fetch hourly blocks: {str(e)}"
        }), 500


@block_bp.route('/<ticker>/current-block', methods=['GET'])
def get_current_block(ticker: str):
    """
    Get data for just the current block

    Returns:
        JSON with:
        {
            "success": true,
            "ticker": "NQ=F",
            "current_time_et": "2025-11-16T10:45:28-05:00",
            "current_block": 3,
            "block_start": "2025-11-16T10:17:08-05:00",
            "block_end": "2025-11-16T10:25:42-05:00",
            "start_time": "2025-11-16T10:17:08-05:00",
            "end_time": "2025-11-16T10:25:42-05:00",
            "ohlc": {...}
        }
    """
    try:
        current_time_utc = get_current_time_utc()
        current_time_et = ensure_et(current_time_utc)

        # Calculate which block we're in
        blocks_info = calculate_block_boundaries(current_time_et)
        current_block_info = None

        for block_info in blocks_info:
            if current_time_et >= block_info['start_time'] and current_time_et < block_info['end_time']:
                current_block_info = block_info
                break

        # If no block found, we're in the last one
        if current_block_info is None:
            current_block_info = blocks_info[-1]

        # Get 1m data
        df_1m = LiveDataFetcher.fetch_data(ticker, interval='1m')

        block_ohlc = extract_block_ohlc(
            df_1m,
            current_block_info['start_time'],
            current_block_info['end_time']
        )

        return jsonify({
            "success": True,
            "ticker": ticker,
            "current_time_et": current_time_et.isoformat(),
            "current_block": current_block_info['block_num'],
            "block_start": current_block_info['start_time'].isoformat(),
            "block_end": current_block_info['end_time'].isoformat(),
            "start_time": current_block_info['start_time'].isoformat(),
            "end_time": current_block_info['end_time'].isoformat(),
            "ohlc": block_ohlc if block_ohlc else None
        }), 200

    except Exception as e:
        logger.error(f"Error fetching current block: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to fetch current block"
        }), 500


@block_bp.route('/<ticker>/summary', methods=['GET'])
def get_blocks_summary(ticker: str):
    """
    Get summary view: current block with progress bar

    Returns:
        JSON with:
        {
            "success": true,
            "ticker": "NQ=F",
            "current_hour": "10:00-11:00 ET",
            "current_block": 3,
            "progress_percent": 28.6,
            "blocks_completed": 2,
            "blocks_total": 7,
            "time_in_current_block_percent": 65.2
        }
    """
    try:
        current_time_utc = get_current_time_utc()
        current_time_et = ensure_et(current_time_utc)

        # Calculate block boundaries
        blocks_info = calculate_block_boundaries(current_time_et)

        # Count completed blocks
        blocks_completed = sum(1 for b in blocks_info if b['is_complete'])

        # Find current block
        current_block = None
        current_block_info = None
        for block_info in blocks_info:
            if current_time_et >= block_info['start_time'] and current_time_et < block_info['end_time']:
                current_block = block_info['block_num']
                current_block_info = block_info
                break

        if current_block is None:
            current_block = BLOCKS_PER_HOUR
            current_block_info = blocks_info[-1]

        # Calculate time into current block
        time_in_block = (current_time_et - current_block_info['start_time']).total_seconds()
        block_duration = (current_block_info['end_time'] - current_block_info['start_time']).total_seconds()
        time_in_block_percent = round((time_in_block / block_duration) * 100, 1) if block_duration > 0 else 0

        # Format current hour
        hour_start = current_time_et.replace(minute=0, second=0, microsecond=0)
        hour_end = (hour_start + timedelta(hours=1)).replace(second=0, microsecond=0)
        current_hour_str = f"{hour_start.strftime('%H:%M')}-{hour_end.strftime('%H:%M')} ET"

        # Calculate overall progress
        progress_percent = round((blocks_completed / BLOCKS_PER_HOUR) * 100, 1)

        return jsonify({
            "success": True,
            "ticker": ticker,
            "current_hour": current_hour_str,
            "current_block": current_block,
            "progress_percent": progress_percent,
            "blocks_completed": blocks_completed,
            "blocks_total": BLOCKS_PER_HOUR,
            "time_in_current_block_percent": time_in_block_percent
        }), 200

    except Exception as e:
        logger.error(f"Error fetching blocks summary: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to fetch blocks summary"
        }), 500
