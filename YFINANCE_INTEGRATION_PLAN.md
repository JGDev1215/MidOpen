# YFinance Integration & Auto-Update Architecture Plan

## Executive Summary

Transform the application from **manual CSV uploads only** to **hybrid mode** with:
- **Automatic 15-minute data pulls** from yfinance (background service)
- **Automatic predictions** on schedule (every 15 minutes)
- **Seamless CSV upload merging** (user can upload anytime, data merged with auto-fetched data)
- **Complete prediction history** tracking all sources
- **Transparent conflict resolution** (newer data always wins)

---

## Part 1: Current State vs. Target State

### Current Architecture (Manual Only)

```
User Uploads CSV
    ↓
Streamlit processes in-memory
    ↓
Prediction model analyzes
    ↓
Results saved to history
    ↓
[User waits for next manual upload]
```

**Problems:**
- ❌ No automatic predictions
- ❌ Data only as fresh as user's manual upload
- ❌ User responsible for timing
- ❌ Gaps in prediction history between uploads

### Target Architecture (Hybrid Auto + Manual)

```
┌─────────────────────────────────────────────────────────────┐
│ SCHEDULED BACKGROUND SERVICE (Every 15 minutes)              │
│                                                              │
│ • Fetch latest 1-minute OHLCV from yfinance                │
│ • Merge with existing data (avoid duplicates)              │
│ • Run prediction model                                      │
│ • Save prediction to history with source="AUTO"            │
│ • Log update event                                          │
└─────────────────────────────────────────────────────────────┘
                        ↓
        ┌───────────────┴───────────────┐
        ↓                               ↓
   Prediction History            Streamlit UI
   (All auto predictions)        (Shows latest)
        ↑                               ↑
        │                               │
        └───────────────┬───────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ USER MANUAL UPLOAD (Anytime - e.g., 4:23pm)                 │
│                                                              │
│ • User uploads CSV with fresh data                         │
│ • Merge with existing auto data                            │
│ • Run prediction model                                      │
│ • Save prediction with source="USER_UPLOAD"                │
│ • Update UI immediately                                     │
│ • Next auto-update at 4:30pm will use merged data          │
└─────────────────────────────────────────────────────────────┘
```

---

## Part 2: Architecture Components

### 2.1 YFinance Data Fetcher Service

**New File:** `src/services/yfinance_data_fetcher.py`

```python
class YFinanceDataFetcher:
    """Fetch real-time 1-minute OHLCV data from yfinance"""

    # Instrument mapping
    INSTRUMENT_TICKERS = {
        'US100': '^NDX',      # NASDAQ 100
        'US500': '^GSPC',     # S&P 500
        'UK100': '^FTSE',     # FTSE 100
    }

    def __init__(self, instrument: str):
        self.instrument = instrument
        self.ticker = self.INSTRUMENT_TICKERS.get(instrument)

    def fetch_latest_data(self, hours_back: int = 24) -> pd.DataFrame:
        """
        Fetch latest OHLCV data (1-minute bars)

        Args:
            hours_back: How far back to fetch (default 24 hours)

        Returns:
            DataFrame with columns: [time, open, high, low, close, volume]
        """
        try:
            data = yf.download(
                self.ticker,
                period=f'{hours_back}h',
                interval='1m',
                progress=False  # Silence download progress
            )

            # Standardize column names
            data = data.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })

            # Reset index to include Datetime as column
            data['time'] = data.index
            data = data.reset_index(drop=True)

            return data[['time', 'open', 'high', 'low', 'close']]

        except Exception as e:
            logger.error(f"Error fetching {self.instrument} data: {e}")
            return None

    def validate_data(self, df: pd.DataFrame) -> bool:
        """Check if data has required columns and is recent"""
        required_cols = ['time', 'open', 'high', 'low', 'close']
        if not all(col in df.columns for col in required_cols):
            return False

        # Check if latest timestamp is recent (within last 30 minutes)
        latest_time = pd.to_datetime(df['time'].iloc[-1])
        age = (datetime.now(pytz.UTC) - latest_time).total_seconds() / 60
        return age <= 30  # Must be recent
```

### 2.2 Data Merge Service

**New File:** `src/services/data_merge_service.py`

```python
class DataMergeService:
    """
    Merge new data with existing historical data.
    Handles deduplication and conflict resolution.
    """

    def merge_data(
        self,
        existing_df: pd.DataFrame,
        new_df: pd.DataFrame,
        instrument: str,
        timezone: str
    ) -> pd.DataFrame:
        """
        Intelligently merge new data with existing data

        Strategy:
        1. Ensure both use same timezone
        2. Identify overlap period (last common timestamp)
        3. Remove duplicates from existing data (keep only before overlap)
        4. Append new data
        5. Validate continuity
        6. Return merged dataframe
        """

        # Normalize timezones
        existing_df['time'] = pd.to_datetime(existing_df['time'])
        new_df['time'] = pd.to_datetime(new_df['time'])

        tz = pytz.timezone(timezone)
        if existing_df['time'].dt.tz is None:
            existing_df['time'] = existing_df['time'].dt.tz_localize(tz)
        if new_df['time'].dt.tz is None:
            new_df['time'] = new_df['time'].dt.tz_localize(tz)

        # Find overlap: where does new data start that existing has?
        latest_existing = existing_df['time'].max()
        new_data_start = new_df['time'].min()

        if new_data_start > latest_existing:
            # No overlap - simply concatenate
            merged = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            # Overlap exists - remove duplicates
            # Keep new data for overlapping timestamps
            cutoff = new_df['time'].min()
            existing_non_overlap = existing_df[existing_df['time'] < cutoff]
            merged = pd.concat([existing_non_overlap, new_df], ignore_index=True)

        # Deduplicate by timestamp (keep last occurrence = newest)
        merged = merged.drop_duplicates(subset=['time'], keep='last')
        merged = merged.sort_values('time').reset_index(drop=True)

        return merged

    def detect_data_gaps(self, df: pd.DataFrame) -> List[Dict]:
        """
        Detect missing periods in time series

        Returns list of gaps:
        [
            {'start': Timestamp, 'end': Timestamp, 'minutes': 15},
            ...
        ]
        """
        df['time'] = pd.to_datetime(df['time'])
        df = df.sort_values('time')

        time_diffs = df['time'].diff()
        expected_diff = pd.Timedelta(minutes=1)  # Expect 1-minute bars

        gaps = []
        for idx, diff in enumerate(time_diffs):
            if diff > expected_diff:
                gap_minutes = int((diff - expected_diff).total_seconds() / 60)
                gaps.append({
                    'start': df['time'].iloc[idx - 1],
                    'end': df['time'].iloc[idx],
                    'minutes': gap_minutes
                })

        return gaps
```

### 2.3 Background Scheduler Service

**New File:** `src/services/background_scheduler.py`

```python
import schedule
import threading
import time
from datetime import datetime

class BackgroundScheduler:
    """
    Manages scheduled background tasks (15-minute auto-updates)

    Runs in separate thread to avoid blocking Streamlit UI.
    Uses APScheduler or schedule library.
    """

    def __init__(self, storage_service, config_service):
        self.storage = storage_service
        self.config = config_service
        self.is_running = False
        self.thread = None
        self.schedule_jobs = {}  # Track scheduled jobs

    def start(self):
        """Start background scheduler in separate thread"""
        if self.is_running:
            return

        self.is_running = True
        self.thread = threading.Thread(daemon=True, target=self._run_scheduler)
        self.thread.start()
        logger.info("Background scheduler started")

    def stop(self):
        """Stop background scheduler"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Background scheduler stopped")

    def _run_scheduler(self):
        """Run schedule loop (internal)"""
        # Schedule auto-update at :00, :15, :30, :45 minutes
        schedule.every().hours.at(":00").do(self._trigger_auto_update, "US100")
        schedule.every().hours.at(":15").do(self._trigger_auto_update, "US100")
        schedule.every().hours.at(":30").do(self._trigger_auto_update, "US100")
        schedule.every().hours.at(":45").do(self._trigger_auto_update, "US100")

        # Same for US500 and UK100
        for time_str in [":00", ":15", ":30", ":45"]:
            schedule.every().hours.at(time_str).do(
                self._trigger_auto_update, "US500"
            )
            schedule.every().hours.at(time_str).do(
                self._trigger_auto_update, "UK100"
            )

        while self.is_running:
            schedule.run_pending()
            time.sleep(1)  # Check every second

    def _trigger_auto_update(self, instrument: str):
        """Execute auto-update for an instrument"""
        try:
            logger.info(f"Auto-update triggered for {instrument}")

            # Fetch latest data from yfinance
            fetcher = YFinanceDataFetcher(instrument)
            new_data = fetcher.fetch_latest_data(hours_back=24)

            if new_data is None or len(new_data) == 0:
                logger.warning(f"No data fetched for {instrument}")
                return

            # Load existing prediction data
            existing_data = self._get_latest_data(instrument)

            # Merge
            if existing_data is not None:
                merger = DataMergeService()
                tz = self.config.TIMEZONE_MAP.get(instrument, 'America/New_York')
                data = merger.merge_data(existing_data, new_data, instrument, tz)
            else:
                data = new_data

            # Run prediction
            prediction = self._run_prediction(data, instrument)

            # Save with source=AUTO
            if prediction:
                prediction['source'] = 'AUTO'
                prediction['auto_update_time'] = datetime.now().isoformat()
                self.storage.save_prediction(prediction)
                logger.info(f"Auto-update completed for {instrument}")

        except Exception as e:
            logger.error(f"Error in auto-update for {instrument}: {e}")

    def _get_latest_data(self, instrument: str) -> pd.DataFrame:
        """Get latest stored data for instrument"""
        # Retrieve from storage service
        predictions = self.storage.get_predictions_by_instrument(instrument)
        if predictions:
            # Use data from most recent prediction
            latest = predictions[0]
            return self._reconstruct_df_from_prediction(latest)
        return None

    def _run_prediction(self, df: pd.DataFrame, instrument: str) -> Dict:
        """Run prediction model and return result"""
        from prediction_model_v3 import PredictionEngine

        engine = PredictionEngine(instrument)
        result = engine.analyze(df)

        return {
            'result': result,
            'instrument': instrument,
            'timestamp': datetime.now().isoformat(),
            'data_length': len(df),
            'current_price': df['close'].iloc[-1]
        }
```

### 2.4 Prediction History Schema Update

**Current Schema** (prediction stored as):
```python
{
    'result': {...},
    'instrument': 'US100',
    'analysis_timestamp': '2025-11-25T14:23:45.123456',
    'data_timestamp': '2025-11-25T14:23:00-05:00',
    'filename': 'user_upload.csv',
    'data_length': 1000,
    'current_price': 24518.2
}
```

**Enhanced Schema** (adds data source tracking):
```python
{
    'result': {...},
    'instrument': 'US100',
    'analysis_timestamp': '2025-11-25T14:23:45.123456',
    'data_timestamp': '2025-11-25T14:23:00-05:00',
    'filename': 'user_upload.csv',  # or 'auto_4-23pm.csv' for auto updates
    'data_length': 1000,
    'current_price': 24518.2,

    # NEW FIELDS:
    'source': 'USER_UPLOAD',  # or 'AUTO', or 'AUTO_WITH_USER_MERGE'
    'auto_update_time': '2025-11-25T14:23:45.123456',  # When auto-update ran
    'is_merged': False,  # True if user data merged with auto data
    'merge_info': {
        'base_source': 'AUTO',  # What was merged with user data
        'user_upload_time': '2025-11-25T14:20:00',
        'last_auto_update': '2025-11-25T14:15:00'
    }
}
```

### 2.5 Data Timeline Example

**Scenario:** User uploads data at 4:23pm, auto-update scheduled every 15 minutes

```
Time        Event                          Data Source      Prediction History
──────────────────────────────────────────────────────────────────────────────
4:00pm      Auto-update #1                 yfinance AUTO    Record #1: AUTO
4:15pm      Auto-update #2                 yfinance AUTO    Record #2: AUTO
4:20pm      ← User Uploads CSV (4:23pm data from their system)
4:23pm      User upload processed          USER_UPLOAD      Record #3: USER_UPLOAD
            (merges with existing auto      MERGED           (contains 4:23pm data
             data from 4:20pm)                               merged with auto data)
4:30pm      Auto-update #3                 yfinance AUTO    Record #4: AUTO
            (uses merged data from         (incorporates     (builds on
             user upload as base)          user data)        user's data)
4:45pm      Auto-update #4                 yfinance AUTO    Record #5: AUTO
5:00pm      Auto-update #5                 yfinance AUTO    Record #6: AUTO
```

---

## Part 3: Implementation Steps

### Phase 1: Foundation (Week 1)

#### Step 1: Add YFinance Dependency
**File: `requirements.txt`**
```
# Add:
yfinance>=0.2.32
schedule>=1.2.0
# Or use APScheduler:
# apscheduler>=3.10.4
```

#### Step 2: Create YFinance Data Fetcher
**File: `src/services/yfinance_data_fetcher.py`**
- Implement `YFinanceDataFetcher` class
- Support US100, US500, UK100 tickers
- Handle errors gracefully (network issues, rate limits)
- Unit tests for ticker mapping and data validation

#### Step 3: Create Data Merge Service
**File: `src/services/data_merge_service.py`**
- Implement `DataMergeService` class
- Handle timezone normalization
- Detect and fill gaps
- Deduplicate by timestamp
- Unit tests for all merge scenarios

#### Step 4: Update Prediction History Schema
**File: `src/infrastructure/storage/postgresql_storage.py` + JSON backend**
- Add `source` column to PostgreSQL table
- Add `source`, `auto_update_time`, `is_merged`, `merge_info` fields to JSON
- Create migration to add new columns
- Ensure backward compatibility

**PostgreSQL Migration:**
```sql
ALTER TABLE predictions ADD COLUMN source VARCHAR(50) DEFAULT 'MANUAL';
ALTER TABLE predictions ADD COLUMN auto_update_time TIMESTAMP;
ALTER TABLE predictions ADD COLUMN is_merged BOOLEAN DEFAULT FALSE;
ALTER TABLE predictions ADD COLUMN merge_info JSONB;
```

### Phase 2: Background Scheduling (Week 2)

#### Step 5: Create Background Scheduler Service
**File: `src/services/background_scheduler.py`**
- Implement `BackgroundScheduler` class
- Schedule 15-minute intervals (:00, :15, :30, :45)
- Thread-safe operation
- Graceful startup/shutdown

#### Step 6: Update DI Container
**File: `src/di/container.py`**
```python
# Add to DIContainer.__init__():
self.background_scheduler = BackgroundScheduler(
    storage_service=self.storage,
    config_service=self.config
)

# Add methods:
def get_background_scheduler(self) -> BackgroundScheduler:
    return self.background_scheduler

def start_background_scheduler(self):
    self.background_scheduler.start()

def stop_background_scheduler(self):
    self.background_scheduler.stop()
```

#### Step 7: Initialize Scheduler in Streamlit App
**File: `Home.py`**
```python
# At app startup (before Streamlit renders):
from src.di.accessors import get_di_container

container = get_di_container()

# Start scheduler on first run
if 'scheduler_started' not in st.session_state:
    container.start_background_scheduler()
    st.session_state.scheduler_started = True

# Cleanup on app close
import atexit
atexit.register(lambda: container.stop_background_scheduler())
```

### Phase 3: CSV Upload Merging (Week 2-3)

#### Step 8: Update CSV Upload Handler
**File: `Home.py`** (lines 243-340, prediction analysis section)

```python
def process_user_upload(uploaded_file, instrument):
    """
    Process user CSV upload with merge logic
    """

    # Load user data
    user_df = pd.read_csv(uploaded_file)
    user_df['time'] = pd.to_datetime(user_df['time'], utc=True)
    user_df.set_index('time', inplace=True)

    # Get existing auto-fetched data (if any)
    existing_predictions = storage.get_predictions_by_instrument(instrument)

    if existing_predictions and len(existing_predictions) > 0:
        # Merge with latest auto data
        latest_pred = existing_predictions[0]
        existing_df = _reconstruct_df_from_prediction(latest_pred)

        # Merge
        merger = DataMergeService()
        merged_df = merger.merge_data(
            existing_df, user_df, instrument, timezone
        )

        is_merged = True
        merge_info = {
            'base_source': latest_pred.get('source', 'UNKNOWN'),
            'user_upload_time': datetime.now().isoformat(),
            'last_auto_update': latest_pred.get('auto_update_time')
        }
    else:
        # No existing data, use user upload as-is
        merged_df = user_df
        is_merged = False
        merge_info = {}

    # Run prediction on merged data
    prediction = engine.analyze(merged_df)

    # Save with metadata
    prediction_record = {
        'result': prediction,
        'instrument': instrument,
        'timestamp': datetime.now().isoformat(),
        'filename': uploaded_file.name,
        'data_length': len(merged_df),
        'current_price': merged_df['close'].iloc[-1],

        # NEW:
        'source': 'AUTO_WITH_USER_MERGE' if is_merged else 'USER_UPLOAD',
        'is_merged': is_merged,
        'merge_info': merge_info if is_merged else None
    }

    storage.save_prediction(prediction_record)

    return prediction_record
```

#### Step 9: Add Merge Indicators to UI
**File: `Home.py`** (prediction results display section)

```python
# After showing prediction results:

if st.session_state.analysis_result:
    source = st.session_state.analysis_result.get('source', 'UNKNOWN')

    if source == 'AUTO':
        st.info("📡 **Auto-fetched from yfinance** (15-minute update)")
    elif source == 'USER_UPLOAD':
        st.info("📤 **Uploaded manually by user**")
    elif source == 'AUTO_WITH_USER_MERGE':
        st.success("✓ **User data merged with auto-fetched data**")
        merge_info = st.session_state.analysis_result.get('merge_info', {})
        st.caption(
            f"User upload merged with {merge_info.get('base_source')} data "
            f"from {merge_info.get('last_auto_update')}"
        )
```

### Phase 4: History Display & Filtering (Week 3)

#### Step 10: Update Prediction History Page
**File: `pages/2_Prediction_History.py`**

```python
# Add source filter to sidebar
source_filter = st.multiselect(
    "Filter by Data Source",
    ['AUTO', 'USER_UPLOAD', 'AUTO_WITH_USER_MERGE'],
    default=['AUTO', 'USER_UPLOAD', 'AUTO_WITH_USER_MERGE']
)

# Add source column to results table
display_df = pd.DataFrame({
    'Timestamp': [p['data_timestamp'] for p in filtered_preds],
    'Bias': [p['result']['analysis']['bias'] for p in filtered_preds],
    'Source': [p.get('source', 'N/A') for p in filtered_preds],
    'Data Points': [p['data_length'] for p in filtered_preds],
    'Current Price': [p['current_price'] for p in filtered_preds],
})

st.dataframe(display_df, use_container_width=True)
```

#### Step 11: Add Timeline Visualization
**File: `pages/2_Prediction_History.py`**

```python
# Add timeline showing auto vs manual updates
import plotly.graph_objects as go

fig = go.Figure()

for pred in predictions:
    source_color = {
        'AUTO': 'blue',
        'USER_UPLOAD': 'green',
        'AUTO_WITH_USER_MERGE': 'orange'
    }.get(pred.get('source'), 'gray')

    fig.add_trace(go.Scatter(
        x=[pd.to_datetime(pred['data_timestamp'])],
        y=[pred['result']['analysis']['confidence']],
        mode='markers',
        marker=dict(size=10, color=source_color),
        name=pred.get('source', 'Unknown'),
        text=f"{pred.get('source')} - {pred['data_timestamp']}"
    ))

fig.update_layout(
    title="Prediction History by Source",
    xaxis_title="Time",
    yaxis_title="Confidence (%)",
    hovermode='x unified'
)

st.plotly_chart(fig, use_container_width=True)
```

### Phase 5: Admin Controls (Week 3-4)

#### Step 12: Add Scheduler Control to Admin Settings
**File: `pages/1_Admin_Settings.py`**

```python
st.divider()
st.subheader("⚙️ Background Update Settings")

col1, col2 = st.columns(2)

with col1:
    scheduler_enabled = st.checkbox(
        "Enable Auto-Update (15-minute intervals)",
        value=True,
        help="Automatically fetch latest data and run predictions"
    )

with col2:
    update_interval = st.selectbox(
        "Update Interval",
        ['15 minutes', '30 minutes', '1 hour'],
        help="How often to fetch new data"
    )

if scheduler_enabled:
    if st.button("🚀 Start Auto-Updates Now"):
        scheduler = get_background_scheduler()
        scheduler.start()
        st.success("✓ Auto-updates started")
else:
    if st.button("⏸ Stop Auto-Updates"):
        scheduler = get_background_scheduler()
        scheduler.stop()
        st.info("Auto-updates stopped")

# Show last update status
last_auto_update = get_last_auto_update_timestamp()
if last_auto_update:
    st.caption(f"Last auto-update: {last_auto_update}")
```

#### Step 13: Add Logging for Updates
**File: `src/services/logging_service.py`** (enhance existing)

```python
def log_auto_update(self, instrument: str, status: str, details: Dict = None):
    """Log background auto-update event"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'event': 'AUTO_UPDATE',
        'instrument': instrument,
        'status': status,  # 'SUCCESS', 'FAILURE', 'SKIPPED'
        'details': details or {}
    }

    # Save to audit log
    self._save_to_log_file(log_entry)

def log_csv_merge(self, instrument: str, merge_info: Dict):
    """Log CSV merge event"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'event': 'CSV_MERGE',
        'instrument': instrument,
        'merge_info': merge_info
    }

    self._save_to_log_file(log_entry)
```

---

## Part 4: Timeline & Conflict Resolution

### 4.1 Timeline Example (Detailed)

**User uploads at 4:23pm, auto-updates every 15 minutes**

```
TIME    EVENT                              DATA USED          RESULT
─────────────────────────────────────────────────────────────────────
4:00pm  Auto-update triggered              yfinance (1-min)   Pred #1: AUTO
        └─ Fetch last 24h from yfinance
        └─ Save prediction

4:15pm  Auto-update triggered              yfinance (1-min)   Pred #2: AUTO
        └─ Fetch last 24h from yfinance
        └─ Merge with existing data
        └─ Save prediction

4:20pm  [Delay in user's system]
        User preparing to upload data

4:23pm  >>> USER UPLOADS CSV <<<
        └─ User has latest data up to 4:23pm

        USER UPLOAD PROCESSING:
        ├─ Load user CSV (4:23pm data)
        ├─ Load latest auto prediction (4:15pm data)
        ├─ MERGE:
        │  ├─ Take existing: data from before 4:23pm
        │  ├─ Add new: user's 4:23pm data
        │  ├─ Result: unified dataset (4:00 - 4:23pm)
        ├─ Run prediction on merged data
        └─ Save as source='AUTO_WITH_USER_MERGE'
                                           Pred #3: MERGED

        SAVED DATA:
        {
            'result': {...},
            'source': 'AUTO_WITH_USER_MERGE',
            'is_merged': True,
            'merge_info': {
                'base_source': 'AUTO',
                'last_auto_update': '2025-11-25T4:15pm',
                'user_upload_time': '2025-11-25T4:23pm'
            }
        }

4:30pm  Auto-update triggered
        ├─ Latest stored data: merged
        │  (contains 4:23pm data from user)
        ├─ Fetch last 24h from yfinance
        │  (4:23pm to 4:30pm new data)
        ├─ MERGE:
        │  ├─ Take existing: 4:00-4:23pm
        │  │  (from user upload + auto)
        │  ├─ Add new: 4:23-4:30pm
        │  │  (freshly fetched yfinance)
        │  ├─ Result: unified 4:00-4:30pm
        ├─ Run prediction on merged data
        └─ Save as source='AUTO'
                                           Pred #4: AUTO

        BENEFIT: User's 4:23pm upload is
        seamlessly incorporated!

4:45pm  Auto-update triggered
        ├─ Latest data: includes user's
        │  4:23pm upload + subsequent
        │  auto fetches
        ├─ Fetch new yfinance (4:30-4:45pm)
        ├─ Merge and predict
        └─ Save
                                           Pred #5: AUTO
```

### 4.2 Conflict Resolution Strategy

**Rule 1: Newer Data Always Wins**
```python
# In DataMergeService.merge_data():
merged = merged.drop_duplicates(
    subset=['time'],  # Deduplicate by timestamp
    keep='last'       # Keep the newest occurrence
)
```

**Rule 2: Avoid Duplicate Predictions**
```python
# Before saving prediction, check:
latest_pred = storage.get_predictions_by_instrument(instrument)
if latest_pred:
    latest_timestamp = latest_pred['data_timestamp']
    new_timestamp = current_prediction['data_timestamp']

    if latest_timestamp == new_timestamp:
        # Update existing instead of creating duplicate
        storage.update_prediction(latest_pred['key'], new_data)
    else:
        # New data, save as new prediction
        storage.save_prediction(new_data)
```

**Rule 3: Source Tracking**
```python
# Track how data was obtained
if is_merged:
    source = 'AUTO_WITH_USER_MERGE'
elif came_from_user:
    source = 'USER_UPLOAD'
else:
    source = 'AUTO'
```

---

## Part 5: Error Handling & Resilience

### 5.1 Network Failures

```python
def fetch_latest_data_with_retry(self, max_retries: int = 3):
    """Fetch data with exponential backoff on failure"""
    for attempt in range(max_retries):
        try:
            return self.fetch_latest_data()
        except Exception as e:
            wait_time = 2 ** attempt  # 1s, 2s, 4s
            if attempt < max_retries - 1:
                logger.warning(
                    f"Fetch failed, retry in {wait_time}s: {e}"
                )
                time.sleep(wait_time)
            else:
                logger.error(f"Fetch failed after {max_retries} attempts")
                return None
```

### 5.2 Market Hours Handling

```python
def is_market_open(self, instrument: str) -> bool:
    """Check if market is currently open"""
    tz = pytz.timezone(self.TIMEZONE_MAP[instrument])
    current_time = datetime.now(tz)

    # Market hours (example for US markets)
    if instrument in ['US100', 'US500']:
        market_open = current_time.replace(hour=9, minute=30)
        market_close = current_time.replace(hour=16, minute=0)

        # Check if within market hours (US trading hours)
        if current_time.weekday() < 5:  # Mon-Fri
            return market_open <= current_time <= market_close

    return False
```

### 5.3 Data Validation

```python
def validate_prediction_before_save(self, prediction: Dict) -> bool:
    """Validate prediction data before saving"""

    required_fields = [
        'result', 'instrument', 'timestamp',
        'data_length', 'current_price'
    ]

    for field in required_fields:
        if field not in prediction:
            logger.error(f"Missing required field: {field}")
            return False

    # Validate result structure
    if 'analysis' not in prediction['result']:
        logger.error("Invalid result structure")
        return False

    # Validate confidence is 0-100
    confidence = prediction['result']['analysis']['confidence']
    if not (0 <= confidence <= 100):
        logger.error(f"Invalid confidence: {confidence}")
        return False

    return True
```

---

## Part 6: Configuration & Environment

### 6.1 New Environment Variables

**File: `.env.example`**
```
# Existing:
DATABASE_URL=postgresql://user:password@localhost:5432/midopen

# NEW - Background Scheduler:
AUTO_UPDATE_ENABLED=true
AUTO_UPDATE_INTERVAL_MINUTES=15
AUTO_UPDATE_TIMEZONE=America/New_York

# NEW - YFinance:
YFINANCE_RETRY_ATTEMPTS=3
YFINANCE_TIMEOUT_SECONDS=30
YFINANCE_MARKET_HOURS_ONLY=false

# NEW - Feature Flags:
FEATURE_AUTO_UPDATE=true
FEATURE_CSV_MERGE=true
FEATURE_TIMELINE_VISUALIZATION=true
```

### 6.2 Configuration Class

**File: `src/services/config_service.py`** (enhance existing)

```python
class SchedulerConfig:
    """Configuration for background scheduler"""

    AUTO_UPDATE_ENABLED = os.getenv('AUTO_UPDATE_ENABLED', 'true').lower() == 'true'
    AUTO_UPDATE_INTERVAL_MINUTES = int(os.getenv('AUTO_UPDATE_INTERVAL_MINUTES', '15'))
    AUTO_UPDATE_TIMEZONE = os.getenv('AUTO_UPDATE_TIMEZONE', 'America/New_York')

    # Derived schedules
    SCHEDULE_TIMES = self._calculate_schedule_times()

    @classmethod
    def _calculate_schedule_times(cls):
        """Calculate exact times for 15-minute intervals"""
        interval = cls.AUTO_UPDATE_INTERVAL_MINUTES
        if interval == 15:
            return [":00", ":15", ":30", ":45"]
        elif interval == 30:
            return [":00", ":30"]
        elif interval == 60:
            return [":00"]
        else:
            return [":00"]  # Default
```

---

## Part 7: Testing Strategy

### 7.1 Unit Tests

**File: `tests/test_yfinance_fetcher.py`**
```python
def test_fetch_valid_data():
    fetcher = YFinanceDataFetcher('US100')
    data = fetcher.fetch_latest_data(hours_back=24)
    assert data is not None
    assert len(data) > 0
    assert 'time' in data.columns

def test_invalid_ticker():
    fetcher = YFinanceDataFetcher('INVALID')
    data = fetcher.fetch_latest_data()
    assert data is None

def test_data_validation():
    fetcher = YFinanceDataFetcher('US100')
    # Create mock data
    mock_data = create_mock_ohlcv()
    assert fetcher.validate_data(mock_data) is True
```

**File: `tests/test_data_merge.py`**
```python
def test_merge_no_overlap():
    # Existing: 1-100, New: 101-110
    # Result: 1-110
    existing = create_df(1, 100)
    new = create_df(101, 110)

    merger = DataMergeService()
    result = merger.merge_data(existing, new, 'US100', 'America/New_York')

    assert len(result) == 110

def test_merge_with_overlap():
    # Existing: 1-100, New: 90-110
    # Result: 1-110 (duplicates removed)
    existing = create_df(1, 100)
    new = create_df(90, 110)

    merger = DataMergeService()
    result = merger.merge_data(existing, new, 'US100', 'America/New_York')

    assert len(result) == 110
    # Verify last 20 values are from 'new'
    assert result[-1]['source'] == 'new'

def test_detect_gaps():
    # Create data with 15-minute gap
    data = create_df_with_gap(5)  # Gap at 5-minute mark

    merger = DataMergeService()
    gaps = merger.detect_data_gaps(data)

    assert len(gaps) > 0
    assert gaps[0]['minutes'] == 5
```

### 7.2 Integration Tests

**File: `tests/test_background_scheduler.py`**
```python
def test_scheduler_starts_stops():
    scheduler = BackgroundScheduler(mock_storage, mock_config)

    scheduler.start()
    assert scheduler.is_running is True

    scheduler.stop()
    assert scheduler.is_running is False

def test_auto_update_executes():
    # Mock yfinance and storage
    scheduler = BackgroundScheduler(mock_storage, mock_config)
    scheduler._trigger_auto_update('US100')

    # Verify save_prediction was called
    assert mock_storage.save_prediction.called
```

### 7.3 End-to-End Tests

```python
def test_user_upload_merge_with_auto():
    """
    Scenario: Auto-update at 4:15pm, user upload at 4:23pm,
    auto-update again at 4:30pm
    """

    # 1. Auto-update at 4:15pm
    trigger_auto_update('US100', time='4:15pm')
    pred_1 = get_latest_prediction('US100')
    assert pred_1['source'] == 'AUTO'

    # 2. User upload at 4:23pm
    upload_csv('test_data.csv', time='4:23pm')
    pred_2 = get_latest_prediction('US100')
    assert pred_2['source'] == 'AUTO_WITH_USER_MERGE'
    assert pred_2['is_merged'] is True

    # 3. Auto-update at 4:30pm (should use merged data)
    trigger_auto_update('US100', time='4:30pm')
    pred_3 = get_latest_prediction('US100')
    assert pred_3['source'] == 'AUTO'
    # Verify it includes user's 4:23pm data
    assert pred_3['data_length'] > pred_1['data_length']
```

---

## Part 8: Deployment Considerations

### 8.1 Docker Deployment

**File: `Dockerfile` (updated)**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Environment variables
ENV AUTO_UPDATE_ENABLED=true
ENV AUTO_UPDATE_INTERVAL_MINUTES=15
ENV PYTHONUNBUFFERED=1

# Run Streamlit
CMD ["streamlit", "run", "Home.py", \
     "--server.port=${PORT:-8501}", \
     "--server.address=0.0.0.0"]
```

### 8.2 Database Migrations

```python
# File: src/infrastructure/storage/migrations/001_add_auto_update_fields.py

def upgrade():
    """Add new columns for auto-update tracking"""
    operations = [
        "ALTER TABLE predictions ADD COLUMN source VARCHAR(50) DEFAULT 'MANUAL'",
        "ALTER TABLE predictions ADD COLUMN auto_update_time TIMESTAMP",
        "ALTER TABLE predictions ADD COLUMN is_merged BOOLEAN DEFAULT FALSE",
        "ALTER TABLE predictions ADD COLUMN merge_info JSONB"
    ]

    for op in operations:
        connection.execute(op)

def downgrade():
    """Remove auto-update columns"""
    operations = [
        "ALTER TABLE predictions DROP COLUMN merge_info",
        "ALTER TABLE predictions DROP COLUMN is_merged",
        "ALTER TABLE predictions DROP COLUMN auto_update_time",
        "ALTER TABLE predictions DROP COLUMN source"
    ]

    for op in operations:
        connection.execute(op)
```

### 8.3 Health Check

```python
# File: src/services/health_check_service.py

class HealthCheckService:
    """Monitor system health and scheduler status"""

    def get_system_status(self) -> Dict:
        return {
            'scheduler_running': self.scheduler.is_running,
            'last_auto_update': self.get_last_update_time(),
            'auto_update_failures': self.get_failure_count(),
            'database_connected': self.check_database(),
            'yfinance_available': self.check_yfinance(),
            'prediction_count': self.storage.get_prediction_count()
        }
```

---

## Part 9: Monitoring & Observability

### 9.1 Metrics to Track

```python
# File: src/services/metrics_service.py

class MetricsService:
    """Track key metrics for monitoring"""

    def record_auto_update(self, instrument: str, duration: float, success: bool):
        """Record auto-update execution"""
        logger.info(
            "auto_update",
            extra={
                'instrument': instrument,
                'duration_seconds': duration,
                'success': success
            }
        )

    def record_csv_merge(self, instrument: str, existing_size: int, new_size: int):
        """Record CSV merge event"""
        logger.info(
            "csv_merge",
            extra={
                'instrument': instrument,
                'existing_records': existing_size,
                'new_records': new_size,
                'merged_records': len(merged)
            }
        )
```

### 9.2 Dashboard Metrics

**In `pages/2_Prediction_History.py`:**
```python
# Add metrics section
col1, col2, col3, col4 = st.columns(4)

with col1:
    auto_count = count_predictions_by_source('AUTO')
    st.metric("Auto-Updates", auto_count)

with col2:
    manual_count = count_predictions_by_source('USER_UPLOAD')
    st.metric("Manual Uploads", manual_count)

with col3:
    merged_count = count_predictions_by_source('AUTO_WITH_USER_MERGE')
    st.metric("Merged Data", merged_count)

with col4:
    success_rate = calculate_success_rate()
    st.metric("Success Rate", f"{success_rate}%")
```

---

## Summary

| Component | Priority | Effort | File(s) |
|-----------|----------|--------|---------|
| YFinance Fetcher | P0 | 2-3hrs | `src/services/yfinance_data_fetcher.py` |
| Data Merge Service | P0 | 3-4hrs | `src/services/data_merge_service.py` |
| Background Scheduler | P0 | 4-5hrs | `src/services/background_scheduler.py` |
| Schema Updates | P0 | 2hrs | Storage backends + migration |
| CSV Merge Handler | P1 | 3hrs | `Home.py` updated |
| History Display | P1 | 2-3hrs | `pages/2_Prediction_History.py` |
| Admin Controls | P2 | 2hrs | `pages/1_Admin_Settings.py` |
| Error Handling | P1 | 3hrs | Scattered updates |
| Tests | P1 | 6-8hrs | `tests/` directory |
| Documentation | P2 | 2hrs | README updates |
| **TOTAL** | | **30-35 hours** | |

**Estimated Timeline:** 3-4 weeks with team of 1-2 developers
