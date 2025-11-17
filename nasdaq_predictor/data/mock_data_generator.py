"""
Mock Data Generator for NQ=F (NASDAQ-100 Micro Futures)

Generates realistic market data for development and testing when yfinance is unavailable.
Simulates real market behavior with proper OHLCV data across all timeframes.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
import logging

logger = logging.getLogger(__name__)

# ET timezone for market hours
ET_TZ = pytz.timezone('America/New_York')

# Realistic NQ=F parameters (based on historical data)
BASE_PRICE = 20000.0  # Starting price around 20,000
DAILY_VOLATILITY = 0.015  # 1.5% daily volatility
INTRADAY_VOLATILITY = 0.003  # 0.3% per hour volatility
MIN_PRICE_MOVE = 0.25  # Minimum tick size
TYPICAL_SPREAD = 1.0  # Typical bid-ask spread


class MockNQDataGenerator:
    """
    Generates realistic mock data for NQ=F futures

    Features:
    - Realistic price movements with volatility
    - Proper OHLCV relationships (High >= Open/Close, Low <= Open/Close)
    - Market hours simulation (Sunday 6 PM - Friday 5 PM ET)
    - Multiple timeframe support (1m, 5m, 15m, 30m, 1h, 1d, 1wk)
    - Consistent price across timeframes
    """

    def __init__(self, base_price: float = BASE_PRICE, seed: int = None):
        """
        Initialize mock data generator

        Args:
            base_price: Starting price level
            seed: Random seed for reproducibility (None = time-based randomness)
        """
        self.base_price = base_price
        if seed is not None:
            np.random.seed(seed)

        # Current price tracking (for continuity across calls)
        self.current_price = base_price
        self.last_update = datetime.now(ET_TZ)

        logger.info(f"Mock data generator initialized at ${base_price:,.2f}")

    def generate_ohlcv(
        self,
        interval: str = '1m',
        num_bars: int = 1000,
        start_time: datetime = None
    ) -> pd.DataFrame:
        """
        Generate realistic OHLCV data for specified interval

        Args:
            interval: Time interval ('1m', '5m', '15m', '30m', '1h', '1d', '1wk')
            num_bars: Number of bars to generate
            start_time: Starting datetime (defaults to appropriate lookback)

        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume
            Index: Datetime in ET timezone
        """
        # Determine bar duration
        interval_minutes = {
            '1m': 1,
            '5m': 5,
            '15m': 15,
            '30m': 30,
            '1h': 60,
            '1d': 1440,
            '1wk': 10080
        }

        if interval not in interval_minutes:
            raise ValueError(f"Unsupported interval: {interval}")

        bar_minutes = interval_minutes[interval]

        # Calculate start time if not provided
        if start_time is None:
            lookback_minutes = num_bars * bar_minutes
            start_time = datetime.now(ET_TZ) - timedelta(minutes=lookback_minutes)

        # Ensure timezone-aware
        if start_time.tzinfo is None:
            start_time = ET_TZ.localize(start_time)
        else:
            start_time = start_time.astimezone(ET_TZ)

        # Generate timestamps
        timestamps = []
        current_time = start_time

        for _ in range(num_bars):
            timestamps.append(current_time)
            current_time += timedelta(minutes=bar_minutes)

        # Generate price data
        bars = []
        price = self.base_price

        for i, ts in enumerate(timestamps):
            # Determine if market is open (for volume simulation)
            is_market_open = self._is_market_open(ts)

            # Generate bar OHLCV
            bar = self._generate_single_bar(
                timestamp=ts,
                current_price=price,
                bar_minutes=bar_minutes,
                is_market_open=is_market_open
            )

            bars.append(bar)

            # Update price for next bar (use close as next open)
            price = bar['Close']

        # Update current price tracking
        self.current_price = bars[-1]['Close']
        self.last_update = timestamps[-1]

        # Create DataFrame
        df = pd.DataFrame(bars, index=timestamps)
        df.index.name = 'Datetime'

        logger.info(f"Generated {len(df)} bars for {interval} "
                   f"(${df['Close'].iloc[-1]:,.2f})")

        return df

    def _generate_single_bar(
        self,
        timestamp: datetime,
        current_price: float,
        bar_minutes: int,
        is_market_open: bool
    ) -> dict:
        """Generate a single OHLCV bar with realistic characteristics"""

        # Calculate volatility based on timeframe
        if bar_minutes <= 5:
            volatility = INTRADAY_VOLATILITY * 0.3  # Lower for very short timeframes
        elif bar_minutes <= 60:
            volatility = INTRADAY_VOLATILITY
        elif bar_minutes <= 1440:
            volatility = DAILY_VOLATILITY * (bar_minutes / 1440)
        else:
            volatility = DAILY_VOLATILITY * (bar_minutes / 1440)

        # Reduce volatility when market is closed
        if not is_market_open:
            volatility *= 0.3

        # Generate price movement (random walk with drift)
        drift = np.random.normal(0, volatility * 0.1)  # Slight upward drift
        random_move = np.random.normal(drift, volatility)

        # Calculate close price
        close = current_price * (1 + random_move)
        close = round(close / MIN_PRICE_MOVE) * MIN_PRICE_MOVE

        # Generate open (slight difference from previous close)
        open_move = np.random.normal(0, volatility * 0.2)
        open_price = current_price * (1 + open_move)
        open_price = round(open_price / MIN_PRICE_MOVE) * MIN_PRICE_MOVE

        # Generate high and low (must contain open and close)
        price_range = abs(open_price - close) + abs(np.random.normal(0, volatility * current_price))

        high = max(open_price, close) + price_range * np.random.uniform(0.3, 0.7)
        low = min(open_price, close) - price_range * np.random.uniform(0.3, 0.7)

        high = round(high / MIN_PRICE_MOVE) * MIN_PRICE_MOVE
        low = round(low / MIN_PRICE_MOVE) * MIN_PRICE_MOVE

        # Ensure OHLC relationships
        high = max(high, open_price, close)
        low = min(low, open_price, close)

        # Generate volume (higher during market hours)
        if is_market_open:
            avg_volume = 50000 * (bar_minutes / 5)  # Scale by timeframe
        else:
            avg_volume = 10000 * (bar_minutes / 5)  # Lower when closed

        volume = int(np.random.lognormal(np.log(avg_volume), 0.5))

        return {
            'Open': open_price,
            'High': high,
            'Low': low,
            'Close': close,
            'Volume': volume
        }

    def _is_market_open(self, timestamp: datetime) -> bool:
        """
        Check if futures market is open at given time

        Market hours: Sunday 6 PM ET - Friday 5 PM ET
        Closed: Friday 5 PM - Sunday 6 PM ET
        """
        # Ensure ET timezone
        if timestamp.tzinfo is None:
            timestamp = ET_TZ.localize(timestamp)
        else:
            timestamp = timestamp.astimezone(ET_TZ)

        day_of_week = timestamp.weekday()  # 0=Monday, 6=Sunday
        hour = timestamp.hour

        # Friday 5 PM ET or later: CLOSED
        if day_of_week == 4 and hour >= 17:
            return False

        # Saturday: CLOSED
        if day_of_week == 5:
            return False

        # Sunday before 6 PM ET: CLOSED
        if day_of_week == 6 and hour < 18:
            return False

        # All other times: OPEN
        return True

    def get_current_price(self) -> float:
        """Get current simulated price"""
        # Update price slightly based on time elapsed
        now = datetime.now(ET_TZ)
        minutes_elapsed = (now - self.last_update).total_seconds() / 60

        if minutes_elapsed > 0:
            # Small random walk
            move = np.random.normal(0, INTRADAY_VOLATILITY * np.sqrt(minutes_elapsed / 60))
            self.current_price *= (1 + move)
            self.current_price = round(self.current_price / MIN_PRICE_MOVE) * MIN_PRICE_MOVE
            self.last_update = now

        return self.current_price


# Global instance for consistent prices across calls
_global_generator = None


def get_mock_data(
    ticker: str,
    interval: str = '1m',
    period: str = '7d'
) -> pd.DataFrame:
    """
    Get mock data for specified ticker and interval

    Args:
        ticker: Ticker symbol (NQ=F, ES=F, etc.)
        interval: Time interval ('1m', '5m', '15m', '30m', '1h', '1d', '1wk')
        period: Period to fetch ('7d', '60d', '730d', 'max')

    Returns:
        DataFrame with OHLCV data in ET timezone
    """
    global _global_generator

    # Initialize global generator if needed
    if _global_generator is None:
        _global_generator = MockNQDataGenerator()

    # Map period to number of bars
    period_bars = {
        '1m': {'7d': 7 * 24 * 60, '1d': 24 * 60},
        '5m': {'60d': 60 * 24 * 12, '7d': 7 * 24 * 12},
        '15m': {'60d': 60 * 24 * 4, '7d': 7 * 24 * 4},
        '30m': {'60d': 60 * 24 * 2, '7d': 7 * 24 * 2},
        '1h': {'730d': 730 * 24, '60d': 60 * 24},
        '1d': {'max': 5 * 252, '730d': 730, '60d': 60},  # 5 years of trading days
        '1wk': {'max': 5 * 52, '730d': 104}  # 5 years of weeks
    }

    # Get number of bars for this interval/period combo
    num_bars = period_bars.get(interval, {}).get(period, 1000)

    logger.info(f"Generating mock data for {ticker} {interval} (period: {period}, bars: {num_bars})")

    # Generate data
    df = _global_generator.generate_ohlcv(
        interval=interval,
        num_bars=num_bars
    )

    return df


def get_mock_current_price(ticker: str = 'NQ=F') -> float:
    """Get current mock price for ticker"""
    global _global_generator

    if _global_generator is None:
        _global_generator = MockNQDataGenerator()

    price = _global_generator.get_current_price()
    logger.debug(f"Mock current price for {ticker}: ${price:,.2f}")

    return price


# Convenience functions
def generate_nq_1m(num_bars: int = 1000) -> pd.DataFrame:
    """Generate 1-minute NQ=F data"""
    return get_mock_data('NQ=F', interval='1m', period='7d')


def generate_nq_daily(num_bars: int = 252) -> pd.DataFrame:
    """Generate daily NQ=F data"""
    return get_mock_data('NQ=F', interval='1d', period='max')


def generate_nq_weekly(num_bars: int = 52) -> pd.DataFrame:
    """Generate weekly NQ=F data"""
    return get_mock_data('NQ=F', interval='1wk', period='max')
