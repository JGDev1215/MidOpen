"""
Session Range Service - Calculate live and historical session ranges

Sessions for NQ=F/ES=F futures (all times in ET):
- Asian: 18:00 (6 PM) - 02:00 (2 AM)
- London: 03:00 (3 AM) - 06:00 (6 AM)
- NY AM: 08:30 (Market open) - 12:00 (Noon)
- NY PM: 14:30 (2:30 PM) - 16:00 (4 PM, close)
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from ..data.fetcher_live import LiveDataFetcher
from ..utils.timezone import get_current_time_utc, ensure_et, is_during_session, ET_TZ

logger = logging.getLogger(__name__)


class SessionRangeService:
    """
    Service to calculate current and previous day session ranges

    Supports: Asian, London, NY AM, NY PM sessions
    """

    # Session definitions (hour, minute tuples in ET)
    SESSIONS = {
        'asian': {
            'name': 'Asian',
            'display': 'Asian (18:00-02:00 ET)',
            'start_hour': 18,
            'start_min': 0,
            'end_hour': 2,
            'end_min': 0,
            'spans_midnight': True
        },
        'london': {
            'name': 'London',
            'display': 'London (03:00-06:00 ET)',
            'start_hour': 3,
            'start_min': 0,
            'end_hour': 6,
            'end_min': 0,
            'spans_midnight': False
        },
        'ny_am': {
            'name': 'NY AM',
            'display': 'NY AM (08:30-12:00)',
            'start_hour': 8,
            'start_min': 30,
            'end_hour': 12,
            'end_min': 0,
            'spans_midnight': False
        },
        'ny_pm': {
            'name': 'NY PM',
            'display': 'NY PM (14:30-16:00)',
            'start_hour': 14,
            'start_min': 30,
            'end_hour': 16,
            'end_min': 0,
            'spans_midnight': False
        }
    }

    @classmethod
    def get_current_session_ranges(
        cls,
        ticker: str = "NQ=F",
        current_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get current session ranges (high/low for each active or recent session)

        Args:
            ticker: Ticker symbol
            current_time: Reference time (default: now in UTC)

        Returns:
            Dict with current session ranges
        """
        if current_time is None:
            current_time = get_current_time_utc()

        current_time_et = ensure_et(current_time)
        today = current_time_et.date()

        try:
            # Fetch 5-minute data (good for session ranges)
            df_5m = LiveDataFetcher.fetch_data(ticker, interval='5m')

            if df_5m is None or df_5m.empty:
                logger.error(f"Failed to fetch 5m data for {ticker}")
                return {"error": "Unable to fetch market data"}

            ranges = {}

            for session_key, session_info in cls.SESSIONS.items():
                session_range = cls._calculate_session_range(
                    df_5m,
                    session_info,
                    today,
                    current_time_et,
                    is_previous=False
                )

                ranges[session_key] = {
                    "name": session_info['display'],
                    "high": session_range['high'],
                    "low": session_range['low'],
                    "range": session_range['range'],
                    "bars_in_session": session_range['bar_count'],
                    "is_active": session_range['is_active']
                }

            return {
                "success": True,
                "ticker": ticker,
                "current_time_utc": current_time.isoformat(),
                "current_time_et": current_time_et.isoformat(),
                "ranges": ranges
            }

        except Exception as e:
            logger.error(f"Error calculating current session ranges: {e}", exc_info=True)
            return {"error": f"Failed to calculate ranges: {str(e)}"}

    @classmethod
    def get_previous_day_session_ranges(
        cls,
        ticker: str = "NQ=F",
        current_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get previous day's session ranges

        Args:
            ticker: Ticker symbol
            current_time: Reference time (default: now in UTC)

        Returns:
            Dict with previous day's session ranges
        """
        if current_time is None:
            current_time = get_current_time_utc()

        current_time_et = ensure_et(current_time)
        prev_day = (current_time_et - timedelta(days=1)).date()

        try:
            # Fetch 5-minute data
            df_5m = LiveDataFetcher.fetch_data(ticker, interval='5m')

            if df_5m is None or df_5m.empty:
                logger.error(f"Failed to fetch 5m data for {ticker}")
                return {"error": "Unable to fetch market data"}

            ranges = {}

            for session_key, session_info in cls.SESSIONS.items():
                session_range = cls._calculate_session_range(
                    df_5m,
                    session_info,
                    prev_day,
                    current_time_et,
                    is_previous=True
                )

                ranges[session_key] = {
                    "name": session_info['display'],
                    "high": session_range['high'],
                    "low": session_range['low'],
                    "range": session_range['range'],
                    "bars_in_session": session_range['bar_count']
                }

            return {
                "success": True,
                "ticker": ticker,
                "date": prev_day.isoformat(),
                "ranges": ranges
            }

        except Exception as e:
            logger.error(f"Error calculating previous day ranges: {e}", exc_info=True)
            return {"error": f"Failed to calculate ranges: {str(e)}"}

    @classmethod
    def get_all_session_ranges(
        cls,
        ticker: str = "NQ=F",
        current_price: Optional[float] = None,
        current_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get current and previous day session ranges with current price comparison

        Args:
            ticker: Ticker symbol
            current_price: Current market price (fetched if not provided)
            current_time: Reference time (default: now in UTC)

        Returns:
            Dict with both current and previous session ranges
        """
        current_ranges = cls.get_current_session_ranges(ticker, current_time)
        previous_ranges = cls.get_previous_day_session_ranges(ticker, current_time)

        if "error" in current_ranges or "error" in previous_ranges:
            return {"error": "Failed to calculate session ranges"}

        if current_price is None:
            current_price = LiveDataFetcher.get_current_price(ticker)

        # Add price comparison
        if current_price is not None:
            for session_key in current_ranges["ranges"]:
                range_data = current_ranges["ranges"][session_key]
                if range_data["high"] and range_data["low"]:
                    range_data["current_price"] = round(current_price, 2)
                    range_data["within_range"] = range_data["low"] <= current_price <= range_data["high"]
                    range_data["above_range"] = current_price > range_data["high"]
                    range_data["below_range"] = current_price < range_data["low"]

        return {
            "success": True,
            "ticker": ticker,
            "current_price": round(current_price, 2) if current_price else None,
            "current_session_ranges": current_ranges.get("ranges", {}),
            "previous_day_session_ranges": previous_ranges.get("ranges", {})
        }

    @staticmethod
    def _calculate_session_range(
        df,
        session_info: Dict,
        target_date,
        current_time_et,
        is_previous: bool = False
    ) -> Dict[str, Any]:
        """
        Calculate high/low for a specific session on a target date

        Args:
            df: 5-minute OHLCV DataFrame (index in ET timezone)
            session_info: Session configuration dict
            target_date: Date to calculate for (as date object)
            current_time_et: Current time in ET (for is_active determination)
            is_previous: If True, this is previous day's range

        Returns:
            Dict with high, low, range, bar_count, is_active
        """
        from datetime import datetime as dt_class

        # DETERMINE THE CORRECT DATE RANGES FOR START AND END
        # For sessions that span midnight, session starts on previous day
        if session_info['spans_midnight'] and session_info['end_hour'] < session_info['start_hour']:
            # Session spans midnight: starts yesterday, ends today
            session_start_date = target_date - timedelta(days=1)  # FIX: Go back one day for start
            session_end_date = target_date  # End is the target date
        else:
            # Normal same-day session
            session_start_date = target_date
            session_end_date = target_date

        # Create session start time
        session_start = dt_class.combine(session_start_date, dt_class.min.time())
        session_start = session_start.replace(
            hour=session_info['start_hour'],
            minute=session_info['start_min']
        )
        # Localize to ET timezone
        session_start = ET_TZ.localize(session_start)

        # Create session end time
        session_end = dt_class.combine(session_end_date, dt_class.min.time())
        session_end = session_end.replace(
            hour=session_info['end_hour'],
            minute=session_info['end_min']
        )

        # Handle sessions spanning midnight (add 1 day to end if needed)
        if session_info['spans_midnight'] and session_info['end_hour'] < session_info['start_hour']:
            session_end = session_end + timedelta(days=1)

        # Localize to ET timezone
        session_end = ET_TZ.localize(session_end)

        # FILTER DATA WITH CORRECTED DATE RANGE
        # FIX: Use the correct date range (start_date and end_date, not target_date and target_date+1)
        session_data = df[
            (df.index.date == session_start_date) |  # FIX: Use session_start_date
            (df.index.date == session_end_date)      # FIX: Use session_end_date
        ]

        # Filter by time range
        session_data = session_data[
            (session_data.index >= session_start) & (session_data.index < session_end)
        ]

        if session_data.empty:
            return {
                "high": None,
                "low": None,
                "range": None,
                "bar_count": 0,
                "is_active": False
            }

        high = float(session_data['High'].max())
        low = float(session_data['Low'].min())
        range_val = high - low

        # Determine if session is active (only for current day, not previous)
        is_active = False
        if not is_previous:
            # Check if current time is within session
            # Both session_start and session_end are already timezone-aware (ET)
            # current_time_et is also timezone-aware (ET)
            is_active = session_start <= current_time_et < session_end

        return {
            "high": round(high, 2),
            "low": round(low, 2),
            "range": round(range_val, 2),
            "bar_count": len(session_data),
            "is_active": is_active
        }
