#!/usr/bin/env python3
"""
Instrument Identifier Module

Identifies financial instruments from filename patterns and returns
the appropriate instrument code and default timezone.

Supported Instruments:
- NQ, US100, NDX, NASDAQ → US100 (NASDAQ-100)
- ES, SPX → ES (S&P 500)
- UK100, FTSE, GER40 → UK100/GER40 (European indices)
"""

import re
from pathlib import Path


def identify_instrument_from_file(filepath):
    """
    Identify instrument from filename.

    Args:
        filepath (str): Path to the CSV file

    Returns:
        tuple: (instrument_code, default_timezone)

    Examples:
        >>> identify_instrument_from_file('data_NQ_20251119.csv')
        ('US100', 'America/New_York')

        >>> identify_instrument_from_file('ES_prices.csv')
        ('ES', 'America/Chicago')
    """

    # Extract filename from path
    filename = Path(filepath).name.upper()

    # Define instrument patterns and their properties
    instruments = {
        # NASDAQ-100 (US100)
        'US100': {
            'patterns': [r'US100', r'NQ', r'NDX', r'NASDAQ'],
            'code': 'US100',
            'timezone': 'America/New_York',
            'name': 'NASDAQ-100 E-Mini Futures'
        },
        # S&P 500 (ES)
        'ES': {
            'patterns': [r'ES\b', r'\bES\b', r'SPX', r'SP500', r'S&P'],
            'code': 'ES',
            'timezone': 'America/Chicago',
            'name': 'S&P 500 E-Mini Futures'
        },
        # FTSE 100 (UK100)
        'UK100': {
            'patterns': [r'UK100', r'FTSE', r'FTSE100', r'FTSE\s*100'],
            'code': 'UK100',
            'timezone': 'Europe/London',
            'name': 'FTSE 100 Index'
        },
        # DAX (Germany)
        'GER40': {
            'patterns': [r'GER40', r'DAX', r'GER\s*40'],
            'code': 'GER40',
            'timezone': 'Europe/Berlin',
            'name': 'DAX Index'
        },
    }

    # Try to match patterns in order of specificity
    # Check each instrument's patterns
    for instrument_key, instrument_info in instruments.items():
        for pattern in instrument_info['patterns']:
            if re.search(pattern, filename):
                return (instrument_info['code'], instrument_info['timezone'])

    # Default fallback
    return ('US100', 'America/New_York')


def get_instrument_info(instrument_code):
    """
    Get detailed information about an instrument.

    Args:
        instrument_code (str): Code like 'US100', 'ES', 'UK100'

    Returns:
        dict: Instrument information including timezone, name, etc.
    """

    instruments = {
        'US100': {
            'name': 'NASDAQ-100 E-Mini Futures',
            'symbol': 'NQ',
            'exchange': 'CME',
            'timezone': 'America/New_York',
            'session_open': '17:00',  # 5:00 PM ET (Sunday-Friday)
            'session_close': '16:00',  # 4:00 PM ET
            'description': 'Tracks the NASDAQ-100 index'
        },
        'ES': {
            'name': 'S&P 500 E-Mini Futures',
            'symbol': 'ES',
            'exchange': 'CME',
            'timezone': 'America/Chicago',
            'session_open': '17:00',  # 5:00 PM CT (Sunday-Friday)
            'session_close': '16:00',  # 4:00 PM CT
            'description': 'Tracks the S&P 500 index'
        },
        'UK100': {
            'name': 'FTSE 100 Index',
            'symbol': 'FTSE',
            'exchange': 'LSE',
            'timezone': 'Europe/London',
            'session_open': '08:00',
            'session_close': '16:30',
            'description': 'Tracks the FTSE 100 index'
        },
        'GER40': {
            'name': 'DAX Index',
            'symbol': 'DAX',
            'exchange': 'Xetra',
            'timezone': 'Europe/Berlin',
            'session_open': '09:00',
            'session_close': '17:30',
            'description': 'Tracks the DAX index'
        }
    }

    return instruments.get(instrument_code, {
        'name': 'Unknown Instrument',
        'symbol': instrument_code,
        'exchange': 'Unknown',
        'timezone': 'UTC',
        'description': f'Instrument: {instrument_code}'
    })


def validate_instrument(instrument_code):
    """
    Check if an instrument code is valid.

    Args:
        instrument_code (str): Instrument code to validate

    Returns:
        bool: True if valid, False otherwise
    """

    valid_instruments = ['US100', 'ES', 'UK100', 'GER40']
    return instrument_code in valid_instruments


if __name__ == '__main__':
    # Test the module
    test_files = [
        'data_NQ_20251119.csv',
        'ES_prices_20251119.csv',
        'FTSE_UK100_data.csv',
        'nasdaq_data.csv'
    ]

    print("Instrument Identifier Test")
    print("=" * 50)

    for filename in test_files:
        instrument, timezone = identify_instrument_from_file(filename)
        info = get_instrument_info(instrument)
        print(f"\nFile: {filename}")
        print(f"  Instrument: {instrument}")
        print(f"  Name: {info['name']}")
        print(f"  Timezone: {timezone}")
