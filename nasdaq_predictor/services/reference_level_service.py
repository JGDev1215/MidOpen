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
    calculate_2hourly_open,
    calculate_30min_open,
    calculate_15min_open,
    calculate_weekly_open,
    calculate_monthly_open,
    calculate_7am_open,
    calculate_830am_open,
    calculate_previous_hourly_open,
    calculate_prev_week_open,
    calculate_prev_day_high_low,
    calculate_prev_week_high,
    calculate_prev_week_low,
    calculate_week_high_low,
    calculate_all_reference_levels
)
from ..utils.timezone import get_current_time_utc, ensure_et

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
            # Convert to ET for time-based calculations
            current_time_et = ensure_et(current_time)
            
            # Fetch all required OHLC data
            hourly_data = LiveDataFetcher.fetch_data(ticker, interval='1h')
            daily_data = LiveDataFetcher.fetch_data(ticker, interval='1d')
            minute_data = LiveDataFetcher.fetch_data(ticker, interval='1m')

            if hourly_data is None or daily_data is None:
                logger.error(f"Failed to fetch data for {ticker}")
                return {"error": "Unable to fetch market data"}

            # Calculate all 16 levels
            levels = {
                "weekly_open": cls._safe_calculate(
                    calculate_weekly_open, hourly_data, current_time_et
                ),
                "monthly_open": cls._safe_calculate(
                    calculate_monthly_open, hourly_data, current_time_et
                ),
                "daily_open_midnight": cls._safe_calculate(
                    calculate_daily_open, hourly_data, current_time_et
                ),
                "ny_open_0830": cls._safe_calculate(
                    calculate_830am_open, hourly_data, current_time_et
                ),
                "ny_open_0700": cls._safe_calculate(
                    calculate_7am_open, hourly_data, current_time_et
                ),
                "four_hour_open": cls._safe_calculate(
                    calculate_4hourly_open, hourly_data
                ),
                "two_hour_open": cls._safe_calculate(
                    calculate_2hourly_open, hourly_data
                ),
                "hourly_open": cls._safe_calculate(
                    calculate_hourly_open, hourly_data
                ),
                "previous_hourly_open": cls._safe_calculate(
                    calculate_previous_hourly_open, hourly_data, current_time_et
                ),
                "fifteen_min_open": cls._safe_calculate(
                    calculate_15min_open, minute_data
                ) if minute_data is not None else None,
                "previous_day_high": cls._safe_calculate(
                    lambda d: calculate_prev_day_high_low(d)[0], daily_data
                ),
                "previous_day_low": cls._safe_calculate(
                    lambda d: calculate_prev_day_high_low(d)[1], daily_data
                ),
                "previous_week_high": cls._safe_calculate(
                    calculate_prev_week_high, daily_data
                ),
                "previous_week_low": cls._safe_calculate(
                    calculate_prev_week_low, daily_data
                ),
                "weekly_high": cls._safe_calculate(
                    lambda d: calculate_week_high_low(d)[0], daily_data
                ),
                "weekly_low": cls._safe_calculate(
                    lambda d: calculate_week_high_low(d)[1], daily_data
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
        """Get current price from yfinance or mock data"""
        return LiveDataFetcher.get_current_price(ticker)

    @staticmethod
    def _safe_calculate(func, *args) -> Optional[float]:
        """Safely call a calculation function, returning None on error"""
        try:
            return func(*args)
        except Exception as e:
            logger.debug(f"Error calculating {func.__name__}: {e}")
            return None

    @classmethod
    def _calculate_signal(cls, current_price: float, reference_level: float) -> tuple:
        """
        Calculate proximity and signal for a reference level

        Args:
            current_price: Current market price
            reference_level: Reference level price

        Returns:
            Tuple of (proximity: "ABOVE"/"NEAR"/"BELOW", signal: 1/-1/0)
        """
        if reference_level is None or reference_level == 0:
            return PriceProximity.NEAR, 0
            
        distance = current_price - reference_level
        distance_pct = abs((distance / reference_level) * 100)

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
        Get summary of key reference levels for dashboard display

        Returns only the most important levels for UI display
        """
        result = cls.calculate_all_levels(ticker, current_price)
        
        if "error" in result:
            return result
        
        # Filter to key levels for dashboard
        key_levels = [
            "weekly_open",
            "daily_open_midnight",
            "ny_open_0830",
            "hourly_open",
            "previous_day_high",
            "previous_day_low"
        ]
        
        summary_levels = {}
        for level_key in key_levels:
            if level_key in result["reference_levels"]:
                summary_levels[level_key] = result["reference_levels"][level_key]
        
        return {
            "success": True,
            "ticker": ticker,
            "current_price": result["current_price"],
            "current_time_utc": result["current_time_utc"],
            "reference_levels": summary_levels,
            "signals": {k: result["signals"][k] for k in key_levels if k in result["signals"]},
            "closest_level": result["closest_level"]
        }
