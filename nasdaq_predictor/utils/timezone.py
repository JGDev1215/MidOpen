"""
Timezone utilities for converting between UTC and ET (America/New_York)

All market calculations are done in ET timezone:
- Reference levels: ET times
- Session ranges: ET boundaries
- Block segmentation: ET time windows
"""

import logging
import pytz
from datetime import datetime, timedelta
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Timezone definitions
ET_TZ = pytz.timezone('America/New_York')
UTC_TZ = pytz.UTC
CST_TZ = pytz.timezone('America/Chicago')  # CME futures exchange timezone


class TimezoneError(Exception):
    """Raised when timezone conversion fails"""
    pass


def ensure_et(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Ensure datetime is in ET timezone

    Args:
        dt: Datetime object (naive or timezone-aware)

    Returns:
        Datetime in ET timezone (aware), or None if input is None

    Raises:
        TimezoneError: If conversion fails
    """
    if dt is None:
        return None

    try:
        if dt.tzinfo is None:
            # Naive datetime - assume UTC
            dt = UTC_TZ.localize(dt)

        # Convert to ET
        return dt.astimezone(ET_TZ)
    except Exception as e:
        raise TimezoneError(f"Failed to convert to ET: {e}")


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Ensure datetime is in UTC timezone

    Args:
        dt: Datetime object (naive or timezone-aware)

    Returns:
        Datetime in UTC timezone (aware), or None if input is None

    Raises:
        TimezoneError: If conversion fails
    """
    if dt is None:
        return None

    try:
        if dt.tzinfo is None:
            # Naive datetime - assume UTC
            dt = UTC_TZ.localize(dt)

        # Convert to UTC
        return dt.astimezone(UTC_TZ)
    except Exception as e:
        raise TimezoneError(f"Failed to convert to UTC: {e}")


def ensure_cst(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Ensure datetime is in CST (CME exchange) timezone

    Args:
        dt: Datetime object (naive or timezone-aware)

    Returns:
        Datetime in CST timezone (aware), or None if input is None
    """
    if dt is None:
        return None

    if dt.tzinfo is None:
        dt = UTC_TZ.localize(dt)

    return dt.astimezone(CST_TZ)


def get_et_midnight(current_time: Optional[datetime] = None) -> datetime:
    """
    Get midnight ET for the current date

    Args:
        current_time: Reference time (default: now in UTC)

    Returns:
        Midnight ET (00:00:00) as UTC datetime
    """
    if current_time is None:
        current_time = datetime.utcnow()

    # Ensure UTC
    current_time_et = ensure_et(current_time)

    # Get midnight ET for the current date
    midnight_et = current_time_et.replace(hour=0, minute=0, second=0, microsecond=0)

    # Convert back to UTC for storage
    return midnight_et.astimezone(UTC_TZ)


def get_et_time(year: int, month: int, day: int, hour: int = 0, minute: int = 0, second: int = 0) -> datetime:
    """
    Create an ET datetime and return as UTC

    Args:
        year, month, day: Date components
        hour, minute, second: Time components (in ET)

    Returns:
        UTC datetime
    """
    et_dt = ET_TZ.localize(datetime(year, month, day, hour, minute, second))
    return et_dt.astimezone(UTC_TZ)


def get_candle_open_time(current_time: Optional[datetime], minutes: int) -> datetime:
    """
    Get the opening time of the current candle for a given interval

    Args:
        current_time: Reference time (default: now in UTC)
        minutes: Candle interval in minutes (60 for hourly, 30 for 30-min, etc.)

    Returns:
        Opening time of current candle in UTC
    """
    if current_time is None:
        current_time = datetime.utcnow()

    # Ensure UTC
    current_time = ensure_utc(current_time)

    # Convert to ET for calculation
    current_time_et = current_time.astimezone(ET_TZ)

    # Calculate minutes since midnight
    seconds_since_midnight = (current_time_et.hour * 3600 +
                             current_time_et.minute * 60 +
                             current_time_et.second)
    minutes_since_midnight = seconds_since_midnight // 60

    # Find the start of the current candle
    candle_start_minutes = (minutes_since_midnight // minutes) * minutes

    # Create the candle open time
    candle_open_et = current_time_et.replace(hour=0, minute=0, second=0, microsecond=0)
    candle_open_et = candle_open_et + timedelta(minutes=candle_start_minutes)

    # Convert back to UTC
    return candle_open_et.astimezone(UTC_TZ)


def get_week_start(current_time: Optional[datetime] = None) -> datetime:
    """
    Get the start of the trading week (Monday 00:00 ET)

    Args:
        current_time: Reference time (default: now in UTC)

    Returns:
        Monday 00:00 ET as UTC datetime
    """
    if current_time is None:
        current_time = datetime.utcnow()

    current_time_et = ensure_et(current_time)

    # Calculate days to subtract to get to Monday (weekday() = 0 for Monday)
    days_to_monday = current_time_et.weekday()

    # Get Monday at midnight ET
    monday_et = current_time_et.replace(hour=0, minute=0, second=0, microsecond=0)
    monday_et = monday_et - timedelta(days=days_to_monday)

    # Convert to UTC
    return monday_et.astimezone(UTC_TZ)


def get_month_start(current_time: Optional[datetime] = None) -> datetime:
    """
    Get the start of the calendar month (1st day at 00:00 ET)

    Args:
        current_time: Reference time (default: now in UTC)

    Returns:
        1st of month at 00:00 ET as UTC datetime
    """
    if current_time is None:
        current_time = datetime.utcnow()

    current_time_et = ensure_et(current_time)

    # Get 1st day of month at midnight ET
    month_start_et = current_time_et.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Convert to UTC
    return month_start_et.astimezone(UTC_TZ)


def get_7am_ny_timestamp(current_time: Optional[datetime] = None) -> datetime:
    """
    Get 7:00 AM ET timestamp

    Args:
        current_time: Reference time (default: now in UTC)

    Returns:
        7:00 AM ET as UTC datetime
    """
    if current_time is None:
        current_time = datetime.utcnow()

    current_time_et = ensure_et(current_time)

    # Get 7 AM ET for current date
    time_7am_et = current_time_et.replace(hour=7, minute=0, second=0, microsecond=0)

    # Convert to UTC
    return time_7am_et.astimezone(UTC_TZ)


def get_830am_ny_timestamp(current_time: Optional[datetime] = None) -> datetime:
    """
    Get 8:30 AM ET timestamp (NYSE market open)

    Args:
        current_time: Reference time (default: now in UTC)

    Returns:
        8:30 AM ET as UTC datetime
    """
    if current_time is None:
        current_time = datetime.utcnow()

    current_time_et = ensure_et(current_time)

    # Get 8:30 AM ET for current date
    time_830am_et = current_time_et.replace(hour=8, minute=30, second=0, microsecond=0)

    # Convert to UTC
    return time_830am_et.astimezone(UTC_TZ)


def get_session_time_range(session_name: str, current_time: Optional[datetime] = None) -> Tuple[datetime, datetime]:
    """
    Get the start and end times for a trading session

    Args:
        session_name: Name of session ('asian', 'london', 'ny_am', 'ny_pm')
        current_time: Reference time (default: now in UTC)

    Returns:
        Tuple of (start_time_utc, end_time_utc)

    Raises:
        ValueError: If session_name is invalid
    """
    if current_time is None:
        current_time = datetime.utcnow()

    current_time_et = ensure_et(current_time)

    # Session times in ET
    sessions = {
        'asian': (18, 0, 2, 0),      # 6 PM - 2 AM ET
        'london': (3, 0, 6, 0),       # 3 AM - 6 AM ET
        'ny_am': (8, 30, 12, 0),      # 8:30 AM - 12 PM ET
        'ny_pm': (14, 30, 16, 0)      # 2:30 PM - 4 PM ET
    }

    if session_name.lower() not in sessions:
        raise ValueError(f"Unknown session: {session_name}. Must be one of {list(sessions.keys())}")

    start_hour, start_min, end_hour, end_min = sessions[session_name.lower()]

    # Handle sessions that span midnight
    session_start = current_time_et.replace(hour=start_hour, minute=start_min, second=0, microsecond=0)
    session_end = current_time_et.replace(hour=end_hour, minute=end_min, second=0, microsecond=0)

    # If Asian session (spans into next day)
    if session_name.lower() == 'asian' and end_hour < start_hour:
        if current_time_et.hour < start_hour:
            # Before 6 PM, so session started yesterday
            session_start = session_start - timedelta(days=1)
        else:
            # After 6 PM, so session will end tomorrow
            session_end = session_end + timedelta(days=1)

    return (session_start.astimezone(UTC_TZ), session_end.astimezone(UTC_TZ))


def is_during_session(session_name: str, current_time: Optional[datetime] = None) -> bool:
    """
    Check if current time is during a specific trading session

    Args:
        session_name: Name of session
        current_time: Reference time (default: now in UTC)

    Returns:
        True if during session, False otherwise
    """
    if current_time is None:
        current_time = datetime.utcnow()

    current_time = ensure_utc(current_time)
    session_start, session_end = get_session_time_range(session_name, current_time)

    return session_start <= current_time <= session_end


def format_et_time(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S %Z") -> str:
    """
    Format a datetime in ET timezone

    Args:
        dt: Datetime to format (any timezone)
        format_str: Format string (default: YYYY-MM-DD HH:MM:SS TZ)

    Returns:
        Formatted string in ET
    """
    dt_et = ensure_et(dt)
    return dt_et.strftime(format_str)


def get_current_time_et() -> datetime:
    """Get current time in ET timezone (aware)"""
    return datetime.now(ET_TZ)


def get_current_time_utc() -> datetime:
    """Get current time in UTC timezone (aware)"""
    return datetime.utcnow().replace(tzinfo=UTC_TZ)
