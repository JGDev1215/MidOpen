"""
Live Data Fetcher - Direct from yfinance for real-time market data

Fetches OHLCV data directly from Yahoo Finance without Supabase caching.
Optimized for live dashboard display with:
- Multiple interval support (1m, 5m, 15m, 30m, 1h, 1d, 1wk)
- Timezone normalization (UTC → ET)
- Rate limiting (1 req/sec)
- Error handling with retry logic
"""

import logging
import yfinance as yf
import pandas as pd
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from ..utils.timezone import ensure_et, ensure_utc, get_current_time_utc
from ..services.market_status_service import MarketStatusService

logger = logging.getLogger(__name__)

# Rate limiting
RATE_LIMIT_DELAY = 1.0  # seconds between requests
last_fetch_time = {}


class RateLimiter:
    """Simple rate limiter to prevent API throttling"""

    def __init__(self, min_interval: float = 1.0):
        self.min_interval = min_interval
        self.last_request_time = {}

    def wait(self, key: str = "default"):
        """Wait if necessary to maintain rate limit"""
        now = time.time()

        if key in self.last_request_time:
            elapsed = now - self.last_request_time[key]
            if elapsed < self.min_interval:
                sleep_time = self.min_interval - elapsed
                logger.debug(f"Rate limit: sleeping {sleep_time:.2f}s for {key}")
                time.sleep(sleep_time)

        self.last_request_time[key] = time.time()


rate_limiter = RateLimiter(min_interval=RATE_LIMIT_DELAY)


class LiveDataFetcher:
    """
    Fetch live market data directly from yfinance

    Supports:
    - 1m: Last 7 days of 1-minute data (for block segmentation, hourly ranges)
    - 5m: Last 60 days of 5-minute data (for session ranges)
    - 15m: Last 60 days of 15-minute data
    - 30m: Last 60 days of 30-minute data
    - 1h: Last 730 days (2 years) of hourly data (for reference levels)
    - 1d: Max available daily data (for pivot calculations)
    - 1wk: Max available weekly data (for weekly pivots, weekly opens)
    """

    # Yahoo Finance data availability limits
    FETCH_CONFIG = {
        '1m': {'period': '7d', 'for': 'block segmentation, current session ranges'},
        '5m': {'period': '60d', 'for': 'session ranges, intraday analysis'},
        '15m': {'period': '60d', 'for': 'mid-timeframe reference levels'},
        '30m': {'period': '60d', 'for': 'hourly level verification'},
        '1h': {'period': '730d', 'for': 'daily opens, reference levels'},
        '1d': {'period': 'max', 'for': 'daily pivots, previous day high/low'},
        '1wk': {'period': 'max', 'for': 'weekly pivots, weekly opens'}
    }

    @classmethod
    def fetch_data(
        cls,
        ticker: str,
        interval: str = '1m',
        max_retries: int = 3
    ) -> Optional[pd.DataFrame]:
        """
        Fetch market data from yfinance for a given interval

        Args:
            ticker: Ticker symbol (e.g., 'NQ=F', 'ES=F')
            interval: Time interval ('1m', '5m', '15m', '30m', '1h', '1d', '1wk')
            max_retries: Maximum retry attempts on failure

        Returns:
            DataFrame with OHLCV data (index: datetime in ET timezone, columns: Open, High, Low, Close, Volume)
            Returns None if fetch fails after all retries

        Example:
            >>> df = LiveDataFetcher.fetch_data('NQ=F', interval='1m')
            >>> if df is not None:
            >>>     print(df.head())
        """
        if interval not in cls.FETCH_CONFIG:
            logger.error(f"Unsupported interval: {interval}. Must be one of {list(cls.FETCH_CONFIG.keys())}")
            return None

        period = cls.FETCH_CONFIG[interval]['period']

        logger.info(f"Fetching {ticker} {interval} data (period: {period})")

        # Retry logic with exponential backoff
        retry_delays = [2, 5, 10]  # seconds

        for attempt in range(max_retries):
            try:
                # Apply rate limiting
                rate_limiter.wait(key=ticker)

                # Fetch data
                ticker_obj = yf.Ticker(ticker)
                df = ticker_obj.history(period=period, interval=interval)

                if df.empty:
                    raise ValueError(f"Empty DataFrame returned for {ticker} {interval}")

                # Normalize timezone: UTC → ET
                df = cls._normalize_timezone(df)

                # Validate data
                is_valid, errors = cls._validate_data(df, ticker, interval)
                if not is_valid:
                    raise ValueError(f"Data validation failed: {errors}")

                logger.info(f"Successfully fetched {len(df)} bars for {ticker} {interval}")
                return df

            except Exception as e:
                logger.warning(f"Fetch attempt {attempt + 1}/{max_retries} failed: {e}")

                if attempt < max_retries - 1:
                    delay = retry_delays[attempt]
                    logger.info(f"Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    logger.error(f"All {max_retries} fetch attempts failed for {ticker} {interval}")
                    return None

    @staticmethod
    def _normalize_timezone(df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize DataFrame timezone from UTC to ET

        yfinance returns data in UTC timezone by default.
        We convert to ET for all calculations and display.

        Args:
            df: DataFrame with UTC index

        Returns:
            DataFrame with ET timezone index
        """
        if df.index.tzinfo is None:
            # Assume UTC if naive
            df.index = df.index.tz_localize('UTC')
        else:
            # Convert to UTC first
            df.index = df.index.tz_convert('UTC')

        # Convert UTC → ET
        df.index = df.index.tz_convert('America/New_York')

        return df

    @staticmethod
    def _validate_data(df: pd.DataFrame, ticker: str, interval: str) -> tuple[bool, List[str]]:
        """
        Validate OHLCV data quality

        Args:
            df: DataFrame with OHLCV data
            ticker: Ticker symbol
            interval: Time interval

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Check 1: Minimum bar count
        min_bars = {
            '1m': 60,    # At least 1 hour
            '5m': 12,    # At least 1 hour
            '15m': 4,    # At least 1 hour
            '30m': 2,    # At least 1 hour
            '1h': 24,    # At least 1 day
            '1d': 5,     # At least 1 week
            '1wk': 1     # At least 1 week
        }.get(interval, 1)

        if len(df) < min_bars:
            errors.append(f"Insufficient bars: {len(df)} < {min_bars} required for {interval}")

        # Check 2: OHLC relationship validity
        # Skip strict validation for daily/weekly data as yfinance sometimes has minor inconsistencies
        # Only validate 1m-1h data strictly
        if interval not in ['1d', '1wk']:
            invalid_ohlc = df[
                (df['High'] < df['Low']) |
                (df['High'] < df['Open']) |
                (df['High'] < df['Close']) |
                (df['Low'] > df['Open']) |
                (df['Low'] > df['Close'])
            ]

            if not invalid_ohlc.empty:
                errors.append(f"Invalid OHLC relationships in {len(invalid_ohlc)} bars")

        # Check 3: NaN values
        nan_count = df[['Open', 'High', 'Low', 'Close', 'Volume']].isna().sum().sum()
        if nan_count > 0:
            errors.append(f"NaN values detected: {nan_count} cells")

        # Check 4: Price continuity (optional warning for large jumps)
        if 'Close' in df.columns and len(df) > 1:
            price_changes = df['Close'].pct_change().abs()
            extreme_jumps = (price_changes > 0.10).sum()  # > 10% jumps
            if extreme_jumps > 0:
                logger.warning(f"Detected {extreme_jumps} price jumps >10% for {ticker} {interval}")

        return (len(errors) == 0, errors)

    @classmethod
    def get_current_price(cls, ticker: str = 'NQ=F') -> Optional[float]:
        """
        Get current price for a ticker

        Args:
            ticker: Ticker symbol

        Returns:
            Current price, or None if fetch fails
        """
        try:
            rate_limiter.wait(key=f"{ticker}_price")

            ticker_obj = yf.Ticker(ticker)
            current_price = ticker_obj.info.get('currentPrice') or ticker_obj.info.get('regularMarketPrice')

            if current_price is None:
                # Fallback: get from latest bar of 1m data
                df = cls.fetch_data(ticker, interval='1m')
                if df is not None and not df.empty:
                    return float(df.iloc[-1]['Close'])

            return current_price

        except Exception as e:
            logger.error(f"Failed to get current price for {ticker}: {e}")
            return None

    @classmethod
    def get_multiple_intervals(
        cls,
        ticker: str,
        intervals: List[str] = None
    ) -> Dict[str, Optional[pd.DataFrame]]:
        """
        Fetch data for multiple intervals in parallel (sequential with rate limiting)

        Args:
            ticker: Ticker symbol
            intervals: List of intervals (default: all)

        Returns:
            Dict mapping interval to DataFrame (or None if fetch failed)
        """
        if intervals is None:
            intervals = ['1m', '5m', '15m', '30m', '1h', '1d', '1wk']

        results = {}

        for interval in intervals:
            try:
                df = cls.fetch_data(ticker, interval=interval)
                results[interval] = df
                logger.info(f"Fetched {interval}: {'OK' if df is not None else 'FAILED'}")
            except Exception as e:
                logger.error(f"Error fetching {interval}: {e}")
                results[interval] = None

        return results

    @classmethod
    def get_session_data(
        cls,
        ticker: str,
        session_start_hour_et: int,
        session_start_min_et: int,
        session_end_hour_et: int,
        session_end_min_et: int
    ) -> Optional[pd.DataFrame]:
        """
        Get data for a specific trading session (e.g., Asian, London, NY AM, NY PM)

        Args:
            ticker: Ticker symbol
            session_start_hour_et: Session start hour (ET, 0-23)
            session_start_min_et: Session start minute (0-59)
            session_end_hour_et: Session end hour (ET, 0-23)
            session_end_min_et: Session end minute (0-59)

        Returns:
            DataFrame with session data, or None if fetch fails
        """
        try:
            # Fetch 5-minute data (good resolution for sessions)
            df = cls.fetch_data(ticker, interval='5m')

            if df is None or df.empty:
                return None

            # Filter to session times
            session_data = []

            for idx, row in df.iterrows():
                hour = idx.hour
                minute = idx.minute

                # Check if time is within session window
                session_start_minutes = session_start_hour_et * 60 + session_start_min_et
                session_end_minutes = session_end_hour_et * 60 + session_end_min_et
                current_minutes = hour * 60 + minute

                # Handle sessions that span midnight
                if session_end_minutes < session_start_minutes:
                    # Session spans midnight
                    if current_minutes >= session_start_minutes or current_minutes < session_end_minutes:
                        session_data.append(row)
                else:
                    # Normal session
                    if session_start_minutes <= current_minutes < session_end_minutes:
                        session_data.append(row)

            if session_data:
                return pd.DataFrame(session_data)
            else:
                logger.warning(f"No data found for session {session_start_hour_et}:{session_start_min_et:02d}-"
                             f"{session_end_hour_et}:{session_end_min_et:02d}")
                return None

        except Exception as e:
            logger.error(f"Error getting session data: {e}")
            return None


# Export convenience functions
def fetch_nq_1m() -> Optional[pd.DataFrame]:
    """Convenience function: Fetch NQ=F 1-minute data"""
    return LiveDataFetcher.fetch_data('NQ=F', interval='1m')


def fetch_nq_daily() -> Optional[pd.DataFrame]:
    """Convenience function: Fetch NQ=F daily data"""
    return LiveDataFetcher.fetch_data('NQ=F', interval='1d')


def fetch_nq_weekly() -> Optional[pd.DataFrame]:
    """Convenience function: Fetch NQ=F weekly data"""
    return LiveDataFetcher.fetch_data('NQ=F', interval='1wk')


def fetch_nq_all_intervals() -> Dict[str, Optional[pd.DataFrame]]:
    """Convenience function: Fetch NQ=F for all intervals"""
    return LiveDataFetcher.get_multiple_intervals('NQ=F')
