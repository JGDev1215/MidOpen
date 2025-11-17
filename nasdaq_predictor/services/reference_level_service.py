"""
Reference Level Service - Calculate all 16 reference levels on-demand

Wraps existing reference_levels.py calculations and adds:
- Price comparison logic (Above/Near/Below)
- Signal generation from reference levels
- Caching for performance (optional)
- API-ready response formatting
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..data.fetcher_live import LiveDataFetcher
from ..analysis.reference_levels import (
    calculate_daily_open,
    calculate_hourly_open,
    calculate_4hourly_open,
    calculate_30min_open,
    calculate_15min_open,
    calculate_weekly_open,
    calculate_monthly_open,
    calculate_7am_open,
    calculate_830am_open,
    calculate_prev_week_open,
    calculate_prev_day_high_low,
    calculate_week_high_low,
    calculate_all_reference_levels
)
from ..utils.timezone import get_current_time_utc

logger = logging.getLogger(__name__)


class PriceProximity:
    """Enum-like class for price proximity status"""
    ABOVE = "ABOVE"
    NEAR = "NEAR"
    BELOW = "BELOW"


class ReferenceLevelService:
    """
    Service to calculate all 16 reference levels and format for API/UI

    Reference levels included:
    1. Weekly Open (Monday 00:00 ET)
    2. Monthly Open (1st day 00:00 ET)
    3. Midnight Open (00:00 ET daily)
    4. NY Open (08:30 ET)
    5. Pre-NY Open (07:00 ET)
    6. 4H Open (current 4-hour candle)
    7. 2H Open (current 2-hour candle)
    8. 1H Open (current hourly candle)
    9. Previous Hour Open
    10. 15min Open
    11. Previous Day High
    12. Previous Day Low
    13. Previous Week High
    14. Previous Week Low
    15. Weekly High (running)
    16. Weekly Low (running)
    """

    # Proximity threshold: price within this % is considered "NEAR"
    NEAR_THRESHOLD_PCT = 0.10  # 0.10% = 10 basis points

    @classmethod
    def calculate_all_levels(
        cls,
        ticker: str = "NQ=F",
        current_price: Optional[float] = None,
        current_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Calculate all 16 reference levels and format for API response

        Args:
            ticker: Ticker symbol (default: NQ=F)
            current_price: Current market price (fetched if not provided)
            current_time: Reference time (default: now in UTC)

        Returns:
            Dict with:
                - current_price: Market price
                - reference_levels: All 16 levels with calculations
                - signals: Buy/sell signals from each level
                - closest_level: Nearest reference level to current price
        """
        if current_time is None:
            current_time = get_current_time_utc()

        if current_price is None:
            current_price = cls._get_current_price(ticker)
            if current_price is None:
                logger.error(f"Failed to get current price for {ticker}")
                return {"error": "Unable to fetch current price"}

        logger.info(f"Calculating reference levels for {ticker} at price {current_price}")

        try:
            # Fetch all required OHLC data
            hourly_data = LiveDataFetcher.fetch_data(ticker, interval='1h')
            daily_data = LiveDataFetcher.fetch_data(ticker, interval='1d')
            minute_data = LiveDataFetcher.fetch_data(ticker, interval='1m')
            weekly_data = LiveDataFetcher.fetch_data(ticker, interval='1wk')

            if hourly_data is None or daily_data is None:
                logger.error(f"Failed to fetch data for {ticker}")
                return {"error": "Unable to fetch market data"}

            # Calculate all 16 levels
            levels = {
                "weekly_open": cls._safe_calculate(
                    calculate_weekly_open, hourly_data, current_time, "Weekly Open"
                ),
                "monthly_open": cls._safe_calculate(
                    calculate_monthly_open, hourly_data, current_time, "Monthly Open"
                ),
                "daily_open_midnight": cls._safe_calculate(
                    calculate_daily_open, hourly_data, current_time, "Midnight Open"
                ),
                "ny_open_0830": cls._safe_calculate(
                    calculate_830am_open, hourly_data, current_time, "NY Open (08:30)"
                ),
                "ny_open_0700": cls._safe_calculate(
                    calculate_7am_open, hourly_data, current_time, "Pre-NY Open (07:00)"
                ),
                "four_hour_open": cls._safe_calculate(
                    calculate_4hourly_open, hourly_data, current_time, "4H Open"
                ),
                "two_hour_open": cls._safe_calculate(
                    calculate_2hourly_open, hourly_data, current_time, "2H Open"
                ),
                "hourly_open": cls._safe_calculate(
                    calculate_hourly_open, hourly_data, current_time, "1H Open"
                ),
                "previous_hourly_open": cls._safe_calculate(
                    calculate_previous_hourly_open, hourly_data, current_time, "Previous Hour Open"
                ),
                "fifteen_min_open": cls._safe_calculate(
                    calculate_15min_open, minute_data, current_time, "15min Open"
                ) if minute_data is not None else None,
                "previous_day_high": cls._safe_calculate(
                    lambda d: calculate_prev_day_high_low(d)[0], daily_data, "Previous Day High"
                ),
                "previous_day_low": cls._safe_calculate(
                    lambda d: calculate_prev_day_high_low(d)[1], daily_data, "Previous Day Low"
                ),
                "previous_week_high": cls._safe_calculate(
                    calculate_prev_week_high, daily_data, current_time, "Previous Week High"
                ),
                "previous_week_low": cls._safe_calculate(
                    calculate_prev_week_low, daily_data, current_time, "Previous Week Low"
                ),
                "weekly_high": cls._safe_calculate(
                    lambda d: calculate_week_high_low(d)[0], daily_data, "Weekly High"
                ),
                "weekly_low": cls._safe_calculate(
                    lambda d: calculate_week_high_low(d)[1], daily_data, "Weekly Low"
                )
            }

            # Calculate signals and format response
            signals = {}
            closest_level = None
            closest_distance = float('inf')

            for level_key, level_price in levels.items():
                if level_price is None:
                    signals[level_key] = None
                    continue

                # Calculate proximity and signal
                proximity, signal = cls._calculate_signal(current_price, level_price)
                distance = current_price - level_price
                distance_pct = (distance / level_price) * 100 if level_price != 0 else 0

                signals[level_key] = {
                    "price": round(level_price, 2),
                    "distance": round(distance, 2),
                    "distance_pct": round(distance_pct, 3),
                    "proximity": proximity,
                    "signal": signal
                }

                # Track closest level
                abs_distance = abs(distance)
                if abs_distance < closest_distance:
                    closest_distance = abs_distance
                    closest_level = {
                        "level": level_key,
                        "price": round(level_price, 2),
                        "distance": round(distance, 2),
                        "proximity": proximity
                    }

            return {
                "success": True,
                "ticker": ticker,
                "current_price": round(current_price, 2),
                "current_time_utc": current_time.isoformat(),
                "reference_levels": levels,
                "signals": signals,
                "closest_level": closest_level
            }

        except Exception as e:
            logger.error(f"Error calculating reference levels: {e}", exc_info=True)
            return {"error": f"Failed to calculate reference levels: {str(e)}"}

    @staticmethod
    def _get_current_price(ticker: str) -> Optional[float]:
        """Get current price from yfinance"""
        return LiveDataFetcher.get_current_price(ticker)

    @staticmethod
    def _safe_calculate(func, *args, **kwargs) -> Optional[float]:
        """Safely call a calculation function, returning None on error"""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            level_name = kwargs.get("level_name", str(func.__name__))
            logger.debug(f"Error calculating {level_name}: {e}")
            return None

    @classmethod
    def _calculate_signal(cls, current_price: float, reference_level: float) -> tuple[str, int]:
        """
        Calculate proximity and signal for a reference level

        Args:
            current_price: Current market price
            reference_level: Reference level price

        Returns:
            Tuple of (proximity: "ABOVE"/"NEAR"/"BELOW", signal: 1/-1/0)
        """
        distance = current_price - reference_level
        distance_pct = abs((distance / reference_level) * 100) if reference_level != 0 else 0

        if distance_pct < cls.NEAR_THRESHOLD_PCT:
            # Price is near reference level
            proximity = PriceProximity.NEAR
            signal = 0  # Neutral signal
        elif distance > 0:
            # Price is above reference level
            proximity = PriceProximity.ABOVE
            signal = 1  # Bullish signal
        else:
            # Price is below reference level
            proximity = PriceProximity.BELOW
            signal = -1  # Bearish signal

        return proximity, signal

    @classmethod
    def get_level_summary(
        cls,
        ticker: str = "NQ=F",
        current_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Get a summary of key reference levels (for UI display)

        Returns only the most important levels for dashboard display

        Args:
            ticker: Ticker symbol
            current_price: Current price (fetched if not provided)

        Returns:
            Dict with key levels formatted for UI
        """
        all_levels = cls.calculate_all_levels(ticker, current_price)

        if "error" in all_levels:
            return all_levels

        # Extract key levels for display
        key_levels = [
            "weekly_open",
            "daily_open_midnight",
            "ny_open_0830",
            "hourly_open",
            "previous_day_high",
            "previous_day_low",
            "weekly_high",
            "weekly_low"
        ]

        summary = {
            "current_price": all_levels["current_price"],
            "current_time": all_levels["current_time_utc"],
            "levels": {}
        }

        for level_key in key_levels:
            if level_key in all_levels["signals"]:
                summary["levels"][level_key] = all_levels["signals"][level_key]

        return summary


# Helper functions for calculations not in reference_levels.py
def calculate_2hourly_open(hourly_hist, current_time):
    """Calculate 2-hourly open from hourly data"""
    from ..utils.timezone import get_candle_open_time
    candle_2h_time = get_candle_open_time(current_time, 120)
    two_hourly_data = hourly_hist[hourly_hist.index >= candle_2h_time]

    if not two_hourly_data.empty:
        return two_hourly_data['Open'].iloc[0]

    nearby_data = hourly_hist[hourly_hist.index <= candle_2h_time]
    if not nearby_data.empty:
        return nearby_data['Open'].iloc[-1]

    return None


def calculate_previous_hourly_open(hourly_hist, current_time):
    """Calculate previous hour's open"""
    from ..utils.timezone import get_candle_open_time
    from datetime import timedelta

    candle_1h_time = get_candle_open_time(current_time, 60)
    prev_1h_time = candle_1h_time - timedelta(hours=1)

    prev_hourly_data = hourly_hist[
        (hourly_hist.index >= prev_1h_time) & (hourly_hist.index < candle_1h_time)
    ]

    if not prev_hourly_data.empty:
        return prev_hourly_data['Open'].iloc[0]
    return None


def calculate_prev_week_high(daily_hist, current_time):
    """Calculate previous week's high"""
    from ..utils.timezone import get_week_start
    from datetime import timedelta

    current_week_start = get_week_start(current_time)
    prev_week_start = current_week_start - timedelta(days=7)
    prev_week_data = daily_hist[(daily_hist.index >= prev_week_start) & (daily_hist.index < current_week_start)]

    if not prev_week_data.empty:
        return prev_week_data['High'].max()
    return None


def calculate_prev_week_low(daily_hist, current_time):
    """Calculate previous week's low"""
    from ..utils.timezone import get_week_start
    from datetime import timedelta

    current_week_start = get_week_start(current_time)
    prev_week_start = current_week_start - timedelta(days=7)
    prev_week_data = daily_hist[(daily_hist.index >= prev_week_start) & (daily_hist.index < current_week_start)]

    if not prev_week_data.empty:
        return prev_week_data['Low'].min()
    return None
