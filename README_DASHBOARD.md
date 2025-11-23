# Financial Prediction Dashboard

A **Streamlit-based web application** for the Prediction Model v3.0 that allows users to upload CSV price data and analyze market predictions using the reference level system.

## Features

✅ **CSV File Upload**
- Drag-and-drop or browse interface
- Automatic file validation
- Support for OHLCV data format

✅ **Instrument Auto-Detection**
- Automatic identification from filename (NQ, ES, UK100)
- Timezone-aware analysis
- Support for US100 (NASDAQ), ES (S&P 500), UK100 (FTSE)

✅ **Real-time Prediction Analysis**
- Reference level calculation
- Weight distribution analysis
- Confidence scoring
- 20-level reference system visualization

✅ **Interactive Results**
- Bias indication (BULLISH/BEARISH/NEUTRAL)
- Confidence metrics
- Weight analysis
- Sortable reference levels table

✅ **Data Export**
- JSON export for raw data
- CSV export of reference levels
- Easy download and sharing

✅ **Analysis History**
- Track previous analyses
- View historical predictions
- Compare results over time

## Setup & Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- `streamlit` - Web UI framework
- `pandas` - Data processing
- `numpy` - Numerical computing
- `pytz` - Timezone handling
- `plotly` - Interactive charts
- `python-dateutil` - Date utilities

### Step 2: Verify Files

Ensure these files are in the project directory:

```
.
├── app.py                              # Main Streamlit application
├── requirements.txt                    # Python dependencies
├── extract_and_analyze.py             # Data extraction utility
├── prediction_model_v3.py             # Core prediction engine
├── instrument_identifier.py           # Instrument detection
├── prediction_model_v3.0_refined.md   # Model documentation
└── README_DASHBOARD.md                # This file
```

### Step 3: Run the Application

```bash
streamlit run app.py
```

The application will:
1. Start a local server (typically at `http://localhost:8501`)
2. Automatically open in your browser
3. Show the Financial Prediction Dashboard

## Usage Guide

### Basic Workflow

#### Step 1: Upload CSV File

1. Click on "Browse files" or drag a CSV file into the upload area
2. Ensure your CSV contains these columns:
   - `time` - ISO 8601 format timestamp (e.g., `2025-11-19T14:30:00Z`)
   - `open` - Opening price for the candle
   - `high` - Highest price in the period
   - `low` - Lowest price in the period
   - `close` - Closing price for the candle

**Example CSV Format:**
```csv
time,open,high,low,close
2025-11-19T19:31:00Z,21500.5,21505.0,21498.0,21502.3
2025-11-19T19:32:00Z,21502.0,21508.0,21501.0,21506.5
2025-11-19T19:33:00Z,21506.0,21510.5,21505.0,21509.8
```

#### Step 2: Review Data

- Preview the first 10 rows of your data
- Verify file size and column count
- Ensure data looks correct

#### Step 3: Run Analysis

- Click the "🔍 Analyze Data" button
- Wait for the prediction engine to process
- Results will display automatically

#### Step 4: View Results

The dashboard shows:
- **Directional Bias:** BULLISH/BEARISH/NEUTRAL
- **Confidence Score:** 0-100% prediction strength
- **Weight Distribution:** Bullish vs Bearish weight percentages
- **Reference Levels:** 20 price levels with details
- **Metadata:** Instrument, price, timestamp, timezone

#### Step 5: Export Results

- Download results as **JSON** for raw data
- Download **CSV** of reference levels
- Share or archive results

### Advanced Features

#### View Analysis History

1. Switch to "View History" mode in the sidebar
2. See all previous analyses
3. Click to expand any result for full details

#### Instrument Detection

The dashboard automatically detects instruments from filename:

| Filename Pattern | Instrument | Timezone |
|-----------------|------------|----------|
| `NQ`, `US100`, `NASDAQ` | US100 (NASDAQ-100) | America/New_York |
| `ES`, `SPX` | ES (S&P 500) | America/Chicago |
| `UK100`, `FTSE` | UK100 (FTSE 100) | Europe/London |

If your filename doesn't match, the default is **US100**.

## Data Format Requirements

### CSV Structure

**Required Columns:**
- `time` - Timestamp in ISO 8601 format with timezone (UTC or instrument timezone)
- `open` - Float/decimal number
- `high` - Float/decimal number (should be >= open and close)
- `low` - Float/decimal number (should be <= open and close)
- `close` - Float/decimal number

**Optional Columns:**
- `volume` - Trading volume (not required, will be ignored)
- Any other columns will be preserved but not used

### Data Quality Guidelines

- **Minimum data:** 100+ candles recommended for accurate reference level calculation
- **Timestamp format:** ISO 8601 (e.g., `2025-11-19T14:30:00Z` or `2025-11-19T14:30:00-05:00`)
- **Time intervals:** Typically 1-minute bars, but works with any interval
- **No gaps:** Data should be continuous without missing bars
- **Valid OHLC:** High >= Max(Open, Close); Low <= Min(Open, Close)

## Output Explanation

### Directional Bias

- **BULLISH (▲)** - More price signals above reference levels
- **BEARISH (▼)** - More price signals below reference levels
- **NEUTRAL (→)** - Balanced signals, no clear direction

### Confidence Score

- **0-30%:** Weak signal (use caution)
- **30-60%:** Moderate signal (proceed carefully)
- **60-100%:** Strong signal (high confidence)

The confidence reflects how concentrated the weighted signals are. High confidence means clear directional agreement; low confidence means ambiguous signals.

### Reference Levels

The system calculates 20 reference levels based on:

**Always Available (14 levels):**
- Daily midnight, previous hourly, 2-hour/4-hour opens
- NY pre-open (7:00 AM) and open (9:30 AM)
- Previous day/week high, low, and opens
- Monthly open

**Conditional (6 levels):**
- Asian range high/low (available after midnight ET)
- London range high/low (available after 11 AM ET)
- NY range high/low (available after 2 PM ET)

For each level:
- **Price:** The calculated level price
- **Distance (%):** How far current price is from the level
- **Position:** ABOVE or BELOW current price
- **Depreciation:** Weight adjustment based on distance
- **Effective Weight:** Final weight used in calculation

### Weight Utilization

Percentage of available levels currently in use. Depends on time of day (some conditional levels only available at certain times).

## Troubleshooting

### ❌ "Missing required columns"
**Solution:** Ensure your CSV has exactly these column names (lowercase):
- `time`, `open`, `high`, `low`, `close`

### ❌ "Analysis failed" error
**Possible causes:**
1. Invalid timestamp format - use ISO 8601 format (e.g., `2025-11-19T14:30:00Z`)
2. Missing data - ensure all rows have values for open, high, low, close
3. Insufficient data - provide at least 100 candles

**Solution:** Check the error details in the expanded section.

### ❌ Application won't start
**Solution:**
```bash
# Verify installation
pip install --upgrade streamlit pandas numpy

# Try running again
streamlit run app.py
```

### ❌ Instrument not detected correctly
**Solution:** Rename your file to include instrument code:
- `data_NQ_20251119.csv` → US100
- `data_ES_20251119.csv` → ES
- `data_UK100_20251119.csv` → UK100

## Performance

- **Analysis Time:** 2-5 seconds for typical datasets (1000+ candles)
- **Max File Size:** ~50 MB (roughly 50,000 1-minute candles)
- **Concurrent Users:** Single user (local/simple deployment)

## File Structure

```
Final/
├── app.py                              # Main Streamlit app
├── requirements.txt                    # Dependencies
├── extract_and_analyze.py             # Data extraction
├── prediction_model_v3.py             # Prediction engine
├── instrument_identifier.py           # Instrument detection
├── prediction_model_v3.0_refined.md   # Model specs
├── EXTRACTION_GUIDE.md                # Extraction documentation
├── EXTRACTION_SUMMARY.md              # Project summary
├── WORKFLOW_DIAGRAM.md                # Workflow visualization
└── README_DASHBOARD.md                # This file
```

## Model Information

This dashboard uses **Prediction Model v3.0**, a reference level-based analytical framework that:

1. **Calculates 20 reference price levels** based on daily/hourly/session ranges
2. **Determines current price position** relative to each level (above/below)
3. **Applies distance-based depreciation** to weight remote levels less
4. **Aggregates weighted signals** into directional bias
5. **Scores confidence** based on signal concentration

**Key Features:**
- Deterministic and transparent calculations
- Works across multiple instruments (US100, ES, UK100)
- Timezone-aware for accurate level calculations
- Time-dependent level availability
- No subjective interpretation

For complete technical details, see `prediction_model_v3.0_refined.md`.

## Limitations

- **Single-user application** - Designed for local use or single analyst
- **No real-time updates** - Re-upload CSV to get latest analysis
- **No persistent storage** - Session history cleared when app restarts
- **Stateless analysis** - Each analysis is independent

## Future Enhancements

Possible improvements (not included in current version):

- [ ] Database storage for historical predictions
- [ ] Real-time data feed integration
- [ ] Multi-user support with authentication
- [ ] Advanced confidence scoring (volatility-adjusted)
- [ ] Statistical model ensemble (ARIMA, Prophet)
- [ ] Backtesting and performance tracking
- [ ] PDF report generation
- [ ] Live WebSocket updates

## Support & Documentation

- **Model Documentation:** See `prediction_model_v3.0_refined.md`
- **Extraction Guide:** See `EXTRACTION_GUIDE.md`
- **Workflow Diagrams:** See `WORKFLOW_DIAGRAM.md`

## License & Disclaimer

This tool is provided for analytical and educational purposes. Predictions are based on mathematical calculations and do not constitute investment advice. Past performance does not guarantee future results.

Always perform your own analysis and consult with financial professionals before making trading decisions.

---

**Version:** 1.0
**Last Updated:** November 20, 2025
**Prediction Model:** v3.0
