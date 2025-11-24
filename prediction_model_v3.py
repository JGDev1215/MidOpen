#!/usr/bin/env python3
"""
Prediction Model v3.0 — Reference Level Analytical System

A multi-instrument prediction framework that analyzes price positions
relative to 20 reference levels (14 always-available, 6 conditional).

Outputs: directional bias, confidence score, weight distribution, and detailed level analysis.
"""

import pandas as pd
from datetime import datetime, timedelta
import pytz
from typing import Dict, List, Tuple, Any


class ReferenceLevel:
    """Represents a single reference level with metadata and calculations."""

    def __init__(self, name: str, base_weight: float, level_type: str = "ALWAYS_AVAILABLE",
                 availability_time: str = None):
        self.name = name
        self.base_weight = base_weight
        self.level_type = level_type
        self.availability_time = availability_time
        self.price = None
        self.normalized_weight = None
        self.effective_weight = None
        self.direction = None
        self.position = None
        self.distance_percent = None
        self.depreciation = 1.0

    def calculate_direction(self, current_price: float) -> str:
        """Determine if price is above, below, or at the level."""
        if self.price is None:
            return "UNAVAILABLE"

        threshold = abs(self.price) * 0.0001  # 0.01% threshold for floating point
        if current_price > self.price + threshold:
            return "BULLISH"
        elif current_price < self.price - threshold:
            return "BEARISH"
        else:
            return "NEUTRAL"

    def calculate_distance(self, current_price: float) -> float:
        """Calculate distance as percentage of current price."""
        if self.price is None or current_price == 0:
            return 0.0
        return abs((current_price - self.price) / current_price) * 100

    def apply_depreciation(self, distance_percent: float):
        """Apply distance-based depreciation: 1.0 at 0%, declining to 0.1 at 5%+"""
        if distance_percent <= 0:
            self.depreciation = 1.0
        elif distance_percent >= 5.0:
            self.depreciation = 0.1
        else:
            # Linear decay from 1.0 to 0.1 between 0% and 5%
            self.depreciation = 1.0 - (distance_percent / 5.0) * 0.9

    def to_dict(self) -> Dict:
        """Convert level to dictionary for output."""
        return {
            'name': self.name,
            'type': self.level_type,
            'price': round(self.price, 2) if self.price else None,
            'position': self.position,
            'distance_percent': round(self.distance_percent, 3) if self.distance_percent else None,
            'base_weight': round(self.base_weight, 4),
            'normalized_weight': round(self.normalized_weight, 4) if self.normalized_weight else None,
            'depreciation': round(self.depreciation, 3),
            'effective_weight': round(self.effective_weight, 4) if self.effective_weight else None,
            'direction': self.direction
        }


class PredictionEngine:
    """Main prediction engine implementing the reference level analytical system."""

    # US100 level specifications
    US100_LEVELS = [
        # Always-available levels (14 total)
        ReferenceLevel('daily_midnight', 0.1339),
        ReferenceLevel('previous_hourly', 0.0822),
        ReferenceLevel('2h_open', 0.0520),
        ReferenceLevel('4h_open', 0.0650),
        ReferenceLevel('ny_open', 0.0779),
        ReferenceLevel('ny_preopen', 0.0391),
        ReferenceLevel('prev_day_high', 0.0260),
        ReferenceLevel('prev_day_low', 0.0260),
        ReferenceLevel('weekly_open', 0.0650),
        ReferenceLevel('weekly_high', 0.0260),
        ReferenceLevel('weekly_low', 0.0260),
        ReferenceLevel('prev_week_high', 0.0520),
        ReferenceLevel('prev_week_low', 0.0520),
        ReferenceLevel('monthly_open', 0.0391),
        # Conditional levels (6 total)
        ReferenceLevel('asian_range_high', 0.0279, 'CONDITIONAL', '00:00'),
        ReferenceLevel('asian_range_low', 0.0279, 'CONDITIONAL', '00:00'),
        ReferenceLevel('london_range_high', 0.0520, 'CONDITIONAL', '11:00'),
        ReferenceLevel('london_range_low', 0.0520, 'CONDITIONAL', '11:00'),
        ReferenceLevel('ny_range_high', 0.0391, 'CONDITIONAL', '14:00'),
        ReferenceLevel('ny_range_low', 0.0391, 'CONDITIONAL', '14:00'),
    ]

    # ES has identical structure to US100
    ES_LEVELS = [
        ReferenceLevel('daily_midnight', 0.1339),
        ReferenceLevel('previous_hourly', 0.0822),
        ReferenceLevel('2h_open', 0.0520),
        ReferenceLevel('4h_open', 0.0650),
        ReferenceLevel('chicago_open', 0.0779),  # Different from NY
        ReferenceLevel('chicago_preopen', 0.0391),  # Different from NY
        ReferenceLevel('prev_day_high', 0.0260),
        ReferenceLevel('prev_day_low', 0.0260),
        ReferenceLevel('weekly_open', 0.0650),
        ReferenceLevel('weekly_high', 0.0260),
        ReferenceLevel('weekly_low', 0.0260),
        ReferenceLevel('prev_week_high', 0.0520),
        ReferenceLevel('prev_week_low', 0.0520),
        ReferenceLevel('monthly_open', 0.0391),
        ReferenceLevel('asian_range_high', 0.0279, 'CONDITIONAL', '00:00'),
        ReferenceLevel('asian_range_low', 0.0279, 'CONDITIONAL', '00:00'),
        ReferenceLevel('london_range_high', 0.0520, 'CONDITIONAL', '11:00'),
        ReferenceLevel('london_range_low', 0.0520, 'CONDITIONAL', '11:00'),
        ReferenceLevel('chicago_range_high', 0.0391, 'CONDITIONAL', '14:00'),
        ReferenceLevel('chicago_range_low', 0.0391, 'CONDITIONAL', '14:00'),
    ]

    # UK100 has 15 levels (all always-available)
    UK100_LEVELS = [
        ReferenceLevel('daily_midnight', 0.1339),
        ReferenceLevel('previous_hourly', 0.0822),
        ReferenceLevel('2h_open', 0.0520),
        ReferenceLevel('4h_open', 0.0650),
        ReferenceLevel('london_open', 0.0779),
        ReferenceLevel('prev_day_high', 0.0260),
        ReferenceLevel('prev_day_low', 0.0260),
        ReferenceLevel('weekly_open', 0.0650),
        ReferenceLevel('weekly_high', 0.0260),
        ReferenceLevel('weekly_low', 0.0260),
        ReferenceLevel('prev_week_high', 0.0520),
        ReferenceLevel('prev_week_low', 0.0520),
        ReferenceLevel('monthly_open', 0.0391),
        ReferenceLevel('london_range_high', 0.0520),
        ReferenceLevel('london_range_low', 0.0520),
    ]

    def __init__(self, instrument: str = 'US100', timezone: str = None):
        """Initialize the prediction engine for a specific instrument.

        Args:
            instrument: 'US100', 'ES', or 'UK100'
            timezone: Explicit timezone override (uses instrument default if not provided)
        """
        self.instrument = instrument

        # Set timezone based on instrument
        timezone_map = {
            'US100': 'America/New_York',
            'ES': 'America/Chicago',
            'UK100': 'Europe/London',
            'GER40': 'Europe/Berlin'
        }
        self.timezone = timezone or timezone_map.get(instrument, 'America/New_York')
        self.tz = pytz.timezone(self.timezone)

        # Select level configuration
        if instrument == 'US100':
            self.levels = [self._copy_level(l) for l in self.US100_LEVELS]
        elif instrument == 'ES':
            self.levels = [self._copy_level(l) for l in self.ES_LEVELS]
        elif instrument == 'UK100':
            self.levels = [self._copy_level(l) for l in self.UK100_LEVELS]
        else:
            # Default to US100 for unknown instruments
            self.levels = [self._copy_level(l) for l in self.US100_LEVELS]

    @staticmethod
    def _copy_level(level: ReferenceLevel) -> ReferenceLevel:
        """Create a fresh copy of a level template."""
        return ReferenceLevel(level.name, level.base_weight, level.level_type, level.availability_time)

    def _calculate_levels(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate all reference level prices from OHLC data."""
        # Convert index to instrument timezone if needed
        current_time = df.index[-1]
        if current_time.tzinfo is None:
            current_time = self.tz.localize(current_time)
        else:
            current_time = current_time.astimezone(self.tz)

        # Extract OHLC data
        opens = df['open']
        highs = df['high']
        lows = df['low']
        closes = df['close']

        # Calculate base levels
        levels_dict = {}

        # Daily levels
        current_date = current_time.date()
        today_start = self.tz.localize(datetime.combine(current_date, datetime.min.time()))
        today_data = df[df.index >= today_start]

        if len(today_data) > 0:
            levels_dict['daily_midnight'] = today_data['open'].iloc[0]
        else:
            levels_dict['daily_midnight'] = opens.iloc[-1]

        # Previous hourly open
        if len(opens) > 1:
            levels_dict['previous_hourly'] = opens.iloc[-2]
        else:
            levels_dict['previous_hourly'] = opens.iloc[-1]

        # 2-hour and 4-hour opens (approximate from available data)
        levels_dict['2h_open'] = opens.iloc[max(0, len(opens) - 120)] if len(opens) > 120 else opens.iloc[0]
        levels_dict['4h_open'] = opens.iloc[max(0, len(opens) - 240)] if len(opens) > 240 else opens.iloc[0]

        # NY/London/Chicago opens (9:30 AM ET for US100, 8:30 AM CT for ES)
        if self.instrument in ['US100', 'ES']:
            if self.instrument == 'US100':
                # NY market opens at 9:30 AM ET
                session_start = today_start.replace(hour=9, minute=30)
                preopen_start = today_start.replace(hour=4)  # Pre-market starts at 4 AM ET
                session_data = df[(df.index >= session_start) & (df.index < today_start.replace(hour=16))]
                preopen_data = df[(df.index >= preopen_start) & (df.index < session_start)]

                levels_dict['ny_open'] = session_data['open'].iloc[0] if len(session_data) > 0 else opens.iloc[-1]
                levels_dict['ny_preopen'] = preopen_data['open'].iloc[0] if len(preopen_data) > 0 else opens.iloc[-1]
            else:  # ES - Chicago market
                # ES (Chicago) opens at 8:30 AM CT (which is 9:30 AM ET)
                chicago_tz = pytz.timezone('America/Chicago')
                current_time_chicago = current_time.astimezone(chicago_tz)
                session_start = chicago_tz.localize(datetime.combine(current_time_chicago.date(), datetime.strptime('08:30', '%H:%M').time()))
                preopen_start = chicago_tz.localize(datetime.combine(current_time_chicago.date(), datetime.strptime('17:00', '%H:%M').time())) - timedelta(days=1)  # Prev day 5 PM CT

                session_data = df[(df.index >= session_start) & (df.index < session_start.replace(hour=15))]
                preopen_data = df[(df.index >= preopen_start) & (df.index < session_start)]

                levels_dict['chicago_open'] = session_data['open'].iloc[0] if len(session_data) > 0 else opens.iloc[-1]
                levels_dict['chicago_preopen'] = preopen_data['open'].iloc[0] if len(preopen_data) > 0 else opens.iloc[-1]
        else:
            # London market opens at 8 AM GMT
            session_start = today_start.replace(hour=8)
            session_data = df[df.index >= session_start]
            levels_dict['london_open'] = session_data['open'].iloc[0] if len(session_data) > 0 else opens.iloc[-1]

        # Previous day high/low
        yesterday_start = today_start - timedelta(days=1)
        yesterday_data = df[(df.index >= yesterday_start) & (df.index < today_start)]

        if len(yesterday_data) > 0:
            levels_dict['prev_day_high'] = yesterday_data['high'].max()
            levels_dict['prev_day_low'] = yesterday_data['low'].min()
        else:
            levels_dict['prev_day_high'] = highs.iloc[-1]
            levels_dict['prev_day_low'] = lows.iloc[-1]

        # Weekly levels
        weekday = current_time.weekday()
        days_since_monday = weekday
        week_start = today_start - timedelta(days=days_since_monday)
        week_data = df[df.index >= week_start]

        if len(week_data) > 0:
            levels_dict['weekly_open'] = week_data['open'].iloc[0]
            levels_dict['weekly_high'] = week_data['high'].max()
            levels_dict['weekly_low'] = week_data['low'].min()
        else:
            levels_dict['weekly_open'] = opens.iloc[-1]
            levels_dict['weekly_high'] = highs.iloc[-1]
            levels_dict['weekly_low'] = lows.iloc[-1]

        # Previous week
        prev_week_start = week_start - timedelta(days=7)
        prev_week_data = df[(df.index >= prev_week_start) & (df.index < week_start)]

        if len(prev_week_data) > 0:
            levels_dict['prev_week_high'] = prev_week_data['high'].max()
            levels_dict['prev_week_low'] = prev_week_data['low'].min()
        else:
            levels_dict['prev_week_high'] = highs.iloc[-1]
            levels_dict['prev_week_low'] = lows.iloc[-1]

        # Monthly levels
        month_start = self.tz.localize(datetime(current_time.year, current_time.month, 1))
        month_data = df[df.index >= month_start]

        if len(month_data) > 0:
            levels_dict['monthly_open'] = month_data['open'].iloc[0]
        else:
            levels_dict['monthly_open'] = opens.iloc[-1]

        # Asian range (20:00 previous day - 00:00 current day, in instrument timezone)
        try:
            asian_start = self.tz.localize(datetime.combine(
                current_date - timedelta(days=1),
                datetime.min.time().replace(hour=20, minute=0, second=0, microsecond=0)
            ))
        except:
            # Handle ambiguous times during DST transitions
            asian_start = self.tz.localize(datetime.combine(
                current_date - timedelta(days=1),
                datetime.min.time().replace(hour=20, minute=0, second=0, microsecond=0)
            ), is_dst=False)

        asian_end = today_start
        asian_data = df[(df.index >= asian_start) & (df.index < asian_end)]

        if len(asian_data) > 0:
            levels_dict['asian_range_high'] = asian_data['high'].max()
            levels_dict['asian_range_low'] = asian_data['low'].min()
        else:
            levels_dict['asian_range_high'] = highs.iloc[-1]
            levels_dict['asian_range_low'] = lows.iloc[-1]

        # London range (03:00 - 11:00 ET or 08:00 - 16:30 GMT)
        london_start = today_start.replace(hour=3)
        london_end = today_start.replace(hour=11)
        london_data = df[(df.index >= london_start) & (df.index < london_end)]

        if len(london_data) > 0:
            levels_dict['london_range_high'] = london_data['high'].max()
            levels_dict['london_range_low'] = london_data['low'].min()
        else:
            levels_dict['london_range_high'] = highs.iloc[-1]
            levels_dict['london_range_low'] = lows.iloc[-1]

        # Trading range - NY for US100, Chicago for ES
        if self.instrument == 'US100':
            # NY range (09:30 AM - 14:00 ET)
            range_start = today_start.replace(hour=9, minute=30)
            range_end = today_start.replace(hour=14)
            range_data = df[(df.index >= range_start) & (df.index < range_end)]

            if len(range_data) > 0:
                levels_dict['ny_range_high'] = range_data['high'].max()
                levels_dict['ny_range_low'] = range_data['low'].min()
            else:
                levels_dict['ny_range_high'] = highs.iloc[-1]
                levels_dict['ny_range_low'] = lows.iloc[-1]
        else:  # ES - Chicago market
            # Chicago range (08:30 AM - 14:00 CT / 9:30 AM - 15:00 ET)
            chicago_tz = pytz.timezone('America/Chicago')
            current_time_chicago = current_time.astimezone(chicago_tz)
            chicago_today_start = chicago_tz.localize(datetime.combine(current_time_chicago.date(), datetime.min.time()))
            range_start = chicago_today_start.replace(hour=8, minute=30)
            range_end = chicago_today_start.replace(hour=14)
            range_data = df[(df.index >= range_start) & (df.index < range_end)]

            if len(range_data) > 0:
                levels_dict['chicago_range_high'] = range_data['high'].max()
                levels_dict['chicago_range_low'] = range_data['low'].min()
            else:
                levels_dict['chicago_range_high'] = highs.iloc[-1]
                levels_dict['chicago_range_low'] = lows.iloc[-1]

        return levels_dict, current_time

    def _determine_available_levels(self, current_time, levels_dict: Dict) -> List[ReferenceLevel]:
        """Determine which levels are available at the current time."""
        available = []

        for level in self.levels:
            if level.level_type == 'ALWAYS_AVAILABLE':
                if level.name in levels_dict:
                    level.price = levels_dict[level.name]
                    available.append(level)
            else:  # CONDITIONAL
                # Check if current time is past availability time
                current_hour = current_time.hour
                avail_hour = int(level.availability_time.split(':')[0])

                if current_hour >= avail_hour:
                    if level.name in levels_dict:
                        level.price = levels_dict[level.name]
                        available.append(level)

        return available

    def _normalize_weights(self, available_levels: List[ReferenceLevel]):
        """Normalize weights to sum to 1.0000."""
        total_base_weight = sum(l.base_weight for l in available_levels)

        if total_base_weight == 0:
            return

        normalization_factor = 1.0 / total_base_weight

        for level in available_levels:
            level.normalized_weight = level.base_weight * normalization_factor

    def _apply_depreciation(self, available_levels: List[ReferenceLevel], current_price: float):
        """Apply distance-based depreciation and calculate effective weights."""
        for level in available_levels:
            if level.price is None:
                continue

            # Calculate distance
            distance = level.calculate_distance(current_price)
            level.distance_percent = distance

            # Apply depreciation
            level.apply_depreciation(distance)

            # Calculate effective weight
            level.effective_weight = level.normalized_weight * level.depreciation

            # Calculate direction (BULLISH if price > level, BEARISH if price < level)
            level.direction = level.calculate_direction(current_price)

            # Set position for output clarity
            if level.direction == 'BULLISH':
                level.position = 'BELOW'
            elif level.direction == 'BEARISH':
                level.position = 'ABOVE'
            else:
                level.position = 'AT'

    def analyze(self, df: pd.DataFrame, timestamp: str = None) -> Dict[str, Any]:
        """Analyze price data and generate prediction output.

        Args:
            df: DataFrame with columns [open, high, low, close] and DatetimeIndex
            timestamp: Optional current timestamp (uses last index if not provided)

        Returns:
            Dictionary with complete analysis output
        """
        if df is None or len(df) == 0:
            return self._empty_result(timestamp)

        # Use provided timestamp or last index value
        if timestamp is None:
            current_time = df.index[-1]
            if current_time.tzinfo is None:
                current_time = self.tz.localize(current_time)
            else:
                current_time = current_time.astimezone(self.tz)
        else:
            try:
                current_time = pd.to_datetime(timestamp)
                if current_time.tzinfo is None:
                    current_time = self.tz.localize(current_time)
                else:
                    current_time = current_time.astimezone(self.tz)
            except:
                current_time = df.index[-1]

        current_price = df['close'].iloc[-1]

        # Calculate all reference levels
        levels_dict, _ = self._calculate_levels(df)

        # Determine available levels
        available_levels = self._determine_available_levels(current_time, levels_dict)

        if not available_levels:
            return self._empty_result(timestamp)

        # Normalize weights
        self._normalize_weights(available_levels)

        # Apply depreciation
        self._apply_depreciation(available_levels, current_price)

        # Calculate directional bias
        bullish_weight = sum(l.effective_weight for l in available_levels if l.direction == 'BULLISH')
        bearish_weight = sum(l.effective_weight for l in available_levels if l.direction == 'BEARISH')

        # Determine bias (binary: BULLISH or BEARISH)
        if bullish_weight >= bearish_weight:
            bias = 'BULLISH'
        else:
            bias = 'BEARISH'

        # Calculate confidence (0-100%)
        total_weight = bullish_weight + bearish_weight
        max_weight = max(bullish_weight, bearish_weight) if total_weight > 0 else 0
        confidence = (max_weight / total_weight * 100) if total_weight > 0 else 0

        # Calculate weight utilization
        available_count = len(available_levels)
        total_count = len(self.levels)
        utilization = available_count / total_count if total_count > 0 else 0

        # Build output
        result = {
            'metadata': {
                'instrument': self.instrument,
                'timezone': self.timezone,
                'timestamp': current_time.isoformat(),
                'current_price': round(current_price, 2),
                'data_points': len(df)
            },
            'analysis': {
                'bias': bias,
                'confidence': round(confidence, 2),
                'bullish_weight': round(bullish_weight, 4),
                'bearish_weight': round(bearish_weight, 4)
            },
            'weights': {
                'available_levels': available_count,
                'total_levels': total_count,
                'utilization': round(utilization, 4)
            },
            'levels': [l.to_dict() for l in available_levels]
        }

        return result

    def _empty_result(self, timestamp: str = None) -> Dict[str, Any]:
        """Return empty analysis result when data is insufficient."""
        return {
            'metadata': {
                'instrument': self.instrument,
                'timezone': self.timezone,
                'timestamp': timestamp or datetime.now(self.tz).isoformat(),
                'current_price': 0.0,
                'data_points': 0
            },
            'analysis': {
                'bias': 'BULLISH',  # Default to BULLISH when no data
                'confidence': 0.0,
                'bullish_weight': 0.0,
                'bearish_weight': 0.0
            },
            'weights': {
                'available_levels': 0,
                'total_levels': len(self.levels),
                'utilization': 0.0
            },
            'levels': []
        }


class OutputFormatter:
    """Formats prediction results for various output formats."""

    @staticmethod
    def format_json(result: Dict) -> Dict:
        """Format result as JSON-compatible dictionary."""
        return result

    @staticmethod
    def format_csv(result: Dict) -> str:
        """Format levels as CSV string."""
        if not result.get('levels'):
            return 'name,price,position,distance_percent,effective_weight,direction'

        lines = ['name,price,position,distance_percent,effective_weight,direction']

        for level in result['levels']:
            line = f"{level['name']},{level['price']},{level['position']},{level['distance_percent']},{level['effective_weight']},{level['direction']}"
            lines.append(line)

        return '\n'.join(lines)

    @staticmethod
    def format_summary(result: Dict) -> str:
        """Format result as human-readable summary."""
        analysis = result['analysis']
        metadata = result['metadata']

        summary = f"""
PREDICTION ANALYSIS - {metadata['instrument']}
{'=' * 50}
Timestamp: {metadata['timestamp']}
Current Price: ${metadata['current_price']:.2f}
Data Points: {metadata['data_points']}

ANALYSIS RESULTS
{'-' * 50}
Directional Bias: {analysis['bias']}
Confidence Score: {analysis['confidence']:.2f}%
Bullish Weight: {analysis['bullish_weight']:.4f}
Bearish Weight: {analysis['bearish_weight']:.4f}

WEIGHT UTILIZATION
{'-' * 50}
Available Levels: {result['weights']['available_levels']}/{result['weights']['total_levels']}
Utilization Rate: {result['weights']['utilization']:.2%}
"""
        return summary


if __name__ == '__main__':
    # Example usage
    print("Prediction Model v3.0 - Testing")
    print("=" * 50)

    # Create sample data
    dates = pd.date_range('2025-11-19 14:00', periods=100, freq='1min', tz='UTC')
    data = {
        'open': [24500 + i * 0.5 for i in range(100)],
        'high': [24525 + i * 0.5 for i in range(100)],
        'low': [24490 + i * 0.5 for i in range(100)],
        'close': [24512 + i * 0.5 for i in range(100)]
    }
    df = pd.DataFrame(data, index=dates)

    # Run analysis
    engine = PredictionEngine(instrument='US100')
    result = engine.analyze(df)

    # Display results
    formatter = OutputFormatter()
    print(formatter.format_summary(result))
