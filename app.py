import io
import os
import re
import time
import json
from datetime import date, datetime, time as dtime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# Import feedback sender from notifier
try:
    from notifierV1 import send_feedback_email
except ImportError:
    def send_feedback_email(sender_name: str, sender_email: str, sentiment: str, message: str) -> bool:
        return False

# Browser LocalStorage integration for Pocket Trader auto-persistence
try:
    from streamlit_local_storage import LocalStorage
    localS = LocalStorage()
    HAS_LOCAL_STORAGE = True
except ImportError:
    localS = None
    HAS_LOCAL_STORAGE = False

# -----------------------------------------------------------------------------
# Configuration & Timezones
# -----------------------------------------------------------------------------
ET_ZONE = ZoneInfo("America/Toronto")
LOCAL_CSV_FILE = "screener_results.csv"
DATA_BRANCH_URL = "https://raw.githubusercontent.com/premsy-maker/tsx-stock-screener/data/screener_results.csv"

st.set_page_config(
    page_title="TrendNorth | TSX Momentum Screener",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# Theming State & Cohesive CSS Variable Injection (TN-019)
# -----------------------------------------------------------------------------
if "theme_mode" not in st.session_state:
    st.session_state["theme_mode"] = "Dark (Terminal) 🌙"

is_dark = "Dark" in st.session_state["theme_mode"]

# Dynamic Color Tokens
bg_main = "#0b1120" if is_dark else "#f8fafc"
bg_card = "#131d33" if is_dark else "#ffffff"
bg_card_hover = "#1e293b" if is_dark else "#f1f5f9"
bg_sidebar = "#070c18" if is_dark else "#ffffff"
border_color = "#243556" if is_dark else "#e2e8f0"
text_main = "#f8fafc" if is_dark else "#0f172a"
text_muted = "#94a3b8" if is_dark else "#64748b"
plotly_theme = "plotly_dark" if is_dark else "plotly_white"

st.markdown(
    f"""
    <style>
    /* 1. Global CSS Root Token Overrides */
    :root {{
        --background-color: {bg_main} !important;
        --secondary-background-color: {bg_card} !important;
        --text-color: {text_main} !important;
    }}

    /* 2. Top Streamlit Header Toolbar (Eliminates Top White Bar) */
    header[data-testid="stHeader"] {{
        background-color: {bg_main} !important;
        border-bottom: 1px solid {border_color} !important;
    }}
    header[data-testid="stHeader"] * {{
        color: {text_main} !important;
    }}

    /* 3. Full App Background */
    .stApp {{
        background-color: {bg_main} !important;
        color: {text_main} !important;
    }}

    /* 4. Sidebar Cohesion */
    section[data-testid="stSidebar"] {{
        background-color: {bg_sidebar} !important;
        border-right: 1px solid {border_color} !important;
    }}
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3, 
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p {{
        color: {text_main} !important;
    }}
    section[data-testid="stSidebar"] .stCaption {{
        color: {text_muted} !important;
    }}

    /* Fix: Multiselect Tag Contrast in Light and Dark Modes */
    span[data-baseweb="tag"] {{
        background-color: #0284c7 !important;
        color: #ffffff !important;
        border-radius: 4px !important;
    }}
    span[data-baseweb="tag"] * {{
        color: #ffffff !important;
    }}

    .block-container {{
        padding-top: 1.8rem !important;
        padding-bottom: 3rem !important;
    }}

    /* 5. Metrics & Session Clocks (Equalized 1:1:1 Columns with Controlled Typography) */
    div[data-testid="stMetric"] {{
        background-color: {bg_card} !important;
        border: 1px solid {border_color} !important;
        border-radius: 10px !important;
        padding: 10px 14px !important;
        min-height: 84px !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
    }}
    div[data-testid="stMetricLabel"] * {{
        color: {text_muted} !important;
        font-weight: 600 !important;
        font-size: 0.78rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
    }}
    div[data-testid="stMetricValue"] * {{
        color: {text_main} !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
        line-height: 1.3 !important;
    }}

    /* Status Alert Banner Match Card Height */
    div[data-testid="stAlert"] {{
        min-height: 84px !important;
        display: flex !important;
        align-items: center !important;
        border-radius: 10px !important;
        border: 1px solid {border_color} !important;
        margin-bottom: 0 !important;
    }}

    /* 6. Sub-Header Metadata Bar */
    .tn-meta-bar span {{
        background: {bg_card} !important;
        border: 1px solid {border_color} !important;
        padding: 4px 10px;
        border-radius: 6px;
        color: {text_muted} !important;
        font-size: 0.85rem;
    }}

    /* 7. Secondary Buttons (Refresh, KPI Tiles, Clear Filters) */
    button[kind="secondary"] {{
        background-color: {bg_card} !important;
        border: 1px solid {border_color} !important;
        color: {text_main} !important;
        border-radius: 8px !important;
        transition: all 0.15s ease-in-out !important;
    }}
    button[kind="secondary"]:hover {{
        background-color: {bg_card_hover} !important;
        border-color: #3b82f6 !important;
        color: #60a5fa !important;
    }}
    button[kind="secondary"] * {{
        color: inherit !important;
    }}

    /* KPI Tiles Typography & Spacing */
    div.kpi-card-container button {{
        min-height: 84px !important;
        padding: 12px 16px !important;
        text-align: left !important;
        white-space: pre-line !important;
        line-height: 1.4 !important;
        font-size: 1.05rem !important;
        font-weight: 700 !important;
    }}

    /* 8. Text Inputs & Form Fields */
    div[data-baseweb="input"] {{
        background-color: {bg_card} !important;
        border-color: {border_color} !important;
    }}
    div[data-baseweb="input"] input {{
        color: {text_main} !important;
    }}

    /* 9. Expanders Theme Alignment (Fixes White Expanders in Manual) */
    div[data-testid="stExpander"] {{
        background-color: {bg_card} !important;
        border: 1px solid {border_color} !important;
        border-radius: 8px !important;
    }}
    div[data-testid="stExpander"] summary {{
        background-color: {bg_card} !important;
        color: {text_main} !important;
    }}
    div[data-testid="stExpander"] summary * {{
        color: {text_main} !important;
    }}
    div[data-testid="stExpander"] div[role="region"] {{
        background-color: {bg_card} !important;
        color: {text_main} !important;
    }}
    div[data-testid="stExpander"] div[role="region"] * {{
        color: {text_main} !important;
    }}

    /* 10. Floating Feedback Popover */
    div[data-testid="stPopover"] {{
        position: fixed;
        bottom: 24px;
        right: 24px;
        z-index: 999999;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# Core Watchlist Company Names Mapping (59 TSX Equities & ETFs)
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

ALL_SIGNAL_TYPES = ["BUY / ACCUMULATE", "SELL / EXIT", "TRIM / TAKE PROFIT", "KEEP / HOLD"]
DEFAULT_ACTIVE_SIGNALS = ["BUY / ACCUMULATE", "SELL / EXIT", "TRIM / TAKE PROFIT"]

# -----------------------------------------------------------------------------
# Session State Initialization (Pre-Widget Registration)
# -----------------------------------------------------------------------------
if "filter_signals" not in st.session_state:
    st.session_state.filter_signals = DEFAULT_ACTIVE_SIGNALS.copy()
if "filter_rsi" not in st.session_state:
    st.session_state.filter_rsi = (0.0, 100.0)
if "filter_sma" not in st.session_state:
    st.session_state.filter_sma = "All Trends"
if "filter_search" not in st.session_state:
    st.session_state.filter_search = ""

def set_signal_filter(signal_name):
    """Callback to set single signal filter cleanly before widget execution."""
    if signal_name == "ALL":
        st.session_state.filter_signals = ALL_SIGNAL_TYPES.copy()
    else:
        st.session_state.filter_signals = [signal_name]

def reset_all_filters():
    """Callback to restore all filters back to default values."""
    st.session_state.filter_signals = DEFAULT_ACTIVE_SIGNALS.copy()
    st.session_state.filter_rsi = (0.0, 100.0)
    st.session_state.filter_sma = "All Trends"
    st.session_state.filter_search = ""

# -----------------------------------------------------------------------------
# TSX Market Session Hours Helper
# -----------------------------------------------------------------------------
def get_tsx_market_status():
    now_et = datetime.now(ET_ZONE)
    weekday = now_et.weekday()
    today_time = now_et.time()

    open_time = dtime(9, 30)
    close_time = dtime(16, 0)

    tsx_holidays_2026 = {
        date(2026, 1, 1), date(2026, 2, 16), date(2026, 4, 3), date(2026, 5, 18),
        date(2026, 7, 1), date(2026, 8, 3), date(2026, 9, 7), date(2026, 9, 30),
        date(2026, 10, 12), date(2026, 12, 25), date(2026, 12, 28),
    }

    if weekday >= 5 or now_et.date() in tsx_holidays_2026:
        return "CLOSED", "Weekend / TSX Market Holiday", "Closed", "Opens next trading day 9:30 AM ET"

    if today_time < open_time:
        time_until = datetime.combine(now_et.date(), open_time, tzinfo=ET_ZONE) - now_et
        total_seconds = int(time_until.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return "PRE-MARKET", f"Opens in {hours:02d}:{minutes:02d}:{seconds:02d}", "Closed", "00:00:00"

    elif open_time <= today_time < close_time:
        elapsed = now_et - datetime.combine(now_et.date(), open_time, tzinfo=ET_ZONE)
        remain = datetime.combine(now_et.date(), close_time, tzinfo=ET_ZONE) - now_et

        el_sec = int(elapsed.total_seconds())
        el_h, el_rem = divmod(el_sec, 3600)
        el_m, el_s = divmod(el_rem, 60)

        rem_sec = int(remain.total_seconds())
        rem_h, rem_rem = divmod(rem_sec, 3600)
        rem_m, rem_s = divmod(rem_rem, 60)

        return "OPEN", "Regular Trading Session", f"{el_h:02d}:{el_m:02d}:{el_s:02d}", f"{rem_h:02d}:{rem_m:02d}:{rem_s:02d}"

    else:
        return "CLOSED", "Market Closed (Post-Session)", "Session Ended", "Opens 9:30 AM ET next trading day"

# -----------------------------------------------------------------------------
# Resilient Data Loader with Cache-Busting & Diagnostics (TN-008 & TN-001)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=60)
def load_screener_results():
    df = None
    mod_time = None
    fetch_error = None

    bust_url = f"{DATA_BRANCH_URL}?t={int(time.time())}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) TrendNorth/1.0",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

    if "GITHUB_TOKEN" in st.secrets:
        headers["Authorization"] = f"token {st.secrets['GITHUB_TOKEN']}"

    try:
        resp = requests.get(bust_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            df = pd.read_csv(io.StringIO(resp.text))
            mod_time = datetime.now(ET_ZONE)
        else:
            fetch_error = f"HTTP {resp.status_code} - {resp.reason}"
    except Exception as e:
        fetch_error = str(e)

    if df is None and os.path.exists(LOCAL_CSV_FILE):
        try:
            raw_mtime = os.path.getmtime(LOCAL_CSV_FILE)
            mod_time = datetime.fromtimestamp(raw_mtime, tz=ZoneInfo("UTC")).astimezone(ET_ZONE)
            df = pd.read_csv(LOCAL_CSV_FILE)
            if fetch_error:
                st.sidebar.warning(f"⚠️ Remote fetch failed ({fetch_error}). Using local fallback.")
        except Exception:
            pass

    if df is None or df.empty:
        return pd.DataFrame(), None

    try:
        if "Symbol" not in df.columns and "Ticker" in df.columns:
            df.rename(columns={"Ticker": "Symbol"}, inplace=True)

        if "Company" not in df.columns and "Symbol" in df.columns:
            df["Company"] = df["Symbol"].map(lambda s: COMPANY_NAMES.get(str(s).strip(), "—"))

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
# Pocket Trader State Management & Helpers
# -----------------------------------------------------------------------------
if "pocket_positions" not in st.session_state:
    st.session_state.pocket_positions = []

if "last_processed_file_id" not in st.session_state:
    st.session_state.last_processed_file_id = None

def sync_pocket_to_storage():
    if HAS_LOCAL_STORAGE and localS is not None:
        try:
            localS.setItem("trendnorth_pocket_positions", st.session_state.pocket_positions)
        except Exception:
            pass

def hydrate_pocket_from_storage():
    if HAS_LOCAL_STORAGE and localS is not None and not st.session_state.pocket_positions:
        try:
            stored = localS.getItem("trendnorth_pocket_positions")
            if stored and isinstance(stored, list):
                st.session_state.pocket_positions = stored
        except Exception:
            pass

hydrate_pocket_from_storage()

def is_exact_duplicate(existing_list, candidate):
    return any(
        pos["Symbol"] == candidate["Symbol"]
        and str(pos.get("Buy Date")) == str(candidate.get("Buy Date"))
        and abs(float(pos.get("Buy Price", 0)) - float(candidate.get("Buy Price", 0))) < 0.001
        and int(pos.get("Shares", 0)) == int(candidate.get("Shares", 0))
        and abs(float(pos.get("Target Gain", 0)) - float(candidate.get("Target Gain", 0))) < 0.001
        for pos in existing_list
    )

# -----------------------------------------------------------------------------
# Main Application Dashboard
# -----------------------------------------------------------------------------
def render_dashboard():
    df_raw, scan_time = load_screener_results()

    # 1. Sidebar Header, Theme Switcher & Filters
    with st.sidebar:
        st.markdown(
            """
            <div style="display: inline-flex; align-items: center; gap: 6px; margin-bottom: 8px;">
                <h3 style="margin: 0; padding: 0; font-size: 1.45rem; font-weight: 800; line-height: 1;">TrendNorth 🇨🇦</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )

        selected_theme = st.radio(
            "Interface Theme",
            options=["Dark (Terminal) 🌙", "Light (Clean) ☀️"],
            index=0 if is_dark else 1,
            horizontal=True,
            key="theme_radio_selector",
            label_visibility="collapsed",
        )
        if selected_theme != st.session_state["theme_mode"]:
            st.session_state["theme_mode"] = selected_theme
            st.rerun()

        if st.button("🔄 Refresh Data Now", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")
        st.subheader("🔍 Screener Filters")

        if not df_raw.empty and "Signal" in df_raw.columns:
            available_signals = sorted(list(df_raw["Signal"].dropna().unique()))
        else:
            available_signals = ALL_SIGNAL_TYPES

        selected_signals = st.multiselect(
            "Signal Classification",
            options=available_signals,
            key="filter_signals",
        )

        rsi_range = st.slider(
            "14-Day RSI Window",
            min_value=0.0,
            max_value=100.0,
            step=1.0,
            key="filter_rsi",
        )

        sma_trend = st.radio(
            "SMA Trend Configuration",
            options=["All Trends", "Bullish (SMA 50 > SMA 200)", "Bearish / Death Cross (SMA 50 < SMA 200)"],
            key="filter_sma",
        )

        search_query = st.text_input(
            "Find Symbol or Company",
            placeholder="e.g. SHOP, BMO, Enbridge",
            key="filter_search",
        ).strip().upper()

        st.markdown("---")
        st.caption("ℹ️ **Educational / Non-Financial Advice Disclaimer**")
        st.caption("TrendNorth is an algorithmic research platform for TSX securities. All indicators and alerts are mathematical representations for self-directed screening and do not constitute financial advice.")

    # 2. Main Title & Session Clock Header (Equal 1:1:1 Balanced Widths)
    status_state, status_detail, elapsed_time, time_to_close = get_tsx_market_status()
    scan_date_str = scan_time.strftime("%b %d, %Y — %I:%M %p ET") if scan_time else "Data Pending"
    today_et_str = datetime.now(ET_ZONE).strftime("%A, %B %d, %Y")
    now_time_et_str = datetime.now(ET_ZONE).strftime("%I:%M:%S %p ET")

    st.title("📈 TrendNorth 🇨🇦")
    st.markdown(
        f"""
        <div class="tn-meta-bar" style="margin-top: -12px; margin-bottom: 18px; display: flex; flex-wrap: wrap; gap: 8px;">
            <span>📅 <b>Date:</b> {today_et_str}</span>
            <span>⏰ <b>Live Clock:</b> {now_time_et_str}</span>
            <span>⚡ <b>Engine Scan Data:</b> {scan_date_str}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Balanced 1:1:1 Equal Width Columns
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    with col_stat1:
        if status_state == "OPEN":
            st.success(f"🟢 **TSX Status:** {status_state}\n\n{status_detail}")
        elif status_state == "PRE-MARKET":
            st.warning(f"🟡 **TSX Status:** {status_state}\n\n{status_detail}")
        else:
            st.info(f"⚪ **TSX Status:** {status_state}\n\n{status_detail}")
    with col_stat2:
        st.metric(label="Counter (Elapsed)", value=elapsed_time)
    with col_stat3:
        st.metric(label="Time to Close", value=time_to_close)

    if df_raw.empty:
        st.warning("Waiting for scan data... Run the GitHub Actions workflow or execute `python ScreenStocksV1.py` locally.")
        return

    # Counts across whole universe
    buy_all_cnt = len(df_raw[df_raw["Signal"] == "BUY / ACCUMULATE"])
    sell_all_cnt = len(df_raw[df_raw["Signal"] == "SELL / EXIT"])
    trim_all_cnt = len(df_raw[df_raw["Signal"] == "TRIM / TAKE PROFIT"])

    # Watchlist Filtering Calculations
    filtered_df = df_raw.copy()
    if selected_signals:
        filtered_df = filtered_df[filtered_df["Signal"].isin(selected_signals)]

    filtered_df = filtered_df[
        (filtered_df["RSI_14"] >= rsi_range[0]) & (filtered_df["RSI_14"] <= rsi_range[1])
    ]

    if sma_trend == "Bullish (SMA 50 > SMA 200)":
        filtered_df = filtered_df[filtered_df["SMA_50"] > filtered_df["SMA_200"]]
    elif sma_trend == "Bearish / Death Cross (SMA 50 < SMA 200)":
        filtered_df = filtered_df[filtered_df["SMA_50"] < filtered_df["SMA_200"]]

    if search_query:
        filtered_df = filtered_df[
            filtered_df["Symbol"].str.contains(search_query, case=False, na=False)
            | filtered_df["Company"].str.contains(search_query, case=False, na=False)
        ]

    # Check if any filters are active
    has_active_filters = (
        set(selected_signals) != set(available_signals)
        or rsi_range != (0.0, 100.0)
        or sma_trend != "All Trends"
        or bool(search_query)
    )

    # 3. Interactive Embedded Metric Cards
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)

    with m_col1:
        st.markdown('<div class="kpi-card-container">', unsafe_allow_html=True)
        st.button(
            f"WATCHLIST DISPLAYED\n{len(filtered_df)} / {len(df_raw)}",
            on_click=set_signal_filter,
            args=("ALL",),
            use_container_width=True,
            key="kpi_tile_all",
            help="Click to display all stocks in the universe"
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with m_col2:
        st.markdown('<div class="kpi-card-container">', unsafe_allow_html=True)
        st.button(
            f"🟢 BUY / ACCUMULATE\n{buy_all_cnt}",
            on_click=set_signal_filter,
            args=("BUY / ACCUMULATE",),
            use_container_width=True,
            key="kpi_tile_buy",
            help="Click to filter by BUY / ACCUMULATE setups"
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with m_col3:
        st.markdown('<div class="kpi-card-container">', unsafe_allow_html=True)
        st.button(
            f"🔴 SELL / EXIT\n{sell_all_cnt}",
            on_click=set_signal_filter,
            args=("SELL / EXIT",),
            use_container_width=True,
            key="kpi_tile_sell",
            help="Click to filter by SELL / EXIT signals"
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with m_col4:
        st.markdown('<div class="kpi-card-container">', unsafe_allow_html=True)
        st.button(
            f"🟡 TRIM / PROFIT\n{trim_all_cnt}",
            on_click=set_signal_filter,
            args=("TRIM / TAKE PROFIT",),
            use_container_width=True,
            key="kpi_tile_trim",
            help="Click to filter by TRIM / TAKE PROFIT signals"
        )
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)

    # 4. Main Content Tabs
    tab_data, tab_pocket, tab_charts, tab_manual = st.tabs(
        ["📋 Filtered Watchlist", "💼 Pocket Trader", "📊 Market Technicals", "📖 User Manual"]
    )

    # -------------------------------------------------------------------------
    # TAB 1: Filtered Watchlist (Interactive Sortable Native Dataframe)
    # -------------------------------------------------------------------------
    with tab_data:
        col_tab_info, col_clear = st.columns([7.5, 2.5])
        with col_clear:
            if has_active_filters:
                st.button("✕ Clear all filters", on_click=reset_all_filters, use_container_width=True, type="secondary", key="btn_clear_filters")

        if filtered_df.empty:
            st.info("No TSX assets match your selected filter criteria.")
        else:
            def signal_styler(val):
                if is_dark:
                    if "BUY" in str(val):
                        return "color: #4ade80; background-color: rgba(34, 197, 94, 0.20); font-weight: 700; border-radius: 4px;"
                    elif "SELL" in str(val):
                        return "color: #f87171; background-color: rgba(239, 68, 68, 0.20); font-weight: 700; border-radius: 4px;"
                    elif "TRIM" in str(val):
                        return "color: #fbbf24; background-color: rgba(245, 158, 11, 0.20); font-weight: 700; border-radius: 4px;"
                    return "color: #94a3b8;"
                else:
                    if "BUY" in str(val):
                        return "color: #15803d; background-color: #f0fdf4; font-weight: 700; border-radius: 4px;"
                    elif "SELL" in str(val):
                        return "color: #b91c1c; background-color: #fef2f2; font-weight: 700; border-radius: 4px;"
                    elif "TRIM" in str(val):
                        return "color: #b45309; background-color: #fffbeb; font-weight: 700; border-radius: 4px;"
                    return "color: #475569;"

            columns_order = [
                "Symbol", "Company", "Price", "Signal", "RSI_14", "SMA_50", "SMA_200", "Rationale"
            ]
            display_cols = [c for c in columns_order if c in filtered_df.columns]

            # Native Styler preserved with sorting & column controls
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

            # Native interactive Streamlit dataframe with full Asc/Desc column sorting
            st.dataframe(styled_df, use_container_width=True, hide_index=True)

            st.download_button(
                label="📥 Export Filtered Watchlist (CSV)",
                data=filtered_df.to_csv(index=False).encode("utf-8"),
                file_name=f"trendnorth_watchlist_{datetime.now(ET_ZONE).strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )

    # -------------------------------------------------------------------------
    # TAB 2: Pocket Trader (Portfolio & Target Execution Companion)
    # -------------------------------------------------------------------------
    with tab_pocket:
        col_hdr1, col_hdr2 = st.columns([3, 2])
        with col_hdr1:
            st.subheader("💼 Pocket Trader — Portfolio & Target Tracker")
            st.caption("Track active positions or planned purchases against live TSX scan prices with custom target gains.")
        with col_hdr2:
            st.info(
                "💾 **Browser Auto-Save Active:** Positions save locally. "
                "Clearing browser data or switching devices resets session. "
                "Export CSV periodically below for offline backup.",
                icon="ℹ️"
            )

        # 1. Batch Position Setup Form
        with st.expander("➕ Log Single or Multiple Positions (Batch Setup)", expanded=False):
            available_symbols = sorted(list(COMPANY_NAMES.keys()))
            chosen_symbols = st.multiselect(
                "Choose Symbol(s) to add to your tracker:",
                options=available_symbols,
                default=[],
                help="Pick one or multiple TSX symbols. An editable staging table will appear below.",
            )

            if chosen_symbols:
                st.caption("Adjust entry details below before adding to your portfolio:")
                staging_rows = []
                for sym in chosen_symbols:
                    cur_price = 0.0
                    if not df_raw.empty:
                        m = df_raw[df_raw["Symbol"] == sym]
                        if not m.empty:
                            cur_price = float(m["Price"].iloc[0])

                    staging_rows.append({
                        "Symbol": sym,
                        "Company": COMPANY_NAMES.get(sym, "—"),
                        "Buy Date": str(date.today()),
                        "Buy Price": round(cur_price, 2),
                        "Shares": 10,
                        "Target Gain ($)": 10.00,
                    })

                staging_df = pd.DataFrame(staging_rows)
                edited_staging = st.data_editor(
                    staging_df,
                    use_container_width=True,
                    num_rows="dynamic",
                    key="pocket_staging_editor",
                )

                if st.button("➕ Add All Selected Positions to Pocket Trader", type="primary"):
                    added_count = 0
                    dup_count = 0
                    for _, r in edited_staging.iterrows():
                        cand = {
                            "Symbol": str(r["Symbol"]).strip(),
                            "Buy Date": str(r["Buy Date"]),
                            "Buy Price": float(r["Buy Price"]),
                            "Shares": int(r["Shares"]),
                            "Target Gain": float(r["Target Gain ($)"]),
                        }
                        if not is_exact_duplicate(st.session_state.pocket_positions, cand):
                            st.session_state.pocket_positions.append(cand)
                            added_count += 1
                        else:
                            dup_count += 1

                    sync_pocket_to_storage()
                    if dup_count > 0:
                        st.warning(f"Added {added_count} position(s). Skipped {dup_count} exact duplicate(s).")
                    else:
                        st.success(f"Added {added_count} position(s) to Pocket Trader!")
                    st.rerun()

        # 2. Render Active Holdings Table
        if not st.session_state.pocket_positions:
            st.info("No active positions tracked in Pocket Trader yet. Add a stock using the batch form above or upload a CSV below.")
        else:
            calc_rows = []
            for i, pos in enumerate(st.session_state.pocket_positions):
                sym = pos["Symbol"]
                buy_p = float(pos.get("Buy Price", 0.0))
                shares = int(pos.get("Shares", 0))
                tgt_gain = float(pos.get("Target Gain", 10.0))

                cur_price = buy_p
                sig = "—"
                rsi = 50.0
                if not df_raw.empty:
                    match = df_raw[df_raw["Symbol"] == sym]
                    if not match.empty:
                        cur_price = float(match["Price"].iloc[0])
                        sig = str(match["Signal"].iloc[0])
                        rsi = float(match["RSI_14"].iloc[0])

                cost_basis = buy_p * shares
                market_val = cur_price * shares
                unrealized_pl = market_val - cost_basis
                unrealized_pct = ((cur_price - buy_p) / buy_p * 100.0) if buy_p > 0 else 0.0
                target_price = buy_p + tgt_gain
                target_reached = cur_price >= target_price

                calc_rows.append({
                    "Index": i,
                    "Symbol": sym,
                    "Company": COMPANY_NAMES.get(sym, "—"),
                    "Buy Date": pos.get("Buy Date", "—"),
                    "Buy Price": buy_p,
                    "Current Price": cur_price,
                    "Shares": shares,
                    "Cost Basis": cost_basis,
                    "Market Value": market_val,
                    "Unrealized P&L ($)": unrealized_pl,
                    "Return (%)": unrealized_pct,
                    "Target Price": target_price,
                    "Status": "🎯 TARGET REACHED" if target_reached else f"${(target_price - cur_price):.2f} to Target",
                    "Live Signal": sig,
                    "RSI_14": rsi,
                })

            port_df = pd.DataFrame(calc_rows)

            total_invested = port_df["Cost Basis"].sum()
            total_current = port_df["Market Value"].sum()
            total_net_pl = total_current - total_invested
            total_net_pct = (total_net_pl / total_invested * 100.0) if total_invested > 0 else 0.0

            p_col1, p_col2, p_col3 = st.columns(3)
            with p_col1:
                st.metric("Total Invested (Cost Basis)", f"${total_invested:,.2f}")
            with p_col2:
                st.metric("Total Portfolio Value", f"${total_current:,.2f}")
            with p_col3:
                delta_str = f"{total_net_pct:+.2f}%"
                st.metric("Cumulative Net Return", f"${total_net_pl:+,.2f}", delta=delta_str)

            display_port = port_df[[
                "Symbol", "Company", "Buy Date", "Buy Price", "Current Price", "Shares",
                "Market Value", "Unrealized P&L ($)", "Return (%)", "Target Price", "Status", "Live Signal"
            ]]

            event = st.dataframe(
                display_port.style.format({
                    "Buy Price": "${:.2f}",
                    "Current Price": "${:.2f}",
                    "Market Value": "${:,.2f}",
                    "Unrealized P&L ($)": "${:+,.2f}",
                    "Return (%)": "{:+.2f}%",
                    "Target Price": "${:.2f}",
                }),
                use_container_width=True,
                hide_index=False,
                on_select="rerun",
                selection_mode="multi-row",
                key="pocket_table_selection",
            )

            # Bulk Removal Action Bar
            selected_rows = event.selection.rows if hasattr(event, "selection") and event.selection else []
            if selected_rows:
                act_col1, _ = st.columns([2, 8])
                with act_col1:
                    if st.button(f"🗑️ Remove ({len(selected_rows)}) Position(s)", type="primary"):
                        st.session_state.pocket_positions = [
                            p for idx, p in enumerate(st.session_state.pocket_positions) if idx not in selected_rows
                        ]
                        sync_pocket_to_storage()
                        st.rerun()

            # 3. Option B: Quick Edit Drawer for Tracked Positions
            with st.expander("✏️ Quick Edit Existing Position", expanded=False):
                edit_options = [
                    f"#{i} — {p['Symbol']} (Bought {p.get('Buy Date', '—')} @ ${p.get('Buy Price', 0):.2f})"
                    for i, p in enumerate(st.session_state.pocket_positions)
                ]
                selected_edit_str = st.selectbox("Select position to modify:", options=edit_options)
                if selected_edit_str:
                    sel_idx = int(selected_edit_str.split(" — ")[0].replace("#", ""))
                    target_pos = st.session_state.pocket_positions[sel_idx]

                    e_col1, e_col2, e_col3, e_col4 = st.columns(4)
                    with e_col1:
                        new_shares = st.number_input("Shares", min_value=1, value=int(target_pos.get("Shares", 10)), step=1)
                    with e_col2:
                        try:
                            cur_d = datetime.strptime(str(target_pos.get("Buy Date")), "%Y-%m-%d").date()
                        except Exception:
                            cur_d = date.today()
                        new_date = st.date_input("Buy Date", value=cur_d)
                    with e_col3:
                        new_price = st.number_input("Buy Price (CAD)", min_value=0.01, value=float(target_pos.get("Buy Price", 10.0)), step=0.1)
                    with e_col4:
                        new_gain = st.number_input("Target Gain ($/sh)", min_value=0.1, value=float(target_pos.get("Target Gain", 10.0)), step=0.5)

                    if st.button(f"💾 Save Changes to {target_pos['Symbol']}", type="primary"):
                        st.session_state.pocket_positions[sel_idx] = {
                            "Symbol": target_pos["Symbol"],
                            "Buy Date": str(new_date),
                            "Buy Price": float(new_price),
                            "Shares": int(new_shares),
                            "Target Gain": float(new_gain),
                        }
                        sync_pocket_to_storage()
                        st.success(f"Updated {target_pos['Symbol']} successfully!")
                        st.rerun()

        # 4. Portfolio Backup & Restore (Unconditionally Available)
        st.markdown("---")
        with st.expander("📁 Portfolio Backup & Restore", expanded=False):
            b_col1, b_col2 = st.columns(2)
            with b_col1:
                st.write("**Backup Portfolio to Disk:**")
                if st.session_state.pocket_positions:
                    export_csv = pd.DataFrame(st.session_state.pocket_positions).to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="📥 Export Portfolio CSV",
                        data=export_csv,
                        file_name=f"trendnorth_pocket_portfolio_{datetime.now(ET_ZONE).strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                    )
                else:
                    st.button("📥 Export Portfolio CSV", disabled=True)

            with b_col2:
                st.write("**Restore / Merge Portfolio from Backup:**")
                uploaded_backup = st.file_uploader(
                    "Upload portfolio CSV",
                    type=["csv"],
                    label_visibility="collapsed",
                    key="pocket_csv_uploader"
                )
                if uploaded_backup is not None:
                    file_sig = f"{uploaded_backup.name}_{uploaded_backup.size}"
                    if st.session_state.last_processed_file_id != file_sig:
                        try:
                            if uploaded_backup.size > 2 * 1024 * 1024:
                                st.error("Uploaded file exceeds the 2 MB limit.")
                            else:
                                imp_df = pd.read_csv(uploaded_backup)
                                required_cols = {"Symbol", "Buy Price", "Shares"}
                                if required_cols.issubset(imp_df.columns):
                                    merged_count = 0
                                    skipped_universe = []
                                    skipped_duplicates = 0

                                    for _, row in imp_df.iterrows():
                                        sym = str(row["Symbol"]).strip().upper()
                                        if sym in COMPANY_NAMES:
                                            cand = {
                                                "Symbol": sym,
                                                "Buy Date": str(row.get("Buy Date", date.today())),
                                                "Buy Price": float(row["Buy Price"]),
                                                "Shares": int(row["Shares"]),
                                                "Target Gain": float(row.get("Target Gain", 10.0)),
                                            }
                                            if not is_exact_duplicate(st.session_state.pocket_positions, cand):
                                                st.session_state.pocket_positions.append(cand)
                                                merged_count += 1
                                            else:
                                                skipped_duplicates += 1
                                        else:
                                            skipped_universe.append(sym)

                                    st.session_state.last_processed_file_id = file_sig
                                    sync_pocket_to_storage()

                                    msg = f"Import complete: {merged_count} position(s) added."
                                    if skipped_duplicates:
                                        msg += f" {skipped_duplicates} duplicate(s) skipped."
                                    if skipped_universe:
                                        st.warning(f"{msg} The following were skipped as they are outside the 59 tracked TSX assets: {', '.join(set(skipped_universe))}")
                                    else:
                                        st.success(msg)
                                    st.rerun()
                                else:
                                    st.error("Missing required headers: Symbol, Buy Price, Shares.")
                        except Exception as err:
                            st.error(f"Error parsing CSV: {err}")
                    else:
                        st.caption(f"ℹ️ `{uploaded_backup.name}` is already synchronized.")

    # -------------------------------------------------------------------------
    # TAB 3: Market Technicals
    # -------------------------------------------------------------------------
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
                        "BUY / ACCUMULATE": "#22c55e",
                        "SELL / EXIT": "#ef4444",
                        "TRIM / TAKE PROFIT": "#f59e0b",
                        "KEEP / HOLD": "#64748b",
                    },
                    template=plotly_theme,
                )
                fig_rsi.add_vline(x=40, line_dash="dot", line_color="#22c55e", annotation_text="Pullback (<=40)")
                fig_rsi.add_vline(x=75, line_dash="dot", line_color="#ef4444", annotation_text="Overbought (>=75)")
                fig_rsi.update_layout(xaxis_title="14-Day RSI", yaxis_title="Equities Count", height=420)
                st.plotly_chart(fig_rsi, use_container_width=True)

            with chart_col2:
                st.subheader("Price vs. 50-Day Moving Average")
                hover_fields = {"Company": True, "RSI_14": True} if "Company" in filtered_df.columns else {"RSI_14": True}
                fig_scatter = px.scatter(
                    filtered_df,
                    x="SMA_50",
                    y="Price",
                    hover_name="Symbol",
                    hover_data=hover_fields,
                    color="Signal",
                    color_discrete_map={
                        "BUY / ACCUMULATE": "#22c55e",
                        "SELL / EXIT": "#ef4444",
                        "TRIM / TAKE PROFIT": "#f59e0b",
                        "KEEP / HOLD": "#64748b",
                    },
                    template=plotly_theme,
                )
                fig_scatter.update_layout(xaxis_title="50-Day SMA (CAD)", yaxis_title="Current Price (CAD)", height=420)
                st.plotly_chart(fig_scatter, use_container_width=True)

    # -------------------------------------------------------------------------
    # TAB 4: User Manual & Methodology
    # -------------------------------------------------------------------------
    with tab_manual:
        st.subheader("📖 TrendNorth Documentation & Operational Manual")

        with st.expander("1. Introduction", expanded=True):
            st.markdown(
                """
                **TrendNorth** is an automated quantitative screening engine monitoring high-liquidity Canadian equities and benchmark ETFs listed on the Toronto Stock Exchange (TSX).
                
                The engine systematically computes momentum oscillators and moving averages to highlight actionable swing trading opportunities while removing emotional bias.
                """
            )

        with st.expander("2. Indicator & Signal Glossary", expanded=True):
            st.markdown(
                """
                | Signal | Rationale | Condition Logic | Interpretation |
                | :--- | :--- | :--- | :--- |
                | **`BUY / ACCUMULATE`** | **Bullish trend + Pullback dip** | `SMA_50 > SMA_200` and `RSI_14 <= 40` | Long-term macro bull trend is intact, but short-term selling has pulled the oscillator into value territory. |
                | **`SELL / EXIT`** | **Death Cross (Bearish trend)** | `SMA_50 < SMA_200` | The 50-day average has crossed below the 200-day average, indicating structural distribution. |
                | **`TRIM / TAKE PROFIT`** | **Overextended momentum** | `RSI_14 >= 75` | Momentum has pushed into overbought territory; higher risk of near-term mean reversion. |
                | **`KEEP / HOLD`** | **Trading within baseline** | Normal range | Price momentum is oscillating within historical ranges without active triggers. |
                """
            )

        with st.expander("3. Pocket Trader Execution Guide", expanded=False):
            st.markdown(
                """
                * **Batch Position Logging:** Select multiple symbols from the 59 tracked assets to track lots simultaneously.
                * **Target Gain Tracking:** Specify your profit objective (e.g., $10/share). The status badge dynamically turns into **🎯 TARGET REACHED** when prices cross above.
                * **Quick Editing:** Use the *Quick Edit Existing Position* drawer to update shares, entry date, buy price, or target price at any time.
                * **Privacy-First Storage:** Positions persist in browser local storage and can be exported or merged anytime via CSV files.
                """
            )

        with st.expander("4. Precision Cloud Scheduling (TN-001)", expanded=False):
            st.markdown(
                """
                * **Morning Dip Scan (10:32 AM ET):** Webhook trigger executes 62 minutes into regular session to identify early intraday oversold pullbacks.
                * **Market Close Scan (4:47 PM ET):** Webhook trigger executes 47 minutes post-close once official daily closing prints and settlements are finalized.
                """
            )

    # -------------------------------------------------------------------------
    # Floating Feedback Popover (Bottom-Right Anchored)
    # -------------------------------------------------------------------------
    with st.popover("💬 Submit Feedback"):
        st.markdown("### 💬 TrendNorth Feedback")
        fb_name = st.text_input("Name (Optional)", placeholder="e.g. John Doe")
        fb_email = st.text_input("Email (Optional)", placeholder="e.g. john@example.com")
        fb_sentiment = st.selectbox("Sentiment", ["Positive 👍", "Bug Report 🐞", "Feature Request 💡", "Neutral 💬"])
        fb_msg = st.text_area("Your Feedback / Suggestions", placeholder="Tell us what you'd like improved...")

        if st.button("Send Feedback", type="primary", use_container_width=True):
            if fb_msg.strip():
                ok = send_feedback_email(fb_name, fb_email, fb_sentiment, fb_msg)
                if ok:
                    st.success("Thank you! Your feedback has been sent directly to the development team.")
                else:
                    st.info("Feedback captured! Thank you for helping improve TrendNorth.")
            else:
                st.warning("Please type a message before submitting.")

if __name__ == "__main__":
    render_dashboard()