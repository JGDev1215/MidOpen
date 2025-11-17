"""
Market Status Service - Determine if futures markets are open/closed for NQ=F and ES=F

NQ=F and ES=F (CME Micro Futures) trading hours:
- Sunday 6:00 PM ET - Friday 5:00 PM ET
- Daily maintenance/rollover: 5:00 PM - 6:00 PM ET (market closed)
"""

import logging
from datetime import datetime, timedelta
import pytz
from enum import Enum
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# Timezone definitions
ET_TZ = pytz.timezone('America/New_York')
UTC_TZ = pytz.UTC


class MarketStatus(Enum):
    """Enum for market status"""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    MAINTENANCE = "MAINTENANCE"


class MarketStatusService:
    """
    Service to determine if futures markets (NQ=F, ES=F) are trading

    Hours: Sunday 6 PM ET - Friday 5 PM ET
    Maintenance: 5 PM - 6 PM ET daily (market closed for rollover)
    """

    # Market hours in ET timezone
    MARKET_OPEN_DAY = 6  # Sunday (0=Monday, 6=Sunday)
    MARKET_OPEN_HOUR = 18  # 6 PM ET
    MARKET_CLOSE_DAY = 4  # Friday (0=Monday, 4=Friday)
    MARKET_CLOSE_HOUR = 17  # 5 PM ET
    MAINTENANCE_START_HOUR = 17  # 5 PM ET
    MAINTENANCE_END_HOUR = 18  # 6 PM ET (next day or same day)

    @staticmethod
    def get_current_time_et() -> datetime:
        """Get current time in ET timezone (naive, ET aware)"""
        return datetime.now(ET_TZ)

    @classmethod
    def is_market_open(cls, ticker: str = "NQ=F", current_time_et: Optional[datetime] = None) -> bool:
        """
        Check if market is currently open for trading

        Args:
            ticker: Ticker symbol (NQ=F or ES=F)
            current_time_et: Time to check (default: now). Can be naive or timezone-aware.

        Returns:
            True if market is open, False otherwise
        """
        if current_time_et is None:
            current_time_et = cls.get_current_time_et()

        # Ensure timezone-aware ET
        if current_time_et.tzinfo is None:
            current_time_et = ET_TZ.localize(current_time_et)
        else:
            current_time_et = current_time_et.astimezone(ET_TZ)

        day_of_week = current_time_et.weekday()  # 0=Monday, 6=Sunday
        hour = current_time_et.hour
        minute = current_time_et.minute

        # Friday 5 PM ET or later (until Sunday 6 PM): CLOSED
        if day_of_week == 4 and (hour > 17 or (hour == 17 and minute >= 0)):
            return False

        # Saturday: CLOSED
        if day_of_week == 5:
            return False

        # Sunday before 6 PM ET: CLOSED
        if day_of_week == 6 and hour < 18:
            return False

        # Daily maintenance: 5 PM - 6 PM ET: CLOSED
        if hour == 17:
            return False

        # All other times (Sunday 6 PM - Friday 5 PM, excluding daily maintenance): OPEN
        return True

    @classmethod
    def get_market_status(cls, ticker: str = "NQ=F", current_time_et: Optional[datetime] = None) -> MarketStatus:
        """
        Get detailed market status

        Args:
            ticker: Ticker symbol
            current_time_et: Time to check (default: now)

        Returns:
            MarketStatus enum value
        """
        if current_time_et is None:
            current_time_et = cls.get_current_time_et()

        # Ensure timezone-aware ET
        if current_time_et.tzinfo is None:
            current_time_et = ET_TZ.localize(current_time_et)
        else:
            current_time_et = current_time_et.astimezone(ET_TZ)

        hour = current_time_et.hour

        # Check for maintenance window
        if hour == 17:  # 5 PM ET
            return MarketStatus.MAINTENANCE

        if cls.is_market_open(ticker, current_time_et):
            return MarketStatus.OPEN
        else:
            return MarketStatus.CLOSED

    @classmethod
    def get_next_event(cls, ticker: str = "NQ=F", current_time_et: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get time of next market event (open or close)

        Args:
            ticker: Ticker symbol
            current_time_et: Time to check (default: now)

        Returns:
            Dict with:
                - type: 'open' or 'close'
                - time_et: Next event time in ET
                - time_utc: Next event time in UTC
                - countdown_seconds: Seconds until event
        """
        if current_time_et is None:
            current_time_et = cls.get_current_time_et()

        # Ensure timezone-aware ET
        if current_time_et.tzinfo is None:
            current_time_et = ET_TZ.localize(current_time_et)
        else:
            current_time_et = current_time_et.astimezone(ET_TZ)

        day_of_week = current_time_et.weekday()
        hour = current_time_et.hour

        # Determine next event
        if cls.is_market_open(ticker, current_time_et):
            # Market is open, next event is CLOSE
            # Market closes Friday 5 PM ET

            if day_of_week < 4:  # Monday-Thursday
                # Close this Friday at 5 PM
                days_until_friday = 4 - day_of_week
                close_time = current_time_et.replace(hour=17, minute=0, second=0, microsecond=0)
                close_time = close_time + timedelta(days=days_until_friday)
            elif day_of_week == 4:  # Friday
                # Close today at 5 PM
                close_time = current_time_et.replace(hour=17, minute=0, second=0, microsecond=0)
                if close_time <= current_time_et:
                    # If already past 5 PM, next close is next Friday
                    close_time = close_time + timedelta(days=7)
            else:  # Saturday or Sunday
                # Next close is Friday of current week or next week
                if day_of_week == 6:  # Sunday
                    # Next Friday (5 days ahead)
                    close_time = current_time_et.replace(hour=17, minute=0, second=0, microsecond=0)
                    close_time = close_time + timedelta(days=5)
                else:  # Saturday
                    # Next Friday (6 days ahead)
                    close_time = current_time_et.replace(hour=17, minute=0, second=0, microsecond=0)
                    close_time = close_time + timedelta(days=6)

            event_type = "close"
            event_time = close_time

        else:
            # Market is closed, next event is OPEN
            # Market opens Sunday 6 PM ET

            if day_of_week < 6:  # Monday-Saturday
                # Open this Sunday at 6 PM
                days_until_sunday = 6 - day_of_week
                open_time = current_time_et.replace(hour=18, minute=0, second=0, microsecond=0)
                open_time = open_time + timedelta(days=days_until_sunday)
            else:  # Sunday
                if hour < 18:
                    # Open later today at 6 PM
                    open_time = current_time_et.replace(hour=18, minute=0, second=0, microsecond=0)
                else:
                    # Open next Sunday at 6 PM
                    open_time = current_time_et.replace(hour=18, minute=0, second=0, microsecond=0)
                    open_time = open_time + timedelta(days=7)

            event_type = "open"
            event_time = open_time

        # Calculate countdown
        countdown = event_time - current_time_et
        countdown_seconds = int(countdown.total_seconds())

        return {
            "type": event_type,
            "time_et": event_time.isoformat(),
            "time_utc": event_time.astimezone(UTC_TZ).isoformat(),
            "countdown_seconds": countdown_seconds,
            "countdown_display": cls._format_countdown(countdown_seconds)
        }

    @staticmethod
    def _format_countdown(seconds: int) -> str:
        """Format countdown in human-readable format"""
        if seconds < 0:
            return "0h 0m"

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60

        return f"{hours}h {minutes}m"

    @classmethod
    def get_market_info(cls, ticker: str = "NQ=F", current_time_et: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get comprehensive market information

        Args:
            ticker: Ticker symbol
            current_time_et: Time to check (default: now)

        Returns:
            Dict with complete market status information
        """
        if current_time_et is None:
            current_time_et = cls.get_current_time_et()

        # Ensure timezone-aware ET
        if current_time_et.tzinfo is None:
            current_time_et = ET_TZ.localize(current_time_et)
        else:
            current_time_et = current_time_et.astimezone(ET_TZ)

        status = cls.get_market_status(ticker, current_time_et)
        next_event = cls.get_next_event(ticker, current_time_et)

        return {
            "success": True,
            "ticker": ticker,
            "current_time_et": current_time_et.isoformat(),
            "current_time_utc": current_time_et.astimezone(UTC_TZ).isoformat(),
            "status": status.value,
            "is_open": status == MarketStatus.OPEN,
            "is_closed": status == MarketStatus.CLOSED,
            "is_maintenance": status == MarketStatus.MAINTENANCE,
            "next_event": next_event,
            "hours_of_operation": "Sunday 6 PM ET - Friday 5 PM ET",
            "daily_maintenance": "5 PM - 6 PM ET"
        }
