#!/usr/bin/env python3
"""
Prediction History Page
Query and view historical predictions organized by instrument
"""

import streamlit as st
import pandas as pd
from datetime import datetime

# Configure page
st.set_page_config(
    page_title="Prediction History - QinPredict",
    page_icon="📊",
    layout="wide"
)

# Import DI accessors for prediction retrieval
from src.di.accessors import (
    get_prediction_count,
    get_predictions_by_instrument
)

st.markdown("# 📊 Prediction History")
st.markdown("View and analyze predictions organized by instrument")
st.divider()

# Show total saved predictions
total_count = get_prediction_count()
st.info(f"📁 **Total Saved Predictions**: {total_count} files")
st.divider()

# Sidebar filters
with st.sidebar:
    st.header("🔍 Filters")

    # Bias filter
    st.markdown("### Bias Filter")
    bias_filter = st.multiselect(
        "Filter by Bias",
        ["BULLISH", "BEARISH"],
        default=["BULLISH", "BEARISH"],
        help="Filter predictions by bullish or bearish bias"
    )

# Display filter info
st.info(f"📊 **Bias Filter**: {', '.join(bias_filter) if bias_filter else 'None selected'}")

st.divider()

# Create tabs for each instrument
tab1, tab2, tab3 = st.tabs(["🇺🇸 US100 (NASDAQ)", "🇬🇧 UK100 (FTSE)", "🇺🇸 US500 (S&P 500)"])

def display_instrument_predictions(tab, instrument: str, bias_list):
    """Display all predictions for a specific instrument"""
    with tab:
        # Get predictions for this instrument
        all_preds = get_predictions_by_instrument(instrument)

        # Sort by data timestamp (newest first)
        all_preds = sorted(all_preds, key=lambda x: x.get('data_timestamp', ''), reverse=True)

        # Filter by bias
        filtered_preds = [p for p in all_preds if p.get('result', {}).get('analysis', {}).get('bias') in bias_list]

        if not filtered_preds:
            st.info(f"No predictions found for {instrument}")
            return

        # Show statistics
        st.markdown(f"## {instrument} Predictions")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Predictions", len(filtered_preds))

        with col2:
            bullish_count = sum(1 for p in filtered_preds if p.get('result', {}).get('analysis', {}).get('bias') == 'BULLISH')
            st.metric("Bullish", bullish_count, f"{bullish_count/len(filtered_preds)*100:.1f}%" if filtered_preds else "0%")

        with col3:
            bearish_count = sum(1 for p in filtered_preds if p.get('result', {}).get('analysis', {}).get('bias') == 'BEARISH')
            st.metric("Bearish", bearish_count, f"{bearish_count/len(filtered_preds)*100:.1f}%" if filtered_preds else "0%")

        with col4:
            avg_confidence = sum(p.get('result', {}).get('analysis', {}).get('confidence', 0) for p in filtered_preds) / len(filtered_preds) if filtered_preds else 0
            st.metric("Avg Confidence", f"{avg_confidence:.2f}%")

        st.divider()

        # Create table
        st.markdown("### Detailed Results")

        table_data = []
        for pred in filtered_preds:
            result = pred.get('result', {})
            analysis = result.get('analysis', {})
            table_data.append({
                'Data Timestamp': pred.get('data_timestamp', 'N/A')[:19],
                'Bias': analysis.get('bias', 'N/A'),
                'Confidence': f"{analysis.get('confidence', 0):.2f}%",
                'Bullish Weight': f"{analysis.get('bullish_weight', 0):.4f}",
                'Bearish Weight': f"{analysis.get('bearish_weight', 0):.4f}",
                'CSV File': pred.get('filename', 'N/A'),
                'Data Points': pred.get('data_length', 0)
            })

        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Chart - Bias distribution
        col1, col2 = st.columns(2)

        with col1:
            bias_counts = {
                'BULLISH': bullish_count,
                'BEARISH': bearish_count
            }
            st.bar_chart(pd.Series(bias_counts))
            st.caption(f"Bias Distribution for {instrument}")

        with col2:
            # Confidence trend (last 20)
            confidence_data = [
                {
                    'Data Date': p.get('data_timestamp', '')[:10],
                    'Confidence': p.get('result', {}).get('analysis', {}).get('confidence', 0)
                }
                for p in filtered_preds[-20:]
            ]
            if confidence_data:
                conf_df = pd.DataFrame(confidence_data)
                st.line_chart(conf_df.set_index('Data Date'))
                st.caption(f"Confidence Trend (Last 20) for {instrument}")

        st.divider()

        # Export option
        if st.button(f"📥 Export {instrument} Predictions (CSV)", key=f"export_{instrument}"):
            csv = df.to_csv(index=False)
            st.download_button(
                label=f"Download {instrument} CSV",
                data=csv,
                file_name=f"{instrument}_predictions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

# Display each instrument
display_instrument_predictions(tab1, "US100", bias_filter)
display_instrument_predictions(tab2, "UK100", bias_filter)
display_instrument_predictions(tab3, "US500", bias_filter)

st.divider()

# Information section
st.markdown("## ℹ️ About Predictions")

with st.expander("How Predictions Work", expanded=False):
    st.markdown("""
    ### Prediction System

    - **Upload**: Place CSV files with OHLC data in the app
    - **Analyze**: Click "Analyze Data" to run instant predictions
    - **Auto-Save**: Results automatically saved to persistent storage
    - **View History**: Browse predictions organized by instrument

    ### Instruments Supported

    | Instrument | Filename Match | Timezone |
    |-----------|----------------|----------|
    | **US100** | NQ, US100, NASDAQ | America/New_York (ET) |
    | **US500** | ES, SP, S&P, US500 | America/Chicago (CT) |
    | **UK100** | UK100, FTSE | Europe/London (GMT) |

    ### Fields Explained

    - **Data Timestamp**: When the latest OHLC candle was recorded
    - **Bias**: BULLISH or BEARISH direction prediction
    - **Confidence**: Strength of prediction (0-100%)
    - **Weights**: Distribution of bullish vs bearish signals
    - **CSV File**: Source filename of the analysis
    - **Data Points**: Number of OHLC candles in the analysis
    """)

st.caption(f"Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
