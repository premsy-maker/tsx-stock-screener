import streamlit as st
import pandas as pd
import plotly.express as px
import os
import re
from datetime import datetime
from notifierV1 import send_feedback_email

# -----------------------------------------------------------------------------
# App Configuration & Page Layout
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Bay Street Pulse",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

APP_VERSION = "v1.0-beta"
CSV_FILE = "screener_results.csv"

# -----------------------------------------------------------------------------
# Data Loader
# -----------------------------------------------------------------------------
def load_screener_data(filepath: str):
    if not os.path.exists(filepath):
        return None, None
    file_mtime = os.path.getmtime(filepath)
    scan_time_str = datetime.fromtimestamp(file_mtime).strftime("%b %d, %Y - %I:%M %p")
    df = pd.read_csv(filepath)
    return df, scan_time_str

def is_valid_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email.strip()))

# -----------------------------------------------------------------------------
# Floating Widgets (Feedback Button + Bottom-Right Version Tag)
# -----------------------------------------------------------------------------
def render_floating_elements():
    st.markdown(
        f"""
        <style>
        /* Position the Feedback Popover Button at Bottom-Right */
        div[data-testid="stPopover"] {{
            position: fixed;
            bottom: 36px;
            right: 24px;
            z-index: 999998;
        }}
        div[data-testid="stPopover"] > button {{
            background-color: #0b3954;
            color: #ffffff;
            border-radius: 20px;
            padding: 8px 18px;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.25);
            border: 1px solid rgba(255, 255, 255, 0.15);
        }}
        div[data-testid="stPopover"] > button:hover {{
            background-color: #125278;
            color: #ffffff;
            border-color: #ffffff;
        }}

        /* Subtle Bottom-Right Version Stamp */
        .bottom-right-version {{
            position: fixed;
            bottom: 10px;
            right: 28px;
            z-index: 999999;
            font-size: 11px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
            color: #888888;
            background: rgba(255, 255, 255, 0.8);
            padding: 2px 6px;
            border-radius: 4px;
            pointer-events: none;
        }}
        @media (prefers-color-scheme: dark) {{
            .bottom-right-version {{
                background: rgba(20, 20, 20, 0.7);
                color: #aaaaaa;
            }}
        }}
        </style>
        <div class="bottom-right-version">Bay Street Pulse &bull; {APP_VERSION}</div>
        """,
        unsafe_allow_html=True
    )

    with st.popover("💬 Submit Feedback"):
        st.subheader("Send Feedback")
        st.caption("Found an issue or have a suggestion? Send a note directly to our inbox.")

        with st.form("feedback_form", clear_on_submit=True):
            user_email = st.text_input("Your Email", placeholder="name@example.com").strip()
            user_comments = st.text_area(
                "Feedback / Comments", 
                placeholder="Write your feedback in a few sentences...",
                height=120
            ).strip()

            submitted = st.form_submit_button("Send Feedback")

            if submitted:
                if not user_email:
                    st.error("Please provide your email address.")
                elif not is_valid_email(user_email):
                    st.error("Please enter a valid email address (e.g., name@domain.com).")
                elif not user_comments or len(user_comments.split()) < 3:
                    st.error("Please enter meaningful feedback (at least a full sentence).")
                else:
                    try:
                        send_feedback_email(sender_email=user_email, feedback_text=user_comments)
                        st.success("Thank you! Your feedback has been sent directly to the inbox.")
                    except Exception as e:
                        st.error(f"Failed to send feedback: {e}")

# -----------------------------------------------------------------------------
# Sidebar: Controls, Filters & Disclaimer
# -----------------------------------------------------------------------------
st.sidebar.title("📈 Bay Street Pulse")
st.sidebar.caption(f"Status: **Beta** ({APP_VERSION})")

refresh_interval = st.sidebar.selectbox(
    "⏱️ Auto-Refresh Interval",
    options=["30s", "1m", "5m", "10m"],
    index=1,
)

if st.sidebar.button("🔄 Refresh Data Now"):
    st.rerun()

st.sidebar.markdown("---")

selected_signals = st.sidebar.multiselect(
    "Signal Classification",
    options=["BUY / ACCUMULATE", "SELL / EXIT", "TRIM / TAKE PROFIT", "KEEP / HOLD"],
    default=["BUY / ACCUMULATE", "SELL / EXIT", "TRIM / TAKE PROFIT", "KEEP / HOLD"]
)

rsi_range = st.sidebar.slider("14-Day RSI Window", 0.0, 100.0, (0.0, 100.0), 1.0)

trend_mode = st.sidebar.radio(
    "SMA Trend Configuration",
    options=["All Trends", "Bullish (SMA 50 > SMA 200)", "Bearish / Death Cross (SMA 50 < SMA 200)"],
    index=0
)

search_input = st.sidebar.text_input("Find Symbol or Company", "").strip().upper()

# Educational Disclaimer in Sidebar
st.sidebar.markdown("---")
st.sidebar.caption(
    "⚠️ **Educational Disclaimer:**\n\n"
    "This platform is developed strictly for **educational and informational purposes only**. "
    "It does not constitute financial, investment, legal, or tax advice. Market data "
    "is sourced via open public endpoints and may be delayed or subject to revision. "
    "Technical indicators and signals do not guarantee future returns. Always conduct "
    "independent research and consult a licensed financial advisor before making investment decisions."
)

# -----------------------------------------------------------------------------
# Main Dashboard
# -----------------------------------------------------------------------------
@st.fragment(run_every=refresh_interval)
def render_live_dashboard():
    df_raw, scan_time_str = load_screener_data(CSV_FILE)

    if df_raw is None or df_raw.empty:
        st.warning(f"Waiting for `{CSV_FILE}`... Run `python ScreenStocksV1.py` first.")
        return

    df = df_raw.copy()

    # Backwards compatibility: rename Ticker to Symbol if reading an older CSV
    if "Ticker" in df.columns and "Symbol" not in df.columns:
        df.rename(columns={"Ticker": "Symbol"}, inplace=True)

    today_date = datetime.now().strftime("%A, %B %d, %Y")
    current_time = datetime.now().strftime("%I:%M:%S %p")

    st.title("📈 Bay Street Pulse")
    st.markdown(
        f"**Date:** {today_date} &nbsp;|&nbsp; "
        f"**Last Refreshed:** {current_time} &nbsp;|&nbsp; "
        f"**Engine Scan Data:** {scan_time_str}"
    )

    filtered_df = df[df["Signal"].isin(selected_signals)]
    filtered_df = filtered_df[filtered_df["RSI_14"].between(rsi_range[0], rsi_range[1])]

    if trend_mode == "Bullish (SMA 50 > SMA 200)":
        filtered_df = filtered_df[filtered_df["SMA_50"] > filtered_df["SMA_200"]]
    elif trend_mode == "Bearish / Death Cross (SMA 50 < SMA 200)":
        filtered_df = filtered_df[filtered_df["SMA_50"] < filtered_df["SMA_200"]]

    # Search filter matching against Symbol or Company
    if search_input:
        has_symbol_match = filtered_df["Symbol"].str.contains(search_input, na=False)
        has_company_match = (
            filtered_df["Company"].str.upper().str.contains(search_input, na=False)
            if "Company" in filtered_df.columns else False
        )
        filtered_df = filtered_df[has_symbol_match | has_company_match]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Watchlist Displayed", f"{len(filtered_df)} / {len(df)}")
    col2.metric("🟢 Buy / Accumulate", len(df[df["Signal"] == "BUY / ACCUMULATE"]))
    col3.metric("🔴 Sell / Exit", len(df[df["Signal"] == "SELL / EXIT"]))
    col4.metric("🟠 Trim / Profit", len(df[df["Signal"] == "TRIM / TAKE PROFIT"]))

    st.markdown("---")

    tab_data, tab_charts, tab_manual = st.tabs(["📋 Filtered Watchlist", "📊 Market Technicals", "📖 User Manual"])

    with tab_data:
        if filtered_df.empty:
            st.info("No symbols match your current filter settings.")
        else:
            def signal_styler(val):
                if "BUY" in str(val):
                    return "color: #4ade80; background-color: rgba(74, 222, 128, 0.15); font-weight: bold;"
                elif "SELL" in str(val):
                    return "color: #f87171; background-color: rgba(248, 113, 113, 0.15); font-weight: bold;"
                elif "TRIM" in str(val):
                    return "color: #fb923c; background-color: rgba(251, 146, 60, 0.15); font-weight: bold;"
                return "color: #9ca3af;"

            styled_df = (
                filtered_df.style
                .format({
                    "Price": "${:.2f}",
                    "SMA_50": "${:.2f}",
                    "SMA_200": "${:.2f}",
                    "RSI_14": "{:.1f}",
                })
                .map(signal_styler, subset=["Signal"])
            )

            st.dataframe(styled_df, width="stretch", hide_index=True)

            st.download_button(
                label="📥 Export Current Filter (CSV)",
                data=filtered_df.to_csv(index=False).encode("utf-8"),
                file_name="bay_street_pulse_filtered.csv",
                mime="text/csv",
                key="download_csv_btn"
            )

    with tab_charts:
        if not filtered_df.empty:
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("RSI Momentum Distribution")
                fig_rsi = px.histogram(
                    filtered_df,
                    x="RSI_14",
                    nbins=20,
                    color="Signal",
                    color_discrete_map={
                        "BUY / ACCUMULATE": "#2e7d32",
                        "SELL / EXIT": "#d32f2f",
                        "TRIM / TAKE PROFIT": "#ed6c02",
                        "KEEP / HOLD": "#757575"
                    },
                    template="plotly_white"
                )
                fig_rsi.add_vline(x=40, line_dash="dot", line_color="green", annotation_text="Pullback (<=40)")
                fig_rsi.add_vline(x=75, line_dash="dot", line_color="red", annotation_text="Overextended (>=75)")
                fig_rsi.update_layout(xaxis_title="14-Day RSI", yaxis_title="Count", height=420)
                st.plotly_chart(fig_rsi, width="stretch")

            with c2:
                st.subheader("Price vs. 50-Day Moving Average")
                fig_spread = px.scatter(
                    filtered_df,
                    x="SMA_50",
                    y="Price",
                    text="Symbol",
                    hover_data=["Company"] if "Company" in filtered_df.columns else None,
                    color="Signal",
                    color_discrete_map={
                        "BUY / ACCUMULATE": "#2e7d32",
                        "SELL / EXIT": "#d32f2f",
                        "TRIM / TAKE PROFIT": "#ed6c02",
                        "KEEP / HOLD": "#757575"
                    },
                    template="plotly_white"
                )
                fig_spread.update_traces(textposition="top center")
                fig_spread.update_layout(xaxis_title="50-Day SMA (CAD)", yaxis_title="Price (CAD)", height=420)
                st.plotly_chart(fig_spread, width="stretch")

    with tab_manual:
        st.subheader("Bay Street Pulse — System Documentation & Guide")

        with st.expander("1. Introduction", expanded=True):
            st.markdown(
                """
                **Bay Street Pulse** is an automated technical momentum dashboard designed 
                to track Canadian large-cap securities and core benchmark ETFs listed on the Toronto Stock Exchange (TSX). 
                
                The engine evaluates trend momentum, moving average relationships, and oscillator conditions 
                across a curated list of liquid equities, transforming raw market bars into clear, rule-based 
                classifications to support self-directed analysis.
                """
            )

        with st.expander("2. What Business Problem This Application Solves", expanded=True):
            st.markdown(
                """
                * **Eliminates Manual Chart Screening:** Scanning individual technical charts across dozens of Canadian equities daily requires hours of manual work. Bay Street Pulse aggregates this into an instant multi-dimensional view.
                * **Removes Emotional & Cognitive Bias:** Trading decisions frequently suffer from subjective bias, FOMO, or hesitation during market pullbacks. The screener applies deterministic mathematical rules consistently.
                * **Identifies Actionable Entry & Exit Windows:** Pinpoints specific structural setups—such as value pullbacks within primary bull trends or emerging macro trend breakdowns—ensuring timely review.
                """
            )

        with st.expander("3. Basic Terminologies & Technical Rationales", expanded=True):
            st.markdown("#### Primary Indicators")
            st.markdown(
                """
                * **RSI_14 (Relative Strength Index - 14 Days):** A bounded momentum oscillator (0 to 100) measuring the velocity and magnitude of directional price movements. It highlights whether an equity is overextended or oversold relative to its 14-day history.
                * **SMA_50 (50-Day Simple Moving Average):** The rolling average closing price over the trailing 50 sessions (~10 weeks). Used as a dynamic intermediate benchmark for medium-term momentum.
                * **SMA_200 (200-Day Simple Moving Average):** The rolling average closing price over 200 trading sessions (~40 weeks). A key institutional indicator separating secular bull markets from bear markets.
                """
            )

            st.markdown("---")
            st.markdown("#### Signal Classifications & Rationale Terms")
            st.markdown(
                """
                | Signal | Rationale | Technical Logic | Market Meaning |
                | :--- | :--- | :--- | :--- |
                | **`BUY / ACCUMULATE`** | **Bullish trend + Pullback dip** | `SMA_50 > SMA_200` and `RSI_14 <= 40` | The security maintains a macro uptrend (Golden regime), but a temporary short-term pullback has pushed the 14-day RSI into value territory. |
                | **`SELL / EXIT`** | **Death Cross (Bearish trend)** | `SMA_50 < SMA_200` | The intermediate 50-day average has crossed beneath the 200-day average, signaling downside pressure and prolonged weakness. |
                | **`TRIM / TAKE PROFIT`** | **Overextended momentum** | `RSI_14 >= 75` | Aggressive buying momentum has pushed the oscillator into extreme overbought territory, increasing mean-reversion risk. |
                | **`KEEP / HOLD`** | **Trading within baseline** | Normal range | Price momentum is oscillating within standard historical bands without technical triggers. |
                """
            )

        with st.expander("4. How Frequently the Data is Refreshed", expanded=True):
            st.markdown(
                """
                Bay Street Pulse functions on a two-tier schedule:
                
                * **Backend Data Pipeline (GitHub Actions Engine):** Executes twice each weekday:
                  * **Morning Session Run:** ~10:32 AM EDT (`14:32 UTC`) to capture early-session volume and price shifts.
                  * **Post-Close Confirmation Run:** ~4:47 PM EDT (`20:47 UTC`), approximately 45 minutes after the TSX closing bell to capture settled daily closing prices.
                * **Streamlit UI Auto-Refresh:** Automatically refreshes without full page reloads according to the sidebar setting (`30s`, `1m`, `5m`, or `10m`), defaulting to **1 minute**.
                """
            )

        with st.expander("5. Data Latency & Source Feeds", expanded=True):
            st.markdown(
                """
                * **Data Feed Origin:** Market prices and volume bars are retrieved via the `yfinance` interface querying public Yahoo Finance endpoints.
                * **Exchange Delay:** Publicly available TSX equity data carries a standard **15 to 20-minute exchange delay** during active market hours.
                * **Calculation Resolution:** Indicator computations (`RSI_14`, `SMA_50`, `SMA_200`) use completed daily session bars. Trend shifts represent daily closing criteria rather than intra-second tick fluctuations.
                """
            )
        with st.expander("6. Canadian Market Alternatives & Differentiation", expanded=False):
            st.markdown(
                """
                | Existing Tool | Coverage | Core Strengths | Limitations Solved by Bay Street Pulse |
                | :--- | :--- | :--- | :--- |
                | **TradingView (TSX)** | Global & TSX | Advanced interactive charting & indicators | Complex interface; lacks automated, opinionated signal alerts without paid tiers. |
                | **Barchart (Canada)** | TSX & TSXV | Pre-computed technical scans | High ad density; scans 1,800+ stocks including illiquid micro-caps. |
                | **TMX / Globe Investor** | TSX | Official exchange data & fundamental metrics | Primarily fundamental-driven; limited technical momentum automation. |
                | **Finviz** | US Only | Gold-standard visual screening & heatmaps | **Does not support Canadian equities (TSX).** |

                **Key Differentiation:**
                * **Curated TSX Universe:** Monitors 59 high-liquidity large-caps and core benchmark ETFs rather than speculative micro-caps.
                * **Rule-Based Classifications:** Translates mathematical indicator pairs directly into prescriptive signals (`BUY / ACCUMULATE`, `SELL / EXIT`).
                * **Automated Alert Pipeline:** Runs twice daily via GitHub Actions to deliver actionable triggers directly to your inbox without requiring daily manual website visits.
                """
            )


    # Footer Disclaimer Note
    st.markdown("---")
    st.caption("ℹ️ *Disclaimer: This platform provides technical momentum metrics for educational tracking only. It is not an advisory service.*")

# -----------------------------------------------------------------------------
# App Execution
# -----------------------------------------------------------------------------
render_live_dashboard()
render_floating_elements()