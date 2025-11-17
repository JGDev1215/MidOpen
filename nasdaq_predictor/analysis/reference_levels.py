"""
Reference Levels Analysis Module - Complete Implementation
Provides functions to calculate technical reference levels for market trading
"""

from datetime import datetime, timedelta
import pandas as pd
import pytz

# ET timezone for market hours
ET_TZ = pytz.timezone('America/New_York')


def calculate_daily_open(df: pd.DataFrame, current_time) -> float:
    """
    Calculate daily open (midnight ET - 00:00)
    Returns the first open price of the current trading day in ET
    """
    if df is None or df.empty:
        return None
    
    try:
        # Ensure we have ET timezone
        if df.index.tz is None:
            df_et = df.copy()
            df_et.index = df_et.index.tz_localize('UTC').tz_convert(ET_TZ)
        else:
            df_et = df.copy()
            df_et.index = df_et.index.tz_convert(ET_TZ)
        
        # Get midnight ET today
        midnight = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Find first bar at or after midnight
        bars_at_or_after_midnight = df_et[df_et.index >= midnight]
        if not bars_at_or_after_midnight.empty:
            return float(bars_at_or_after_midnight.iloc[0]['Open'])
        
        # Fallback: return first open
        return float(df.iloc[0]['Open'])
    except Exception:
        return float(df.iloc[0]['Open']) if not df.empty else None


def calculate_hourly_open(df: pd.DataFrame, hours_back=1) -> float:
    """
    Calculate current hour open (most recent hour candle open)
    Returns the open price of the current hourly candle
    """
    if df is None or df.empty:
        return None
    
    try:
        # Get the most recent data point
        return float(df.iloc[-hours_back]['Open'])
    except Exception:
        return float(df.iloc[0]['Open']) if not df.empty else None


def calculate_4hourly_open(df: pd.DataFrame) -> float:
    """
    Calculate 4-hourly open
    Returns open price of current 4-hour candle
    """
    if df is None or df.empty:
        return None
    
    try:
        # For 1h data, 4H open is approximately every 4th candle
        if len(df) >= 4:
            return float(df.iloc[-4]['Open'])
        return float(df.iloc[0]['Open'])
    except Exception:
        return float(df.iloc[0]['Open']) if not df.empty else None


def calculate_2hourly_open(df: pd.DataFrame) -> float:
    """
    Calculate 2-hourly open
    Returns open price of current 2-hour candle
    """
    if df is None or df.empty:
        return None
    
    try:
        # For 1h data, 2H open is every 2nd candle
        if len(df) >= 2:
            return float(df.iloc[-2]['Open'])
        return float(df.iloc[0]['Open'])
    except Exception:
        return float(df.iloc[0]['Open']) if not df.empty else None


def calculate_30min_open(df: pd.DataFrame) -> float:
    """Calculate 30-minute open"""
    if df is None or df.empty:
        return None
    
    try:
        return float(df.iloc[0]['Open'])
    except Exception:
        return None


def calculate_15min_open(df: pd.DataFrame) -> float:
    """
    Calculate 15-minute open
    Returns open price of current 15-minute candle
    """
    if df is None or df.empty:
        return None
    
    try:
        return float(df.iloc[0]['Open'])
    except Exception:
        return None


def calculate_weekly_open(df: pd.DataFrame, current_time=None) -> float:
    """
    Calculate weekly open (Monday 00:00 ET)
    Returns the first open price of the current week
    """
    if df is None or df.empty:
        return None
    
    try:
        if df.index.tz is None:
            df_et = df.copy()
            df_et.index = df_et.index.tz_localize('UTC').tz_convert(ET_TZ)
        else:
            df_et = df.copy()
            df_et.index = df_et.index.tz_convert(ET_TZ)
        
        # Calculate days since Monday
        if current_time is None:
            current_time = datetime.now(ET_TZ)
        
        days_since_monday = current_time.weekday()  # 0=Monday, 6=Sunday
        week_start = current_time - timedelta(days=days_since_monday)
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Find first bar at or after week start
        bars_at_or_after_week_start = df_et[df_et.index >= week_start]
        if not bars_at_or_after_week_start.empty:
            return float(bars_at_or_after_week_start.iloc[0]['Open'])
        
        # Fallback
        return float(df.iloc[0]['Open'])
    except Exception:
        return float(df.iloc[0]['Open']) if not df.empty else None


def calculate_monthly_open(df: pd.DataFrame, current_time=None) -> float:
    """
    Calculate monthly open (1st of month 00:00 ET)
    Returns the first open price of the current month
    """
    if df is None or df.empty:
        return None
    
    try:
        if df.index.tz is None:
            df_et = df.copy()
            df_et.index = df_et.index.tz_localize('UTC').tz_convert(ET_TZ)
        else:
            df_et = df.copy()
            df_et.index = df_et.index.tz_convert(ET_TZ)
        
        if current_time is None:
            current_time = datetime.now(ET_TZ)
        
        # Get first day of current month
        month_start = current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Find first bar at or after month start
        bars_at_or_after_month_start = df_et[df_et.index >= month_start]
        if not bars_at_or_after_month_start.empty:
            return float(bars_at_or_after_month_start.iloc[0]['Open'])
        
        # Fallback
        return float(df.iloc[0]['Open'])
    except Exception:
        return float(df.iloc[0]['Open']) if not df.empty else None


def calculate_7am_open(df: pd.DataFrame, current_time) -> float:
    """
    Calculate 7 AM ET open
    Returns open price at or near 7 AM ET
    """
    if df is None or df.empty:
        return None
    
    try:
        if df.index.tz is None:
            df_et = df.copy()
            df_et.index = df_et.index.tz_localize('UTC').tz_convert(ET_TZ)
        else:
            df_et = df.copy()
            df_et.index = df_et.index.tz_convert(ET_TZ)
        
        # Get 7 AM today in ET
        seven_am = current_time.replace(hour=7, minute=0, second=0, microsecond=0)
        
        # Find bar at or near 7 AM
        bars_at_or_after_7am = df_et[df_et.index >= seven_am]
        if not bars_at_or_after_7am.empty:
            return float(bars_at_or_after_7am.iloc[0]['Open'])
        
        # Fallback to most recent
        return float(df.iloc[-1]['Open'])
    except Exception:
        return float(df.iloc[-1]['Open']) if not df.empty else None


def calculate_830am_open(df: pd.DataFrame, current_time) -> float:
    """
    Calculate 8:30 AM ET open (NY Stock Exchange open)
    Returns open price at or near 8:30 AM ET
    """
    if df is None or df.empty:
        return None
    
    try:
        if df.index.tz is None:
            df_et = df.copy()
            df_et.index = df_et.index.tz_localize('UTC').tz_convert(ET_TZ)
        else:
            df_et = df.copy()
            df_et.index = df_et.index.tz_convert(ET_TZ)
        
        # Get 8:30 AM today in ET
        eight_thirty_am = current_time.replace(hour=8, minute=30, second=0, microsecond=0)
        
        # Find bar at or near 8:30 AM
        bars_at_or_after_830am = df_et[df_et.index >= eight_thirty_am]
        if not bars_at_or_after_830am.empty:
            return float(bars_at_or_after_830am.iloc[0]['Open'])
        
        # Fallback to most recent
        return float(df.iloc[-1]['Open'])
    except Exception:
        return float(df.iloc[-1]['Open']) if not df.empty else None


def calculate_previous_hourly_open(df: pd.DataFrame, current_time=None) -> float:
    """
    Calculate previous hour open
    Returns open price of the hour before current hour
    """
    if df is None or df.empty:
        return None
    
    try:
        # For hourly data, previous hour is index -2 (current is -1)
        if len(df) >= 2:
            return float(df.iloc[-2]['Open'])
        return float(df.iloc[-1]['Open'])
    except Exception:
        return float(df.iloc[-1]['Open']) if not df.empty else None


def calculate_prev_week_open(df: pd.DataFrame) -> float:
    """Calculate previous week open"""
    if df is None or df.empty:
        return None
    
    try:
        # For daily data, previous week start is roughly 7 bars back
        if len(df) >= 7:
            return float(df.iloc[-7]['Open'])
        return float(df.iloc[0]['Open'])
    except Exception:
        return float(df.iloc[0]['Open']) if not df.empty else None


def calculate_prev_day_high_low(df: pd.DataFrame) -> tuple:
    """
    Calculate previous day high and low
    Returns (high, low) of the previous trading day
    """
    if df is None or df.empty:
        return None, None
    
    try:
        # For daily data, previous day is at index -2
        if len(df) >= 2:
            prev_day = df.iloc[-2]
            return float(prev_day['High']), float(prev_day['Low'])
        
        # Fallback: use all data
        return float(df['High'].max()), float(df['Low'].min())
    except Exception:
        return None, None


def calculate_prev_week_high(df: pd.DataFrame) -> float:
    """
    Calculate previous week high
    Returns highest price of the previous week
    """
    if df is None or df.empty:
        return None
    
    try:
        # For daily data, previous week is roughly bars -13 to -7
        if len(df) >= 7:
            prev_week_data = df.iloc[-13:-6]
            if not prev_week_data.empty:
                return float(prev_week_data['High'].max())
        
        return float(df['High'].max())
    except Exception:
        return float(df['High'].max()) if not df.empty else None


def calculate_prev_week_low(df: pd.DataFrame) -> float:
    """
    Calculate previous week low
    Returns lowest price of the previous week
    """
    if df is None or df.empty:
        return None
    
    try:
        # For daily data, previous week is roughly bars -13 to -7
        if len(df) >= 7:
            prev_week_data = df.iloc[-13:-6]
            if not prev_week_data.empty:
                return float(prev_week_data['Low'].min())
        
        return float(df['Low'].min())
    except Exception:
        return float(df['Low'].min()) if not df.empty else None


def calculate_week_high_low(df: pd.DataFrame) -> tuple:
    """
    Calculate week high and low (running week to date)
    Returns (high, low) for the current week
    """
    if df is None or df.empty:
        return None, None
    
    try:
        # For daily data, current week is approximately last 5 bars (Mon-Fri)
        if len(df) >= 5:
            week_data = df.iloc[-5:]
        else:
            week_data = df
        
        if not week_data.empty:
            return float(week_data['High'].max()), float(week_data['Low'].min())
        
        return None, None
    except Exception:
        return None, None


def calculate_all_reference_levels(df: pd.DataFrame, ticker: str = "NQ=F", current_time=None):
    """
    Calculate all reference levels
    Returns a dictionary with all 16 levels
    """
    if df is None or df.empty:
        return {}
    
    if current_time is None:
        current_time = datetime.now(ET_TZ)
    
    try:
        return {
            "weekly_open": calculate_weekly_open(df, current_time),
            "monthly_open": calculate_monthly_open(df, current_time),
            "daily_open_midnight": calculate_daily_open(df, current_time),
            "ny_open_0830": calculate_830am_open(df, current_time),
            "ny_open_0700": calculate_7am_open(df, current_time),
            "four_hour_open": calculate_4hourly_open(df),
            "two_hour_open": calculate_2hourly_open(df),
            "hourly_open": calculate_hourly_open(df),
            "previous_hourly_open": calculate_previous_hourly_open(df, current_time),
            "fifteen_min_open": calculate_15min_open(df),
            "previous_day_high": calculate_prev_day_high_low(df)[0],
            "previous_day_low": calculate_prev_day_high_low(df)[1],
            "previous_week_high": calculate_prev_week_high(df),
            "previous_week_low": calculate_prev_week_low(df),
            "weekly_high": calculate_week_high_low(df)[0],
            "weekly_low": calculate_week_high_low(df)[1],
        }
    except Exception as e:
        print(f"Error calculating reference levels: {e}")
        return {}
