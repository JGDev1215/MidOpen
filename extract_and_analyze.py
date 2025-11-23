#!/usr/bin/env python3
"""
Data Extraction Script for Prediction Model v3.0

Extracts price data from CSV files and passes it to the prediction model for analysis.
Handles instrument identification and timezone conversion automatically.

Usage:
    python extract_and_analyze.py <path_to_csv_file> [--timestamp TIMESTAMP]
"""

import argparse
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

# Import from existing modules
from instrument_identifier import identify_instrument_from_file


# Instrument to timezone mapping for prediction model
PREDICTION_MODEL_TIMEZONES = {
    'NQ': 'America/New_York',      # NASDAQ-100 = US100 in prediction model
    'US100': 'America/New_York',
    'NDX': 'America/New_York',
    'ES': 'America/Chicago',
    'SPX': 'America/New_York',
    'UK100': 'Europe/London',
    'GER40': 'Europe/Berlin',
}


class DataExtractor:
    """Extract and prepare price data for prediction model"""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.instrument = None
        self.timezone = None
        self.df = None
        
    def identify_instrument(self):
        """Identify instrument from filename"""
        instrument, timezone = identify_instrument_from_file(self.filepath)
        
        # Map to prediction model instrument names
        instrument_mapping = {
            'NQ': 'US100',
            'NDX': 'US100',
            'NASDAQ': 'US100',
        }
        
        self.instrument = instrument_mapping.get(instrument, instrument)
        
        # Get timezone for prediction model
        if self.instrument in PREDICTION_MODEL_TIMEZONES:
            self.timezone = PREDICTION_MODEL_TIMEZONES[self.instrument]
        else:
            self.timezone = timezone  # Use default from identifier
            
        print(f"✓ Identified instrument: {self.instrument}")
        print(f"✓ Using timezone: {self.timezone}")
        
        return self.instrument, self.timezone
    
    def load_and_parse(self):
        """Load CSV and parse with proper datetime handling"""
        print(f"\nLoading data from: {self.filepath}")
        
        # Read CSV
        self.df = pd.read_csv(self.filepath)
        
        # Validate required columns
        required_cols = ['time', 'open', 'high', 'low', 'close']
        missing = set(required_cols) - set(self.df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        
        # Parse time column - handle UTC timestamps
        self.df['time'] = pd.to_datetime(self.df['time'], utc=True)
        self.df.set_index('time', inplace=True)
        
        # Convert to target timezone
        self.df.index = self.df.index.tz_convert(self.timezone)
        
        print(f"✓ Loaded {len(self.df)} candles")
        print(f"✓ Date range: {self.df.index[0]} to {self.df.index[-1]}")
        print(f"✓ Latest price: {self.df.iloc[-1]['close']:.2f}")
        
        return self.df
    
    def get_latest_timestamp(self):
        """Get the latest timestamp from the data"""
        if self.df is None:
            raise ValueError("Data not loaded. Call load_and_parse() first.")
        
        return str(self.df.index[-1])
    
    def prepare_for_prediction(self, timestamp: str = None):
        """
        Prepare data for prediction model
        
        Args:
            timestamp: Optional specific timestamp to analyze. 
                      If None, uses latest timestamp in data.
        
        Returns:
            Tuple of (dataframe, timestamp_string)
        """
        if timestamp is None:
            timestamp = self.get_latest_timestamp()
        
        print(f"\n✓ Analysis timestamp: {timestamp}")
        
        return self.df, timestamp


def main():
    """Main execution"""
    parser = argparse.ArgumentParser(
        description='Extract price data and pass to Prediction Model v3.0'
    )
    
    parser.add_argument(
        'filepath',
        help='Path to CSV file with price data'
    )
    
    parser.add_argument(
        '--timestamp',
        help='Specific timestamp to analyze (ISO format). Uses latest if not specified.',
        default=None
    )
    
    parser.add_argument(
        '--show-data',
        action='store_true',
        help='Show first/last few rows of data'
    )
    
    args = parser.parse_args()
    
    # Validate file exists
    if not Path(args.filepath).exists():
        print(f"ERROR: File not found: {args.filepath}")
        sys.exit(1)
    
    print("=" * 60)
    print("DATA EXTRACTION FOR PREDICTION MODEL v3.0")
    print("=" * 60)
    
    try:
        # Initialize extractor
        extractor = DataExtractor(args.filepath)
        
        # Step 1: Identify instrument
        instrument, timezone = extractor.identify_instrument()
        
        # Step 2: Load and parse data
        df = extractor.load_and_parse()
        
        # Show data preview if requested
        if args.show_data:
            print("\nFirst 5 candles:")
            print(df.head())
            print("\nLast 5 candles:")
            print(df.tail())
        
        # Step 3: Prepare for prediction
        df_prepared, timestamp = extractor.prepare_for_prediction(args.timestamp)
        
        print("\n" + "=" * 60)
        print("DATA READY FOR PREDICTION MODEL")
        print("=" * 60)
        print(f"Instrument: {instrument}")
        print(f"Timezone: {timezone}")
        print(f"Candles: {len(df_prepared)}")
        print(f"Analysis timestamp: {timestamp}")
        print(f"Current price: {df_prepared.iloc[-1]['close']:.2f}")
        
        # Now pass to prediction model
        print("\n" + "=" * 60)
        print("PASSING TO PREDICTION MODEL...")
        print("=" * 60)
        
        # Import and run prediction model
        from prediction_model_v3 import PredictionEngine, OutputFormatter
        
        # Map instrument for prediction engine
        prediction_instrument = "US100" if instrument in ['NQ', 'US100', 'NDX'] else instrument
        
        # Initialize engine
        engine = PredictionEngine(instrument=prediction_instrument)
        
        # Run analysis
        result = engine.analyze(df_prepared, timestamp)
        
        # Format and display output
        formatter = OutputFormatter()
        console_output = formatter.to_console(result)
        
        print()
        print(console_output)
        
        # Save JSON output
        output_file = f'prediction_result_{instrument}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        json_output = formatter.to_json(result)
        with open(output_file, 'w') as f:
            f.write(json_output)
        
        print()
        print(f"✓ JSON output saved to: {output_file}")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
