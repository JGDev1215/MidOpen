# Prediction Model v3.0 — Complete Specifications

**Multi-Instrument Analytical Reference Level System**

| Field | Value |
|-------|-------|
| **Version** | 3.0 |
| **Release Date** | November 19, 2025 |
| **Status** | Production Ready |

---

## Table of Contents

1. [Core Principles](#core-principles)
2. [System Architecture](#system-architecture)
3. [Supported Instruments](#supported-instruments)
4. [Reference Level System](#reference-level-system)
5. [Weight Calculation Pipeline](#weight-calculation-pipeline)
6. [Depreciation Mechanics](#depreciation-mechanics)
7. [Bias Determination](#bias-determination)
8. [Confidence Calculation](#confidence-calculation)
9. [Output Specification](#output-specification)
10. [Implementation Guide](#implementation-guide)
11. [Appendix: Calculation Workflow](#appendix-calculation-workflow)
12. [Version History](#version-history)
13. [Disclaimers & Methodology Statement](#disclaimers--methodology-statement)

---

## Core Principles

### 1. Objective Analysis Framework

The model is **a pure analytical tool** that:

- Calculates price positions relative to reference levels
- Weights these positions according to a defined distribution
- Aggregates weighted directional signals
- Computes confidence based on weight concentration

The model **does not**:

- Interpret market significance
- Recommend trading actions
- Predict future price movement
- Assign subjective strength labels

### 2. Mathematical Foundation

#### Directional Assignment

```python
for each reference level:
    if current_price > level_price:
        direction = BULLISH
    elif current_price < level_price:
        direction = BEARISH
    else:
        direction = NEUTRAL  # no weight contribution
```

#### Weight Aggregation

```python
total_bullish_weight = Σ(effective_weight) where price > level
total_bearish_weight = Σ(effective_weight) where price < level

if total_bullish_weight > total_bearish_weight:
    overall_bias = BULLISH
elif total_bearish_weight > total_bullish_weight:
    overall_bias = BEARISH
else:
    overall_bias = NEUTRAL
```

### 3. Information Hierarchy

The model output prioritizes:

1. **Raw position data** — price vs. level, distance
2. **Calculated weights** — adjusted for time and distance
3. **Aggregated signals** — total bullish/bearish
4. **Confidence metric** — weight utilization and spread

---

## System Architecture

### Processing Pipeline

```
Raw Market Data
       ↓
[1] LEVEL CALCULATION
    • Calculate all reference level prices
    • Determine which levels are available at current time
       ↓
[2] WEIGHT NORMALIZATION
    • Sum available base weights
    • Normalize to total 1.0000
       ↓
[3] DEPRECIATION APPLICATION
    • Calculate distance from current price
    • Apply distance-based depreciation factor
    • Compute effective weights
       ↓
[4] DIRECTIONAL AGGREGATION
    • Sum effective weights by direction
    • Determine overall bias
       ↓
[5] CONFIDENCE CALCULATION
    • Calculate bullish/bearish spread
    • Measure weight utilization
    • Compute confidence score
       ↓
Analysis Output
```

### Level State Management

Each reference level exists in one of three states:

| State | Definition | Use Case |
|-------|-----------|----------|
| **ALWAYS_AVAILABLE** | Exists at all times (daily/weekly/monthly opens) | All times |
| **CONDITIONALLY_AVAILABLE** | Requires specific session completion | Only after condition met |
| **UNAVAILABLE** | Condition not yet met | Excluded from calculation |

---

## Supported Instruments

### US100 (NASDAQ-100 E-Mini Futures)

| Property | Value |
|----------|-------|
| **Timezone** | America/New_York (ET) |
| **Trading Hours** | 24-hour (Sunday 6 PM – Friday 5 PM ET) |
| **Reference Levels** | 20 total (14 always + 6 conditional) |
| **Base Weight Total** | 1.0000 (100%) |

#### Always-Available Levels (14 total — 0.8622 weight)

- Daily Midnight (00:00 ET)
- Previous Hourly Open
- 2-Hour Open
- 4-Hour Open
- NY Open (9:30 AM ET)
- NY Pre-Open (7:00 AM ET)
- Previous Day High
- Previous Day Low
- Weekly Open (Monday 00:00 ET)
- Weekly High
- Weekly Low
- Previous Week High
- Previous Week Low
- Monthly Open (1st 00:00 ET)

#### Conditional Levels (6 total — 0.1378 weight)

- Asian Range High/Low (available after 00:00 ET)
- London Range High/Low (available after 11:00 AM ET)
- NY Range High/Low (available after 2:00 PM ET)

### ES (S&P 500 E-Mini Futures)

| Property | Value |
|----------|-------|
| **Timezone** | America/New_York (ET) |
| **Trading Hours** | 24-hour (Sunday 6 PM – Friday 5 PM ET) |
| **Reference Levels** | 20 total (14 always + 6 conditional) |
| **Base Weight Total** | 1.0000 (100%) |
| **Configuration** | Identical to US100 |

### FTSE (FTSE 100 Index — UK Equities)

| Property | Value |
|----------|-------|
| **Timezone** | Europe/London (GMT) |
| **Trading Hours** | 24-hour |
| **Reference Levels** | 15 total (all always-available) |
| **Base Weight Total** | 1.0000 (100%) |

#### Always-Available Levels (15 total)

- Daily Midnight (00:00 GMT)
- Previous Hourly Open
- 2-Hour Open
- 4-Hour Open
- London Open (8:00 AM GMT)
- Previous Day High
- Previous Day Low
- Weekly Open (Monday 00:00 GMT)
- Weekly High
- Weekly Low
- Previous Week High
- Previous Week Low
- Monthly Open (1st 00:00 GMT)
- London Range High (8 AM – 4:30 PM)
- London Range Low (8 AM – 4:30 PM)

---

## Reference Level System

### US100 Level Specification

#### Always-Available Levels

| Level Name | Time Reference | Base Weight | Importance |
|-----------|----------------|-------------|------------|
| `daily_midnight` | Today 00:00 ET | 0.1339 | Primary |
| `previous_hourly` | Previous hour open | 0.0822 | Secondary |
| `2h_open` | 2 hours ago | 0.0520 | Tertiary |
| `4h_open` | 4 hours ago | 0.0650 | Secondary |
| `ny_open` | 9:30 AM ET | 0.0779 | Primary |
| `ny_preopen` | 7:00 AM ET | 0.0391 | Tertiary |
| `prev_day_high` | Yesterday high | 0.0260 | Tertiary |
| `prev_day_low` | Yesterday low | 0.0260 | Tertiary |
| `weekly_open` | Monday 00:00 ET | 0.0650 | Secondary |
| `weekly_high` | Current week high | 0.0260 | Tertiary |
| `weekly_low` | Current week low | 0.0260 | Tertiary |
| `prev_week_high` | Last week high | 0.0520 | Secondary |
| `prev_week_low` | Last week low | 0.0520 | Secondary |
| `monthly_open` | 1st 00:00 ET | 0.0391 | Tertiary |

**Subtotal Weight:** 0.8622 (86.22%)

#### Conditional Levels

| Level Name | Definition | Available After | Base Weight |
|-----------|-----------|----------------|-------------|
| `asian_range_high` | High: 20:00 – 00:00 ET | 00:00 ET | 0.0279 |
| `asian_range_low` | Low: 20:00 – 00:00 ET | 00:00 ET | 0.0279 |
| `london_range_high` | High: 03:00 – 11:00 ET | 11:00 AM ET | 0.0520 |
| `london_range_low` | Low: 03:00 – 11:00 ET | 11:00 AM ET | 0.0520 |
| `ny_range_high` | High: 09:30 AM+ ET | 2:00 PM ET | 0.0391 |
| `ny_range_low` | Low: 09:30 AM+ ET | 2:00 PM ET | 0.0391 |

**Subtotal Weight:** 0.1378 (13.78%)

**Total Weight:** 1.0000 (100%)

---

## Weight Calculation Pipeline

### Phase 1: Identify Available Levels

At any given moment, determine which levels have data:

```python
available_levels = []

for level in all_levels:
    if level.type == "ALWAYS_AVAILABLE":
        available_levels.append(level)
    elif level.type == "CONDITIONAL":
        if current_time >= level.availability_time:
            available_levels.append(level)

return available_levels
```

#### Example at 9:30 AM ET

- All 14 always-available levels ✓
- Asian Range High/Low ✓ (became available at midnight)
- London Range High/Low ✓ (became available at 11 AM)
- NY Range High/Low ✗ (not available until 2 PM)

**Result:** 16/20 levels available

### Phase 2: Calculate Sum of Available Base Weights

```python
available_base_weight_sum = Σ(base_weight) for level in available_levels
```

#### Example Continuation

- 14 always-available: 0.8622
- 2 Asian ranges: 0.0279 + 0.0279 = 0.0558
- 2 London ranges: 0.0520 + 0.0520 = 0.1040
- NY ranges: not available
- **Total:** 0.8622 + 0.0558 + 0.1040 = 1.0220

> **Note:** Sum exceeds 1.0 because conditional levels weren't initially weighted for full 24-hour availability.

### Phase 3: Normalize Weights to 1.0000

Apply normalization factor:

```python
normalization_factor = 1.0000 / available_base_weight_sum
normalized_weight(level) = base_weight(level) × normalization_factor
```

#### Example Continuation

```python
normalization_factor = 1.0000 / 1.0220 = 0.9785

daily_midnight_normalized = 0.1339 × 0.9785 = 0.1310
asian_range_high_normalized = 0.0279 × 0.9785 = 0.0273
london_range_high_normalized = 0.0520 × 0.9785 = 0.0509
# (etc.)

# Verification: Σ(normalized weights) = 1.0000 ✓
```

### Phase 4: Apply Depreciation Factor

For each available level, calculate distance-based depreciation.

---

## Depreciation Mechanics

### Depreciation Function

The depreciation factor reduces weight influence based on distance from current price.

#### Distance Calculation

```python
distance_percent = (|level_price - current_price| / current_price) × 100
```

#### Depreciation Tiers

| Distance Range | Formula | Behavior |
|---------------|---------|----------|
| 0.00% to 0.50% | `1.0` | Full weight (price at or very near level) |
| 0.50% to 2.00% | `1.0 - ((d - 0.5) / 1.5) × 0.5` | Linear decay from 1.0 to 0.5 |
| 2.00%+ | `0.5 × e^(-d / 2.0)` | Exponential decay below 0.5 |

#### Depreciation Examples

| Distance | Depreciation | Interpretation |
|----------|--------------|----------------|
| 0.00% | 1.000 | Price exactly at level (maximum relevance) |
| 0.25% | 1.000 | Price within 0.25% (full weight) |
| 0.50% | 1.000 | Boundary of full weight zone |
| 1.00% | 0.833 | 83% of base weight remains |
| 1.50% | 0.667 | 67% of base weight remains |
| 2.00% | 0.500 | 50% of base weight remains (transition point) |
| 3.00% | 0.303 | 30% of base weight remains |
| 4.00% | 0.184 | 18% of base weight remains |
| 5.00% | 0.111 | 11% of base weight remains |

### Effective Weight Calculation

```python
effective_weight = normalized_weight × depreciation_factor
```

#### Multi-Level Example

**Level: `daily_midnight`**

```python
normalized_weight = 0.1310
current_price = 24622.90
level_price = 24644.50
distance = ((24644.50 - 24622.90) / 24622.90) × 100 = 0.0876%
depreciation = 1.000  # within 0.50% zone
effective_weight = 0.1310 × 1.000 = 0.1310
```

**Level: `weekly_open`**

```python
normalized_weight = 0.0636  # (0.0650 × 0.9785)
current_price = 24622.90
level_price = 25187.00
distance = ((25187.00 - 24622.90) / 24622.90) × 100 = 2.289%
depreciation = 0.5 × e^(-2.289/2.0) = 0.5 × e^(-1.145) = 0.5 × 0.319 = 0.159
effective_weight = 0.0636 × 0.159 = 0.0101
```

### Weight Utilization Metric

```python
weight_utilization = Σ(effective_weight) / 1.0000
```

#### Utilization Interpretation

| Utilization Range | Signal Strength | Market Condition |
|------------------|----------------|------------------|
| 85-100% | Strong | Price near cluster of levels |
| 70-85% | Moderate | Typical trending market |
| 50-70% | Weak | Price far from most levels |
| <50% | Very Weak | Strong directional move |

---

## Bias Determination

### Simple Aggregation

```python
bullish_weight = Σ(effective_weight) where price > level
bearish_weight = Σ(effective_weight) where price < level

if bullish_weight > bearish_weight:
    bias = BULLISH
elif bearish_weight > bullish_weight:
    bias = BEARISH
else:
    bias = NEUTRAL
```

### Spread Calculation

```python
directional_spread = |bullish_weight - bearish_weight|
```

#### Spread Interpretation

| Spread | Meaning |
|--------|---------|
| 0.00 to 0.10 | Minimal directional preference |
| 0.10 to 0.30 | Slight directional bias |
| 0.30 to 0.50 | Moderate directional bias |
| 0.50+ | Strong directional bias |

---

## Confidence Calculation

### Two-Component Formula

```python
confidence_percent = directional_spread × weight_utilization × 100
```

### Components

1. **Directional Spread** (0.0 to 1.0)
   - Measures how lopsidedly weights cluster
   - Range: 0 (neutral) to 1.0 (100% one direction)

2. **Weight Utilization** (0.0 to 1.0)
   - Measures how many levels are relevant
   - Range: <0.5 (few levels relevant) to 1.0 (all levels relevant)

3. **Result: 0-100%**
   - Multiplying ensures both factors matter
   - High confidence requires BOTH directional clarity AND level relevance

### Confidence Interpretation

| Range | Assessment | Conditions |
|-------|-----------|-----------|
| 0-10% | Neutral | Weights balanced or low utilization |
| 11-33% | Weak Signal | One direction dominant but utilization low |
| 34-66% | Moderate Signal | Directional bias present, normal conditions |
| 67-100% | Strong Signal | Clear directional bias + high utilization |

> **Important:** Confidence measures **calculation strength**, not **predictive accuracy**.

---

## Output Specification

### Data Structure (JSON)

```json
{
    "metadata": {
        "instrument": "US100",
        "timestamp": "2025-11-19T14:30:00-05:00",
        "timezone": "America/New_York",
        "current_price": 24622.90
    },
    "analysis": {
        "bias": "BEARISH",
        "confidence": 64.13,
        "bullish_weight": 0.1794,
        "bearish_weight": 0.8206,
        "directional_spread": 0.6412
    },
    "weights": {
        "utilization": 0.785,
        "available_levels": 18,
        "total_levels": 20
    },
    "levels": [
        {
            "name": "daily_midnight",
            "price": 24644.50,
            "distance_percent": -0.088,
            "position": "BELOW",
            "depreciation": 1.000,
            "base_weight": 0.1339,
            "normalized_weight": 0.1310,
            "effective_weight": 0.1310
        },
        {
            "name": "previous_hourly",
            "price": 24644.50,
            "distance_percent": -0.088,
            "position": "BELOW",
            "depreciation": 1.000,
            "base_weight": 0.0822,
            "normalized_weight": 0.0804,
            "effective_weight": 0.0804
        }
        // ... additional levels
    ]
}
```

### Console Output Format

```
══════════════════════════════════════════════════════════════════════════════
                          ANALYSIS REPORT — v3.0
══════════════════════════════════════════════════════════════════════════════

Instrument:      US100 (NASDAQ-100 E-Mini Futures)
Timestamp:       November 19, 2025 @ 2:30 PM EST
Current Price:   24,622.90

──────────────────────────────────────────────────────────────────────────────
DIRECTIONAL ANALYSIS
──────────────────────────────────────────────────────────────────────────────

Bias:            BEARISH
Confidence:      64.13%

Composition:
  Bullish:       17.94% (price above these levels)
  Bearish:       82.06% (price below these levels)
  Spread:        64.12% (bullish/bearish difference)

──────────────────────────────────────────────────────────────────────────────
WEIGHT ANALYSIS
──────────────────────────────────────────────────────────────────────────────

Available Levels:        18 / 20
Weight Utilization:      78.5%

Unavailable Levels (2):
  • ny_range_high         (available after 2:00 PM ET)
  • ny_range_low          (available after 2:00 PM ET)

──────────────────────────────────────────────────────────────────────────────
REFERENCE LEVEL POSITIONS
──────────────────────────────────────────────────────────────────────────────

Level Name              Price       Distance    Position    Eff Weight
──────────────────────────────────────────────────────────────────────────────
daily_midnight       24,644.50      -0.088%     BELOW        0.1310
previous_hourly      24,644.50      -0.088%     BELOW        0.0804
2h_open              24,640.10      -0.070%     BELOW        0.0509
4h_open              24,680.50      -0.233%     BELOW        0.0636
ny_open              24,650.00      -0.110%     BELOW        0.0763
ny_preopen           24,574.30      +0.188%     ABOVE        0.0382
prev_day_high        24,630.70      -0.318%     BELOW        0.0255
prev_day_low         24,520.20      +0.421%     ABOVE        0.0255
weekly_open          25,187.00      -2.289%     BELOW        0.0101
weekly_high          25,100.00      -1.897%     BELOW        0.0255
weekly_low           24,100.00      +2.162%     ABOVE        0.0255
prev_week_high       25,345.00      -2.851%     BELOW        0.0100
prev_week_low        24,050.00      +2.381%     ABOVE        0.0255
monthly_open         24,520.00      +0.421%     ABOVE        0.0382
asian_range_high     24,645.00      -0.089%     BELOW        0.0273
asian_range_low      24,520.00      +0.421%     ABOVE        0.0273
london_range_high    24,645.00      -0.089%     BELOW        0.0509
london_range_low     24,520.00      +0.421%     ABOVE        0.0509
(ny_range_high)      [unavailable]
(ny_range_low)       [unavailable]

══════════════════════════════════════════════════════════════════════════════
```

---

## Implementation Guide

### Quick Start

```python
from nq_prediction_model_v3 import PredictionEngine, OutputFormatter

# Initialize
engine = PredictionEngine()

# Load data and run analysis
df = load_market_data('us100_ohlcv.csv')
result = engine.analyze(
    dataframe=df,
    instrument='US100',
    current_timestamp='2025-11-19T14:30:00-05:00'
)

# Format output
formatter = OutputFormatter()
console_output = formatter.to_console(result)
json_output = formatter.to_json(result)

print(console_output)
```

### Key Functions

| Function | Purpose | Returns |
|----------|---------|---------|
| `get_available_levels(timestamp)` | Identify which levels are available at given time | List of level objects |
| `calculate_reference_levels(df, instrument)` | Compute all reference level prices | Dict of level prices |
| `normalize_weights(available_levels)` | Apply normalization factor | Dict of normalized weights |
| `apply_depreciation(levels, current_price)` | Calculate depreciation for each level | Dict of effective weights |
| `calculate_bias(effective_weights, current_price)` | Aggregate weights and determine bias | Bias and spread |
| `calculate_confidence(spread, utilization)` | Compute confidence score | Float 0-100 |

### Integration Points

#### Backward Compatibility

The v3.0 model maintains backward compatibility for:

- Data input format (CSV with OHLCV)
- Instrument specifications
- Level definitions
- Calculation methodology

#### Breaking Changes

- Output format (no trading recommendations)
- Function naming conventions
- Confidence formula adjustment (now includes utilization)

---

## Appendix: Calculation Workflow

### Complete Example (9:30 AM ET)

#### Input

- **Current time:** 9:30 AM ET
- **Current price:** 24,622.90
- **Instrument:** US100

#### Step 1: Available Levels

```
Always-available: 14 levels ✓
Asian Range: Available since midnight ✓
London Range: Available since 11 AM ✓
NY Range: Not available until 2 PM ✗

Result: 16/20 levels
```

#### Step 2: Normalize Weights

```python
sum_of_16_available_base_weights = 0.9622
normalization_factor = 1.0000 / 0.9622 = 1.0393
# Apply factor to each available level's weight
```

#### Step 3: Depreciation

```python
for each level:
    calculate_distance_percent()
    apply_depreciation_formula()
    effective_weight = normalized_weight × depreciation
```

#### Step 4: Aggregate

```python
# Count effective_weights where price > level = bullish
# Count effective_weights where price < level = bearish

total_bullish = 0.1794  # 17.94%
total_bearish = 0.8206  # 82.06%
bias = BEARISH
```

#### Step 5: Confidence

```python
directional_spread = |0.1794 - 0.8206| = 0.6412
weight_utilization = 0.785
confidence = 0.6412 × 0.785 = 0.5033 = 50.33%
```

---

## Version History

### v3.0 (Current)

**Release Date:** November 19, 2025

**Improvements:**

- ✅ Clearer system architecture with explicit pipeline stages
- ✅ Separated always-available from conditional levels
- ✅ Enhanced weight normalization documentation
- ✅ More detailed depreciation examples
- ✅ Two-component confidence formula (spread × utilization)
- ✅ Comprehensive output specification
- ✅ State management clarity

**Breaking Changes:**

- Function naming updated
- Output JSON structure revised
- Confidence calculation refined

### v2.3 (Previous)

**Release Date:** November 18, 2025

**Features:**

- Pure analytical framework (no recommendations)
- Proprietary methodology statement
- Multi-instrument support
- Dynamic time-aware normalization

### v2.2

**Release Date:** Earlier

**Features:**

- Multi-instrument foundation
- Conditional level availability
- Trading recommendations (removed in v2.3)

---

## Disclaimers & Methodology Statement

This model represents proprietary independent research developed through systematic analysis of market structure and price-level relationships. The methodology does not reference or incorporate teachings from external trading frameworks. All calculations are mathematical operations on observable price data without subjective interpretation.

**This is an analytical tool, not financial advice.**

---

*End of Specification Document*
