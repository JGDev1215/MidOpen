# NQ=F Real-Time Market Data Dashboard - Setup & Testing

## Phase 1 & 2 Complete: Backend API Endpoints

All 6 API endpoint groups are now implemented and ready for testing.

### Quick Start

#### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 2. Start Flask Server
```bash
python app.py
```

The API will be available at `http://localhost:5000`

#### 3. Run API Tests (in another terminal)
```bash
python test_api_endpoints.py
```

---

## API Endpoints Overview

### 1. Market Status (3 endpoints)
Detects if NQ=F market is open/closed and provides countdown to next event.

- `GET /api/market-status/NQ=F` - Full market info with status and countdown
- `GET /api/market-status/NQ=F/is-open` - Quick boolean check
- `GET /api/market-status/NQ=F/next-event` - Time until next open/close

**Market Hours**: Sunday 6 PM - Friday 5 PM ET
**Daily Maintenance**: 5 PM - 6 PM ET

---

### 2. Current Price (2 endpoints)
Real-time price with change indicators and OHLC data.

- `GET /api/current-price/NQ=F` - Current price, change, 1-hour reference
- `GET /api/current-price/NQ=F/ohlc` - Current minute OHLC

**Data Source**: yfinance (1m interval)

---

### 3. Reference Levels (3 endpoints)
All 16 reference levels calculated on-demand with proximity analysis.

- `GET /api/reference-levels/NQ=F` - All 16 levels with signals
- `GET /api/reference-levels/NQ=F/summary` - Key levels for dashboard display
- `GET /api/reference-levels/NQ=F/closest` - Nearest level to current price

**16 Reference Levels**:
1. Weekly Open (Monday 00:00 ET)
2. Monthly Open (1st day 00:00 ET)
3. Daily Open Midnight (00:00 ET)
4. NY Open 08:30 (08:30 ET)
5. Pre-NY Open (07:00 ET)
6. 4H Open
7. 2H Open
8. 1H Open
9. Previous Hour Open
10. 15min Open
11. Previous Day High
12. Previous Day Low
13. Previous Week High
14. Previous Week Low
15. Weekly High (running)
16. Weekly Low (running)

**Signal Format**:
- `proximity`: ABOVE, NEAR (within 0.1%), BELOW
- `signal`: 1 (bullish), 0 (neutral), -1 (bearish)

---

### 4. Session Ranges (3 endpoints)
High/low for each trading session (current and previous day).

- `GET /api/session-ranges/NQ=F` - Current and previous session ranges
- `GET /api/session-ranges/NQ=F/current` - Current sessions only
- `GET /api/session-ranges/NQ=F/previous` - Previous day sessions only

**4 Trading Sessions**:
- **Asian**: 18:00-02:00 ET (spans midnight)
- **London**: 03:00-06:00 ET
- **NY AM**: 08:30-12:00 ET
- **NY PM**: 14:30-16:00 ET (until market close)

---

### 5. Fibonacci Pivots (3 endpoints)
Weekly and daily Fibonacci pivot levels (R3-R1, PP, S1-S3).

- `GET /api/fibonacci-pivots/NQ=F` - Weekly and daily pivots
- `GET /api/fibonacci-pivots/NQ=F/daily` - Daily pivots only
- `GET /api/fibonacci-pivots/NQ=F/weekly` - Weekly pivots only

**Pivot Formula**:
```
PP = (High + Low + Close) / 3
R3 = PP + 2.0 * (High - Low)
R2 = PP + 1.618 * (High - Low)
R1 = PP + 1.0 * (High - Low)
S1 = PP - 1.0 * (High - Low)
S2 = PP - 1.618 * (High - Low)
S3 = PP - 2.0 * (High - Low)
```

---

### 6. Hourly Blocks (3 endpoints)
7-block hourly segmentation (~8.57 minutes per block) with OHLC for each.

- `GET /api/hourly-blocks/NQ=F` - Full 7-block segmentation for current hour
- `GET /api/hourly-blocks/NQ=F/current-block` - Current block only
- `GET /api/hourly-blocks/NQ=F/summary` - Progress bar data

**Block Information**:
- 7 blocks per hour (~8.57 minutes each)
- OHLC, volume, bar count for each block
- Block completion status
- Progress percentage

---

## Test Suite

The `test_api_endpoints.py` script provides comprehensive testing:

### Features
- ✓ Tests all 16 endpoints (6 groups + health/info)
- ✓ Measures latency (goal: <200ms)
- ✓ Validates JSON responses
- ✓ Checks success flags
- ✓ Detailed timing statistics
- ✓ Color-coded terminal output

### Running Tests
```bash
python test_api_endpoints.py
```

### Sample Output
```
============================================================
0. HEALTH & INFO ENDPOINTS
============================================================

✓ PASS | /                                                  | 12.3ms | 1847 bytes
✓ PASS | /health                                            | 4.2ms | 67 bytes

============================================================
1. MARKET STATUS ENDPOINTS
============================================================

✓ PASS | /api/market-status/NQ=F                            | 145.6ms | 542 bytes
✓ PASS | /api/market-status/NQ=F/is-open                    | 42.3ms | 89 bytes
✓ PASS | /api/market-status/NQ=F/next-event                 | 78.5ms | 234 bytes
...

TEST SUMMARY
Total Tests: 16
Passed: 16
Failed: 0
Pass Rate: 100.0%

Latency Statistics:

MARKET_STATUS:
  Min:   42.3ms
  Max:   145.6ms
  Avg:   88.8ms
  Tests: 3

PRICE:
  Min:   89.5ms
  Max:   156.2ms
  Avg:   120.4ms
  Tests: 2

✓ All endpoints under 200ms
```

---

## Architecture

### Phase 1: Core Services (Completed)
1. **market_status_service.py** - Market open/close detection
2. **timezone.py** - UTC ↔ ET conversion utilities
3. **fetcher_live.py** - Direct yfinance data fetching with rate limiting
4. **reference_level_service.py** - Calculate 16 reference levels on-demand
5. **session_range_service.py** - Live session range calculations

### Phase 2: API Endpoints (Completed)
6 endpoint groups with consistent JSON response format:
- market_status_routes.py
- price_routes.py
- reference_levels_routes.py
- session_ranges_routes.py
- fibonacci_routes.py
- block_routes.py

### Phase 3: UI Dashboard (Next)
Bootstrap 5 responsive dashboard with:
- MarketStatusTimer component
- CurrentPriceDisplay component
- ReferenceLevelsTable component
- SessionRanges component
- FibonacciPivots component
- HourlyBlockSegmentation component
- 75-second auto-refresh

---

## Data Characteristics

### Real-Time Data
- **Source**: yfinance (no Supabase storage)
- **Intervals**: 1m, 5m, 15m, 30m, 1h, 1d, 1wk
- **Rate Limiting**: 1 request/second per ticker
- **Retry Logic**: Exponential backoff (2s, 5s, 10s)

### Timezone Handling
- **Storage**: UTC (internal)
- **Display**: ET (API responses)
- **DST**: Automatic handling via pytz

### Performance
- **Target Latency**: <200ms per endpoint
- **Refresh Rate**: 75 seconds (configurable)
- **CORS**: Enabled for all routes

---

## Troubleshooting

### "Connection refused" error
Make sure Flask server is running:
```bash
python app.py
```

### "Unable to fetch price data"
yfinance may be rate-limited or the market data isn't available. Check:
- Market hours (Sun 6PM - Fri 5PM ET)
- Internet connection
- yfinance service status

### Slow endpoints (>200ms)
First request to yfinance is slower due to data fetch overhead. Subsequent requests
are faster as pandas caches data in memory.

### Timezone issues
All timestamps in API responses are in ISO 8601 format with timezone info:
- `"current_time_et": "2025-11-16T10:45:28-05:00"`
- `"current_time_utc": "2025-11-16T15:45:28+00:00"`

---

## Next Steps: Phase 3 - UI Dashboard

Once Phase 2 testing is complete, Phase 3 will implement:

1. **Dashboard HTML** (templates/dashboard/index.html)
   - Bootstrap 5 responsive layout
   - 6 main components + navigation

2. **Components**
   - MarketStatusTimer: Current time, status, countdown
   - CurrentPriceDisplay: Price, change, 1H reference
   - ReferenceLevelsTable: 16 levels with color coding
   - SessionRanges: Current and previous day sessions
   - FibonacciPivots: Weekly and daily pivots
   - HourlyBlockSegmentation: 7-block chart and progress bar

3. **Auto-Refresh**
   - 75-second refresh cycle
   - Smooth transitions between data updates
   - Loading indicators

4. **Responsive Design**
   - Mobile (320-575px)
   - Tablet (576-991px)
   - Desktop (992px+)

---

## Files Created in Phase 2

### API Routes (6 files)
- `nasdaq_predictor/api/routes/market_status_routes.py`
- `nasdaq_predictor/api/routes/price_routes.py`
- `nasdaq_predictor/api/routes/reference_levels_routes.py`
- `nasdaq_predictor/api/routes/session_ranges_routes.py`
- `nasdaq_predictor/api/routes/fibonacci_routes.py`
- `nasdaq_predictor/api/routes/block_routes.py`

### Main Application
- `app.py` - Flask application with route registration
- `requirements.txt` - Python dependencies
- `test_api_endpoints.py` - Comprehensive endpoint testing

---

## Running the Full Stack

Terminal 1 - Start API Server:
```bash
python app.py
```

Terminal 2 - Run Tests:
```bash
python test_api_endpoints.py
```

Terminal 3 - Monitor Logs (optional):
```bash
tail -f app.log
```

---

## API Response Format

All successful responses follow this format:
```json
{
  "success": true,
  "ticker": "NQ=F",
  "current_price": 17245.50,
  "current_time_utc": "2025-11-16T15:45:28+00:00",
  "current_time_et": "2025-11-16T10:45:28-05:00",
  ...endpoint-specific fields...
}
```

Error responses:
```json
{
  "success": false,
  "error": "Unable to fetch current price"
}
```

HTTP Status Codes:
- `200` - Success
- `400` - Invalid request (bad ticker)
- `503` - Service unavailable (yfinance error)
- `500` - Server error

---

## Performance Optimization Notes

1. **Caching**: yfinance caches data in memory during execution
2. **Rate Limiting**: Token bucket ensures 1 req/sec to yfinance
3. **Parallel Requests**: Different intervals fetched in sequence (not parallel)
4. **Data Validation**: All OHLC data validated before returning

---

Generated: 2025-11-17
Status: Phase 2 Complete, Ready for Testing
