import os
import re
import time
from datetime import date, datetime, time as dtime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
import plotly.express as px
import streamlit as st

# Import feedback sender from notifier
try:
  from notifierV1 import send_feedback_email
except ImportError:

  def send_feedback_email(
      sender_name: str, sender_email: str, sentiment: str, message: str
  ) -> bool:
    return False


# -----------------------------------------------------------------------------
# Configuration & Timezones
# -----------------------------------------------------------------------------
ET_ZONE = ZoneInfo("America/Toronto")
#CSV_FILE = "screener_results.csv"
LOCAL_CSV_FILE = "screener_results.csv"
DATA_BRANCH_URL = "https://raw.githubusercontent.com/premsy-maker/tsx-stock-screener/data/screener_results.csv"

st.set_page_config(
    page_title="TrendNorth | TSX Momentum Screener",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Core Watchlist Company Names Mapping (for fallback display)
COMPANY_NAMES = {
    "XEQT.TO": "iShares Core Equity ETF Portfolio",
    "XIU.TO": "iShares S&P/TSX 60 Index ETF",
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
    "ENB.TO": "Enbridge Inc.",
    "TRP.TO": "TC Energy Corporation",
    "PPL.TO": "Pembina Pipeline",
    "CNQ.TO": "Canadian Natural Resources",
    "SU.TO": "Suncor Energy",
    "CVE.TO": "Cenovus Energy",
    "IMO.TO": "Imperial Oil",
    "TOU.TO": "Tourmaline Oil",
    "CNR.TO": "Canadian National Railway",
    "CP.TO": "Canadian Pacific Kansas City",
    "WCN.TO": "Waste Connections",
    "WSP.TO": "WSP Global",
    "TRI.TO": "Thomson Reuters",
    "CAE.TO": "CAE Inc.",
    "SHOP.TO": "Shopify Inc.",
    "CSU.TO": "Constellation Software",
    "CLS.TO": "Celestica",
    "GIB-A.TO": "CGI Inc.",
    "OTEX.TO": "OpenText Corporation",
    "ATD.TO": "Alimentation Couche-Tard",
    "DOL.TO": "Dollarama Inc.",
    "L.TO": "Loblaw Companies",
    "MRU.TO": "Metro Inc.",
    "WN.TO": "George Weston",
    "QSR.TO": "Restaurant Brands International",
    "CTC-A.TO": "Canadian Tire Corporation",
    "MG.TO": "Magna International",
    "GIL.TO": "Gildan Activewear",
    "FTS.TO": "Fortis Inc.",
    "H.TO": "Hydro One",
    "EMA.TO": "Emera Incorporated",
    "BIP-UN.TO": "Brookfield Infrastructure Partners",
    "T.TO": "TELUS Corporation",
    "BCE.TO": "BCE Inc.",
    "RCI-B.TO": "Rogers Communications",
    "NTR.TO": "Nutrien Ltd.",
    "ABX.TO": "Barrick Gold",
    "AEM.TO": "Agnico Eagle Mines",
    "FNV.TO": "Franco-Nevada",
    "WPM.TO": "Wheaton Precious Metals",
    "CCO.TO": "Cameco Corporation",
    "TECK-B.TO": "Teck Resources",
    "FM.TO": "First Quantum Minerals",
    "K.TO": "Kinross Gold",
}


# -----------------------------------------------------------------------------
# TSX Market Status & Holiday Calculation Helper
# -----------------------------------------------------------------------------
def get_tsx_market_status(now_et: datetime):
  """Calculates whether the Toronto Stock Exchange is currently OPEN or CLOSED.

  Considers:
  - Weekends (Saturday/Sunday)
  - Canadian statutory and TSX market holidays
  - Standard regular market hours (09:30:00 AM to 04:00:00 PM ET)
  Returns:
      (status_str, color_hex, elapsed_str, remaining_str, holiday_reason)
  """
  today = now_et.date()
  year = today.year

  def get_nth_weekday_of_month(yr, mo, weekday, n):
    first_day = date(yr, mo, 1)
    day_diff = (weekday - first_day.weekday()) % 7
    return first_day + timedelta(days=day_diff + (n - 1) * 7)

  # Good Friday (Anonymous Gregorian algorithm)
  a = year % 19
  b = year // 100
  c = year % 100
  d = b // 4
  e = b % 4
  f = (b + 8) // 25
  g = (b - f + 1) // 3
  h = (19 * a + b - d - g + 15) % 30
  i = c // 4
  k = c % 4
  l = (32 + 2 * e + 2 * i - h - k) % 7
  m = (a + 11 * h + 22 * l) // 451
  easter_month = (h + l - 7 * m + 114) // 31
  easter_day = ((h + l - 7 * m + 114) % 31) + 1
  easter_sunday = date(year, easter_month, easter_day)
  good_friday = easter_sunday - timedelta(days=2)

  # TSX Observed Holidays
  holidays = {
      date(year, 1, 1): "New Year's Day",
      get_nth_weekday_of_month(year, 2, 0, 3): "Family Day",
      good_friday: "Good Friday",
      date(year, 5, 24)
      - timedelta(days=(date(year, 5, 24).weekday())): "Victoria Day",
      date(year, 7, 1): "Canada Day",
      get_nth_weekday_of_month(year, 8, 0, 1): "Civic Holiday",
      get_nth_weekday_of_month(year, 9, 0, 1): "Labour Day",
      date(year, 9, 30): "National Day for Truth and Reconciliation",
      get_nth_weekday_of_month(year, 10, 0, 2): "Thanksgiving",
      date(year, 12, 25): "Christmas Day",
      date(year, 12, 26): "Boxing Day",
  }

  observed_holidays = {}
  for hol_date, name in holidays.items():
    if hol_date.weekday() == 5:  # Saturday -> Friday or Monday
      observed_holidays[hol_date + timedelta(days=2)] = f"{name} (Observed)"
    elif hol_date.weekday() == 6:  # Sunday -> Monday
      observed_holidays[hol_date + timedelta(days=1)] = f"{name} (Observed)"
    else:
      observed_holidays[hol_date] = name

  # 1. Weekend check
  if today.weekday() >= 5:
    return ("CLOSED", "#ef4444", "00:00:00", "--:--:--", "Weekend")

  # 2. Holiday check
  if today in observed_holidays:
    return ("CLOSED", "#ef4444", "00:00:00", "--:--:--", observed_holidays[today])

  # 3. Regular trading hours (09:30 AM to 04:00 PM ET)
  market_open = dtime(9, 30, 0)
  market_close = dtime(16, 0, 0)
  current_time = now_et.time()

  if market_open <= current_time < market_close:
    open_dt = datetime.combine(today, market_open, tzinfo=ET_ZONE)
    close_dt = datetime.combine(today, market_close, tzinfo=ET_ZONE)

    elapsed_secs = int((now_et - open_dt).total_seconds())
    rem_secs = int((close_dt - now_et).total_seconds())

    e_hrs, e_mins, e_secs = (
        elapsed_secs // 3600,
        (elapsed_secs % 3600) // 60,
        elapsed_secs % 60,
    )
    r_hrs, r_mins, r_secs = (
        rem_secs // 3600,
        (rem_secs % 3600) // 60,
        rem_secs % 60,
    )

    elapsed_str = f"{e_hrs:02d}:{e_mins:02d}:{e_secs:02d}"
    remaining_str = f"{r_hrs:02d}:{r_mins:02d}:{r_secs:02d}"

    return ("OPEN", "#16a34a", elapsed_str, remaining_str, None)
  else:
    return (
        "CLOSED",
        "#ef4444",
        "00:00:00",
        "--:--:--",
        "Outside Regular Hours",
    )


# # -----------------------------------------------------------------------------
# # Data Loader
# # -----------------------------------------------------------------------------
# @st.cache_data(ttl=60)
# def load_screener_results():
#   if not os.path.exists(CSV_FILE):
#     return pd.DataFrame(), None

#   try:
#     raw_mtime = os.path.getmtime(CSV_FILE)
#     mod_time = datetime.fromtimestamp(raw_mtime, tz=ZoneInfo("UTC")).astimezone(
#         ET_ZONE
#     )
#     df = pd.read_csv(CSV_FILE)

#     # Standardize Symbol / Ticker column
#     if "Symbol" not in df.columns and "Ticker" in df.columns:
#       df.rename(columns={"Ticker": "Symbol"}, inplace=True)

#     if "Company" not in df.columns and "Symbol" in df.columns:
#       df["Company"] = df["Symbol"].map(
#           lambda s: COMPANY_NAMES.get(str(s).strip(), "—")
#       )

#     for col in ["Price", "RSI_14", "SMA_50", "SMA_200"]:
#       if col in df.columns:
#         df[col] = (
#             df[col]
#             .astype(str)
#             .str.replace("$", "", regex=False)
#             .str.replace(",", "", regex=False)
#             .str.strip()
#         )
#         df[col] = pd.to_numeric(df[col], errors="coerce")

#     return df, mod_time
#   except Exception as e:
#     st.error(f"Error loading screener data: {e}")
#     return pd.DataFrame(), None
# -----------------------------------------------------------------------------
# Data Loader (TN-008: Decoupled Data Branch with Local Fallback)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=120)
def load_screener_results():
  """Loads screener results directly from the GitHub 'data' branch with local fallback."""
  df = None
  mod_time = None

  # 1. Try pulling fresh data from remote 'data' branch URL
  try:
    df = pd.read_csv(DATA_BRANCH_URL)
    mod_time = datetime.now(ET_ZONE)
  except Exception:
    pass

  # 2. Fallback to local CSV if offline or if remote data branch is not reachable
  if df is None and os.path.exists(LOCAL_CSV_FILE):
    try:
      raw_mtime = os.path.getmtime(LOCAL_CSV_FILE)
      mod_time = datetime.fromtimestamp(
          raw_mtime, tz=ZoneInfo("UTC")
      ).astimezone(ET_ZONE)
      df = pd.read_csv(LOCAL_CSV_FILE)
    except Exception:
      pass

  if df is None:
    return pd.DataFrame(), None

  try:
    # Standardize Symbol / Ticker column
    if "Symbol" not in df.columns and "Ticker" in df.columns:
      df.rename(columns={"Ticker": "Symbol"}, inplace=True)

    if "Company" not in df.columns and "Symbol" in df.columns:
      df["Company"] = df["Symbol"].map(
          lambda s: COMPANY_NAMES.get(str(s).strip(), "—")
      )

    for col in ["Price", "RSI_14", "SMA_50", "SMA_200"]:
      if col in df.columns:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace("$", "", regex=False)
            .str.replace(",", "", regex=False)
            .str.strip()
        )
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df, mod_time
  except Exception as e:
    st.error(f"Error processing screener data: {e}")
    return pd.DataFrame(), None

# -----------------------------------------------------------------------------
# Sidebar: Filters & Configuration
# -----------------------------------------------------------------------------
st.sidebar.markdown(
    """<div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
<h2 style="margin: 0; padding: 0; font-size: 1.5rem;">TrendNorth</h2>
<img src="https://flagcdn.com/w40/ca.png" width="24" height="12" style="border-radius: 2px;">
</div>""",
    unsafe_allow_html=True,
)

if st.sidebar.button(
    "🔄 Refresh Data Now", help="Clear memory cache and reload CSV"
):
  st.cache_data.clear()
  st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Screener Filters")

selected_signals = st.sidebar.multiselect(
    "Signal Classification",
    options=["BUY / ACCUMULATE", "SELL / EXIT", "TRIM / TAKE PROFIT", "KEEP / HOLD"],
    default=["BUY / ACCUMULATE", "SELL / EXIT", "TRIM / TAKE PROFIT"],
)

rsi_min, rsi_max = st.sidebar.slider(
    "14-Day RSI Window",
    min_value=0.0,
    max_value=100.0,
    value=(0.0, 100.0),
    step=1.0,
)

trend_filter = st.sidebar.radio(
    "SMA Trend Configuration",
    options=[
        "All Trends",
        "Bullish (SMA 50 > SMA 200)",
        "Bearish / Death Cross (SMA 50 < SMA 200)",
    ],
    index=0,
)

search_term = (
    st.sidebar.text_input("Find Symbol or Company", "").strip().upper()
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "**Disclaimer:** For educational & informational analysis only. Not"
    " financial advice."
)


# -----------------------------------------------------------------------------
# Main Application Layout
# -----------------------------------------------------------------------------
def render_dashboard():
  df_raw, scan_time = load_screener_results()

  # if df_raw is None or df_raw.empty:
  #   st.warning(
  #       f"Waiting for `{CSV_FILE}`... Run `python ScreenStocksV1.py` to"
  #       " generate initial scan results."
  #   )
  #   return
  if df_raw is None or df_raw.empty:
    st.warning(
        "Waiting for scan data... Run `python ScreenStocksV1.py` locally or"
        " trigger the GitHub Actions workflow."
    )
    return

  df = df_raw.copy()

  # Main Header with Canadian Flag (flush left to prevent code block escaping)
  header_html = """<div style="display: flex; align-items: center; gap: 14px; margin-bottom: 2px;">
<h1 style="margin: 0; padding: 0; font-size: 2.25rem; font-weight: 700;">📈 TrendNorth</h1>
<img src="https://flagcdn.com/w40/ca.png" 
     srcset="https://flagcdn.com/w80/ca.png 2x" 
     width="34" 
     height="17" 
     alt="Canada" 
     style="border-radius: 3px; box-shadow: 0 1px 4px rgba(0,0,0,0.25); display: inline-block;">
</div>"""
  st.markdown(header_html, unsafe_allow_html=True)

  # Timestamps
  now_et = datetime.now(ET_ZONE)
  today_display = now_et.strftime("%A, %B %d, %Y")
  last_refreshed_time = now_et.strftime("%I:%M:%S %p ET")
  scan_timestamp_str = (
      scan_time.strftime("%b %d, %Y — %I:%M %p ET")
      if scan_time
      else "Awaiting scan"
  )

  # Calculate Market Status and Elapsed/Remaining Trading Counters
  (
      tsx_status,
      status_color,
      session_counter,
      remaining_counter,
      holiday_reason,
  ) = get_tsx_market_status(now_et)
  reason_badge = (
      f"&nbsp;<span style='font-size: 11px; color: #94a3b8; font-weight:"
      f" 400;'>({holiday_reason})</span>"
      if holiday_reason
      else ""
  )

  # Status Banner HTML (strictly flush left to eliminate markdown code indentation issues)
  status_banner_html = f"""<div style="margin-bottom: 16px;">
<div style="color: #64748b; font-size: 13px; margin-top: -6px; margin-bottom: 8px;">
<b>Date:</b> {today_display} &nbsp;|&nbsp; <b>Last Refreshed:</b> {last_refreshed_time} &nbsp;|&nbsp; <b>Engine Scan Data:</b> {scan_timestamp_str}
</div>
<div style="display: inline-flex; align-items: center; gap: 14px; background-color: #f8fafc; border: 1px solid #e2e8f0; padding: 5px 14px; border-radius: 6px; box-shadow: 0 1px 2px rgba(0,0,0,0.02);">
<div style="display: flex; align-items: center; gap: 6px;">
<span style="height: 10px; width: 10px; background-color: {status_color}; border-radius: 50%; display: inline-block;"></span>
<span style="font-weight: 700; font-size: 13px; color: #1e293b;">TSX Status:</span>
<span style="font-weight: 800; font-size: 13px; color: {status_color};">{tsx_status}</span>
{reason_badge}
</div>
<div style="color: #cbd5e1; font-weight: 300;">|</div>
<div style="display: flex; align-items: center; gap: 6px;">
<span style="font-size: 12px; color: #64748b; font-weight: 600;">Counter (Elapsed):</span>
<span style="font-family: 'Courier New', Courier, monospace; font-size: 13px; font-weight: 700; color: #0f172a; background-color: #ffffff; padding: 1px 6px; border-radius: 4px; border: 1px solid #e2e8f0;">{session_counter}</span>
</div>
<div style="color: #cbd5e1; font-weight: 300;">|</div>
<div style="display: flex; align-items: center; gap: 6px;">
<span style="font-size: 12px; color: #64748b; font-weight: 600;">Time to Close:</span>
<span style="font-family: 'Courier New', Courier, monospace; font-size: 13px; font-weight: 700; color: #0f172a; background-color: #ffffff; padding: 1px 6px; border-radius: 4px; border: 1px solid #e2e8f0;">{remaining_counter}</span>
</div>
</div>
</div>"""
  st.markdown(status_banner_html, unsafe_allow_html=True)

  # Filter Data
  filtered_df = df[df["Signal"].isin(selected_signals)]
  filtered_df = filtered_df[filtered_df["RSI_14"].between(rsi_min, rsi_max)]

  if trend_filter == "Bullish (SMA 50 > SMA 200)":
    filtered_df = filtered_df[filtered_df["SMA_50"] > filtered_df["SMA_200"]]
  elif trend_filter == "Bearish / Death Cross (SMA 50 < SMA 200)":
    filtered_df = filtered_df[filtered_df["SMA_50"] < filtered_df["SMA_200"]]

  if search_term:
    sym_match = filtered_df["Symbol"].str.contains(search_term, na=False)
    comp_match = filtered_df["Company"].str.upper().str.contains(search_term)
    filtered_df = filtered_df[sym_match | comp_match]

  # KPI Summary Metrics Row
  col1, col2, col3, col4 = st.columns(4)
  buy_count = len(df[df["Signal"] == "BUY / ACCUMULATE"])
  sell_count = len(df[df["Signal"] == "SELL / EXIT"])
  trim_count = len(df[df["Signal"] == "TRIM / TAKE PROFIT"])

  col1.metric("Watchlist Displayed", f"{len(filtered_df)} / {len(df)}")
  col2.metric("🟢 Buy / Accumulate", buy_count)
  col3.metric("🔴 Sell / Exit", sell_count)
  col4.metric("🟡 Trim / Profit", trim_count)

  # Main Content Tabs
  tab_data, tab_charts, tab_manual = st.tabs(
      ["📋 Filtered Watchlist", "📊 Market Technicals", "📖 User Manual"]
  )

  with tab_data:
    if filtered_df.empty:
      st.info(
          "No assets match your current filters. Adjust your filters in the"
          " sidebar to expand results."
      )
    else:

      def signal_styler(val):
        if "BUY" in str(val):
          return (
              "color: #1b5e20; background-color: #e8f5e9; font-weight: bold;"
          )
        elif "SELL" in str(val):
          return (
              "color: #b71c1c; background-color: #ffebee; font-weight: bold;"
          )
        elif "TRIM" in str(val):
          return (
              "color: #b45309; background-color: #fef3c7; font-weight: bold;"
          )
        return "color: #475569;"

      columns_order = [
          "Symbol",
          "Company",
          "Price",
          "Signal",
          "RSI_14",
          "SMA_50",
          "SMA_200",
          "Rationale",
      ]
      display_cols = [c for c in columns_order if c in filtered_df.columns]

      styled_df = (
          filtered_df[display_cols]
          .style.format({
              "Price": "${:.2f}",
              "SMA_50": "${:.2f}",
              "SMA_200": "${:.2f}",
              "RSI_14": "{:.1f}",
          })
          .map(signal_styler, subset=["Signal"])
      )

      st.dataframe(styled_df, use_container_width=True, hide_index=False)

      st.download_button(
          label="📥 Export Filtered Results (CSV)",
          data=filtered_df.to_csv(index=False).encode("utf-8"),
          file_name="trendnorth_filtered.csv",
          mime="text/csv",
      )

  with tab_charts:
    if not filtered_df.empty:
      chart_col1, chart_col2 = st.columns(2)

      with chart_col1:
        st.subheader("RSI Momentum Distribution")
        fig_rsi = px.histogram(
            filtered_df,
            x="RSI_14",
            nbins=18,
            color="Signal",
            color_discrete_map={
                "BUY / ACCUMULATE": "#16a34a",
                "SELL / EXIT": "#ef4444",
                "TRIM / TAKE PROFIT": "#f59e0b",
                "KEEP / HOLD": "#64748b",
            },
            template="plotly_white",
        )
        fig_rsi.add_vline(
            x=40,
            line_dash="dot",
            line_color="green",
            annotation_text="Pullback (<=40)",
        )
        fig_rsi.add_vline(
            x=75,
            line_dash="dot",
            line_color="red",
            annotation_text="Overbought (>=75)",
        )
        fig_rsi.update_layout(
            xaxis_title="14-Day RSI", yaxis_title="Equities Count", height=430
        )
        st.plotly_chart(fig_rsi, use_container_width=True)

      with chart_col2:
        st.subheader("Price vs. 50-Day Moving Average")
        hover_data = (
            {"Company": True, "RSI_14": True}
            if "Company" in filtered_df.columns
            else {"RSI_14": True}
        )
        fig_spread = px.scatter(
            filtered_df,
            x="SMA_50",
            y="Price",
            hover_name="Symbol",
            hover_data=hover_data,
            color="Signal",
            color_discrete_map={
                "BUY / ACCUMULATE": "#16a34a",
                "SELL / EXIT": "#ef4444",
                "TRIM / TAKE PROFIT": "#f59e0b",
                "KEEP / HOLD": "#64748b",
            },
            template="plotly_white",
        )
        fig_spread.update_layout(
            xaxis_title="50-Day SMA (CAD)",
            yaxis_title="Current Price (CAD)",
            height=430,
        )
        st.plotly_chart(fig_spread, use_container_width=True)

  with tab_manual:
    st.markdown("""
        ### 📖 TrendNorth Operational Manual & Documentation
        
        #### 1. Introduction
        TrendNorth is an automated quantitative screening dashboard tracking large-cap Canadian equities and core ETFs listed on the Toronto Stock Exchange (TSX). It computes institutional-grade momentum and moving average indicators to systematically highlight actionable swing trading opportunities.
        
        #### 2. What Business Problem Does TrendNorth Solve?
        Individual Canadian retail investors often suffer from **market noise, emotional bias, and screen fatigue**. 
        * Most mainstream screeners are heavily US-centric and flood users with thousands of speculative penny stocks.
        * TrendNorth isolates **59 highly liquid TSX sector leaders and core index ETFs**, applying deterministic technical rules to clearly distinguish between pullbacks worth accumulating versus structural breakdowns worth exiting.
        
        #### 3. Technical Indicator Definitions
        * **14-Day RSI (Relative Strength Index):** Momentum oscillator bounded between 0 and 100.
            * $\mathbf{\le 40}$ **(Oversold / Dip):** Highlights a pullback during a strong broader trend.
            * $\mathbf{\ge 75}$ **(Overbought):** Indicates overextended short-term momentum where trimming profits is prudent.
        * **50-Day SMA (Simple Moving Average):** Medium-term baseline trend (~10 weeks of trading).
        * **200-Day SMA:** Long-term institutional dividing line between secular bull and bear markets (~40 weeks).
        * **Signal Rationales:**
            * **BUY / ACCUMULATE:** Bullish trend ($\text{SMA}_{50} > \text{SMA}_{200}$) accompanied by a temporary pullback ($\text{RSI}_{14} \le 40$).
            * **SELL / EXIT:** Structural breakdown ($\text{SMA}_{50} < \text{SMA}_{200}$) known as a Death Cross.
            * **TRIM / TAKE PROFIT:** Extreme overextended momentum ($\text{RSI}_{14} \ge 75$).
            * **KEEP / HOLD:** Asset is healthy and trading within normal baseline volatility.
            
        #### 4. Refresh Frequency & Pipeline Schedule
        * Scans run twice daily via headless serverless runners:
            * **Morning Market Open Scan:** 10:32 AM EDT (post-opening volatility resolution).
            * **After Market Close Scan:** 04:47 PM EDT (captures confirmed daily closing candles).
            
        #### 5. Data Latency & Source
        * Market pricing data is sourced via Yahoo Finance with standard ~15-minute exchange latency. TrendNorth is engineered for daily swing and positional trend monitoring, not high-frequency intraday scalping.
        """)


render_dashboard()

# -----------------------------------------------------------------------------
# Floating User Feedback Popover (Spam-Protected)
# -----------------------------------------------------------------------------
st.markdown("---")
with st.popover("💬 Submit Feedback"):
  st.markdown("#### Send Us Feedback")
  st.caption("Help improve TrendNorth with bug reports or feature suggestions.")

  if st.session_state.get("feedback_sent_success", False):
    st.success("✅ Thank you! Your feedback has already been received.")
  else:
    fb_name = st.text_input("Your Name", max_chars=50, placeholder="e.g. Alex")
    fb_email = st.text_input(
        "Your Email", max_chars=80, placeholder="name@domain.com"
    )
    fb_sentiment = st.selectbox(
        "Topic",
        [
            "Feature Suggestion",
            "Bug Report",
            "Data Inaccuracy",
            "General Feedback",
        ],
    )
    fb_message = st.text_area(
        "Your Comments",
        max_chars=600,
        placeholder="Describe your suggestion or issue...",
    )

    # Honeypot field (hidden from view)
    hp_bot = st.text_input(
        "Leave empty", label_visibility="collapsed", key="honeypot_trap"
    )

    def is_valid_email(addr: str) -> bool:
      return bool(
          re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", addr.strip())
      )

    if st.button("Submit Feedback", type="primary", use_container_width=True):
      if hp_bot.strip():
        st.success("Thank you! Your feedback has been received.")
        st.stop()

      if not fb_name.strip():
        st.error("Please enter your name.")
      elif not is_valid_email(fb_email):
        st.error("Please enter a valid email address.")
      elif len(fb_message.strip().split()) < 3:
        st.error("Please enter at least 3 words describing your feedback.")
      elif any(
          link in fb_message.lower() for link in ["http://", "https://", "www."]
      ):
        st.error("Links and URLs are not permitted in feedback.")
      else:
        last_time = st.session_state.get("last_fb_time", 0)
        if time.time() - last_time < 60:
          st.warning("Please wait a moment before submitting again.")
        else:
          with st.spinner("Sending feedback..."):
            success = send_feedback_email(
                sender_name=fb_name.strip(),
                sender_email=fb_email.strip(),
                sentiment=fb_sentiment,
                message=fb_message.strip(),
            )
            if success:
              st.session_state.feedback_sent_success = True
              st.session_state.last_fb_time = time.time()
              st.success(
                  "Thank you! Your feedback has been sent directly to the team."
              )
              st.rerun()
            else:
              st.error(
                  "Could not send feedback at this time. Please try again"
                  " later."
              )