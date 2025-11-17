"""
Live Data Fetcher - Direct from yfinance for real-time market data

Optimized implementation with:
- Aggressive 95-second caching (matches dashboard update interval)
- Improved session handling for API reliability
- Fallback data persistence for API failures
- Multiple interval support (1m, 5m, 15m, 30m, 1h, 1d, 1wk)
- Timezone normalization (UTC → ET)
- Rate limiting (1 req/sec per symbol)
- Robust error handling with retry logic
"""

import logging
import yfinance as yf
import pandas as pd
import time
import json
import os
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from pathlib import Path

from ..utils.timezone import ensure_et, ensure_utc, get_current_time_utc
from ..services.market_status_service import MarketStatusService

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION: Switch between real yfinance data and mock data
# ============================================================================
USE_MOCK_DATA = True  # Set to False to use real yfinance (when Yahoo unblocked)
# ============================================================================

# Rate limiting
RATE_LIMIT_DELAY = 1.0  # seconds between requests
CACHE_TTL = 95  # Cache for 95 seconds (dashboard update interval)

# Cache directory for persistence
CACHE_DIR = Path(__file__).parent.parent.parent / '.cache'
CACHE_DIR.mkdir(exist_ok=True)


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


class DataCache:
    """In-memory cache with optional persistent fallback storage"""

    def __init__(self, ttl_seconds: int = 95):
        self.cache = {}  # {key: (timestamp, dataframe)}
        self.fallback = {}  # {key: dataframe} - last successful fetch
        self.ttl = ttl_seconds

    def get(self, key: str) -> Optional[pd.DataFrame]:
        """Get data from cache if not expired"""
        if key not in self.cache:
            return None

        timestamp, data = self.cache[key]
        age = time.time() - timestamp

        if age < self.ttl:
            logger.debug(f"Cache HIT for {key} (age: {age:.1f}s / TTL: {self.ttl}s)")
            return data.copy()

        logger.debug(f"Cache EXPIRED for {key} (age: {age:.1f}s / TTL: {self.ttl}s)")
        return None

    def set(self, key: str, data: pd.DataFrame) -> None:
        """Store data in cache and update fallback"""
        self.cache[key] = (time.time(), data.copy())
        self.fallback[key] = data.copy()  # Always keep last successful fetch
        logger.debug(f"Cache SET for {key} (size: {len(data)} bars)")

    def get_fallback(self, key: str) -> Optional[pd.DataFrame]:
        """Get last successfully fetched data (even if API fails now)"""
        if key in self.fallback:
            logger.warning(f"Using fallback data for {key} ({len(self.fallback[key])} bars)")
            return self.fallback[key].copy()
        return None

    def clear_expired(self) -> None:
        """Remove expired entries to save memory"""
        now = time.time()
        expired_keys = [
            key for key, (timestamp, _) in self.cache.items()
            if now - timestamp > self.ttl * 2  # Keep for 2x TTL for flexibility
        ]
        for key in expired_keys:
            del self.cache[key]


cache = DataCache(ttl_seconds=CACHE_TTL)
rate_limiter = RateLimiter(min_interval=RATE_LIMIT_DELAY)


class LiveDataFetcher:
    """
    Fetch live market data directly from yfinance with intelligent caching

    Supports:
    - 1m: Last 7 days of 1-minute data (for block segmentation, hourly ranges)
    - 5m: Last 60 days of 5-minute data (for session ranges)
    - 15m: Last 60 days of 15-minute data
    - 30m: Last 60 days of 30-minute data
    - 1h: Last 730 days (2 years) of hourly data (for reference levels)
    - 1d: Max available daily data (for pivot calculations)
    - 1wk: Max available weekly data (for weekly pivots, weekly opens)

    Features:
    - Aggressive 95-second caching (matches dashboard interval)
    - Fallback to last successful fetch if API fails
    - Proper session handling for Yahoo Finance API
    - Exponential backoff retry logic
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
    def _create_session(cls) -> requests.Session:
        """Create a properly configured requests session for Yahoo Finance"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        return session

    @classmethod
    def fetch_data(
        cls,
        ticker: str,
        interval: str = '1m',
        max_retries: int = 3,
        use_cache: bool = True
    ) -> Optional[pd.DataFrame]:
        """
        Fetch market data from yfinance for a given interval

        Args:
            ticker: Ticker symbol (e.g., 'NQ=F', 'ES=F')
            interval: Time interval ('1m', '5m', '15m', '30m', '1h', '1d', '1wk')
            max_retries: Maximum retry attempts on failure
            use_cache: Whether to use 95-second cache (default: True)

        Returns:
            DataFrame with OHLCV data (index: datetime in ET timezone, columns: Open, High, Low, Close, Volume)
            Returns None if fetch fails after all retries
        """
        if interval not in cls.FETCH_CONFIG:
            logger.error(f"Unsupported interval: {interval}. Must be one of {list(cls.FETCH_CONFIG.keys())}")
            return None

        cache_key = f"{ticker}_{interval}"

        # Check cache first
        if use_cache:
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                return cached_data

        # USE MOCK DATA if configured (when Yahoo Finance unavailable)
        if USE_MOCK_DATA:
            logger.info(f"Using MOCK data for {ticker} {interval}")
            from .mock_data_generator import get_mock_data
            period = cls.FETCH_CONFIG[interval]['period']
            df = get_mock_data(ticker, interval, period)

            # Cache mock data (still benefits from 95-second cache)
            cache.set(cache_key, df)
            logger.info(f"Generated {len(df)} mock bars for {ticker} {interval}")
            return df

        period = cls.FETCH_CONFIG[interval]['period']
        logger.info(f"Fetching {ticker} {interval} data (period: {period})")

        # Retry logic with exponential backoff
        retry_delays = [2, 5, 10]  # seconds

        for attempt in range(max_retries):
            try:
                # Apply rate limiting
                rate_limiter.wait(key=ticker)

                # Create fresh session for each attempt (helps with API 401 issues)
                session = cls._create_session()

                # Fetch data
                ticker_obj = yf.Ticker(ticker, session=session)
                df = ticker_obj.history(period=period, interval=interval)

                if df.empty:
                    raise ValueError(f"Empty DataFrame returned for {ticker} {interval}")

                # Normalize timezone: UTC → ET
                df = cls._normalize_timezone(df)

                # Validate data
                is_valid, errors = cls._validate_data(df, ticker, interval)
                if not is_valid:
                    raise ValueError(f"Data validation failed: {errors}")

                # Cache successful result
                cache.set(cache_key, df)
                logger.info(f"Successfully fetched {len(df)} bars for {ticker} {interval}")
                return df

            except Exception as e:
                logger.warning(f"Fetch attempt {attempt + 1}/{max_retries} failed: {e}")

                if attempt < max_retries - 1:
                    delay = retry_delays[attempt]
                    logger.info(f"Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    # All retries exhausted - try fallback data
                    logger.error(f"All {max_retries} fetch attempts failed for {ticker} {interval}")
                    fallback_data = cache.get_fallback(cache_key)
                    if fallback_data is not None:
                        logger.info(f"Returning fallback data ({len(fallback_data)} bars)")
                        return fallback_data
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
        # USE MOCK DATA if configured
        if USE_MOCK_DATA:
            from .mock_data_generator import get_mock_current_price
            return get_mock_current_price(ticker)

        try:
            rate_limiter.wait(key=f"{ticker}_price")

            session = cls._create_session()
            ticker_obj = yf.Ticker(ticker, session=session)
            current_price = ticker_obj.info.get('currentPrice') or ticker_obj.info.get('regularMarketPrice')

            if current_price is None:
                # Fallback: get from latest bar of 1m data
                df = cls.fetch_data(ticker, interval='1m', use_cache=True)
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
        Fetch data for multiple intervals with caching

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
                df = cls.fetch_data(ticker, interval=interval, use_cache=True)
                results[interval] = df
                status = 'OK' if df is not None else 'FAILED'
                logger.info(f"Fetched {interval}: {status}")
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
            # Fetch 5-minute data (good resolution for sessions) with caching
            df = cls.fetch_data(ticker, interval='5m', use_cache=True)

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


# Periodic cache maintenance
def maintenance_cleanup():
    """Clean up expired cache entries"""
    cache.clear_expired()
    logger.debug("Cache maintenance completed")


# Export convenience functions
def fetch_nq_1m() -> Optional[pd.DataFrame]:
    """Convenience function: Fetch NQ=F 1-minute data with caching"""
    return LiveDataFetcher.fetch_data('NQ=F', interval='1m', use_cache=True)


def fetch_nq_daily() -> Optional[pd.DataFrame]:
    """Convenience function: Fetch NQ=F daily data with caching"""
    return LiveDataFetcher.fetch_data('NQ=F', interval='1d', use_cache=True)


def fetch_nq_weekly() -> Optional[pd.DataFrame]:
    """Convenience function: Fetch NQ=F weekly data with caching"""
    return LiveDataFetcher.fetch_data('NQ=F', interval='1wk', use_cache=True)


def fetch_nq_all_intervals() -> Dict[str, Optional[pd.DataFrame]]:
    """Convenience function: Fetch NQ=F for all intervals with caching"""
    return LiveDataFetcher.get_multiple_intervals('NQ=F')
