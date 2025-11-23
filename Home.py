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
    .job-status-running {
        color: #00AA00;
        font-weight: bold;
    }
    .job-status-stopped {
        color: #FF0000;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

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

    # Reference levels table
    st.subheader("📊 Reference Levels (20)")

    # Convert levels to dataframe for display
    levels_data = []
    for level in result['levels']:
        distance = level['distance_percent'] if level['distance_percent'] is not None else 0.0
        levels_data.append({
            'Level Name': level['name'].replace('_', ' ').title(),
            'Price': f"${level['price']:.2f}",
            'Distance (%)': f"{distance:.3f}%",
            'Position': level['position'],
            'Depreciation': f"{level['depreciation']:.3f}",
            'Effective Weight': f"{level['effective_weight']:.4f}"
        })

    levels_df = pd.DataFrame(levels_data)
    st.dataframe(levels_df, use_container_width=True, hide_index=True)

    st.divider()

    # Export section
    st.subheader("💾 Export Options")

    col1, col2 = st.columns(2)

    with col1:
        json_str = json.dumps(result, indent=2)
        st.download_button(
            label="📥 Download JSON",
            data=json_str,
            file_name=f"prediction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )

    with col2:
        levels_csv = levels_df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV (Levels)",
            data=levels_csv,
            file_name=f"levels_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

# Footer
st.divider()
st.caption("""
Prediction Model v3.0 — Reference Level-based Analytical Framework
Designed for technical analysis of financial instruments (US100/NASDAQ, ES/S&P500, UK100/FTSE)
Background Scheduler: APScheduler with Streamlit integration | Pages: Admin Settings, Prediction History, Scheduler Status
""")
