"""
Refresh Status Service - Manages 602-second countdown timer state
Provides real-time status for dashboard refresh cycles
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import pytz

logger = logging.getLogger(__name__)

# Refresh interval configuration
REFRESH_INTERVAL_SECONDS = 602  # 10 minutes 2 seconds

# Color thresholds (seconds remaining)
GREEN_THRESHOLD = 200   # 602-200 seconds = fresh data
ORANGE_THRESHOLD = 60   # 200-60 seconds = mild staleness
# RED = 60-0 seconds = refreshing soon


class RefreshStatusService:
    """
    Service to calculate countdown timer status for dashboard

    Tracks when data was last refreshed and calculates:
    - Seconds until next refresh
    - Color status (GREEN/ORANGE/RED)
    - Last/Next update timestamps
    """

    # Global timestamp tracking (in-memory, persists across requests)
    _last_refresh_time: Optional[float] = None
    _initialization_time: float = time.time()

    @classmethod
    def initialize(cls):
        """Initialize refresh tracking on application start"""
        cls._initialization_time = time.time()
        cls._last_refresh_time = cls._initialization_time
        logger.info(f"Refresh status initialized at {datetime.fromtimestamp(cls._initialization_time)}")

    @classmethod
    def mark_refresh(cls):
        """Mark that a refresh has occurred (called after data fetch)"""
        cls._last_refresh_time = time.time()
        logger.debug(f"Refresh marked at {datetime.fromtimestamp(cls._last_refresh_time)}")

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        """
        Get current refresh status with countdown information

        Returns:
            {
                "success": true,
                "seconds_remaining": 425,
                "seconds_elapsed": 177,
                "total_interval": 602,
                "color_status": "GREEN",
                "color_hex": "#10b981",
                "color_name": "Fresh Data",
                "progress_percent": 29.4,
                "last_refresh_time": "2025-11-17T10:30:00-05:00",
                "next_refresh_time": "2025-11-17T10:40:02-05:00",
                "last_refresh_timestamp": 1700237400,
                "next_refresh_timestamp": 1700238002,
                "formatted_countdown": "07:05",
                "is_overdue": false
            }
        """
        # Initialize if needed
        if cls._last_refresh_time is None:
            cls.initialize()

        current_time = time.time()
        time_since_last_refresh = current_time - cls._last_refresh_time

        # Calculate seconds remaining (can be negative if overdue)
        seconds_remaining = REFRESH_INTERVAL_SECONDS - time_since_last_refresh
        seconds_elapsed = time_since_last_refresh

        # Determine color status based on thresholds
        if seconds_remaining > GREEN_THRESHOLD:
            color_status = "GREEN"
            color_hex = "#10b981"  # Emerald green
            color_name = "Fresh Data"
        elif seconds_remaining > ORANGE_THRESHOLD:
            color_status = "ORANGE"
            color_hex = "#f59e0b"  # Amber orange
            color_name = "Aging Data"
        else:
            color_status = "RED"
            color_hex = "#ef4444"  # Red
            color_name = "Stale Data"

        # Handle overdue case
        is_overdue = seconds_remaining < 0
        if is_overdue:
            color_status = "RED"
            color_hex = "#dc2626"  # Darker red
            color_name = "Refreshing"

        # Calculate progress percentage (0-100)
        progress_percent = (seconds_elapsed / REFRESH_INTERVAL_SECONDS) * 100
        progress_percent = min(100, max(0, progress_percent))

        # Convert timestamps to ET datetime
        et_tz = pytz.timezone('America/New_York')
        last_refresh_dt = datetime.fromtimestamp(cls._last_refresh_time, tz=et_tz)
        next_refresh_dt = datetime.fromtimestamp(cls._last_refresh_time + REFRESH_INTERVAL_SECONDS, tz=et_tz)

        return {
            "success": True,
            "seconds_remaining": max(0, int(seconds_remaining)),
            "seconds_elapsed": int(seconds_elapsed),
            "total_interval": REFRESH_INTERVAL_SECONDS,
            "color_status": color_status,
            "color_hex": color_hex,
            "color_name": color_name,
            "progress_percent": round(progress_percent, 1),
            "last_refresh_time": last_refresh_dt.isoformat(),
            "next_refresh_time": next_refresh_dt.isoformat(),
            "last_refresh_timestamp": int(cls._last_refresh_time),
            "next_refresh_timestamp": int(cls._last_refresh_time + REFRESH_INTERVAL_SECONDS),
            "is_overdue": is_overdue,
            "formatted_countdown": cls._format_countdown(max(0, int(seconds_remaining)))
        }

    @staticmethod
    def _format_countdown(seconds: int) -> str:
        """
        Format seconds into human-readable countdown

        Args:
            seconds: Seconds remaining

        Returns:
            Formatted string like "10:02" (MM:SS)
        """
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes:02d}:{secs:02d}"

    @classmethod
    def reset_timer(cls):
        """Reset the timer (useful for testing or manual triggers)"""
        cls._last_refresh_time = time.time()
        logger.info("Refresh timer manually reset")
