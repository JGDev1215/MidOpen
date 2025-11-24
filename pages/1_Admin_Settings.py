#!/usr/bin/env python3
"""
Admin Settings Page
Configure weights for prediction levels with audit logging
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime
from pathlib import Path

# Configure page
st.set_page_config(
    page_title="Admin Settings - QinPredict",
    page_icon="⚙️",
    layout="wide"
)

# Import DI accessors for weight and logging management
from src.di.accessors import (
    get_config_service,
    get_logging_service,
    get_weights,
    set_weights,
    validate_weights,
    get_all_instruments,
    log_weight_change,
    get_weight_change_history,
    get_summary_statistics
)

st.markdown("# ⚙️ Admin Settings")
st.markdown("Configure prediction model weights and view adjustment history")
st.divider()

# Sidebar for instrument selection
with st.sidebar:
    st.header("🎯 Configuration")
    selected_instrument = st.selectbox(
        "Select Instrument",
        ["US100", "UK100", "US500"],
        help="Choose which instrument to configure"
    )

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.header(f"📊 Weight Configuration: {selected_instrument}")

with col2:
    # Quick actions
    if st.button("🔄 Reset to Defaults", use_container_width=True):
        config_service = get_config_service()
        config_service.reset_instrument_weights(selected_instrument)
        
        # Update session state
        defaults = config_service.get_weights(selected_instrument)
        for level_name, weight in defaults.items():
            st.session_state[f"slider_{level_name}"] = weight
            
        st.success(f"Reset {selected_instrument} weights to defaults")
        st.rerun()

st.markdown("Adjust weights for all reference levels. Weights must sum to **1.0**")
st.divider()

# Get current weights
current_weights = get_weights(selected_instrument)
weight_names = list(current_weights.keys())

# CRITICAL FIX #1: Initialize session state for all sliders BEFORE rendering them
# This ensures Streamlit properly tracks slider values across reruns
for level_name in weight_names:
    slider_key = f"slider_{level_name}"
    if slider_key not in st.session_state:
        st.session_state[slider_key] = current_weights.get(level_name, 0.0)

# Create columns for weight sliders
col_heading, col_button = st.columns([4, 1])

with col_heading:
    st.markdown("### 🎚️ Level Weights")

with col_button:
    if st.button("⚖️ Normalize Weights", use_container_width=True, help="Adjust all weights proportionally so they sum to 1.0"):
        # Read current slider values from session state (preserving user's manual adjustments)
        current_slider_values = {}
        total_current_weight = 0.0

        for level_name in weight_names:
            # Get value from session state (user modified) or fall back to saved weight
            val = st.session_state.get(f"slider_{level_name}", current_weights.get(level_name, 0.0))
            current_slider_values[level_name] = val
            total_current_weight += val

        # Normalize weights: scale proportionally so sum = 1.0
        normalized_weights = {}

        if total_current_weight > 0.0:
            # Proportional scaling: preserve relative proportions while summing to 1.0
            for level_name, current_val in current_slider_values.items():
                normalized_weights[level_name] = round(current_val / total_current_weight, 6)
        else:
            # Edge case: all weights are 0, fall back to equal distribution
            equal_weight = 1.0 / len(weight_names)
            remaining = 1.0
            for i, level_name in enumerate(weight_names):
                if i == len(weight_names) - 1:
                    normalized_weights[level_name] = round(remaining, 6)
                else:
                    normalized_weights[level_name] = round(equal_weight, 6)
                    remaining -= round(equal_weight, 6)

        # Save normalized weights
        set_weights(selected_instrument, normalized_weights)

        # Update session state BEFORE displaying success message
        # This ensures sliders will reflect new values when page reruns
        for level_name, weight in normalized_weights.items():
            st.session_state[f"slider_{level_name}"] = weight

        # Log the change
        log_weight_change(
            instrument=selected_instrument,
            old_weights=current_weights,
            new_weights=normalized_weights,
            user="admin",
            reason="Proportional normalization via Normalize Weights button"
        )

        st.success(f"✅ Weights normalized and saved! Total weight now equals 1.0")

        # Force UI update to show normalized values in sliders
        st.rerun()

# Display weights in groups
col_count = 2
cols = st.columns(col_count)
col_idx = 0

new_weights = {}

for level_name in weight_names:
    col = cols[col_idx % col_count]

    with col:
        # CRITICAL FIX #4: Use session state value as the slider's default
        # This ensures sliders show the most recent value (either from disk or from equalization)
        # If user adjusted a slider, session state will have that value
        # If equalize was clicked, session state will have the equalized value
        session_value = st.session_state.get(f"slider_{level_name}", current_weights.get(level_name, 0.0))
        
        st.markdown(f"**{level_name.replace('_', ' ').title()}**")

        # CRITICAL FIX #5: Increase max_value from 0.2 to 1.0
        # Previous constraint of 0.2 meant users couldn't allocate more than 20% to any weight
        # With 20 levels, equal distribution is 5% (0.05)
        # Some users might want to weight one level heavily (e.g., 0.25 or 0.40)
        # This was artificially limiting and confusing
        # NOTE: Validation still ensures total = 1.0, so this won't break anything
        new_value = st.slider(
            label=f"Weight for {level_name}",
            min_value=0.0,
            max_value=1.0,  # FIX: Increased from 0.2 to 1.0 for better flexibility
            value=session_value,
            step=0.000001,
            label_visibility="collapsed",
            key=f"slider_{level_name}"
        )

        st.text(f"Current: {new_value:.6f}")
        new_weights[level_name] = new_value

    col_idx += 1

st.divider()

# Weight validation and summary
st.markdown("### 📊 Weight Summary")

total_weight = sum(new_weights.values())
is_valid, validation_message = validate_weights(new_weights)

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="Total Weight",
        value=f"{total_weight:.6f}",
        delta="Target: 1.000000"
    )

with col2:
    st.metric(
        label="Weight Count",
        value=len(new_weights),
        delta=f"{len([w for w in new_weights.values() if w > 0])} active"
    )

with col3:
    if is_valid:
        st.metric(label="Status", value="✅ Valid", delta="Weights sum to 1.0")
    else:
        st.metric(label="Status", value="❌ Invalid", delta=validation_message)

# Detailed weight list
st.markdown("### 📋 Weight Details")

weights_table_data = []
for level_name, weight in new_weights.items():
    old_weight = current_weights.get(level_name, 0.0)
    change = weight - old_weight

    weights_table_data.append({
        'Level': level_name.replace('_', ' ').title(),
        'Current': f"{weight:.6f}",
        'Previous': f"{old_weight:.6f}",
        'Change': f"{change:+.6f}",
        'Percentage': f"{weight*100:.4f}%"
    })

weights_df = pd.DataFrame(weights_table_data)
st.dataframe(weights_df, use_container_width=True, hide_index=True)

st.divider()

# Save or discard changes
col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    if st.button("💾 Save Changes", use_container_width=True, type="primary"):
        if not is_valid:
            st.error(f"❌ Cannot save: {validation_message}")
        else:
            try:
                # Check if there are actual changes
                has_changes = any(
                    abs(new_weights.get(k, 0.0) - current_weights.get(k, 0.0)) > 0.00001
                    for k in set(list(new_weights.keys()) + list(current_weights.keys()))
                )

                if has_changes:
                    # Save weights first
                    set_weights(selected_instrument, new_weights)

                    # Log the change only if saved
                    log_weight_change(
                        instrument=selected_instrument,
                        old_weights=current_weights,
                        new_weights=new_weights,
                        user="admin",
                        reason="Manual adjustment via Admin Settings"
                    )

                    st.success(f"✅ Weights for {selected_instrument} updated successfully!")
                    st.info("Changes logged for audit trail")
                    st.rerun()
                else:
                    st.info("No changes detected - weights are identical to current values")
            except Exception as e:
                st.error(f"❌ Error saving weights: {str(e)}")

with col2:
    if st.button("↩️ Discard Changes", use_container_width=True):
        st.info("Changes discarded - reloading original values")
        st.rerun()

with col3:
    st.info("💡 Only saved changes are logged for audit purposes")

st.divider()

# Change history
st.markdown("## 📜 Weight Change History")

change_history = get_weight_change_history(instrument=selected_instrument, days=30)

if not change_history:
    st.info(f"No weight changes recorded for {selected_instrument} in the last 30 days")
else:
    st.markdown(f"**Latest {len(change_history)} changes for {selected_instrument}:**")

    for idx, entry in enumerate(change_history):
        with st.expander(f"📝 {entry['timestamp'][:19]} - {entry['num_changed_levels']} levels modified"):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.write(f"**User:** {entry['user']}")
                st.write(f"**Reason:** {entry['reason']}")

            with col2:
                st.write(f"**Levels Changed:** {entry['num_changed_levels']}")
                st.write(f"**Old Total:** {entry['old_total']:.6f}")

            with col3:
                st.write(f"**New Total:** {entry['new_total']:.6f}")

            # Show changed levels
            st.markdown("**Changed Levels:**")
            change_details = []
            for level_name, changes in entry['changes'].items():
                change_details.append({
                    'Level': level_name.replace('_', ' ').title(),
                    'Old': f"{changes['old']:.6f}",
                    'New': f"{changes['new']:.6f}",
                    'Change': f"{changes['change']:+.6f}"
                })

            changes_df = pd.DataFrame(change_details)
            st.dataframe(changes_df, use_container_width=True, hide_index=True)

st.divider()

# Statistics
st.markdown("## 📈 Adjustment Statistics")

stats = get_summary_statistics(selected_instrument)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Total Adjustments",
        value=stats.get('total_changes', 0),
        delta="All time"
    )

with col2:
    most_adjusted_level = stats.get('most_adjusted_level')
    most_adjusted_count = stats.get('most_adjusted_count', 0)
    st.metric(
        label="Most Adjusted Level",
        value=most_adjusted_level[:20] if most_adjusted_level else "N/A",
        delta=f"{most_adjusted_count} times"
    )

with col3:
    st.metric(
        label="Unique Levels Modified",
        value=stats.get('unique_levels_modified', 0),
        delta=f"of {len(weight_names)} total"
    )

with col4:
    last_change = stats.get('last_change')
    if last_change:
        st.metric(
            label="Last Change",
            value=last_change[:10],
            delta=last_change[11:19]
        )
    else:
        st.metric(label="Last Change", value="Never")

st.divider()

# Export options
st.markdown("## 💾 Export Options")

col1, col2 = st.columns(2)

with col1:
    if st.button("📥 Export Current Weights (JSON)"):
        config_service = get_config_service()
        weights_export = config_service.export_weights()
        json_str = json.dumps(weights_export, indent=2)
        st.download_button(
            label="Download Weights JSON",
            data=json_str,
            file_name=f"weights_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )

with col2:
    if st.button("📥 Export Change History (CSV)"):
        # Get logging service and export history
        logging_service = get_logging_service()
        history = logging_service.get_change_history(instrument=selected_instrument, days=365)

        if history:
            # Convert history to CSV format
            import io
            csv_buffer = io.StringIO()
            csv_buffer.write("Timestamp,User,Reason,Num_Changed_Levels,Old_Total,New_Total\n")

            for entry in history:
                csv_buffer.write(f"{entry['timestamp']},{entry.get('user', 'unknown')},{entry.get('reason', '')},{entry['num_changed_levels']},{entry['old_total']},{entry['new_total']}\n")

            csv_content = csv_buffer.getvalue()

            st.download_button(
                label="Download Change History CSV",
                data=csv_content,
                file_name=f"weight_history_{selected_instrument}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No change history available to export")

st.divider()

# Info section
st.markdown("## ℹ️ Information")

with st.expander("How weight adjustments work", expanded=False):
    st.markdown("""
    ### Weight Adjustment System

    - **Weights**: Control how much each reference level influences the final prediction
    - **Sum Requirement**: All weights for an instrument must sum to exactly 1.0
    - **Normalization**: The system automatically normalizes weights if some levels are unavailable
    - **Audit Trail**: Every adjustment is logged with timestamp, user, and reason
    - **History**: View past changes in the "Weight Change History" section above

    ### Best Practices

    1. Make small, gradual adjustments to weights
    2. Always document your reason for changes
    3. Monitor prediction accuracy after adjustments
    4. Use the export feature to backup configurations
    5. Review the change history regularly

    ### Reference Levels

    Each weight controls the influence of different market reference points:
    - **Daily levels**: Daily midnight, hourly opens, previous day high/low
    - **Weekly levels**: Week start, high, low, previous week values
    - **Session levels**: Market session opens (NY, London, Asian, Chicago)
    - **Conditional levels**: Only available during specific market hours
    """)

with st.expander("Audit trail information", expanded=False):
    st.markdown("""
    ### Audit Logging

    All weight changes are automatically logged with:
    - **Timestamp**: Exact time of modification
    - **User**: Who made the change (default: admin)
    - **Reason**: Why the change was made
    - **Changes**: Detailed list of all modified levels
    - **Old/New Values**: Before and after weights

    ### Access to Logs

    Weight change logs are stored in:
    - **Location**: `config/weight_changes/`
    - **Format**: JSON files organized by date
    - **Retention**: Unlimited historical records

    ### Export

    Use the export options above to:
    - Download current weight configuration as JSON
    - Export full change history as CSV for external analysis
    - Create backups before major adjustments
    """)

st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Configuration: {selected_instrument}")
