# NQ=F Real-Time Market Data Dashboard

## Overview

A real-time market data dashboard for NASDAQ-100 Micro Futures (NQ=F) with live price data from yfinance, advanced technical analysis (16 reference levels, Fibonacci pivots, session ranges), and hourly block segmentation.

**Status**: Phase 2 Complete ✅ | Phase 3 Ready (UI Dashboard)

---

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start API Server
```bash
python app.py
```
Server runs on `http://localhost:5000`

### 3. Test All Endpoints
```bash
python test_api_endpoints.py
```

### 4. Example API Call
```bash
curl http://localhost:5000/api/current-price/NQ=F
```

---

## Project Structure

```
NQPV2/
├── app.py                                    # Flask application
├── requirements.txt                          # Python dependencies
├── test_api_endpoints.py                     # Comprehensive test suite
│
├── nasdaq_predictor/
│   ├── api/
│   │   └── routes/                          # API endpoint blueprints
│   │       ├── market_status_routes.py       # Market status (3 endpoints)
│   │       ├── price_routes.py               # Current price (2 endpoints)
│   │       ├── reference_levels_routes.py    # 16 levels (3 endpoints)
│   │       ├── session_ranges_routes.py      # Sessions (3 endpoints)
│   │       ├── fibonacci_routes.py           # Pivots (3 endpoints)
│   │       └── block_routes.py               # Blocks (3 endpoints)
│   │
│   ├── services/                            # Business logic
│   │   ├── market_status_service.py          # Market open/close detection
│   │   ├── reference_level_service.py        # 16 level calculations
│   │   └── session_range_service.py          # Session range calculations
│   │
│   ├── data/
│   │   └── fetcher_live.py                   # yfinance data fetching
│   │
│   └── utils/
│       └── timezone.py                       # UTC ↔ ET conversion
│
├── SETUP_AND_TEST.md                        # Setup guide and API reference
├── PHASE2_COMPLETION_SUMMARY.md              # Phase 2 summary
├── ARCHITECTURE.md                           # System architecture
└── README.md                                 # This file
```

---

## API Endpoints

### Overview
- **16 endpoints** across **6 groups**
- **Real-time data** from yfinance
- **Consistent JSON format** with error handling
- **<200ms latency target**
- **Market hours**: Sunday 6 PM - Friday 5 PM ET

### Endpoint Groups

#### 1. Market Status (3 endpoints)
Monitor NQ=F market open/closed status and countdown to next event.

```bash
GET /api/market-status/NQ=F                  # Full status
GET /api/market-status/NQ=F/is-open          # Quick check
GET /api/market-status/NQ=F/next-event       # Event countdown
```

**Response**: Market status (OPEN/CLOSED/MAINTENANCE), countdown timer, hours of operation

#### 2. Current Price (2 endpoints)
Real-time price data with change indicators.

```bash
GET /api/current-price/NQ=F                  # Price with 1H change
GET /api/current-price/NQ=F/ohlc             # Current minute OHLC
```

**Response**: Current price, change, daily high/low, timestamps (ET + UTC)

#### 3. Reference Levels (3 endpoints)
All 16 reference levels with proximity analysis.

```bash
GET /api/reference-levels/NQ=F               # All 16 levels
GET /api/reference-levels/NQ=F/summary       # Key levels for UI
GET /api/reference-levels/NQ=F/closest       # Nearest level
```

**16 Levels**:
- 5 time-based opens (Weekly, Monthly, Daily, NY, 4H, 2H, 1H)
- 5 previous/related prices (Prev day H/L, Prev week H/L, 15min open)
- 3 running extrema (Weekly H/L, Previous hour open)

**Response**: Level price, distance from current price, proximity signal (ABOVE/NEAR/BELOW)

#### 4. Session Ranges (3 endpoints)
High/low for 4 trading sessions (current and previous day).

```bash
GET /api/session-ranges/NQ=F                 # Current + previous
GET /api/session-ranges/NQ=F/current         # Current only
GET /api/session-ranges/NQ=F/previous        # Previous only
```

**4 Sessions**:
- Asian: 18:00-02:00 ET (8 hours)
- London: 03:00-06:00 ET (3 hours)
- NY AM: 08:30-12:00 ET (3.5 hours)
- NY PM: 14:30-16:00 ET (1.5 hours)

**Response**: High, low, range, bar count per session, price comparison (within/above/below)

#### 5. Fibonacci Pivots (3 endpoints)
Weekly and daily Fibonacci pivot levels (R1-R3, PP, S1-S3).

```bash
GET /api/fibonacci-pivots/NQ=F               # Weekly + daily
GET /api/fibonacci-pivots/NQ=F/daily         # Daily only
GET /api/fibonacci-pivots/NQ=F/weekly        # Weekly only
```

**Calculation**: `PP = (H+L+C)/3` with R/S levels at 1.0, 1.618, 2.0 multiples of range

**Response**: Pivot levels, distances from current price, closest pivot

#### 6. Hourly Blocks (3 endpoints)
7-block hourly segmentation (~8.57 min per block) with OHLC for each.

```bash
GET /api/hourly-blocks/NQ=F                  # Full 7-block data
GET /api/hourly-blocks/NQ=F/current-block    # Current block only
GET /api/hourly-blocks/NQ=F/summary          # Progress bar data
```

**Response**: Block OHLC, volume, bar count, completion status, progress percentage

---

## Core Architecture

### Data Flow
```
yfinance (1m/5m/15m/30m/1h/1d/1wk)
    ↓ LiveDataFetcher (rate limit: 1 req/sec)
Services (market_status, reference_levels, session_ranges)
    ↓
Flask Routes (6 endpoint groups)
    ↓
JSON Response (ET + UTC)
    ↓
Client Dashboard (Phase 3)
```

### Services

**LiveDataFetcher** (`nasdaq_predictor/data/fetcher_live.py`)
- Direct yfinance integration
- 7 intervals supported
- Rate limiting and retry logic
- Data validation
- Timezone normalization (UTC → ET)

**MarketStatusService** (`nasdaq_predictor/services/market_status_service.py`)
- Market open/close detection
- Daily maintenance window (5-6 PM ET)
- Countdown to next event
- Hours of operation tracking

**ReferenceLevelService** (`nasdaq_predictor/services/reference_level_service.py`)
- Calculate 16 levels on-demand
- Proximity analysis (distance, percentage, signal)
- Closest level detection

**SessionRangeService** (`nasdaq_predictor/services/session_range_service.py`)
- Calculate 4 trading sessions
- High/low per session
- Current and previous day ranges
- Price comparison (within/above/below)

**Timezone Utilities** (`nasdaq_predictor/utils/timezone.py`)
- UTC ↔ ET conversion
- Session boundary calculations
- Candle open time helpers
- DST-aware handling

---

## Market Hours

```
NQ=F Trading Hours: Sunday 6 PM ET - Friday 5 PM ET

Daily Maintenance: 5 PM - 6 PM ET (all days market is open)

Time Zones:
- ET (Eastern Time) - Used for display
- UTC - Used internally
```

---

## Response Format

### Success Response (200)
```json
{
  "success": true,
  "ticker": "NQ=F",
  "current_price": 17245.50,
  "current_time_et": "2025-11-16T10:45:28-05:00",
  "current_time_utc": "2025-11-16T15:45:28+00:00",
  "...": "endpoint-specific data"
}
```

### Error Response (400/503/500)
```json
{
  "success": false,
  "error": "Unable to fetch current price"
}
```

### HTTP Status Codes
- `200` - Success
- `400` - Invalid request (bad ticker)
- `503` - Service unavailable (yfinance error)
- `500` - Server error

---

## Testing

### Run All Tests
```bash
python test_api_endpoints.py
```

### Features
- Tests all 16 endpoints + health checks
- Measures latency (goal: <200ms)
- Validates JSON responses
- Detailed performance statistics
- Color-coded output

### Example Output
```
Total Tests: 18
Passed: 18
Failed: 0
Pass Rate: 100.0%

Latency Statistics:
MARKET_STATUS:
  Min:   42.3ms
  Max:   145.6ms
  Avg:   88.8ms

✓ All endpoints under 200ms
```

---

## Performance

### Latency Targets
- Goal: <200ms per endpoint
- First request: 50-100ms slower (data fetch)
- Subsequent requests: Faster (caching)

### Rate Limiting
- Token bucket: 1 request/second per ticker
- Prevents yfinance abuse
- Exponential backoff on failures (2s, 5s, 10s)

---

## Configuration

### Market Configuration
- Ticker: NQ=F (configurable)
- Market hours: Sun 6PM - Fri 5PM ET
- Maintenance: 5PM - 6PM ET daily
- Refresh interval: 75 seconds (frontend)

### Flask Configuration
- Host: 0.0.0.0
- Port: 5000
- Debug: False (production)
- CORS: Enabled

---

## Development

### Installing Development Dependencies
```bash
pip install -r requirements.txt
```

### Starting Development Server
```bash
python app.py
```

### Adding New Endpoint
1. Create route in `nasdaq_predictor/api/routes/`
2. Register blueprint in `app.py`
3. Add tests to `test_api_endpoints.py`

### Adding New Service
1. Create service in `nasdaq_predictor/services/`
2. Import in route handlers
3. Test service methods

---

## Known Limitations

1. **Single Ticker**: Currently NQ=F only (easily extensible)
2. **No Persistence**: Live data only (no historical storage)
3. **Rate Limited**: 1 req/sec per endpoint
4. **No Authentication**: Public endpoints (add before production)
5. **Single Worker**: Sequential processing (scale with workers)

---

## Future Enhancements

### Phase 3: UI Dashboard (In Progress)
- Bootstrap 5 responsive layout
- 6 main components
- 75-second auto-refresh
- Mobile/tablet/desktop responsive design

### Phase 4: Advanced Features
- Multiple ticker support
- Historical data caching
- WebSocket real-time updates
- User preferences/alerts
- Chart visualization

### Phase 5: Production Hardening
- Database integration (TimescaleDB)
- Authentication/authorization
- Rate limiting per client
- Metrics and monitoring
- Deployment containerization

---

## Troubleshooting

### "Connection refused" Error
Ensure Flask server is running: `python app.py`

### "Unable to fetch price data" Error
Check:
- Market hours (Sun 6PM - Fri 5PM ET)
- Internet connection
- yfinance service availability

### Slow Endpoints (>200ms)
- First request slower due to yfinance fetch
- Subsequent requests faster (cached)
- Monitor yfinance API response times

### Timezone Issues
- All timestamps in ISO 8601 format with timezone
- ET format: `2025-11-16T10:45:28-05:00`
- UTC format: `2025-11-16T15:45:28+00:00`

---

## Documentation

- **[SETUP_AND_TEST.md](SETUP_AND_TEST.md)** - Setup guide and API reference
- **[PHASE2_COMPLETION_SUMMARY.md](PHASE2_COMPLETION_SUMMARY.md)** - Phase 2 summary
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture details

---

## Technology Stack

- **Backend**: Flask 3.0.0, Python 3.8+
- **Data Source**: yfinance 0.2.32
- **Data Processing**: pandas 2.1.3, numpy 1.26.2
- **Timezone**: pytz 2023.3
- **Frontend**: Bootstrap 5 (Phase 3)

---

## Git Status

- **Branch**: main
- **Commits**: Latest with Phase 2 complete
- **Files**: 11 new, 2385 insertions
- **Status**: Ready for Phase 3 UI development

---

## License

Proprietary - NQ=F Trading Analysis Tool

---

## Support

For issues or questions:
1. Check [TROUBLESHOOTING](SETUP_AND_TEST.md#troubleshooting) section
2. Review [ARCHITECTURE.md](ARCHITECTURE.md) for design decisions
3. Run tests: `python test_api_endpoints.py`

---

## Next Steps

### Phase 3: UI Dashboard
The backend API is ready. Next:

1. Create `templates/dashboard/index.html` with Bootstrap 5 layout
2. Build 6 components:
   - MarketStatusTimer
   - CurrentPriceDisplay
   - ReferenceLevelsTable
   - SessionRanges
   - FibonacciPivots
   - HourlyBlockSegmentation
3. Implement 75-second auto-refresh
4. Test responsive design (mobile/tablet/desktop)

Estimated timeline: 2-3 days for full dashboard

---

**Status**: Phase 2 Complete ✅ | Phase 3 Ready
**Date**: 2025-11-17
**Last Updated**: 2025-11-17
