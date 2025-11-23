# Quick Start Guide - Financial Prediction Dashboard

Get the dashboard up and running in 5 minutes!

## Prerequisites

- Python 3.8+ installed
- Terminal/Command Prompt access

## Installation (3 steps)

### 1. Install Dependencies

```bash
cd /Users/soonjeongguan/Desktop/Repository/CLAUDECODE/Final
pip install -r requirements.txt
```

**Expected output:**
```
Successfully installed streamlit-1.28.1 pandas-2.1.1 numpy-1.24.3 ...
```

### 2. Verify Required Files

Check that these files exist in the directory:
- ✅ `app.py`
- ✅ `extract_and_analyze.py`
- ✅ `prediction_model_v3.py`
- ✅ `instrument_identifier.py`
- ✅ `requirements.txt`

### 3. Start the Application

```bash
streamlit run app.py
```

**Expected output:**
```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

The app will automatically open in your browser at `http://localhost:8501`

---

## First Test (5 minutes)

### 1. Upload Sample Data

1. In the dashboard, click **"Browse files"**
2. Select `sample_data_NQ.csv` from the same directory
3. Click **"Analyze Data"** button

### 2. View Results

The dashboard will display:
- ✅ Directional bias (BULLISH/BEARISH/NEUTRAL)
- ✅ Confidence score
- ✅ Weight distribution
- ✅ 20 reference levels table
- ✅ Export options

### 3. Download Results

Click:
- **"📥 Download JSON"** to save raw results
- **"📥 Download Levels CSV"** to save the levels table

---

## Using Your Own Data

### CSV Format Required

Your file must have these exact column names (lowercase):

```csv
time,open,high,low,close
2025-11-19T14:00:00Z,24500.00,24525.50,24490.00,24512.75
2025-11-19T14:01:00Z,24512.50,24535.00,24510.00,24530.25
```

**Column Details:**
- `time` - ISO 8601 format: `2025-11-19T14:30:00Z` or `2025-11-19T14:30:00-05:00`
- `open`, `high`, `low`, `close` - Decimal numbers

### Filename Instrument Detection

The dashboard auto-detects instrument from your filename:

| Filename Contains | Detects As | Timezone |
|------------------|-----------|----------|
| `NQ` or `US100` | US100 (NASDAQ) | America/New_York |
| `ES` | ES (S&P 500) | America/Chicago |
| `UK100` or `FTSE` | UK100 (FTSE) | Europe/London |

**Example:** `ES_data_20251119.csv` → Automatically uses ES settings

---

## Common Issues & Fixes

### Issue: "Missing required columns"

**Check:** Does your CSV have these exact columns?
- `time`
- `open`
- `high`
- `low`
- `close`

**Fix:** Rename columns in your CSV or create it in the correct format.

### Issue: "Analysis failed" error

**Check:**
1. Are timestamps in ISO 8601 format? (e.g., `2025-11-19T14:30:00Z`)
2. Are all rows complete? (no missing values)
3. Do you have at least 100 rows of data?

**Fix:**
```bash
# Verify CSV format
head -2 your_file.csv
```

### Issue: Module not found error

**Check:** Are all 4 Python files in the same directory?
- `extract_and_analyze.py`
- `prediction_model_v3.py`
- `instrument_identifier.py`

**Fix:**
```bash
ls -la *.py
# Should show all 4 files
```

### Issue: "ModuleNotFoundError: No module named 'streamlit'"

**Fix:**
```bash
pip install --upgrade streamlit pandas
streamlit run app.py
```

---

## What the Dashboard Does

1. **Receives CSV** with price data (OHLCV)
2. **Identifies instrument** from filename
3. **Calculates 20 reference levels** (daily/hourly/session ranges)
4. **Determines price position** relative to each level
5. **Weights the signals** based on distance and availability
6. **Generates bias & confidence** score
7. **Displays results** in interactive dashboard

---

## Next Steps

- 📖 **Full docs:** Read `README_DASHBOARD.md`
- 📚 **Model specs:** See `prediction_model_v3.0_refined.md`
- 🔧 **Technical details:** Check `EXTRACTION_GUIDE.md`

---

## Stop the Application

Press `Ctrl+C` in the terminal to stop:

```
Shutting down...
Bye!
```

To restart: `streamlit run app.py`

---

**Version:** 1.0
**Last Updated:** November 20, 2025
**Prediction Model:** v3.0
