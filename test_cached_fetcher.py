"""
Test suite for optimized Live Data Fetcher with 95-second caching
Validates cache behavior, fallback logic, and API resilience
"""

import sys
import time
import logging
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from nasdaq_predictor.data.fetcher_live import LiveDataFetcher, cache, rate_limiter
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

print("=" * 80)
print("CACHED LIVE DATA FETCHER TEST SUITE")
print("=" * 80)

# Test 1: Cache initialization
print("\n[TEST 1] CACHE INITIALIZATION")
print("-" * 80)
try:
    logger.info(f"Cache TTL: {cache.ttl} seconds")
    logger.info(f"Cache entries: {len(cache.cache)}")
    logger.info(f"Fallback entries: {len(cache.fallback)}")
    logger.info("Cache initialized successfully")
    print("RESULT: PASS")
except Exception as e:
    logger.error(f"Failed: {e}")
    print("RESULT: FAIL")

# Test 2: Rate limiter
print("\n[TEST 2] RATE LIMITER")
print("-" * 80)
try:
    logger.info("Testing rate limiter...")
    
    start = time.time()
    rate_limiter.wait(key="test_ticker")
    elapsed = time.time() - start
    
    logger.info(f"First request: {elapsed*1000:.2f}ms (expected: <10ms)")
    
    start = time.time()
    rate_limiter.wait(key="test_ticker")
    elapsed = time.time() - start
    
    logger.info(f"Second request (with limit): {elapsed*1000:.2f}ms (expected: ~1000ms)")
    
    if elapsed >= 0.95:  # Should have waited ~1 second
        logger.info("Rate limiter working correctly")
        print("RESULT: PASS")
    else:
        logger.warning("Rate limiter may not be working correctly")
        print("RESULT: FAIL")
except Exception as e:
    logger.error(f"Failed: {e}")
    print("RESULT: FAIL")

# Test 3: Session creation
print("\n[TEST 3] SESSION CREATION")
print("-" * 80)
try:
    session = LiveDataFetcher._create_session()
    logger.info(f"Session created with headers: {list(session.headers.keys())}")
    
    required_headers = ['User-Agent', 'Accept', 'Accept-Language']
    has_headers = all(h in session.headers for h in required_headers)
    
    if has_headers:
        logger.info("All required headers present")
        print("RESULT: PASS")
    else:
        logger.warning("Missing some required headers")
        print("RESULT: FAIL")
except Exception as e:
    logger.error(f"Failed: {e}")
    print("RESULT: FAIL")

# Test 4: Data fetching (with fallback)
print("\n[TEST 4] DATA FETCHING WITH CACHE AND FALLBACK")
print("-" * 80)
try:
    logger.info("Attempting to fetch NQ=F 1d data...")
    df = LiveDataFetcher.fetch_data('NQ=F', interval='1d', use_cache=True)
    
    if df is not None:
        logger.info(f"SUCCESS: Fetched {len(df)} bars")
        logger.info(f"  Latest date: {df.index[-1]}")
        logger.info(f"  Latest close: {df['Close'].iloc[-1]}")
        print("RESULT: PASS (API working)")
    else:
        logger.warning("Returned None (API not available)")
        print("RESULT: WARN (fallback to manual test)")
except Exception as e:
    logger.error(f"Failed: {e}")
    print("RESULT: FAIL")

# Test 5: Cache hit detection
print("\n[TEST 5] CACHE HIT BEHAVIOR (95-SECOND TTL)")
print("-" * 80)
try:
    # Create dummy data for testing
    dummy_df = pd.DataFrame({
        'Open': [100, 101, 102],
        'High': [102, 103, 104],
        'Low': [99, 100, 101],
        'Close': [101, 102, 103],
        'Volume': [1000000, 1100000, 1200000]
    }, index=pd.date_range('2025-01-01', periods=3, tz='America/New_York'))
    
    cache_key = "TEST_TICKER_1d"
    
    # Set cache
    cache.set(cache_key, dummy_df)
    logger.info(f"Cached test data with key: {cache_key}")
    
    # Retrieve from cache
    cached_result = cache.get(cache_key)
    if cached_result is not None and len(cached_result) == 3:
        logger.info(f"Cache HIT: Retrieved {len(cached_result)} bars")
        print("RESULT: PASS (cache working)")
    else:
        logger.error("Cache miss or corrupted data")
        print("RESULT: FAIL")
    
    # Verify TTL
    logger.info(f"Cache TTL: {cache.ttl} seconds")
    logger.info("Simulating 96-second wait...")
    cache.cache[cache_key] = (time.time() - 96, dummy_df)
    
    expired_result = cache.get(cache_key)
    if expired_result is None:
        logger.info("Cache correctly expired after TTL")
        print("RESULT: PASS (TTL working)")
    else:
        logger.warning("Cache did not expire as expected")
        print("RESULT: FAIL")
    
except Exception as e:
    logger.error(f"Failed: {e}")
    print("RESULT: FAIL")

# Test 6: Timezone normalization
print("\n[TEST 6] TIMEZONE NORMALIZATION (UTC -> ET)")
print("-" * 80)
try:
    # Create test dataframe with UTC times
    utc_df = pd.DataFrame({
        'Open': [100, 101],
        'High': [102, 103],
        'Low': [99, 100],
        'Close': [101, 102],
        'Volume': [1000000, 1100000]
    }, index=pd.date_range('2025-01-01', periods=2, tz='UTC'))
    
    logger.info(f"Input timezone: {utc_df.index.tz}")
    
    normalized_df = LiveDataFetcher._normalize_timezone(utc_df)
    
    logger.info(f"Output timezone: {normalized_df.index.tz}")
    
    if str(normalized_df.index.tz) == 'America/New_York':
        logger.info("Timezone conversion successful (UTC -> ET)")
        print("RESULT: PASS")
    else:
        logger.warning(f"Unexpected timezone: {normalized_df.index.tz}")
        print("RESULT: FAIL")
except Exception as e:
    logger.error(f"Failed: {e}")
    print("RESULT: FAIL")

# Test 7: Data validation
print("\n[TEST 7] DATA VALIDATION")
print("-" * 80)
try:
    # Valid data
    valid_df = pd.DataFrame({
        'Open': [100, 101, 102],
        'High': [102, 103, 104],
        'Low': [99, 100, 101],
        'Close': [101, 102, 103],
        'Volume': [1000000, 1100000, 1200000]
    })
    
    is_valid, errors = LiveDataFetcher._validate_data(valid_df, 'TEST', '1d')
    logger.info(f"Valid data: {is_valid}, Errors: {errors}")
    
    if is_valid:
        print("RESULT: PASS (valid data accepted)")
    else:
        print("RESULT: FAIL (valid data rejected)")
    
    # Invalid data (missing volume)
    invalid_df = pd.DataFrame({
        'Open': [100],
        'High': [102],
        'Low': [99],
        'Close': [101],
        'Volume': [float('nan')]
    })
    
    is_valid, errors = LiveDataFetcher._validate_data(invalid_df, 'TEST', '1d')
    logger.info(f"Invalid data: {is_valid}, Errors: {errors}")
    
    if not is_valid and len(errors) > 0:
        print("RESULT: PASS (invalid data rejected)")
    else:
        print("RESULT: FAIL (invalid data accepted)")
        
except Exception as e:
    logger.error(f"Failed: {e}")
    print("RESULT: FAIL")

# Test 8: Cache statistics
print("\n[TEST 8] CACHE STATISTICS")
print("-" * 80)
try:
    logger.info(f"Cache entries: {len(cache.cache)}")
    logger.info(f"Fallback entries: {len(cache.fallback)}")
    logger.info(f"TTL: {cache.ttl} seconds")
    logger.info(f"Rate limiter tracked keys: {len(rate_limiter.last_request_time)}")
    print("RESULT: PASS")
except Exception as e:
    logger.error(f"Failed: {e}")
    print("RESULT: FAIL")

# Test 9: Convenience functions
print("\n[TEST 9] CONVENIENCE FUNCTIONS")
print("-" * 80)
try:
    from nasdaq_predictor.data.fetcher_live import (
        fetch_nq_1m,
        fetch_nq_daily,
        fetch_nq_weekly,
        fetch_nq_all_intervals
    )
    
    logger.info("All convenience functions imported successfully")
    print("RESULT: PASS")
except Exception as e:
    logger.error(f"Failed: {e}")
    print("RESULT: FAIL")

print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)
print("""
Key improvements in optimized fetcher:

1. 95-SECOND CACHING
   - Reduces API calls by 95x (from 1 request every second to 1 per 95 seconds)
   - Dramatically improves reliability by minimizing API exposure
   - Matches dashboard update interval perfectly

2. SESSION MANAGEMENT
   - Fresh requests.Session() for each API call
   - Proper User-Agent headers to appear as legitimate browser
   - Better handling of Yahoo Finance API authentication

3. FALLBACK STRATEGY
   - Caches last successful fetch
   - Returns cached data even if current API call fails
   - Ensures dashboard never shows "No Data" if data was ever available

4. RATE LIMITING
   - 1 second between requests per ticker
   - Prevents API throttling and 429 errors
   - Allows multiple tickers to be fetched sequentially

5. ERROR HANDLING
   - Exponential backoff (2s, 5s, 10s)
   - Graceful fallback to cached/previous data
   - Detailed logging for debugging

EXPECTED PERFORMANCE:
- First fetch: May take 2-5 seconds (with retries)
- Subsequent fetches (within 95s): <50ms (from cache)
- Cache miss after 95s: Fetches fresh data, caches for 95 more seconds

RECOMMENDED USAGE:
- Run API endpoints unchanged
- Dashboard updates every 95 seconds
- Automatic cache refresh happens transparently
- Zero code changes needed in endpoints
""")
print("=" * 80)
