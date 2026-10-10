import os
import re
from datetime import datetime
import pandas as pd
import plotly.express as px
import streamlit as st

# Import feedback mailer helper
from notifierV1 import send_feedback_email

# ---------------------------------------------------------
# Page Configuration & Brand Setup
# ---------------------------------------------------------
st.set_page_config(
    page_title="TrendNorth | TSX Momentum Screener",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling (Dark theme adjustments, badge, & popover placement)
st.markdown(
    """
    <style>
    /* Fixed bottom-right version badge */
    .version-badge {
        position: fixed;
        bottom: 12px;
        right: 12px;
        background-color: rgba(30, 41, 59, 0.85);
        color: #94a3b8;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 11px;
        font-family: monospace;
        border: 1px solid #334155;
        z-index: 999;
        pointer-events: none;
    }
    /* Fixed floating feedback button */
    div[data-testid="stPopover"] {
        position: fixed;
        bottom: 38px;
        right: 12px;
        z-index: 1000;
    }
    </style>
    <div class="version-badge">TrendNorth v1.0-beta</div>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# Company Name Lookup Dictionary
# ---------------------------------------------------------
COMPANY_NAMES = {
    # Benchmark ETFs
    "XEQT.TO": "iShares Core Equity ETF Portfolio",
    "XIU.TO": "iShares S&P/TSX 60 Index ETF",
    # Financials
    "RY.TO": "Royal Bank of Canada",
    "TD.TO": "Toronto-Dominion Bank",
    "BMO.TO": "Bank of Montreal",
    "BNS.TO": "Bank of Nova Scotia",
    "CM.TO": "Canadian Imperial Bank of Commerce",
    "NA.TO": "National Bank of Canada",
    "MFC.TO": "Manulife Financial",
    "SLF.TO": "Sun Life Financial",
    "BN.TO": "Brookfield Corporation",
    "BAM.TO": "Brookfield Asset Management",
    "POW.TO": "Power Corporation of Canada",
    "FFH.TO": "Fairfax Financial Holdings",
    "IFC.TO": "Intact Financial",
    # Energy
    "ENB.TO": "Enbridge Inc.",
    "TRP.TO": "TC Energy Corporation",
    "PPL.TO": "Pembina Pipeline",
    "CNQ.TO": "Canadian Natural Resources",
    "SU.TO": "Suncor Energy",
    "CVE.TO": "Cenovus Energy",
    "IMO.TO": "Imperial Oil",
    "TOU.TO": "Tourmaline Oil",
    # Industrials & Rails
    "CNR.TO": "Canadian National Railway",
    "CP.TO": "Canadian Pacific Kansas City",
    "WCN.TO": "Waste Connections",
    "WSP.TO": "WSP Global",
    "TRI.TO": "Thomson Reuters",
    "CAE.TO": "CAE Inc.",
    # Technology
    "SHOP.TO": "Shopify Inc.",
    "CSU.TO": "Constellation Software",
    "CLS.TO": "Celestica Inc.",
    "GIB-A.TO": "CGI Inc.",
    "OTEX.TO": "OpenText Corporation",
    # Consumer
    "ATD.TO": "Alimentation Couche-Tard",
    "DOL.TO": "Dollarama Inc.",
    "L.TO": "Loblaw Companies",
    "MRU.TO": "Metro Inc.",
    "WN.TO": "George Weston Ltd.",
    "QSR.TO": "Restaurant Brands International",
    "CTC-A.TO": "Canadian Tire Corporation",
    "MG.TO": "Magna International",
    "GIL.TO": "Gildan Activewear",
    # Utilities & Infrastructure
    "FTS.TO": "Fortis Inc.",
    "H.TO": "Hydro One",
    "EMA.TO": "Emera Inc.",
    "BIP-UN.TO": "Brookfield Infrastructure Partners",
    # Telecommunications
    "T.TO": "Telus Corporation",
    "BCE.TO": "BCE Inc.",
    "RCI-B.TO": "Rogers Communications",
    # Materials & Mining
    "NTR.TO": "Nutrien Ltd.",
    "ABX.TO": "Barrick Gold Corporation",
    "AEM.TO": "Agnico Eagle Mines",
    "FNV.TO": "Franco-Nevada Corporation",
    "WPM.TO": "Wheaton Precious Metals",
    "CCO.TO": "Cameco Corporation",
    "TECK-B.TO": "Teck Resources",
    "FM.TO": "First Quantum Minerals",
    "K.TO": "Kinross Gold Corporation",
}


# ---------------------------------------------------------
# Data Loader
# ---------------------------------------------------------
@st.cache_data(ttl=60)
def load_screener_results():
    csv_file = "screener_results.csv"
    if not os.path.exists(csv_file):
        return pd.DataFrame(), None

    try:
        mod_time = datetime.fromtimestamp(os.path.getmtime(csv_file))
        df = pd.read_csv(csv_file)

        # Map company names if not present
        if "Company" not in df.columns and "Ticker" in df.columns:
            df["Company"] = df["Ticker"].map(
                lambda t: COMPANY_NAMES.get(str(t).strip(), "—")
            )

        # Standardize numeric columns
        for col in ["Price", "RSI_14", "SMA_50", "SMA_200"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        return df, mod_time
    except Exception as e:
        st.error(f"Error loading screener data: {e}")
        return pd.DataFrame(), None


df_raw, scan_time = load_screener_results()

# ---------------------------------------------------------
# Sidebar Configuration & Filters
# ---------------------------------------------------------
st.sidebar.title("TrendNorth")
st.sidebar.caption("TSX Momentum & Trend Screener (v1.0-beta)")

refresh_interval = st.sidebar.selectbox(
    "⏱ Auto-Refresh Interval",
    options=["1m", "5m", "15m", "Manual Only"],
    index=1,
)

if st.sidebar.button("🔄 Refresh Data Now"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("Filter Watchlist")

# 1. Signal Selection
all_signals = ["BUY / ACCUMULATE", "SELL / EXIT", "TRIM / TAKE PROFIT", "KEEP / HOLD"]
selected_signals = st.sidebar.multiselect(
    "Signal Classification",
    options=all_signals,
    default=["BUY / ACCUMULATE", "SELL / EXIT", "TRIM / TAKE PROFIT"],
)

# 2. RSI Window
rsi_min, rsi_max = st.sidebar.slider(
    "14-Day RSI Window",
    min_value=0.0,
    max_value=100.0,
    value=(0.0, 100.0),
    step=1.0,
)

# 3. SMA Trend Regime
sma_trend_filter = st.sidebar.radio(
    "SMA Trend Configuration",
    options=[
        "All Trends",
        "Bullish (SMA 50 > SMA 200)",
        "Bearish / Death Cross (SMA 50 < SMA 200)",
    ],
    index=0,
)

# 4. Search Filter
search_query = st.sidebar.text_input(
    "Find Symbol or Company", placeholder="e.g. RY, Shopify, Enbridge"
).strip()

st.sidebar.markdown("---")
st.sidebar.markdown(
    """
<div style="font-size: 11px; color: #888; line-height: 1.4;">
<b>⚠️ Educational Disclaimer:</b><br>
TrendNorth provides rule-based quantitative indicators for educational and informational tracking only. It does not constitute financial, investment, legal, or tax advice. Always conduct independent research before making trading decisions.
</div>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# Filter Application
# ---------------------------------------------------------
filtered_df = df_raw.copy()

if not filtered_df.empty:
    if selected_signals:
        filtered_df = filtered_df[filtered_df["Signal"].isin(selected_signals)]

    if "RSI_14" in filtered_df.columns:
        filtered_df = filtered_df[
            (filtered_df["RSI_14"] >= rsi_min)
            & (filtered_df["RSI_14"] <= rsi_max)
        ]

    if (
        sma_trend_filter == "Bullish (SMA 50 > SMA 200)"
        and "SMA_50" in filtered_df.columns
    ):
        filtered_df = filtered_df[filtered_df["SMA_50"] > filtered_df["SMA_200"]]
    elif (
        sma_trend_filter == "Bearish / Death Cross (SMA 50 < SMA 200)"
        and "SMA_50" in filtered_df.columns
    ):
        filtered_df = filtered_df[filtered_df["SMA_50"] < filtered_df["SMA_200"]]

    if search_query:
        query = search_query.lower()
        filtered_df = filtered_df[
            filtered_df["Ticker"].astype(str).str.lower().str.contains(query)
            | filtered_df["Company"]
            .astype(str)
            .str.lower()
            .str.contains(query)
        ]

# ---------------------------------------------------------
# Main UI Layout
# ---------------------------------------------------------
st.title("📈 TrendNorth")

today_display = datetime.now().strftime("%A, %B %d, %Y")
last_refreshed_time = datetime.now().strftime("%I:%M:%S %p")
scan_timestamp_str = (
    scan_time.strftime("%b %d, %Y — %I:%M %p") if scan_time else "Awaiting scan"
)

st.markdown(
    f"""
    <div style="color: #64748b; font-size: 13px; margin-top: -12px; margin-bottom: 20px;">
        <b>Date:</b> {today_display} &nbsp;|&nbsp; 
        <b>Last Refreshed:</b> {last_refreshed_time} &nbsp;|&nbsp; 
        <b>Engine Scan Data:</b> {scan_timestamp_str}
    </div>
    """,
    unsafe_allow_html=True,
)

# KPI Metric Cards
total_tracked = len(df_raw) if not df_raw.empty else 0
displayed_count = len(filtered_df)

col_m1, col_m2, col_m3, col_m4 = st.columns(4)

with col_m1:
    st.metric("Watchlist Displayed", f"{displayed_count} / {total_tracked}")

with col_m2:
    buy_count = (
        len(df_raw[df_raw["Signal"] == "BUY / ACCUMULATE"])
        if not df_raw.empty
        else 0
    )
    st.metric("🟢 Buy / Accumulate", buy_count)

with col_m3:
    sell_count = (
        len(df_raw[df_raw["Signal"] == "SELL / EXIT"])
        if not df_raw.empty
        else 0
    )
    st.metric("🔴 Sell / Exit", sell_count)

with col_m4:
    trim_count = (
        len(df_raw[df_raw["Signal"] == "TRIM / TAKE PROFIT"])
        if not df_raw.empty
        else 0
    )
    st.metric("🟡 Trim / Profit", trim_count)

# Navigation Tabs
tab_table, tab_charts, tab_manual = st.tabs(
    ["📋 Filtered Watchlist", "📊 Market Technicals", "📖 User Manual"]
)

# ---------------------------------------------------------
# Tab 1: Filtered Watchlist Table
# ---------------------------------------------------------
with tab_table:
    if filtered_df.empty:
        st.warning("No TSX assets match the current filter selection.")
    else:
        # Reorder columns for display
        cols = [c for c in ["Ticker", "Company", "Price", "Signal", "RSI_14", "SMA_50", "SMA_200", "Rationale"] if c in filtered_df.columns]
        display_table = filtered_df[cols].copy()

        # Format numeric presentation
        st.dataframe(
            display_table.style.format({
                "Price": "${:.2f}",
                "SMA_50": "${:.2f}",
                "SMA_200": "${:.2f}",
                "RSI_14": "{:.1f}",
            }),
            use_container_width=True,
            height=500,
        )

        csv_download = display_table.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Export Filtered Watchlist (CSV)",
            data=csv_download,
            file_name=f"trendnorth_watchlist_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

# ---------------------------------------------------------
# Tab 2: Market Technicals Charts
# ---------------------------------------------------------
with tab_charts:
    if df_raw.empty:
        st.info("Market data will populate once the first screener scan completes.")
    else:
        c_left, c_right = st.columns(2)

        with c_left:
            st.subheader("RSI Momentum Distribution")
            fig_rsi = px.histogram(
                df_raw,
                x="RSI_14",
                color="Signal",
                nbins=20,
                color_discrete_map={
                    "BUY / ACCUMULATE": "#10b981",
                    "SELL / EXIT": "#ef4444",
                    "TRIM / TAKE PROFIT": "#f59e0b",
                    "KEEP / HOLD": "#64748b",
                },
                labels={"RSI_14": "14-Day RSI", "count": "Stock Count"},
            )
            # Reference benchmark lines
            fig_rsi.add_vline(
                x=40,
                line_dash="dash",
                line_color="#10b981",
                annotation_text="Pullback Dip (40)",
                annotation_position="top left",
            )
            fig_rsi.add_vline(
                x=75,
                line_dash="dash",
                line_color="#ef4444",
                annotation_text="Overextended (75)",
                annotation_position="top right",
            )
            fig_rsi.update_layout(
                template="plotly_dark",
                margin=dict(l=20, r=20, t=30, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig_rsi, use_container_width=True)

        with c_right:
            st.subheader("Price vs. 50-Day Moving Average")
            fig_scatter = px.scatter(
                df_raw,
                x="SMA_50",
                y="Price",
                color="Signal",
                hover_name="Ticker",
                hover_data=["Company", "RSI_14"],
                color_discrete_map={
                    "BUY / ACCUMULATE": "#10b981",
                    "SELL / EXIT": "#ef4444",
                    "TRIM / TAKE PROFIT": "#f59e0b",
                    "KEEP / HOLD": "#64748b",
                },
                labels={"SMA_50": "50-Day SMA (CAD)", "Price": "Price (CAD)"},
            )
            fig_scatter.update_layout(
                template="plotly_dark",
                margin=dict(l=20, r=20, t=30, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

# ---------------------------------------------------------
# Tab 3: User Manual & Documentation
# ---------------------------------------------------------
with tab_manual:
    st.markdown("### 📖 TrendNorth Operational & Technical Manual")

    with st.expander("1. Introduction to TrendNorth", expanded=True):
        st.markdown(
            """
            **TrendNorth** is an automated quantitative screening engine and momentum dashboard designed specifically for high-liquidity assets listed on the **Toronto Stock Exchange (TSX)**.
            
            By computing multi-timeframe moving averages and momentum oscillators over daily closing bars, TrendNorth replaces manual chart scanning with deterministic, rule-based alerts.
            """
        )

    with st.expander("2. Business Problem & Solution Scope", expanded=False):
        st.markdown(
            """
            * **Manual Fatigue:** Analyzing 59 charts daily causes cognitive fatigue and missed entries. TrendNorth aggregates the entire TSX liquid core in seconds.
            * **Emotional Bias:** Subjective trading leads to buying overextended tops or catching falling knives. TrendNorth enforces deterministic criteria.
            * **Actionable Timeliness:** Automated GitHub Actions cron pipelines dispatch notifications directly when opportunities strike.
            """
        )

    with st.expander("3. Indicator Definitions & Signal Logic", expanded=False):
        st.markdown(
            """
            | Signal | Rationale | Criteria | Interpretation |
            | :--- | :--- | :--- | :--- |
            | **BUY / ACCUMULATE** | Bullish trend + Pullback dip | `SMA_50 > SMA_200` & `RSI_14 <= 40` | Structural Golden trend intact; temporary short-term dip into value. |
            | **SELL / EXIT** | Death Cross (Bearish) | `SMA_50 < SMA_200` | Intermediate trend broken beneath long-term baseline. Risk mitigation zone. |
            | **TRIM / TAKE PROFIT** | Overextended momentum | `RSI_14 >= 75` | Excessive buyer momentum; heightened mean-reversion risk. |
            | **KEEP / HOLD** | Trading within baseline | Standard historical range | Asset operates within baseline volatility. No action required. |
            """
        )

    with st.expander("4. Pipeline Schedule & Refresh Frequency", expanded=False):
        st.markdown(
            """
            * **Engine Execution:** Screened twice daily via GitHub Actions (`daily_screener.yml`):
                * Pre-market sanity check (~8:30 AM EST)
                * Post-close settlement bar (~4:30 PM EST)
            * **Dashboard Cache:** Automatically pulls newly committed scan data every 60 seconds.
            """
        )

    with st.expander("5. Data Latency & Exchange Disclaimers", expanded=False):
        st.markdown(
            """
            * Market quotes are gathered via `yfinance` daily bars and subject to standard exchange delays (15–20 minutes).
            * Calculations reflect end-of-day daily session closes rather than tick-level intra-second pricing.
            """
        )

    with st.expander("6. Canadian Market Alternatives & Differentiation", expanded=False):
        st.markdown(
            """
            | Existing Platform | TSX Coverage | Core Strengths | Limitations Solved by TrendNorth |
            | :--- | :--- | :--- | :--- |
            | **TradingView (TSX)** | Global & TSX | Advanced chart drawing tools | High UI complexity; alerts require paid subscription tiers. |
            | **Barchart (Canada)** | TSX & TSXV | Pre-computed technical tables | Heavy ad density; scans thousands of illiquid micro-caps. |
            | **TMX / Globe Investor** | TSX Core | Fundamental ratios & company news | Primarily fundamental; lacks automated technical momentum alerts. |
            | **Finviz** | US Only | Leading visual heatmaps & screener | **Does not support Canadian equities (TSX).** |

            **TrendNorth Core Advantages:**
            1. **Curated TSX Focus:** Zero micro-cap noise—tracks only liquid blue-chips and core index ETFs (`XEQT`, `XIU`).
            2. **Opinionated Signals:** Translates raw metrics into deterministic actions (`BUY`, `SELL`, `TRIM`).
            3. **Decoupled Delivery:** Delivers alerts directly to your inbox so you don't have to keep the dashboard open all day.
            """
        )

# ---------------------------------------------------------
# Floating User Feedback Popover
# ---------------------------------------------------------
with st.popover("💬 Submit Feedback"):
    st.markdown("#### Send Us Feedback")
    st.caption("Help improve TrendNorth with bug reports or feature requests.")

    fb_name = st.text_input("Your Name", placeholder="e.g. Premsy")
    fb_email = st.text_input("Your Email", placeholder="name@domain.com")
    fb_sentiment = st.selectbox("Topic", ["Feature Suggestion", "Bug Report", "Data Inaccuracy", "General Feedback"])
    fb_message = st.text_area("Your Comments", placeholder="Describe your experience or suggestion...")

    def is_valid_email(addr: str) -> bool:
        return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", addr.strip()))

    if st.button("Submit Feedback", type="primary", use_container_width=True):
        if not fb_name.strip():
            st.error("Please provide your name.")
        elif not is_valid_email(fb_email):
            st.error("Please enter a valid email address.")
        elif len(fb_message.strip().split()) < 3:
            st.error("Please enter a brief sentence describing your feedback.")
        else:
            with st.spinner("Submitting feedback..."):
                success = send_feedback_email(
                    sender_name=fb_name.strip(),
                    sender_email=fb_email.strip(),
                    sentiment=fb_sentiment,
                    message=fb_message.strip(),
                )
                if success:
                    st.success("Thank you! Your feedback has been sent directly to the development team.")
                else:
                    st.error("Could not send feedback at this time. Please check SMTP secrets.")