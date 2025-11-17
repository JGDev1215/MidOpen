# yfinance Data Limitation - Analysis & Workarounds

**Date**: November 17, 2025
**System**: NQ=F Market Data Dashboard API
**Status**: Critical - No market data available

---

## Executive Summary

The NQ=F Market Data Dashboard is experiencing **complete data unavailability** from the yfinance library due to Yahoo Finance API limitations. This document provides detailed analysis of the issue and comprehensive workarounds.

### Root Causes Identified

1. **HTTP 429 - Too Many Requests**: Yahoo Finance is rate-limiting API requests
2. **No Price Data**: NQ=F futures symbol returns empty datasets
3. **JSON Parse Errors**: Yahoo returning HTML error pages instead of JSON data

---

## Detailed Problem Analysis

### Error Logs from Production

```
ERROR - 429 Client Error: Too Many Requests for url:
https://query2.finance.yahoo.com/v10/finance/quoteSummary/NQ=F

ERROR - NQ=F: No price data found, symbol may be delisted (period=7d)

ERROR - Failed to get ticker 'NQ=F' reason: Expecting value: line 1 column 1 (char 0)
```

### What's Failing

| Endpoint | Status | Error Type |
|----------|--------|------------|
| `/api/current-price/NQ=F` | 503 Service Unavailable | Empty DataFrame |
| `/api/reference-levels/NQ=F` | 503 Service Unavailable | 429 Too Many Requests |
| `/api/fibonacci-pivots/NQ=F` | 503 Service Unavailable | 429 Too Many Requests |
| `/api/session-ranges/NQ=F` | 503 Service Unavailable | 429 Too Many Requests |
| `/api/hourly-blocks/NQ=F` | 503 Service Unavailable | Empty DataFrame |

### yfinance Behavior

Testing shows **all ticker symbols** fail to return data:
- `NQ=F` (NASDAQ-100 Micro Futures) - 0 rows
- `MNQ=F` (Alternative symbol) - 0 rows
- `ES=F` (S&P 500 Futures) - 0 rows
- `^IXIC` (NASDAQ Index) - 0 rows
- `QQQ` (NASDAQ ETF) - 0 rows

**Conclusion**: This is a **yfinance/Yahoo Finance API-wide issue**, not specific to NQ=F.

---

## Why yfinance Fails for Live Trading Data

### Fundamental Limitations

1. **Not Designed for Live Data**
   - yfinance is primarily for **historical research and backtesting**
   - Yahoo Finance API is **unreliable for real-time applications**
   - No SLA or uptime guarantees

2. **Rate Limiting**
   - Yahoo Finance aggressively rate-limits requests
   - No official API key system
   - Shared IP addresses get blocked quickly

3. **Futures Data Availability**
   - Futures symbols (`=F` suffix) have **limited support**
   - Data may only update at EOD (end of day)
   - Intraday futures data often unavailable

4. **Legal/Commercial Restrictions**
   - Yahoo Finance TOS prohibits automated access for commercial use
   - Data is meant for personal research only
   - Real-time futures data requires exchange licensing

---

## Workarounds & Solutions

### Solution 1: Use QQQ ETF as NQ=F Proxy (Quick Fix)

**Pros:**
- Free, readily available
- Tracks NASDAQ-100 closely
- More reliable than futures symbols

**Cons:**
- Not exact 1:1 with NQ=F
- Only trades during regular market hours (9:30 AM - 4:00 PM ET)
- No futures-specific data (no 24/5 trading coverage)

**Implementation:**
```python
# Replace NQ=F with QQQ in fetch calls
df = LiveDataFetcher.fetch_data('QQQ', interval='1m')
```

**Effort**: Low (1 hour)
**Reliability**: Medium

---

### Solution 2: Add Request Headers & User-Agent Spoofing

**Rationale**: Yahoo Finance blocks requests that look automated

**Implementation:**
```python
# In fetcher_live.py, modify yfinance requests
import yfinance as yf

# Add headers to avoid detection
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
})

ticker = yf.Ticker('NQ=F', session=session)
```

**Effort**: Low (2 hours)
**Reliability**: Medium-Low (Yahoo can still detect patterns)

---

### Solution 3: Implement Redis Caching Layer

**Strategy**: Cache last known good data to reduce API calls

**Implementation:**
```python
import redis
import json
from datetime import timedelta

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def fetch_with_cache(ticker, interval, cache_ttl=60):
    """Fetch data with Redis caching"""
    cache_key = f"market_data:{ticker}:{interval}"

    # Try cache first
    cached_data = redis_client.get(cache_key)
    if cached_data:
        return pd.read_json(cached_data)

    # Fetch from yfinance
    df = LiveDataFetcher.fetch_data(ticker, interval)

    # Store in cache
    if df is not None:
        redis_client.setex(
            cache_key,
            timedelta(seconds=cache_ttl),
            df.to_json()
        )

    return df
```

**Pros:**
- Reduces API calls by 90%+
- Serves stale data when Yahoo is down
- Improves response times

**Cons:**
- Requires Redis installation
- Data may be outdated

**Effort**: Medium (4-6 hours)
**Reliability**: High

---

### Solution 4: Switch to Alpha Vantage API (Free Tier)

**Provider**: https://www.alphavantage.co/

**Pros:**
- Official API with documentation
- Free tier: 25 requests/day
- More reliable than yfinance
- Supports stocks and some futures

**Cons:**
- Limited free tier (only 25 calls/day)
- May not support NQ=F futures directly
- Requires API key

**Implementation:**
```python
import requests

API_KEY = 'your_alpha_vantage_key'

def fetch_alpha_vantage(symbol='QQQ', interval='1min'):
    url = f'https://www.alphavantage.co/query'
    params = {
        'function': 'TIME_SERIES_INTRADAY',
        'symbol': symbol,
        'interval': interval,
        'apikey': API_KEY,
        'outputsize': 'full'
    }

    response = requests.get(url, params=params)
    data = response.json()

    # Convert to pandas DataFrame
    # ... (process data)
    return df
```

**Effort**: Medium (6-8 hours)
**Reliability**: High
**Cost**: Free (limited) / $50/month (premium)

---

### Solution 5: Polygon.io API (Recommended for Production)

**Provider**: https://polygon.io/

**Pros:**
- Professional-grade market data
- Real-time and historical data
- Excellent API documentation
- Supports futures, stocks, forex, crypto
- WebSocket streaming for live data

**Cons:**
- Paid service ($29-$199/month)
- Requires account setup

**Pricing:**
- **Starter**: $29/month - 5 API calls/minute, delayed data
- **Developer**: $99/month - 100 API calls/minute, delayed data
- **Advanced**: $199/month - Real-time data, unlimited calls

**Implementation:**
```python
from polygon import RESTClient

client = RESTClient(api_key='YOUR_API_KEY')

def fetch_polygon_futures(ticker='NQ', interval='1min', limit=1000):
    """Fetch futures data from Polygon.io"""

    # Get aggregates (OHLCV bars)
    aggs = client.get_aggs(
        ticker=ticker,
        multiplier=1,
        timespan='minute',
        from_='2025-11-10',
        to='2025-11-17',
        limit=limit
    )

    # Convert to DataFrame
    df = pd.DataFrame([{
        'timestamp': pd.to_datetime(a.timestamp, unit='ms'),
        'open': a.open,
        'high': a.high,
        'low': a.low,
        'close': a.close,
        'volume': a.volume
    } for a in aggs])

    return df
```

**Effort**: Medium-High (8-12 hours to integrate)
**Reliability**: Very High
**Cost**: $29-$199/month

---

### Solution 6: Interactive Brokers API (IBKR)

**Provider**: https://www.interactivebrokers.com/

**Pros:**
- Brokerage-grade real-time data
- Supports all futures contracts
- Free with funded account ($0-10/month data fees)
- WebSocket streaming
- Historical data available

**Cons:**
- Requires Interactive Brokers account
- Complex API (ib_insync library recommended)
- Must maintain minimum balance

**Implementation:**
```python
from ib_insync import *

ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)

# Define NQ futures contract
contract = Future('NQ', '20251219', 'CME')

# Get historical bars
bars = ib.reqHistoricalData(
    contract,
    endDateTime='',
    durationStr='7 D',
    barSizeSetting='1 min',
    whatToShow='TRADES',
    useRTH=False
)

# Convert to DataFrame
df = util.df(bars)
```

**Effort**: High (16-24 hours)
**Reliability**: Very High (institutional grade)
**Cost**: Free with account + $10/month CME data feed

---

### Solution 7: Twelve Data API

**Provider**: https://twelvedata.com/

**Pros:**
- Free tier: 800 requests/day
- Good documentation
- Supports stocks, ETFs, some futures
- WebSocket support

**Cons:**
- Limited futures coverage
- Rate limits on free tier

**Pricing:**
- **Free**: 800 API calls/day
- **Basic**: $29/month - 20K calls/day
- **Pro**: $79/month - 80K calls/day

**Implementation:**
```python
import requests

API_KEY = 'your_twelve_data_key'

def fetch_twelve_data(symbol='QQQ', interval='1min'):
    url = 'https://api.twelvedata.com/time_series'
    params = {
        'symbol': symbol,
        'interval': interval,
        'apikey': API_KEY,
        'outputsize': 5000
    }

    response = requests.get(url, params=params)
    data = response.json()

    # Convert to DataFrame
    # ... (process data)
    return df
```

**Effort**: Medium (6-8 hours)
**Reliability**: High
**Cost**: Free (limited) / $29-79/month

---

### Solution 8: Mock Data Generator (For Development)

**Use Case**: Development and testing without live data dependency

**Implementation:**
```python
import numpy as np
from datetime import datetime, timedelta

def generate_mock_nq_data(start_price=20000, num_bars=1000, interval_minutes=1):
    """Generate realistic mock NQ=F price data"""

    timestamps = [
        datetime.now() - timedelta(minutes=interval_minutes * i)
        for i in range(num_bars, 0, -1)
    ]

    # Random walk with volatility
    returns = np.random.normal(0.0001, 0.002, num_bars)  # 20 bps std dev
    prices = start_price * np.exp(np.cumsum(returns))

    data = []
    for i, ts in enumerate(timestamps):
        price = prices[i]
        volatility = abs(np.random.normal(0, 5))  # ~5 point range

        data.append({
            'timestamp': ts,
            'open': price,
            'high': price + volatility,
            'low': price - volatility,
            'close': price + np.random.normal(0, 2),
            'volume': int(np.random.uniform(100, 1000))
        })

    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    return df
```

**Effort**: Low (2-3 hours)
**Reliability**: N/A (fake data)
**Cost**: Free

---

## Recommended Implementation Strategy

### Phase 1: Immediate (This Week)

1. **Implement Mock Data Generator**
   - Enable development and testing to continue
   - Validate all calculation logic works correctly
   - Complete UI development

2. **Add Redis Caching Layer**
   - Reduce yfinance API calls by 90%
   - Serve stale data when API fails
   - Improve response times

3. **Try QQQ as Fallback**
   - More reliable than NQ=F
   - Good enough for development/demo

### Phase 2: Short-Term (Next 2 Weeks)

4. **Sign up for Polygon.io Starter**
   - $29/month for professional data
   - Integrate with existing fetcher_live.py
   - Test with real NQ futures data

5. **Implement Fallback Chain**
   ```python
   def fetch_with_fallback(ticker, interval):
       # Try Polygon first
       data = fetch_polygon(ticker, interval)
       if data is not None:
           return data

       # Fallback to cached data
       data = get_from_cache(ticker, interval)
       if data is not None:
           return data

       # Last resort: yfinance (likely to fail)
       data = fetch_yfinance(ticker, interval)
       if data is not None:
           return data

       # Return mock data for development
       return generate_mock_data(ticker, interval)
   ```

### Phase 3: Production (1 Month)

6. **Upgrade to Polygon.io Advanced** ($199/month)
   - Real-time data
   - Unlimited API calls
   - WebSocket streaming

7. **Or: Interactive Brokers Integration**
   - Institutional-grade data
   - Lower cost long-term
   - Additional trading capabilities

---

## Cost Comparison

| Solution | Setup Effort | Monthly Cost | Reliability | Real-time | Futures Support |
|----------|-------------|--------------|-------------|-----------|-----------------|
| yfinance (current) | None | Free | ❌ Very Low | ❌ No | ⚠️ Limited |
| QQQ Fallback | 1 hour | Free | ⚠️ Medium | ❌ No | ❌ No |
| Alpha Vantage | 6 hours | $0-50 | ✅ High | ⚠️ Delayed | ❌ No |
| Twelve Data | 6 hours | $0-79 | ✅ High | ⚠️ Delayed | ⚠️ Limited |
| Polygon.io | 8 hours | $29-199 | ✅ Very High | ✅ Yes | ✅ Yes |
| IBKR | 16 hours | $10 | ✅ Very High | ✅ Yes | ✅ Yes |
| Redis Caching | 4 hours | $0 | ✅ High | ⚠️ Cached | N/A |
| Mock Data | 2 hours | $0 | N/A | N/A | N/A |

---

## Technical Implementation Priority

### Priority 1 (Critical - Do Now)
1. ✅ Mock data generator for development
2. ✅ Redis caching to reduce API load
3. ✅ QQQ fallback for demos

### Priority 2 (High - This Week)
4. Sign up for Polygon.io Starter ($29/month)
5. Integrate Polygon.io adapter class
6. Test with real NQ futures data

### Priority 3 (Medium - Next Sprint)
7. Implement multi-source fallback chain
8. Add data source health monitoring
9. Create admin dashboard for data source status

### Priority 4 (Low - Future)
10. Evaluate Interactive Brokers integration
11. Consider Twelve Data as secondary source
12. Build custom data aggregation layer

---

## Code Structure for Multi-Source Support

```python
# nasdaq_predictor/data/data_source_adapter.py

from abc import ABC, abstractmethod
import pandas as pd

class DataSourceAdapter(ABC):
    """Abstract base class for market data sources"""

    @abstractmethod
    def fetch_data(self, ticker: str, interval: str, period: str) -> pd.DataFrame:
        pass

    @abstractmethod
    def get_current_price(self, ticker: str) -> float:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if data source is currently available"""
        pass


class YFinanceAdapter(DataSourceAdapter):
    """yfinance implementation (current)"""
    # ... existing implementation


class PolygonAdapter(DataSourceAdapter):
    """Polygon.io implementation"""
    # ... new implementation


class MockDataAdapter(DataSourceAdapter):
    """Mock data generator for development"""
    # ... mock implementation


class DataSourceManager:
    """Manages multiple data sources with fallback"""

    def __init__(self):
        self.sources = [
            PolygonAdapter(),  # Primary
            YFinanceAdapter(), # Fallback
            MockDataAdapter()  # Development
        ]

    def fetch_data(self, ticker: str, interval: str) -> pd.DataFrame:
        """Try each source in order until one succeeds"""
        for source in self.sources:
            if not source.is_available():
                continue

            try:
                data = source.fetch_data(ticker, interval, period='7d')
                if data is not None and not data.empty:
                    return data
            except Exception as e:
                logger.warning(f"{source.__class__.__name__} failed: {e}")
                continue

        return None
```

---

## Conclusion

The yfinance limitation is a **critical blocker** for production deployment but has **multiple viable solutions**.

**Recommended Path:**
1. **Immediate**: Implement mock data + Redis caching (development continues)
2. **Short-term**: Sign up for Polygon.io ($29/month)
3. **Production**: Upgrade to Polygon.io Advanced or IBKR

**Total Cost**: $29-199/month for professional-grade data
**Total Effort**: 20-30 hours of development

This is a **necessary investment** for any serious trading application. Free data sources like yfinance are unsuitable for production use.

---

**Document Version**: 1.0
**Last Updated**: November 17, 2025
**Next Review**: After implementing Phase 1 solutions
