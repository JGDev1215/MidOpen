#!/usr/bin/env python3
"""
Financial Prediction Dashboard with DI Architecture
Streamlit UI for Prediction Model v3.0 + Dependency Injection Services
"""

import streamlit as st
import pandas as pd
import json
import logging
from datetime import datetime
from pathlib import Path
import traceback
from zoneinfo import ZoneInfo

# Import DI accessors for services
from src.di.accessors import (
    get_top_predictions,
    get_prediction_count,
    save_prediction,
    get_predictions_by_instrument
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure page
st.set_page_config(
    page_title="Financial Prediction Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin: 10px 0;
    }
    .bullish {
        color: #00AA00;
        font-weight: bold;
    }
    .bearish {
        color: #FF0000;
        font-weight: bold;
    }
    .neutral {
        color: #FFA500;
        font-weight: bold;
    }
    .main-title {
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 10px;
    }
    .market-open {
        color: #00AA00;
        font-weight: bold;
    }
    .market-closed {
        color: #FF0000;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Market status helper function
def get_market_status(instrument: str, current_time: datetime = None) -> dict:
    """
    Determine if market is open or closed based on instrument and time.
    
    Futures markets trading hours:
    - UK100 (FTSE): Sunday 6pm - Friday 5pm ET (continuous with short break)
    - US500 (S&P 500): Sunday 6pm - Friday 5pm ET (continuous with short break)
    - US100 (NASDAQ): Sunday 6pm - Friday 5pm ET (continuous with short break)
    """
    if current_time is None:
        current_time = datetime.now(ZoneInfo("UTC"))
    
    # Convert to ET for consistency
    et_time = current_time.astimezone(ZoneInfo("America/New_York"))
    weekday = et_time.weekday()  # 0=Monday, 6=Sunday
    hour = et_time.hour
    minute = et_time.minute
    
    # Convert to minutes since midnight for easier comparison
    minutes_since_midnight = hour * 60 + minute
    
    # Futures market hours: Sunday 6 PM (22:00 Sunday ET) to Friday 5 PM (17:00 Friday ET)
    # With 1 hour break from 5 PM to 6 PM ET each day
    
    is_open = False
    reason = ""
    
    if weekday == 6:  # Sunday
        if minutes_since_midnight >= 22 * 60:  # After 10 PM ET Sunday
            is_open = True
            reason = "Sunday evening opening"
        else:
            is_open = False
            reason = "Market closed (awaiting Sunday opening)"
    elif weekday < 5:  # Monday to Friday
        if minutes_since_midnight < 17 * 60:  # Before 5 PM ET (market hours)
            is_open = True
            reason = "Regular trading hours"
        elif minutes_since_midnight >= 18 * 60:  # After 6 PM ET (resume trading)
            is_open = True
            reason = "Evening trading"
        else:  # 5 PM - 6 PM ET
            is_open = False
            reason = "Daily closing break (5-6 PM ET)"
    elif weekday == 5:  # Saturday
        is_open = False
        reason = "Market closed (weekend)"
    
    return {
        'is_open': is_open,
        'status': 'OPEN' if is_open else 'CLOSED',
        'reason': reason,
        'timestamp': et_time.isoformat()
    }

# Note: Background scheduler disabled - all analysis is on-demand with manual CSV uploads

# ========== SIDEBAR: INFORMATION ==========

with st.sidebar:
    st.header("📋 Information")

    st.info("📤 **Manual Upload Mode**\n\nUpload CSV files with OHLC data (columns: time, open, high, low, close) to analyze predictions. All analysis is performed on-demand when you click the Analyze button.")

    # Analysis mode selector
    st.markdown("### 📊 Analysis Mode")
    analysis_mode = st.radio(
        "Select Mode",
        ("Upload & Analyze", "View History"),
        help="Choose between analyzing new data or viewing past predictions"
    )

# ========== MAIN CONTENT ==========

# Title
st.markdown('<div class="main-title">📊 Financial Prediction Dashboard</div>', unsafe_allow_html=True)
st.markdown("Analyze price data using the Reference Level Prediction System")
st.divider()

# ========== LATEST BIAS RESULTS SECTION ==========
st.markdown("## 📈 Latest Market Bias Results")

# Get latest predictions for each instrument
us100_preds = get_predictions_by_instrument("US100")
uk100_preds = get_predictions_by_instrument("UK100")
us500_preds = get_predictions_by_instrument("US500")

col1, col2, col3 = st.columns(3)

# US100 Display
with col1:
    st.markdown("### US100 (NASDAQ)")
    if us100_preds:
        latest_us100 = sorted(us100_preds, key=lambda x: x.get('analysis_timestamp', ''), reverse=True)[0]
        bias = latest_us100.get('result', {}).get('analysis', {}).get('bias', 'UNKNOWN')
        confidence = latest_us100.get('result', {}).get('analysis', {}).get('confidence', 0)
        update_time = latest_us100.get('analysis_timestamp', 'N/A')
        
        bias_emoji = "🟢" if bias == "BULLISH" else "🔴"
        st.markdown(f"**Bias:** {bias_emoji} {bias}")
        st.metric("Confidence", f"{confidence:.1f}%")
        st.caption(f"Updated: {update_time[:19] if update_time != 'N/A' else 'N/A'}")
        
        # Market status
        status = get_market_status("US100")
        status_class = "market-open" if status['is_open'] else "market-closed"
        st.markdown(f"**Market Status:** <span class='{status_class}'>{status['status']}</span>", unsafe_allow_html=True)
        st.caption(status['reason'])
    else:
        st.info("No predictions available yet")

# UK100 Display
with col2:
    st.markdown("### UK100 (FTSE)")
    if uk100_preds:
        latest_uk100 = sorted(uk100_preds, key=lambda x: x.get('analysis_timestamp', ''), reverse=True)[0]
        bias = latest_uk100.get('result', {}).get('analysis', {}).get('bias', 'UNKNOWN')
        confidence = latest_uk100.get('result', {}).get('analysis', {}).get('confidence', 0)
        update_time = latest_uk100.get('analysis_timestamp', 'N/A')
        
        bias_emoji = "🟢" if bias == "BULLISH" else "🔴"
        st.markdown(f"**Bias:** {bias_emoji} {bias}")
        st.metric("Confidence", f"{confidence:.1f}%")
        st.caption(f"Updated: {update_time[:19] if update_time != 'N/A' else 'N/A'}")
        
        # Market status
        status = get_market_status("UK100")
        status_class = "market-open" if status['is_open'] else "market-closed"
        st.markdown(f"**Market Status:** <span class='{status_class}'>{status['status']}</span>", unsafe_allow_html=True)
        st.caption(status['reason'])
    else:
        st.info("No predictions available yet")

# US500 Display
with col3:
    st.markdown("### US500 (S&P 500)")
    if us500_preds:
        latest_us500 = sorted(us500_preds, key=lambda x: x.get('analysis_timestamp', ''), reverse=True)[0]
        bias = latest_us500.get('result', {}).get('analysis', {}).get('bias', 'UNKNOWN')
        confidence = latest_us500.get('result', {}).get('analysis', {}).get('confidence', 0)
        update_time = latest_us500.get('analysis_timestamp', 'N/A')
        
        bias_emoji = "🟢" if bias == "BULLISH" else "🔴"
        st.markdown(f"**Bias:** {bias_emoji} {bias}")
        st.metric("Confidence", f"{confidence:.1f}%")
        st.caption(f"Updated: {update_time[:19] if update_time != 'N/A' else 'N/A'}")
        
        # Market status
        status = get_market_status("US500")
        status_class = "market-open" if status['is_open'] else "market-closed"
        st.markdown(f"**Market Status:** <span class='{status_class}'>{status['status']}</span>", unsafe_allow_html=True)
        st.caption(status['reason'])
    else:
        st.info("No predictions available yet")

st.divider()

# Initialize session state for analysis results
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None
if 'analysis_history' not in st.session_state:
    st.session_state.analysis_history = []

# Main content
if analysis_mode == "Upload & Analyze":
    # File upload section
    st.header("📁 Step 1: Upload CSV File")

    uploaded_file = st.file_uploader(
        "Choose a CSV file with OHLCV data",
        type="csv",
        help="Required columns: time, open, high, low, close"
    )

    if uploaded_file is not None:
        # Load CSV
        df = pd.read_csv(uploaded_file)

        # Validate columns
        required_cols = ['time', 'open', 'high', 'low', 'close']
        missing_cols = set(required_cols) - set(df.columns)

        if missing_cols:
            st.error(f"❌ Missing required columns: {', '.join(missing_cols)}")
            st.info(f"Required columns: {', '.join(required_cols)}")
        else:
            # Show preview
            st.subheader("📊 Data Preview")
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Total candles:** {len(df)}")
                st.write(f"**Columns:** {', '.join(df.columns.tolist())}")
            with col2:
                st.write(f"**File size:** {uploaded_file.size / 1024:.1f} KB")
                st.write(f"**Uploaded:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            with st.expander("View sample data (first 10 rows)"):
                st.dataframe(df.head(10), use_container_width=True)

            # Analyze button
            st.divider()
            st.header("📈 Step 2: Run Analysis")

            if st.button("🔍 Analyze Data", key="analyze_btn", use_container_width=True):
                with st.spinner("Running prediction analysis..."):
                    try:
                        # Import prediction engine
                        from prediction_model_v3 import PredictionEngine

                        # Parse time column
                        df['time'] = pd.to_datetime(df['time'], utc=True)
                        df.set_index('time', inplace=True)

                        # Identify instrument from filename
                        filename = uploaded_file.name
                        instrument = "US100"  # Default

                        if "NQ" in filename.upper():
                            instrument = "US100"
                        elif "ES" in filename.upper() or "SP" in filename.upper() or "US500" in filename.upper():
                            instrument = "US500"
                        elif "UK100" in filename.upper() or "FTSE" in filename.upper():
                            instrument = "UK100"

                        # Get timezone mapping
                        timezone_map = {
                            'US100': 'America/New_York',
                            'US500': 'America/Chicago',
                            'UK100': 'Europe/London',
                        }

                        timezone = timezone_map.get(instrument, 'UTC')

                        # Convert timezone
                        df.index = df.index.tz_convert(timezone)

                        # Get latest timestamp
                        latest_timestamp = str(df.index[-1])

                        # Run prediction
                        engine = PredictionEngine(instrument=instrument)
                        result = engine.analyze(df, latest_timestamp)

                        # Store result
                        st.session_state.analysis_result = {
                            'result': result,
                            'instrument': instrument,
                            'timezone': timezone,
                            'timestamp': datetime.now().isoformat(),
                            'filename': filename,
                            'data_length': len(df),
                            'current_price': df.iloc[-1]['close']
                        }

                        # Add to history
                        st.session_state.analysis_history.append(st.session_state.analysis_result)

                        # Auto-save to persistent storage
                        if save_prediction(st.session_state.analysis_result):
                            logger.info("Prediction auto-saved to storage")
                        else:
                            logger.warning("Failed to auto-save prediction")

                        st.success("✅ Analysis completed successfully!")
                        st.rerun()

                    except Exception as e:
                        st.error(f"❌ Analysis failed: {str(e)}")
                        st.info("💡 Make sure the CSV has the required columns: time, open, high, low, close")
                        with st.expander("Show error details"):
                            st.code(traceback.format_exc())

elif analysis_mode == "View History":
    st.header("📜 Analysis History (Top 50 by Data Timestamp)")
    st.markdown("Ranked by latest data point timestamp - newest data first")

    # Load top 50 predictions from persistent storage
    predictions = get_top_predictions(n=50)

    if not predictions:
        st.info("No analysis history yet. Upload and analyze a CSV file first.")
    else:
        st.metric("Total Predictions Saved", get_prediction_count(), delta="in database")
        st.divider()

        for item in predictions:
            # Extract key information
            result = item.get('result', {})
            analysis = result.get('analysis', {})
            bias = analysis.get('bias', 'UNKNOWN')
            confidence = analysis.get('confidence', 0)
            analysis_time = item.get('analysis_timestamp', 'N/A')
            latest_data_time = item.get('data_timestamp', 'N/A')

            # Create color-coded title
            bias_color = "🟢" if bias == "BULLISH" else "🔴"
            instrument = item.get('instrument', 'UNKNOWN')
            title = f"{bias_color} {instrument} - {bias} ({confidence:.1f}% confidence) | Data: {latest_data_time[:10]}"

            with st.expander(title):
                # Row 1: Timing Information
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**📅 Analysis Executed:**")
                    st.write(f"{analysis_time[:10]} at {analysis_time[11:19]}" if analysis_time != 'N/A' else "N/A")
                with col2:
                    st.write("**📊 Latest Data Point:**")
                    st.write(f"{latest_data_time[:10]} at {latest_data_time[11:19]}" if latest_data_time != 'N/A' else "N/A")

                st.divider()

                # Row 2: Result Highlight
                if bias == "BULLISH":
                    st.markdown(
                        '<div style="background-color: #00AA0020; padding: 15px; border-radius: 5px; border-left: 4px solid #00AA00;">'
                        '<span style="color: #00AA00; font-size: 24px; font-weight: bold;">▲ BULLISH</span><br>'
                        f'<span style="font-size: 18px;">Confidence: {confidence:.2f}%</span></div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        '<div style="background-color: #FF000020; padding: 15px; border-radius: 5px; border-left: 4px solid #FF0000;">'
                        '<span style="color: #FF0000; font-size: 24px; font-weight: bold;">▼ BEARISH</span><br>'
                        f'<span style="font-size: 18px;">Confidence: {confidence:.2f}%</span></div>',
                        unsafe_allow_html=True
                    )

                st.divider()

                # Row 3: Additional Details
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Instrument", instrument)
                with col2:
                    current_price = item.get('current_price', 0)
                    st.metric("Current Price", f"${current_price:.2f}")
                with col3:
                    data_length = item.get('data_length', 0)
                    st.metric("Data Points", data_length)
                with col4:
                    bullish_pct = analysis.get('bullish_weight', 0) * 100
                    bearish_pct = analysis.get('bearish_weight', 0) * 100
                    st.metric("Bull/Bear", f"{bullish_pct:.1f}% / {bearish_pct:.1f}%")

                # Optional: Full JSON details
                with st.expander("🔍 View Full Analysis Details"):
                    st.json(result)


# Display results if available
if st.session_state.analysis_result:
    st.divider()
    st.header("📊 Step 3: Analysis Results")

    result = st.session_state.analysis_result['result']
    instrument = st.session_state.analysis_result['instrument']
    current_price = st.session_state.analysis_result['current_price']

    # Main metrics in columns
    col1, col2, col3, col4 = st.columns(4)

    # Bias
    bias = result['analysis']['bias']
    confidence = result['analysis']['confidence']
    bullish_weight = result['analysis']['bullish_weight']
    bearish_weight = result['analysis']['bearish_weight']

    with col1:
        st.metric(
            label="Directional Bias",
            value=bias,
            delta=f"{confidence:.2f}% confidence"
        )
        if bias == "BULLISH":
            st.markdown('<span class="bullish">▲ BULLISH</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="bearish">▼ BEARISH</span>', unsafe_allow_html=True)

    with col2:
        st.metric(
            label="Confidence Score",
            value=f"{confidence:.2f}%",
            delta="Prediction strength"
        )

    with col3:
        st.metric(
            label="Bullish Weight",
            value=f"{bullish_weight*100:.2f}%",
            delta=f"{bullish_weight*100:.2f}% of signals"
        )

    with col4:
        st.metric(
            label="Bearish Weight",
            value=f"{bearish_weight*100:.2f}%",
            delta=f"{bearish_weight*100:.2f}% of signals"
        )

    st.divider()

    # Metadata section
    st.subheader("📋 Analysis Metadata")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.write(f"**Instrument:** {instrument}")
        st.write(f"**Current Price:** ${current_price:.2f}")

    with col2:
        st.write(f"**Timezone:** {st.session_state.analysis_result['timezone']}")
        st.write(f"**Timestamp:** {result['metadata']['timestamp']}")

    with col3:
        st.write(f"**Available Levels:** {result['weights']['available_levels']}/{result['weights']['total_levels']}")
        st.write(f"**Weight Utilization:** {result['weights']['utilization']*100:.2f}%")

    st.divider()

    # Reference levels table - Updated terminology
    st.subheader("📊 Reference Levels (20)")

    # Convert levels to dataframe for display
    levels_data = []
    for level in result['levels']:
        distance = level['distance_percent'] if level['distance_percent'] is not None else 0.0
        
        # Determine if level is bullish (above) or bearish (below)
        position_type = "Bullish" if level['position'] == 'above' else "Bearish"
        
        levels_data.append({
            'Level Name': level['name'].replace('_', ' ').title(),
            'Price': f"${level['price']:.2f}",
            'Distance (%)': f"{distance:.3f}%",
            'Position': position_type,
            'Depreciation': f"{level['depreciation']:.3f}",
            'Effective Weight': f"{level['effective_weight']:.4f}"
        })

    levels_df = pd.DataFrame(levels_data)
    st.dataframe(levels_df, use_container_width=True, hide_index=True)

    st.divider()

# Footer
st.divider()
st.caption("""
Prediction Model v3.0 — Reference Level-based Analytical Framework
Designed for technical analysis of financial instruments (US100/NASDAQ, ES/S&P500, UK100/FTSE)
Manual Analysis Mode | Pages: Admin Settings, Prediction History
""")
