# Price Data Gaps Analysis & Remediation Strategy

## Executive Summary

When users upload CSV files with incomplete price history (e.g., 1-minute chart data covering only the latest hour), the current script lacks mechanisms to:
1. **Detect** when reference level prices are stale/expired
2. **Validate** that fallback prices are still relevant for the current market context
3. **Prevent** analysis using outdated reference points

This document outlines the problem, current behavior, and a comprehensive remediation strategy.

---

## Part 1: Problem Analysis

### 1.1 The Gap Issue

**Scenario:** User uploads 1-minute price data for US100 (NQ) covering only the last 1 hour

```
CSV Contains:
- Latest 60 x 1-minute candles (most recent: 2025-11-25 14:00 UTC)
- Data range: 2025-11-25 13:00 UTC → 2025-11-25 14:00 UTC

Missing Data:
- Daily Midnight Open (2025-11-25 00:00 UTC) ❌
- 4-hour Open (would be 2025-11-25 12:00 UTC) ❌
- 2-hour Open (would be 2025-11-25 13:00 UTC) - Partially available (just at edge)
- Previous Day High/Low (2025-11-24 data) ❌
- Weekly Open (Monday 2025-11-24 00:00 UTC) ❌
- NY Open (2025-11-25 09:30 ET) ❌ or partially available
```

### 1.2 Reference Levels Requiring Historical Context

| Reference Level | Required Historical Span | Data Gap Risk |
|---|---|---|
| `daily_midnight` | Previous 24 hours | **CRITICAL** - Missing entire previous day |
| `4h_open` | Previous 4 hours | **CRITICAL** - Missing if data < 4 hours old |
| `2h_open` | Previous 2 hours | **HIGH** - Missing if data < 2 hours old |
| `ny_open` (9:30 AM ET) | Current US trading day | **HIGH** - Missing if pre-market or current |
| `weekly_open` | Previous 7 days | **CRITICAL** - Missing if no Monday data |
| `prev_day_high/low` | Previous 24 hours | **CRITICAL** - Incomplete range |
| `asian_range_high/low` | Last 8 hours (00:00-08:00 ET) | **HIGH** - Incomplete |
| `london_range_high/low` | Last 8 hours (03:00-11:00 ET) | **HIGH** - Incomplete |
| `ny_range_high/low` | Last 6.5 hours (09:30-16:00 ET) | **MEDIUM** - Incomplete |

### 1.3 Current Behavior - The Fallback Issue

**What the current script does** (`prediction_model_v3.py`, lines 186-363):

```python
# Example: 4-hour open calculation (line 254-255)
hours_4_back = df.index[-1] - timedelta(hours=4)
data_4h_ago = df[df.index >= hours_4_back]

if len(data_4h_ago) > 0:
    levels_dict['4h_open'] = data_4h_ago['open'].iloc[0]
else:
    levels_dict['4h_open'] = opens.iloc[0]  # Falls back to earliest data
```

**The Problem:**
- ✅ If 1-hour data is available: uses it
- ❌ If 1-hour data is NOT available: uses the earliest available data WITHOUT checking how stale it is
- ❌ No expiry validation - a 4-hour open from 10 hours ago is treated the same as one from 3.5 hours ago

**Example of the Bug:**
```
Scenario:
- Current time: 2025-11-25 14:00 UTC
- Data available: 2025-11-24 12:00 UTC → 2025-11-25 14:00 UTC (26 hours of old data)
- User asks: What is the 4-hour open?

Current behavior:
→ Searches for data >= (14:00 - 4h) = 10:00 UTC on 2025-11-25
→ Finds data from 2025-11-25 10:00 UTC ✓
→ Uses that as 4-hour open ✓ (CORRECT)

BUT if the data is:
- Current time: 2025-11-25 14:00 UTC
- Data available: 2025-11-24 04:00 UTC only (36 hours stale)
- User asks: What is the 4-hour open?

Current behavior:
→ Searches for data >= (14:00 - 4h) = 10:00 UTC
→ Finds nothing recent
→ Falls back to opens.iloc[0] = 2025-11-24 04:00 UTC ✓ (WRONG - 34 hours stale!)
→ Uses this stale data in analysis without any warning ❌
```

---

## Part 2: Current Implementation State

### 2.1 Existing Mechanisms (Partial Solutions)

The codebase DOES have some data quality checks:

1. **CSV Column Validation** (`extract_and_analyze.py`, lines 75-78)
   - Validates required columns exist: `time`, `open`, `high`, `low`, `close`
   - ✅ WORKS: Prevents completely malformed data

2. **Timezone Conversion** (`prediction_model_v3.py`, lines 284-309)
   - Converts all timestamps to instrument timezone
   - ✅ WORKS: Ensures time comparisons are consistent

3. **Empty Result Handling** (`prediction_model_v3.py`, lines 517-539)
   - Returns default analysis when data is insufficient
   - ⚠️ PARTIAL: Detects when result is empty, but not granular per level

4. **Weight Normalization** (`prediction_model_v3.py`, lines 386-396)
   - Re-normalizes available levels to sum to 1.0
   - ✅ WORKS: Maintains weight integrity

### 2.2 What's Missing

- ❌ **No staleness checking**: No validation of fallback data age
- ❌ **No expiry mechanism**: No per-level maximum age constraints
- ❌ **No warnings**: User not informed when using stale fallback data
- ❌ **No data quality scoring**: No confidence metric based on data freshness
- ❌ **No fallback chain**: Only single-level fallback (to earliest available)

---

## Part 3: Remediation Strategy

### 3.1 Implementation Overview

Add a **Data Freshness Validation System** that:

1. **Defines maximum age thresholds** for each reference level
2. **Validates fallback data** against these thresholds
3. **Excludes expired fallback data** from analysis
4. **Tracks data quality** and warns users
5. **Provides user feedback** on data limitations

### 3.2 Step-by-Step Remediation

#### **STEP 1: Define Data Freshness Thresholds**

Create a new configuration in `src/services/config_service.py`:

```python
class DataFreshnessConfig:
    """
    Maximum age thresholds for fallback price data.
    If fallback data exceeds this age, it is considered expired.
    """

    # Format: (level_name, max_age_hours, description)
    FRESHNESS_THRESHOLDS = {
        # Daily/Multi-day levels
        'daily_midnight': (24, "Must be from today or yesterday"),
        'prev_day_high': (48, "Must be from last 2 days"),
        'prev_day_low': (48, "Must be from last 2 days"),
        'weekly_open': (7 * 24, "Must be from current or previous week"),
        'weekly_high': (7 * 24, "Must be from current or previous week"),
        'weekly_low': (7 * 24, "Must be from current or previous week"),
        'prev_week_high': (14 * 24, "Must be from last 2 weeks"),
        'prev_week_low': (14 * 24, "Must be from last 2 weeks"),
        'monthly_open': (30 * 24, "Must be from current or previous month"),

        # Intraday levels - STRICT
        '4h_open': (4.5, "Must be from last 4.5 hours (with 30-min buffer)"),
        '2h_open': (2.5, "Must be from last 2.5 hours (with 30-min buffer)"),

        # Session-specific - STRICT
        'ny_open': (24, "NY market open - reset daily"),
        'ny_preopen': (24, "NY pre-market - reset daily"),
        'asian_range_high': (8.5, "Asian session - 8.5 hours (00:00-08:00 ET)"),
        'asian_range_low': (8.5, "Asian session - 8.5 hours (00:00-08:00 ET)"),
        'london_range_high': (8.5, "London session - 8.5 hours (03:00-11:00 ET)"),
        'london_range_low': (8.5, "London session - 8.5 hours (03:00-11:00 ET)"),
        'ny_range_high': (7, "NY session - 7 hours (09:30-16:30 ET)"),
        'ny_range_low': (7, "NY session - 7 hours (09:30-16:30 ET)"),

        # Hourly - VERY STRICT
        'previous_hourly': (1.5, "Previous hour - must be within 1.5 hours"),
    }
```

#### **STEP 2: Create Freshness Validation Module**

Create new file: `src/services/data_freshness_validator.py`

```python
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
import pytz

class DataFreshnessValidator:
    """
    Validates that fallback price data is not too stale for use.
    """

    def __init__(self, timezone_str: str = 'US/Eastern'):
        self.tz = pytz.timezone(timezone_str)
        self.freshness_config = self._build_freshness_config()

    def _build_freshness_config(self) -> Dict[str, float]:
        """Build dictionary of level -> max_age_hours"""
        return {
            # Daily/Multi-day
            'daily_midnight': 24,
            'prev_day_high': 48,
            'prev_day_low': 48,
            'weekly_open': 7 * 24,
            'weekly_high': 7 * 24,
            'weekly_low': 7 * 24,
            'prev_week_high': 14 * 24,
            'prev_week_low': 14 * 24,
            'monthly_open': 30 * 24,

            # Intraday - STRICT
            '4h_open': 4.5,
            '2h_open': 2.5,

            # Session-specific - STRICT
            'ny_open': 24,
            'ny_preopen': 24,
            'asian_range_high': 8.5,
            'asian_range_low': 8.5,
            'london_range_high': 8.5,
            'london_range_low': 8.5,
            'ny_range_high': 7,
            'ny_range_low': 7,

            # Hourly
            'previous_hourly': 1.5,
        }

    def validate_fallback_price(
        self,
        level_name: str,
        fallback_timestamp: datetime,
        current_timestamp: datetime
    ) -> Tuple[bool, str]:
        """
        Check if fallback price data is fresh enough to use.

        Args:
            level_name: Name of the reference level (e.g., '4h_open')
            fallback_timestamp: When the fallback data is from
            current_timestamp: Current market time

        Returns:
            (is_valid, reason_string)
            - is_valid=True: Data is fresh, safe to use
            - is_valid=False: Data is stale, should not use
        """

        if level_name not in self.freshness_config:
            return True, f"Unknown level {level_name} - no validation"

        max_age_hours = self.freshness_config[level_name]
        age_hours = (current_timestamp - fallback_timestamp).total_seconds() / 3600

        if age_hours <= max_age_hours:
            return True, f"{level_name} is fresh ({age_hours:.1f}h old, max {max_age_hours}h)"
        else:
            return False, f"{level_name} is STALE ({age_hours:.1f}h old, max {max_age_hours}h)"

    def validate_level_data(
        self,
        level_name: str,
        level_price: Optional[float],
        level_timestamp: Optional[datetime],
        current_timestamp: datetime
    ) -> Tuple[bool, Optional[float], str]:
        """
        Comprehensive validation of a reference level.

        Returns:
            (is_valid, price_to_use, reason)
            - is_valid=True: Use the level price
            - is_valid=False: Exclude this level from analysis (price=None)
        """

        if level_price is None:
            return False, None, f"{level_name}: No price data available"

        if level_timestamp is None:
            return False, None, f"{level_name}: No timestamp for validation"

        is_fresh, reason = self.validate_fallback_price(
            level_name, level_timestamp, current_timestamp
        )

        if is_fresh:
            return True, level_price, f"✓ {reason}"
        else:
            return False, None, f"✗ {reason} - data excluded"
```

#### **STEP 3: Integrate into Prediction Model**

Modify `prediction_model_v3.py` to use freshness validation:

```python
# Add to imports
from src.services.data_freshness_validator import DataFreshnessValidator

class PredictionModel:

    def __init__(self, instrument: str, timezone: str, weights: Dict[str, float]):
        # ... existing code ...
        self.freshness_validator = DataFreshnessValidator(timezone)
        self.data_quality_report = {}  # Track which levels passed validation

    def _calculate_levels(self, df: pd.DataFrame, current_timestamp: str) -> Dict[str, float]:
        """Enhanced level calculation with freshness validation"""

        levels_dict = {}
        timestamp_dict = {}  # Track when each level price comes from

        # ... existing calculation code ...

        current_time = pd.to_datetime(current_timestamp)

        # For each level, track when the data comes from:
        for level_name in ['daily_midnight', '4h_open', '2h_open', ...]:

            # Calculate the level price (existing logic)
            level_price = levels_dict.get(level_name)
            level_timestamp = timestamp_dict.get(level_name)  # NEW

            # NEW: Validate freshness
            is_valid, validated_price, reason = self.freshness_validator.validate_level_data(
                level_name, level_price, level_timestamp, current_time
            )

            # Store validation result
            self.data_quality_report[level_name] = {
                'is_valid': is_valid,
                'price': level_price if is_valid else None,
                'age_hours': (current_time - level_timestamp).total_seconds() / 3600 if level_timestamp else None,
                'reason': reason
            }

            # Update levels_dict to use validated price
            if is_valid:
                levels_dict[level_name] = validated_price
            else:
                levels_dict[level_name] = None  # Exclude from analysis

        return levels_dict

    def _determine_available_levels(self, df: pd.DataFrame, current_timestamp: str):
        """Filter out expired levels"""

        # Existing logic, but now data_quality_report is populated
        available_levels = [
            level for level in self.levels
            if level.price is not None
            and self.data_quality_report[level.name]['is_valid']  # NEW
        ]

        return available_levels

    def get_data_quality_report(self) -> Dict:
        """Return quality report for UI display"""
        return self.data_quality_report
```

#### **STEP 4: Update CSV Upload Validation**

Enhance `Home.py` upload section with freshness warning:

```python
# In Home.py, around line 284-309 (CSV processing)

if uploaded_file is not None:
    # ... existing CSV parsing ...

    # NEW: Check data freshness
    from src.services.data_freshness_validator import DataFreshnessValidator

    df_min_time = pd.to_datetime(df['time'].min())
    df_max_time = pd.to_datetime(df['time'].max())
    current_time = pd.to_datetime('now')

    hours_of_data = (df_max_time - df_min_time).total_seconds() / 3600
    data_age_hours = (current_time - df_max_time).total_seconds() / 3600

    # Show data quality warning
    st.info(
        f"📊 **Data Summary:**\n"
        f"- Coverage: {hours_of_data:.1f} hours\n"
        f"- Latest data: {data_age_hours:.1f} hours old\n"
        f"- Range: {df_min_time} to {df_max_time}"
    )

    # NEW: Warn about insufficient data for specific levels
    if hours_of_data < 4:
        st.warning(
            "⚠️ **Insufficient Data for 4-Hour Analysis**\n\n"
            f"Your CSV only covers {hours_of_data:.1f} hours, but the 4-hour open "
            "requires 4+ hours of data. The analysis will exclude the 4-hour reference level."
        )

    if hours_of_data < 24:
        st.warning(
            "⚠️ **Insufficient Data for Daily Analysis**\n\n"
            f"Your CSV only covers {hours_of_data:.1f} hours, but daily analysis "
            "requires 24+ hours. Daily and weekly reference levels will be excluded."
        )

    if data_age_hours > 6:
        st.warning(
            "⚠️ **Stale Data**\n\n"
            f"The latest price in your CSV is {data_age_hours:.1f} hours old. "
            "Consider updating with more recent data for accurate analysis."
        )
```

#### **STEP 5: Display Data Quality in Results**

Add quality report to prediction results in `Home.py`:

```python
# After prediction calculation, around line 380-430

if prediction_result:
    # Existing results display

    # NEW: Show data quality report
    with st.expander("📋 Data Quality Report", expanded=False):
        quality_report = model.get_data_quality_report()

        valid_levels = [k for k, v in quality_report.items() if v['is_valid']]
        invalid_levels = [k for k, v in quality_report.items() if not v['is_valid']]

        col1, col2 = st.columns(2)

        with col1:
            st.write(f"✓ **Valid Levels ({len(valid_levels)}):**")
            for level_name in valid_levels:
                report = quality_report[level_name]
                age = report['age_hours']
                st.caption(f"  • {level_name}: {age:.1f}h old")

        with col2:
            st.write(f"✗ **Excluded Levels ({len(invalid_levels)}):**")
            for level_name in invalid_levels:
                report = quality_report[level_name]
                reason = report['reason'].replace('✗', '').strip()
                st.caption(f"  • {reason}")

        st.divider()
        st.write("**Excluded Reason Details:**")
        for level_name, report in quality_report.items():
            if not report['is_valid']:
                st.caption(f"_{report['reason']}_")
```

#### **STEP 6: Create User Documentation**

Create a new file: `USING_INCOMPLETE_DATA.md`

```markdown
# Using Incomplete Price Data

## Understanding Data Gaps

When you upload price data that doesn't span a full day, week, or month, some
reference levels may not be available.

### Examples:

**1-hour chart with only 1 hour of data:**
- ❌ Cannot calculate: Daily open, 4-hour open, previous day levels, weekly levels
- ✓ Can calculate: Current bar, potentially previous hour

**4-hour chart with only 1 day of data:**
- ❌ Cannot calculate: Weekly open, previous week levels, 4-hour opens before today
- ✓ Can calculate: Daily levels, 2-hour opens

## How the System Handles Data Gaps

### Validation Process

1. **Checks required columns** exist (time, open, high, low, close)
2. **Checks data freshness** for each reference level
3. **Excludes stale levels** from analysis automatically
4. **Normalizes remaining weights** to maintain mathematical integrity

### Data Age Limits (Maximum Staleness)

| Reference Level | Maximum Age | Reason |
|---|---|---|
| `previous_hourly` | 1.5 hours | Must be from previous hour block |
| `2h_open` | 2.5 hours | Must be from last 2-hour period |
| `4h_open` | 4.5 hours | Must be from last 4-hour period |
| `daily_midnight` | 24 hours | Resets daily at market open |
| `weekly_open` | 7 days | Resets weekly on Monday |
| `monthly_open` | 30 days | Resets monthly on 1st |

## What You'll See

### Data Quality Report

After analysis, you'll see which levels were used:

```
✓ Valid Levels (14):
  • daily_midnight: 2.5h old
  • previous_hourly: 0.8h old
  • 2h_open: 1.2h old
  • ny_open: 4.3h old
  ... (11 more)

✗ Excluded Levels (6):
  • 4h_open: 6.5h old, max 4.5h
  • weekly_open: Data not available
  • asian_range_high: Incomplete session data
  ... (3 more)
```

### Weight Adjustment

The remaining valid levels are re-weighted automatically to maintain:
- Total weight = 100% (or 1.0)
- Relative proportions intact
- Depreciation applied for distance from current price

## Best Practices

### For Intraday Analysis
- Provide **at least 4-8 hours** of minute-level data
- This ensures 2h and 4h opens are available
- Ideal: Provide full trading day for most reference points

### For Daily/Swing Analysis
- Provide **at least 2-4 weeks** of daily data
- This ensures weekly and monthly levels are meaningful
- Ideal: Provide 3+ months for monthly/seasonal context

### For Historical Backtesting
- Provide **1+ year** of historical data
- This enables robust statistical analysis
- Include pre/post market session data if available

## Limitations to Understand

### What Cannot Be Calculated Without Data
- **Weekly levels** require Monday opening price in dataset
- **Daily levels** require full 24-hour period
- **4-hour opens** require at least 4+ hours of data
- **Previous session levels** require previous session's data

### What Happens When Data is Missing
1. Level is **excluded** from analysis
2. Remaining levels are **re-weighted** proportionally
3. You receive a **quality report** explaining exclusions
4. Analysis confidence may be **lower** with fewer levels

## Example Scenario

### Your CSV has:
- 2 hours of 1-minute data (13:00 - 15:00 UTC)
- From US100 (NQ)

### System will:
```
✓ Calculate and use:
- previous_hourly (from 13:00-14:00)
- 2h_open (from 13:00 open)
- Current hourly candles

✗ Cannot use:
- daily_midnight (need full day, only have 2h)
- 4h_open (need 4h, only have 2h)
- Previous day high/low (not in dataset)
- Weekly/monthly levels (insufficient history)

Result:
- Analysis weight distributed across 8 valid levels instead of 20
- Confidence may be lower but still valid
- User receives warning about limited data
```

## Need More Reference Points?

### Option 1: Upload More Data
- Use daily or 4-hour charts with longer history
- Easier to get 1-2 years of daily data
- Provides more stable reference levels

### Option 2: Use Available Levels
- Accept the limitation for current timeframe analysis
- Combine with longer-term data for context
- Monitor which levels are actually used (see quality report)

### Option 3: Consider Data Source
- Ensure CSV has complete OHLC data
- Verify no gaps in time series
- Check for data corruption or filtering
```

#### **STEP 7: Add Unit Tests**

Create `tests/test_data_freshness_validator.py`:

```python
import pytest
from datetime import datetime, timedelta
import pytz
from src.services.data_freshness_validator import DataFreshnessValidator

class TestDataFreshnessValidator:

    def setup_method(self):
        self.validator = DataFreshnessValidator('US/Eastern')
        self.now = datetime(2025, 11, 25, 14, 0, 0, tzinfo=pytz.UTC)

    def test_fresh_4h_open(self):
        """4-hour open from 3 hours ago should be valid"""
        three_hours_ago = self.now - timedelta(hours=3)
        is_valid, reason = self.validator.validate_fallback_price(
            '4h_open', three_hours_ago, self.now
        )
        assert is_valid is True
        assert "fresh" in reason.lower()

    def test_stale_4h_open(self):
        """4-hour open from 6 hours ago should be invalid"""
        six_hours_ago = self.now - timedelta(hours=6)
        is_valid, reason = self.validator.validate_fallback_price(
            '4h_open', six_hours_ago, self.now
        )
        assert is_valid is False
        assert "stale" in reason.lower()

    def test_fresh_daily_midnight(self):
        """Daily midnight from 12 hours ago should be valid"""
        twelve_hours_ago = self.now - timedelta(hours=12)
        is_valid, reason = self.validator.validate_fallback_price(
            'daily_midnight', twelve_hours_ago, self.now
        )
        assert is_valid is True

    def test_stale_daily_midnight(self):
        """Daily midnight from 30 hours ago should be invalid"""
        thirty_hours_ago = self.now - timedelta(hours=30)
        is_valid, reason = self.validator.validate_fallback_price(
            'daily_midnight', thirty_hours_ago, self.now
        )
        assert is_valid is False

    def test_fresh_weekly_open(self):
        """Weekly open from 3 days ago should be valid"""
        three_days_ago = self.now - timedelta(days=3)
        is_valid, reason = self.validator.validate_fallback_price(
            'weekly_open', three_days_ago, self.now
        )
        assert is_valid is True

    def test_stale_weekly_open(self):
        """Weekly open from 10 days ago should be invalid"""
        ten_days_ago = self.now - timedelta(days=10)
        is_valid, reason = self.validator.validate_fallback_price(
            'weekly_open', ten_days_ago, self.now
        )
        assert is_valid is False
```

---

### 3.3 Configuration Summary

| Component | File | Purpose |
|---|---|---|
| **Thresholds** | `src/services/config_service.py` | Define max age per level |
| **Validator Logic** | `src/services/data_freshness_validator.py` | Validate data age |
| **Model Integration** | `prediction_model_v3.py` | Use validation in calculations |
| **UI Warning** | `Home.py` | Display quality warnings |
| **Documentation** | `USING_INCOMPLETE_DATA.md` | User guide |
| **Tests** | `tests/test_data_freshness_validator.py` | Unit test coverage |

---

## Part 4: Implementation Timeline & Priorities

### Phase 1: Core Validation (Essential)
- ✅ Create `DataFreshnessValidator` class
- ✅ Define freshness thresholds
- ✅ Integrate into `PredictionModel`
- ✅ Add unit tests

**Effort:** 2-3 hours | **Priority:** CRITICAL

### Phase 2: UI & Feedback (Important)
- ✅ Add CSV upload warnings
- ✅ Display quality report in results
- ✅ Create user documentation
- ✅ Add debug logging

**Effort:** 1-2 hours | **Priority:** HIGH

### Phase 3: Advanced Features (Nice-to-Have)
- ⭕ Data completeness scoring (0-100%)
- ⭕ Confidence adjustment based on data freshness
- ⭕ Historical data quality metrics
- ⭕ Automated data gap filling from other sources

**Effort:** 3-4 hours | **Priority:** MEDIUM

---

## Part 5: Benefits of Implementation

### For Users
✅ **Clarity:** Know exactly which levels are excluded and why
✅ **Safety:** Never uses stale data without awareness
✅ **Guidance:** Suggestions to improve data quality
✅ **Transparency:** Quality report shows analysis limitations

### For Application
✅ **Robustness:** Handles incomplete data gracefully
✅ **Reliability:** Prevents false signals from stale data
✅ **Maintainability:** Centralized data validation logic
✅ **Testability:** Unit tests for all validation rules

### For Support
✅ **Debugging:** Easy to identify data quality issues
✅ **Documentation:** Clear rules for data requirements
✅ **User Education:** Built-in explanations in UI

---

## Part 6: Monitoring & Maintenance

### Track in Logs
```python
# Log excluded levels for monitoring
logger.warning(
    f"Excluded levels: {invalid_levels}",
    extra={
        'data_age_hours': data_age_hours,
        'data_span_hours': hours_of_data,
        'excluded_count': len(invalid_levels)
    }
)
```

### Metrics to Monitor
1. **Average data freshness** per uploaded file
2. **Most frequently excluded levels**
3. **User impact** of exclusions on prediction accuracy
4. **Adjustment needed** to freshness thresholds

### Quarterly Review
- Analyze threshold effectiveness
- Adjust based on real-world data patterns
- Update documentation with learnings

---

## Conclusion

This remediation strategy transforms the application from **silently using stale fallback data** to **explicitly validating data freshness and keeping users informed**.

The implementation is modular, testable, and maintains the existing architecture while adding critical data quality safeguards.

