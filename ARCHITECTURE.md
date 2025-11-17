# NQ=F Real-Time Market Data Dashboard - Architecture

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLIENT BROWSER (Phase 3)                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Dashboard UI (Bootstrap 5 Responsive)                       │  │
│  │  ┌─────────────┐ ┌──────────────┐ ┌─────────────────────┐   │  │
│  │  │   Market    │ │   Current    │ │  Reference Levels   │   │  │
│  │  │   Status    │ │    Price     │ │  (16 levels)        │   │  │
│  │  └─────────────┘ └──────────────┘ └─────────────────────┘   │  │
│  │  ┌─────────────┐ ┌──────────────┐ ┌─────────────────────┐   │  │
│  │  │   Session   │ │  Fibonacci   │ │  Hourly Blocks      │   │  │
│  │  │   Ranges    │ │   Pivots     │ │  (7-block chart)    │   │  │
│  │  └─────────────┘ └──────────────┘ └─────────────────────┘   │  │
│  │                                                               │  │
│  │  Auto-Refresh: Every 75 seconds                              │  │
│  │  Timezone: ET (ET + UTC in data)                             │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                               ↓ HTTP REST
┌─────────────────────────────────────────────────────────────────────┐
│              FLASK API SERVER (app.py) - Phase 2 ✅                │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Blueprint Registration & Route Management                  │   │
│  │  ┌───────────────────────────────────────────────────────┐  │   │
│  │  │ 6 Endpoint Groups (16 endpoints total)                │  │   │
│  │  │ ┌──────────────┐ ┌──────────────┐ ┌─────────────────┐ │  │   │
│  │  │ │   Market     │ │    Price     │ │   Reference     │ │  │   │
│  │  │ │   Status     │ │   Routes     │ │   Levels Routes │ │  │   │
│  │  │ │   Routes     │ │   (2 eps)    │ │   (3 eps)       │ │  │   │
│  │  │ │   (3 eps)    │ └──────────────┘ └─────────────────┘ │  │   │
│  │  │ └──────────────┘                                       │  │   │
│  │  │ ┌──────────────┐ ┌──────────────┐ ┌─────────────────┐ │  │   │
│  │  │ │   Session    │ │ Fibonacci    │ │   Hourly Block  │ │  │   │
│  │  │ │   Ranges     │ │   Pivots     │ │   Routes        │ │  │   │
│  │  │ │   Routes     │ │   Routes     │ │   (3 eps)       │ │  │   │
│  │  │ │   (3 eps)    │ │   (3 eps)    │ └─────────────────┘ │  │   │
│  │  │ └──────────────┘ └──────────────┘                       │  │   │
│  │  │                                                           │  │   │
│  │  │  Error Handling: 400, 503, 500                           │  │   │
│  │  │  Response Format: JSON with timezone (ET + UTC)          │  │   │
│  │  │  CORS: Enabled for all routes                            │  │   │
│  │  └───────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                               ↓ Data Fetching
┌─────────────────────────────────────────────────────────────────────┐
│          SERVICE LAYER - Phase 1 ✅                                │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  market_status_service.py                                   │   │
│  │  ✓ Market open/close detection                             │   │
│  │  ✓ Countdown to next event                                 │   │
│  │  ✓ Daily maintenance window (5-6 PM ET)                   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  reference_level_service.py                                 │   │
│  │  ✓ 16 reference levels calculated on-demand                │   │
│  │  ✓ Proximity analysis (ABOVE/NEAR/BELOW)                   │   │
│  │  ✓ Signal generation (bullish/neutral/bearish)             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  session_range_service.py                                   │   │
│  │  ✓ 4 trading sessions (Asian, London, NY AM, NY PM)        │   │
│  │  ✓ Current and previous day ranges                         │   │
│  │  ✓ High/low with bar counts per session                    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  timezone.py - UTC ↔ ET conversion utilities                │   │
│  │  ✓ Market time helpers (session boundaries, candle opens)  │   │
│  │  ✓ DST-aware timezone conversion                           │   │
│  │  ✓ Week/month start calculations                           │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  fetcher_live.py - Direct yfinance integration              │   │
│  │  ✓ Rate limiting (1 req/sec per ticker)                    │   │
│  │  ✓ 7 intervals: 1m, 5m, 15m, 30m, 1h, 1d, 1wk             │   │
│  │  ✓ Data validation (OHLC integrity, NaN detection)         │   │
│  │  ✓ Retry logic with exponential backoff                    │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                               ↓ External API
┌─────────────────────────────────────────────────────────────────────┐
│                  yfinance - Real-Time Market Data                   │
│  ✓ No Supabase dependency                                           │
│  ✓ Direct data fetch (no persistence layer)                         │
│  ✓ OHLC data for multiple intervals                                │
│  ✓ NQ=F futures data                                                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

```
Request from Client
     ↓
Flask Route Handler
     ↓
Parameter Validation
     ↓
Service Layer
 ├─ Get current time (UTC + ET)
 ├─ Fetch yfinance data
 ├─ Calculate values
 ├─ Validate results
 └─ Format response
     ↓
JSON Response (ET + UTC)
     ↓
Client receives data
```

---

## Component Interaction Matrix

| Endpoint | Uses LiveDataFetcher | Uses Service | Calculates |
|----------|---------------------|--------------|-----------|
| /market-status/{ticker} | No | MarketStatusService | Status, countdown |
| /current-price/{ticker} | Yes | None | Price, change, OHLC |
| /reference-levels/{ticker} | Yes | ReferenceLevel | 16 levels, signals |
| /session-ranges/{ticker} | Yes | SessionRange | High/low per session |
| /fibonacci-pivots/{ticker} | Yes | None | Pivots, distances |
| /hourly-blocks/{ticker} | Yes | None | Block OHLC, progress |

---

## Data Transformation Pipeline

```
Raw yfinance Data (UTC)
     ↓
LiveDataFetcher
 ├─ Normalize timezone to ET
 ├─ Validate OHLC
 └─ Return DataFrame
     ↓
Service Layer
 ├─ Calculate indicators
 ├─ Apply business logic
 └─ Generate signals
     ↓
API Route
 ├─ Format as JSON
 ├─ Add timestamps (ET + UTC)
 └─ Return 200/400/503/500
     ↓
Client
 ├─ Display in dashboard
 ├─ Update every 75 seconds
 └─ Show timezone info
```

---

## Request/Response Lifecycle

```
Client Request: GET /api/reference-levels/NQ=F

1. Flask route receives request
2. Validate ticker parameter ← if invalid → 400
3. LiveDataFetcher.get_current_price(NQ=F)
4. Fetch 1m, 5m, 15m, 30m, 1h, 1d, 1wk data
5. ReferenceLevelService.calculate_all_levels()
   ├─ Calculate 16 levels
   ├─ Calculate proximity (distance, %)
   ├─ Determine signals
   └─ Find closest level
6. Format JSON response
   {
     "success": true,
     "ticker": "NQ=F",
     "current_price": 17245.50,
     "reference_levels": {...16 levels...},
     "signals": {...proximity analysis...},
     "closest_level": {...nearest level...},
     "current_time_et": "...",
     "current_time_utc": "..."
   }
7. Return 200 OK

Total latency target: <200ms
```

---

## Timezone Architecture

```
External: yfinance (UTC)
     ↓
LiveDataFetcher
     ├─ Input: UTC datetime
     ├─ Process: Convert to ET
     └─ Output: DataFrame with ET index
     ↓
Services
     ├─ Input: ET timestamps
     ├─ Process: Calculate using ET timezone
     └─ Output: Results in ET
     ↓
Routes
     ├─ Store in UTC internally
     ├─ Add ET for display
     └─ Output both in JSON
     ↓
Client
     └─ Display ET with UTC reference
```

---

## Rate Limiting Strategy

```
TokenBucketLimiter (1 request/second per ticker)

Request arrives
     ↓
Check token availability
     ├─ Token available → Proceed, consume token
     └─ No token → Wait for refill (1 per second)
     ↓
Fetch data from yfinance
     ↓
Return to caller
```

---

## Error Handling Flow

```
API Endpoint receives request
     ↓
Try to:
 ├─ Validate parameters
 ├─ Fetch data
 └─ Calculate values
     ↓
If error:
 ├─ Validation error → 400 Bad Request
 ├─ Data unavailable → 503 Service Unavailable
 ├─ Other error → 500 Internal Server Error
     ↓
Response:
 {
   "success": false,
   "error": "error message"
 }
```

---

## Market Hours State Machine

```
                 ┌─────────────────────┐
                 │   CLOSED (Fri 5PM)   │
                 └─────────────────────┘
                           ↓
                 ┌─────────────────────┐
                 │  MAINTENANCE WINDOW  │
                 │    (5PM - 6PM ET)    │
                 │ (Daily, all days)    │
                 └─────────────────────┘
                           ↓
                 ┌─────────────────────┐
                 │   CLOSED (until Sun) │
                 └─────────────────────┘
                           ↓
                 ┌─────────────────────┐
                 │   OPEN (Sun 6PM ET)  │
                 └─────────────────────┘
                           ↓
                 ┌─────────────────────┐
                 │   OPEN (all week)    │
                 │  until Fri 5PM ET    │
                 └─────────────────────┘
```

---

## 16 Reference Levels Calculation Tree

```
Current Market Data
     ├─ Current Price (most recent close)
     ├─ Current Time (ET)
     └─ Intervals: 1m, 5m, 15m, 30m, 1h, 1d, 1wk
          ↓
     ┌────────────────────────────────────┐
     │  TIME-BASED LEVELS (8 total)       │
     ├────────────────────────────────────┤
     ├─ Weekly Open (Monday 00:00 ET)
     ├─ Monthly Open (1st day 00:00 ET)
     ├─ Daily Open Midnight (00:00 ET)
     ├─ NY Open (08:30 ET)
     ├─ Pre-NY Open (07:00 ET)
     ├─ 4H Open
     ├─ 2H Open
     ├─ 1H Open
     └─ Previous Hour Open
          ↓
     ┌────────────────────────────────────┐
     │  PRICE-BASED LEVELS (5 total)      │
     ├────────────────────────────────────┤
     ├─ Previous Day High
     ├─ Previous Day Low
     ├─ Previous Week High
     ├─ Previous Week Low
     └─ 15min Open
          ↓
     ┌────────────────────────────────────┐
     │  EXTREMA LEVELS (3 total)          │
     ├────────────────────────────────────┤
     ├─ Weekly High (running)
     └─ Weekly Low (running)
```

---

## Session Range Calculation

```
Trading Day Segmentation (4 Sessions)

18:00 ET ─────────────────── ASIAN ─────────────────── 02:00 ET
                                  (8 hours)
03:00 ET ─────────────────── LONDON ─────────────────── 06:00 ET
                                  (3 hours)
08:30 ET ─────────────────── NY AM ─────────────────── 12:00 ET
                                  (3.5 hours)
14:30 ET ─────────────────── NY PM ─────────────────── 16:00 ET
                                  (1.5 hours)

For each session:
├─ Get high and low
├─ Count bars (intervals)
├─ Calculate range
├─ Compare vs current price
└─ Determine position (within/above/below)
```

---

## Hourly Block Segmentation

```
Current Hour (60 minutes)

Block 1 ├─ Block 2 ├─ Block 3 ├─ Block 4 ├─ Block 5 ├─ Block 6 ├─ Block 7 │
8:34min | 8:34min | 8:34min | 8:34min | 8:34min | 8:34min | 8:34min

For each block:
├─ Start/end time
├─ OHLC (from 1m bars)
├─ Volume (sum of 1m)
├─ Bar count
└─ Completion status (true/false)

Progress tracking:
├─ Current block number
├─ Blocks completed
├─ Progress percentage
└─ Time into current block
```

---

## Performance Targets

```
Endpoint Group          Goal    Typical
─────────────────────────────────────────
Market Status           <200ms  40-80ms
Current Price           <200ms  90-150ms
Reference Levels        <200ms  120-180ms
Session Ranges          <200ms  100-160ms
Fibonacci Pivots        <200ms  95-155ms
Hourly Blocks           <200ms  110-170ms

First request: 50-100ms slower (data fetch)
Subsequent requests: Faster (in-memory cache)
```

---

## Scalability Considerations

### Current (NQ=F Only)
- Single ticker focused
- Minimal resource usage
- Rate limit: 1 req/sec per endpoint

### Future Expansion
- Multiple tickers (ES=F, YM=F, etc.)
- Request queuing per ticker
- Dedicated cache per ticker
- Connection pooling to yfinance

### Database Consideration
- Currently: No persistence (live data only)
- Future: Could add TimescaleDB for historical storage
- Trade-off: Real-time vs. historical analysis

---

## Security Considerations

1. **Input Validation**
   - Ticker validation (2+ chars)
   - No SQL injection (no database)
   - No XSS (JSON responses)

2. **Rate Limiting**
   - Token bucket (1 req/sec per endpoint)
   - Prevents yfinance abuse

3. **CORS**
   - Enabled for all origins
   - Can be restricted in production

4. **Error Messages**
   - Generic error messages (no system info leak)
   - Detailed logging (internal only)

---

## Deployment Architecture

```
Production Server
     ├─ app.py (Flask)
     ├─ requirements.txt (dependencies)
     ├─ nasdaq_predictor/ (source)
     │  ├─ api/routes/ (6 endpoint files)
     │  ├─ services/ (service layer)
     │  └─ utils/ (timezone, helpers)
     ├─ static/ (CSS, JS - Phase 3)
     ├─ templates/ (HTML - Phase 3)
     └─ logs/ (application logs)

Port: 5000
Workers: 1 (single-threaded yfinance)
Timeout: 30 seconds
Debug: False (production)
```

---

## Testing Architecture

```
test_api_endpoints.py
     ├─ Health endpoints (2)
     ├─ Market status (3)
     ├─ Price (2)
     ├─ Reference levels (3)
     ├─ Session ranges (3)
     ├─ Fibonacci (3)
     └─ Hourly blocks (3)
          ↓
     Latency measurement (<200ms target)
          ↓
     Response validation (JSON structure)
          ↓
     Success flag verification
          ↓
     Summary report with stats
```

---

## Monitoring Points

For production monitoring:
- Response time per endpoint
- Error rate (40x, 50x codes)
- yfinance API availability
- Rate limiter token refresh
- Memory usage (data caching)
- Concurrent request count

---

This architecture ensures:
✓ Real-time data without persistence
✓ Scalable service design
✓ Timezone correctness
✓ Rate limiting protection
✓ Error resilience
✓ Clean separation of concerns
✓ Ready for Phase 3 UI integration
