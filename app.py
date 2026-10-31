import io
import os
import re
import time
import json
from datetime import date, datetime, time as dtime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf

# Supabase Client Import
try:
    from supabase import create_client, Client
except ImportError:
    create_client = None

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
# Wealthsimple Minimalist Clean Light Theme Tokens & CSS Injection
# -----------------------------------------------------------------------------
bg_main = "#f8fafc"
bg_card = "#ffffff"
bg_card_hover = "#f1f5f9"
bg_sidebar = "#ffffff"
border_col = "#e2e8f0"
text_title = "#0f172a"
text_sub = "#475569"
input_bg = "#ffffff"
input_text = "#0f172a"
plotly_tpl = "plotly_white"
active_tab_color = "#0284c7"

st.markdown(
    f"""
    <style>
    /* Global App Background & Text */
    .stApp {{
        background-color: {bg_main} !important;
        color: {text_title} !important;
    }}
    header[data-testid="stHeader"] {{
        background-color: #ffffff !important;
        border-bottom: 1px solid {border_col} !important;
    }}
    header[data-testid="stHeader"] * {{
        color: {text_title} !important;
    }}

    /* Container Spacing */
    .block-container {{
        padding-top: 3.2rem !important;
        padding-bottom: 3rem !important;
    }}

    /* Sidebar Theming */
    section[data-testid="stSidebar"] {{
        background-color: {bg_sidebar} !important;
        border-right: 1px solid {border_col} !important;
    }}
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3, 
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span {{
        color: {text_title} !important;
    }}
    section[data-testid="stSidebar"] .stCaption {{
        color: {text_sub} !important;
    }}

    /* Inputs, Select Boxes, & Dropdowns */
    div[data-baseweb="input"], div[data-baseweb="select"], div[data-baseweb="select"] > div {{
        background-color: {input_bg} !important;
        border: 1px solid {border_col} !important;
        border-radius: 8px !important;
        color: {input_text} !important;
    }}
    div[data-baseweb="input"] input, div[data-baseweb="select"] * {{
        color: {input_text} !important;
        background-color: transparent !important;
    }}
    ul[role="listbox"], li[role="option"] {{
        background-color: #ffffff !important;
        color: #0f172a !important;
    }}
    li[role="option"]:hover {{
        background-color: #f1f5f9 !important;
    }}

    /* Multiselect Tags */
    span[data-baseweb="tag"] {{
        background-color: #e0f2fe !important;
        color: #0369a1 !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
    }}
    span[data-baseweb="tag"] * {{
        color: #0369a1 !important;
    }}

    /* Universal Metric Cards */
    div[data-testid="stMetric"] {{
        background-color: #ffffff !important;
        border: 1px solid {border_col} !important;
        border-radius: 12px !important;
        padding: 14px 18px !important;
        min-height: 86px !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
    }}
    div[data-testid="stMetricLabel"] {{
        color: #475569 !important;
    }}
    div[data-testid="stMetricLabel"] * {{
        color: #475569 !important;
        font-weight: 700 !important;
        font-size: 0.80rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
    }}
    div[data-testid="stMetricValue"] {{
        color: #0f172a !important;
    }}
    div[data-testid="stMetricValue"] * {{
        color: #0f172a !important;
        font-weight: 800 !important;
        font-size: 1.25rem !important;
        line-height: 1.25 !important;
    }}

    /* Top Sub-Header Meta Tags */
    .tn-meta-bar span {{
        background: #ffffff !important;
        border: 1px solid {border_col} !important;
        padding: 6px 14px;
        border-radius: 8px;
        color: #475569 !important;
        font-size: 0.85rem;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }}

    /* Interactive Embedded KPI Filter Cards */
    div.kpi-card-container button {{
        width: 100% !important;
        background-color: #ffffff !important;
        border: 1px solid {border_col} !important;
        border-radius: 12px !important;
        padding: 12px 14px !important;
        text-align: left !important;
        white-space: pre-line !important;
        line-height: 1.35 !important;
        font-size: 0.95rem !important;
        font-weight: 700 !important;
        min-height: 86px !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        color: {text_title} !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
    }}
    div.kpi-card-container button:hover {{
        border-color: #0284c7 !important;
        background-color: {bg_card_hover} !important;
        transform: translateY(-2px);
        box-shadow: 0 4px 14px rgba(2, 132, 199, 0.12) !important;
    }}
    div.kpi-card-container button p {{
        color: {text_title} !important;
    }}

    /* Wealthsimple Detail & Metric Cards */
    .ws-card {{
        background-color: #ffffff;
        border: 1px solid {border_col};
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 20px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }}
    .ws-stat-tile {{
        background-color: #f8fafc;
        border: 1px solid {border_col};
        border-radius: 10px;
        padding: 12px 16px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        transition: border-color 0.15s ease;
    }}
    .ws-stat-tile:hover {{
        border-color: #0284c7;
    }}
    .ws-metric-label {{
        color: #64748b;
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 4px;
    }}
    .ws-metric-val {{
        color: #0f172a;
        font-size: 1.15rem;
        font-weight: 800;
        font-variant-numeric: tabular-nums;
    }}
    .ws-badge {{
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.76rem;
        font-weight: 700;
        margin-left: 6px;
    }}
    .ws-badge-green {{
        background-color: rgba(34, 197, 94, 0.12);
        color: #16a34a;
    }}
    .ws-meta-pill {{
        background-color: #f1f5f9;
        border: 1px solid {border_col};
        border-radius: 8px;
        padding: 6px 12px;
        color: #475569;
        font-size: 0.86rem;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }}
    .ws-meta-pill b {{
        color: #0f172a;
    }}

    /* Buttons */
    button[kind="secondary"] {{
        background-color: #ffffff !important;
        border: 1px solid {border_col} !important;
        color: #0f172a !important;
        border-radius: 8px !important;
    }}
    button[kind="secondary"]:hover {{
        background-color: #f1f5f9 !important;
        border-color: #0284c7 !important;
        color: #0284c7 !important;
    }}

    /* High-Contrast Visible Tabs */
    button[data-testid="stTab"] {{
        background-color: transparent !important;
        border: none !important;
        padding: 10px 18px !important;
    }}
    button[data-testid="stTab"] p {{
        color: #475569 !important;
        font-weight: 700 !important;
        font-size: 0.96rem !important;
    }}
    button[data-testid="stTab"][aria-selected="true"] {{
        border-bottom: 3px solid {active_tab_color} !important;
    }}
    button[data-testid="stTab"][aria-selected="true"] p {{
        color: {active_tab_color} !important;
        font-weight: 800 !important;
    }}
    button[data-testid="stTab"]:hover p {{
        color: #0f172a !important;
    }}

    /* Expanders */
    div[data-testid="stExpander"] {{
        background-color: #ffffff !important;
        border: 1px solid {border_col} !important;
        border-radius: 10px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important;
    }}
    div[data-testid="stExpander"] summary,
    div[data-testid="stExpander"] div[role="region"] {{
        background-color: #ffffff !important;
        color: #0f172a !important;
    }}
    div[data-testid="stExpander"] * {{
        color: #0f172a !important;
    }}

    /* Fix Dark Code Blocks in User Manual */
    code {{
        background-color: #f1f5f9 !important;
        color: #0f172a !important;
        padding: 2px 6px !important;
        border-radius: 4px !important;
        border: 1px solid #e2e8f0 !important;
        font-weight: 700 !important;
    }}

    /* Modern Table Hint Pill */
    .tn-table-hint {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background-color: #f1f5f9;
        border: 1px solid {border_col};
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.85rem;
        color: #475569;
        margin-bottom: 12px;
    }}
    .tn-table-hint b {{
        color: #0284c7;
    }}

    /* Dataframe Overrides */
    div[data-testid="stDataFrame"] {{
        background-color: #ffffff !important;
        border: 1px solid {border_col} !important;
        border-radius: 12px !important;
        overflow: hidden !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
    }}

    /* Hide the radio/checkbox column on watchlist */
    div[data-testid="stDataFrame"] div[role="columnheader"]:first-child,
    div[data-testid="stDataFrame"] div[role="row"] > div[role="gridcell"]:first-child:has(input[type="checkbox"]),
    div[data-testid="stDataFrame"] div[role="row"] > div[role="gridcell"]:first-child:has(input[type="radio"]) {{
        display: none !important;
    }}

    /* Floating Feedback Popover */
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

# -----------------------------------------------------------------------------
# Baseline 59 Monitored TSX Universe
# -----------------------------------------------------------------------------
BASE_COMPANY_NAMES = {
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

# Extended Catalog for Instant Search Suggestions
EXTENDED_CATALOG = {
    **BASE_COMPANY_NAMES,
    "AC.TO": "Air Canada",
    "AQN.TO": "Algonquin Power & Utilities",
    "BB.TO": "BlackBerry Limited",
    "CJT.TO": "Cargojet Inc.",
    "BBD-B.TO": "Bombardier Inc.",
    "LUN.TO": "Lundin Mining",
    "HBM.TO": "Hudbay Minerals",
    "IVN.TO": "Ivanhoe Mines",
    "ARX.TO": "ARC Resources",
    "CPG.TO": "Crescent Point Energy",
    "VET.TO": "Vermilion Energy",
    "MEG.TO": "MEG Energy",
    "PAAS.TO": "Pan American Silver",
    "EQX.TO": "Equinox Gold",
    "NVEI.TO": "Nuvei Corporation",
    "LSPD.TO": "Lightspeed Commerce",
    "DND.TO": "Dye & Durham",
    "CTS.TO": "Converge Technology Solutions",
    "NFI.TO": "NFI Group",
    "TIH.TO": "Toromont Industries",
    "RCH.TO": "Richelieu Hardware",
    "MTL.TO": "Mullen Group",
    "TFII.TO": "TFI International",
    "BYD.TO": "Boyd Group Services",
    "PBH.TO": "Premium Brands Holdings",
    "SAP.TO": "Saputo Inc.",
    "JWEL.TO": "JAMIESON Wellness",
    "MTY.TO": "MTY Food Group",
    "CU.TO": "Canadian Utilities",
    "NPI.TO": "Northland Power",
    "BLX.TO": "Boralex Inc.",
    "INE.TO": "Innergex Renewable Energy",
    "TA.TO": "TransAlta Corporation",
    "RNW.TO": "TransAlta Renewables",
    "CAR-UN.TO": "Canadian Apartment Properties REIT",
    "REI-UN.TO": "RioCan REIT",
    "GRT-UN.TO": "Granite REIT",
    "CHP-UN.TO": "Choice Properties REIT",
    "DIR-UN.TO": "Dream Industrial REIT",
    "SRU-UN.TO": "SmartCentres REIT",
    "AP-UN.TO": "Allied Properties REIT",
    "HR-UN.TO": "H&R REIT",
    "IIP-UN.TO": "InterRent REIT",
    "KMP-UN.TO": "Killam Apartment REIT",
    "MI-UF.TO": "Minto Apartment REIT",
    "CRR-UN.TO": "Crombie REIT",
    "CSH-UN.TO": "Chartwell Retirement Residences",
    "SIA.TO": "Sienna Senior Living",
    "EXE.TO": "Extendicare Inc.",
}

ALL_SIGNAL_TYPES = ["BUY / ACCUMULATE", "SELL / EXIT", "TRIM / TAKE PROFIT", "KEEP / HOLD"]
DEFAULT_ACTIVE_SIGNALS = ["BUY / ACCUMULATE", "SELL / EXIT", "TRIM / TAKE PROFIT"]

# -----------------------------------------------------------------------------
# Robust Dynamic Ticker & Name Resolver (Auto-Appends .TO for TSX)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=86400)
def sanitize_and_resolve_ticker(raw_sym: str) -> tuple[str, str]:
    sym = str(raw_sym).strip().upper()
    if not sym:
        return "", ""

    if sym in EXTENDED_CATALOG:
        return sym, EXTENDED_CATALOG[sym]
    if f"{sym}.TO" in EXTENDED_CATALOG:
        return f"{sym}.TO", EXTENDED_CATALOG[f"{sym}.TO"]

    candidates = [sym] if ("." in sym or sym.endswith(".TO")) else [f"{sym}.TO", sym]
    for cand in candidates:
        try:
            t = yf.Ticker(cand)
            info = t.info
            if info and ("shortName" in info or "regularMarketPrice" in info or "previousClose" in info):
                name = info.get("shortName") or info.get("longName") or cand
                return cand, name
        except Exception:
            continue

    return sym, sym

# -----------------------------------------------------------------------------
# Supabase Custom Watchlist Synchronization Helpers
# -----------------------------------------------------------------------------
def db_add_custom_symbol(symbol: str, company: str):
    supabase_url = st.secrets.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL")
    supabase_key = st.secrets.get("SUPABASE_KEY") or os.environ.get("SUPABASE_KEY")
    if supabase_url and supabase_key and create_client is not None:
        try:
            client: Client = create_client(supabase_url, supabase_key)
            client.table("custom_watchlist").upsert({"symbol": symbol, "company": company}).execute()
        except Exception as e:
            st.warning(f"Note: Could not sync {symbol} to cloud DB: {e}")

def db_remove_custom_symbol(symbol: str):
    supabase_url = st.secrets.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL")
    supabase_key = st.secrets.get("SUPABASE_KEY") or os.environ.get("SUPABASE_KEY")
    if supabase_url and supabase_key and create_client is not None:
        try:
            client: Client = create_client(supabase_url, supabase_key)
            client.table("custom_watchlist").delete().eq("symbol", symbol).execute()
        except Exception as e:
            st.warning(f"Note: Could not remove {symbol} from cloud DB: {e}")

def db_load_custom_watchlist() -> list[str]:
    supabase_url = st.secrets.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL")
    supabase_key = st.secrets.get("SUPABASE_KEY") or os.environ.get("SUPABASE_KEY")
    if supabase_url and supabase_key and create_client is not None:
        try:
            client: Client = create_client(supabase_url, supabase_key)
            res = client.table("custom_watchlist").select("symbol").execute()
            if res.data:
                return [row["symbol"] for row in res.data]
        except Exception:
            pass
    return []

# -----------------------------------------------------------------------------
# Watchlist Membership State (Custom Adds & Removals)
# -----------------------------------------------------------------------------
if "custom_watchlist_symbols" not in st.session_state:
    st.session_state.custom_watchlist_symbols = db_load_custom_watchlist()

if "removed_watchlist_symbols" not in st.session_state:
    st.session_state.removed_watchlist_symbols = []

if "filter_signals" not in st.session_state:
    st.session_state.filter_signals = DEFAULT_ACTIVE_SIGNALS.copy()
if "filter_rsi" not in st.session_state:
    st.session_state.filter_rsi = (0.0, 100.0)
if "filter_sma" not in st.session_state:
    st.session_state.filter_sma = "All Trends"
if "filter_search_select" not in st.session_state:
    st.session_state.filter_search_select = "-- All Assets (No Filter) --"

def set_signal_filter(signal_name):
    if signal_name == "ALL":
        st.session_state.filter_signals = ALL_SIGNAL_TYPES.copy()
    else:
        st.session_state.filter_signals = [signal_name]

def reset_all_filters():
    st.session_state.filter_signals = DEFAULT_ACTIVE_SIGNALS.copy()
    st.session_state.filter_rsi = (0.0, 100.0)
    st.session_state.filter_sma = "All Trends"
    st.session_state.filter_search_select = "-- All Assets (No Filter) --"

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
        return "CLOSED", "Weekend / Holiday", "Closed", "Opens 9:30 AM ET next trading day"

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
# On-Demand Technical Indicator Engine
# -----------------------------------------------------------------------------
@st.cache_data(ttl=600)
def calculate_on_demand_technicals(ticker: str):
    """Calculates RSI_14, SMA_50, SMA_200, and signal dynamically for any ticker."""
    try:
        t = yf.Ticker(ticker)
        df_hist = t.history(period="1y", interval="1d")
        if df_hist.empty or len(df_hist) < 20:
            return None

        closes = df_hist["Close"]
        cur_price = float(closes.iloc[-1])

        sma_50 = float(closes.rolling(window=50).mean().iloc[-1]) if len(closes) >= 50 else float(closes.mean())
        sma_200 = float(closes.rolling(window=200).mean().iloc[-1]) if len(closes) >= 200 else float(closes.mean())

        delta = closes.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi_14 = float((100 - (100 / (1 + rs))).iloc[-1])

        if pd.isna(rsi_14):
            rsi_14 = 50.0

        if sma_50 > sma_200 and rsi_14 <= 40.0:
            signal = "BUY / ACCUMULATE"
            rationale = "Bullish trend + Pullback dip"
        elif sma_50 < sma_200:
            signal = "SELL / EXIT"
            rationale = "Death Cross (Bearish trend)"
        elif rsi_14 >= 75.0:
            signal = "TRIM / TAKE PROFIT"
            rationale = "Overextended momentum"
        else:
            signal = "KEEP / HOLD"
            rationale = "Trading within baseline"

        return {
            "price": cur_price,
            "sma_50": sma_50,
            "sma_200": sma_200,
            "rsi_14": rsi_14,
            "signal": signal,
            "rationale": rationale,
        }
    except Exception:
        return None

# -----------------------------------------------------------------------------
# Resilient Data Loader with Supabase Primary & Cloud Fallback
# -----------------------------------------------------------------------------
@st.cache_data(ttl=60)
def load_screener_results():
    df = None
    mod_time = None
    fetch_error = None

    supabase_url = st.secrets.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL")
    supabase_key = st.secrets.get("SUPABASE_KEY") or os.environ.get("SUPABASE_KEY")

    if supabase_url and supabase_key and create_client is not None:
        try:
            supabase: Client = create_client(supabase_url, supabase_key)
            latest_run = (
                supabase.table("screener_results")
                .select("scan_timestamp")
                .order("scan_timestamp", desc=True)
                .limit(1)
                .execute()
            )

            if latest_run.data:
                latest_ts_str = latest_run.data[0]["scan_timestamp"]
                res = (
                    supabase.table("screener_results")
                    .select("symbol, company, price, signal, rsi_14, sma_50, sma_200, sma_trend, rationale, scan_timestamp")
                    .eq("scan_timestamp", latest_ts_str)
                    .execute()
                )

                if res.data:
                    df = pd.DataFrame(res.data)
                    df.rename(columns={
                        "symbol": "Symbol",
                        "company": "Company",
                        "price": "Price",
                        "signal": "Signal",
                        "rsi_14": "RSI_14",
                        "sma_50": "SMA_50",
                        "sma_200": "SMA_200",
                        "sma_trend": "SMA_Trend",
                        "rationale": "Rationale",
                    }, inplace=True)

                    try:
                        parsed_dt = datetime.fromisoformat(latest_ts_str.replace("Z", "+00:00"))
                        mod_time = parsed_dt.astimezone(ET_ZONE)
                    except Exception:
                        mod_time = datetime.now(ET_ZONE)
        except Exception as e:
            fetch_error = f"Supabase: {e}"

    if df is None or df.empty:
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
                fetch_error = f"HTTP {resp.status_code}: {resp.reason}"
        except Exception as e:
            fetch_error = f"Remote URL: {e}"

    if (df is None or df.empty) and os.path.exists(LOCAL_CSV_FILE):
        try:
            raw_mtime = os.path.getmtime(LOCAL_CSV_FILE)
            mod_time = datetime.fromtimestamp(raw_mtime, tz=ZoneInfo("UTC")).astimezone(ET_ZONE)
            df = pd.read_csv(LOCAL_CSV_FILE)
        except Exception:
            pass

    if df is None or df.empty:
        return pd.DataFrame(), None

    try:
        if "Symbol" not in df.columns and "Ticker" in df.columns:
            df.rename(columns={"Ticker": "Symbol"}, inplace=True)

        if "Company" not in df.columns and "Symbol" in df.columns:
            df["Company"] = df["Symbol"].map(lambda s: sanitize_and_resolve_ticker(s)[1])

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
# Fundamental & Market Data Fetcher
# -----------------------------------------------------------------------------
@st.cache_data(ttl=1800)
def fetch_stock_market_details(ticker: str):
    clean_sym, company_name = sanitize_and_resolve_ticker(ticker)
    try:
        t = yf.Ticker(clean_sym)
        info = t.info

        ex_div_ts = info.get("exDividendDate")
        ex_div_str = (
            datetime.fromtimestamp(ex_div_ts).strftime("%B %d, %Y")
            if ex_div_ts else "Announcement pending"
        )

        div_yield_val = info.get("dividendYield")
        div_yield_str = f"{(div_yield_val * 100):.2f}%" if div_yield_val else "N/A"

        mcap = info.get("marketCap")
        if mcap:
            if mcap >= 1e12:
                mcap_str = f"${mcap / 1e12:.2f}T"
            elif mcap >= 1e9:
                mcap_str = f"${mcap / 1e9:.2f}B"
            elif mcap >= 1e6:
                mcap_str = f"${mcap / 1e6:.2f}M"
            else:
                mcap_str = f"${mcap:,.0f}"
        else:
            mcap_str = "N/A"

        shares = info.get("sharesOutstanding")
        if shares:
            if shares >= 1e9:
                shares_str = f"{shares / 1e9:.2f}B"
            elif shares >= 1e6:
                shares_str = f"{shares / 1e6:.2f}M"
            else:
                shares_str = f"{shares:,.0f}"
        else:
            shares_str = "N/A"

        pe = info.get("trailingPE") or info.get("forwardPE")
        pe_str = f"{pe:.2f}" if pe else "N/A"

        open_p = info.get("open") or info.get("regularMarketOpen")
        prev_close = info.get("previousClose") or open_p or 1.0
        cur_p = info.get("currentPrice") or info.get("regularMarketPrice") or open_p

        price_diff = (cur_p - prev_close) if cur_p and prev_close else 0.0
        pct_diff = (price_diff / prev_close * 100) if prev_close else 0.0

        return {
            "symbol": clean_sym,
            "shortName": info.get("shortName") or info.get("longName") or company_name,
            "currentPrice": cur_p if cur_p else 0.0,
            "priceDiff": price_diff,
            "pctDiff": pct_diff,
            "open": f"${open_p:.2f}" if open_p else "N/A",
            "high": f"${info.get('dayHigh'):.2f}" if info.get('dayHigh') else "N/A",
            "low": f"${info.get('dayLow'):.2f}" if info.get('dayLow') else "N/A",
            "week52High": f"${info.get('fiftyTwoWeekHigh'):.2f}" if info.get('fiftyTwoWeekHigh') else "N/A",
            "week52Low": f"${info.get('fiftyTwoWeekLow'):.2f}" if info.get('fiftyTwoWeekLow') else "N/A",
            "volume": f"{info.get('volume', 0):,}" if info.get('volume') else "N/A",
            "avgVolume": f"{info.get('averageVolume', 0):,}" if info.get('averageVolume') else "N/A",
            "exchange": info.get("exchange", "TSX"),
            "divYield": div_yield_str,
            "divYieldVal": div_yield_val or 0.0,
            "divFrequency": "Quarterly" if div_yield_val else "None",
            "exDivDate": ex_div_str,
            "marketCap": mcap_str,
            "sharesOut": shares_str,
            "peRatio": pe_str,
            "summary": info.get("longBusinessSummary", "Company description and operational breakdown are currently unavailable."),
            "website": info.get("website", ""),
            "country": info.get("country", "Canada"),
            "employees": f"{info.get('fullTimeEmployees', 0):,}" if info.get('fullTimeEmployees') else "N/A",
            "industry": info.get("industry", "Equities"),
            "officer": (info.get("companyOfficers", [{}])[0].get("name", "N/A") if info.get("companyOfficers") else "N/A")
        }
    except Exception as e:
        return None

@st.cache_data(ttl=900)
def fetch_stock_chart_history(ticker: str, period: str = "1y", interval: str = "1d"):
    clean_sym, _ = sanitize_and_resolve_ticker(ticker)
    try:
        t = yf.Ticker(clean_sym)
        df_hist = t.history(period=period, interval=interval)
        if df_hist.empty:
            return pd.DataFrame()
        df_hist.reset_index(inplace=True)
        return df_hist
    except Exception:
        return pd.DataFrame()

# -----------------------------------------------------------------------------
# TradingView Lightweight Interactive Financial Chart
# -----------------------------------------------------------------------------
def render_tradingview_area_chart(df_hist: pd.DataFrame, is_positive: bool = True):
    if df_hist.empty or "Close" not in df_hist.columns:
        st.info("Chart data currently unavailable for this timeframe.")
        return

    date_col = "Date" if "Date" in df_hist.columns else df_hist.columns[0]
    df_sorted = df_hist.copy().sort_values(by=date_col)
    
    chart_points = []
    seen_dates = set()
    for _, row in df_sorted.iterrows():
        try:
            d_val = row[date_col]
            time_str = d_val.strftime("%Y-%m-%d") if hasattr(d_val, "strftime") else str(d_val)[:10]
            if time_str in seen_dates:
                continue
            close_p = float(row["Close"])
            if not pd.isna(close_p) and close_p > 0:
                seen_dates.add(time_str)
                chart_points.append({"time": time_str, "value": round(close_p, 2)})
        except Exception:
            continue

    if not chart_points:
        st.info("Insufficient price points for TradingView chart.")
        return

    json_points = json.dumps(chart_points)
    
    line_col = "#16a34a" if is_positive else "#dc2626"
    top_col = "rgba(22, 163, 74, 0.22)" if is_positive else "rgba(220, 38, 38, 0.22)"
    bottom_col = "rgba(255, 255, 255, 0.0)"

    tv_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8" />
        <script src="https://unpkg.com/lightweight-charts@4.2.1/dist/lightweight-charts.standalone.production.js"></script>
        <style>
            html, body {{
                margin: 0;
                padding: 0;
                width: 100%;
                height: 100%;
                background-color: #ffffff;
                overflow: hidden;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }}
            #tv_chart_container {{
                width: 100%;
                height: 310px;
                position: relative;
            }}
        </style>
    </head>
    <body>
        <div id="tv_chart_container"></div>
        <script>
            (function() {{
                const container = document.getElementById('tv_chart_container');
                if (!container || typeof LightweightCharts === 'undefined') return;

                const chart = LightweightCharts.createChart(container, {{
                    autoSize: true,
                    layout: {{
                        background: {{ color: '#ffffff' }},
                        textColor: '#64748b',
                        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                    }},
                    grid: {{
                        vertLines: {{ visible: false }},
                        horzLines: {{ color: '#f1f5f9' }},
                    }},
                    crosshair: {{
                        vertLine: {{
                            color: '#94a3b8',
                            width: 1,
                            style: LightweightCharts.LineStyle.Dotted,
                            labelBackgroundColor: '#0f172a',
                        }},
                        horzLine: {{
                            color: '#94a3b8',
                            width: 1,
                            style: LightweightCharts.LineStyle.Dotted,
                            labelBackgroundColor: '#0f172a',
                        }},
                    }},
                    rightPriceScale: {{
                        borderColor: '#e2e8f0',
                        scaleMargins: {{
                            top: 0.12,
                            bottom: 0.08,
                        }},
                    }},
                    timeScale: {{
                        borderColor: '#e2e8f0',
                        timeVisible: true,
                        secondsVisible: false,
                    }},
                    handleScroll: false,
                    handleScale: false,
                }});

                const areaSeries = chart.addAreaSeries ? 
                    chart.addAreaSeries({{
                        topColor: '{top_col}',
                        bottomColor: '{bottom_col}',
                        lineColor: '{line_col}',
                        lineWidth: 2.5,
                        priceFormat: {{ type: 'price', precision: 2, minMove: 0.01 }},
                    }}) :
                    chart.addSeries(LightweightCharts.AreaSeries, {{
                        topColor: '{top_col}',
                        bottomColor: '{bottom_col}',
                        lineColor: '{line_col}',
                        lineWidth: 2.5,
                        priceFormat: {{ type: 'price', precision: 2, minMove: 0.01 }},
                    }});

                const data = {json_points};
                areaSeries.setData(data);
                chart.timeScale().fitContent();
            }})();
        </script>
    </body>
    </html>
    """
    components.html(tv_html, height=320)

# -----------------------------------------------------------------------------
# Wealthsimple-Style Market Details Page
# -----------------------------------------------------------------------------
def render_market_data_page(ticker: str):
    clean_sym, company_name = sanitize_and_resolve_ticker(ticker)
    st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)

    # 1. Top Navigation Bar: Back Button, Dynamic Add/Remove Watchlist Button, & Autocomplete Switcher
    col_back, col_add_watch, col_switch = st.columns([2.5, 3.5, 4.0])
    with col_back:
        if st.button("⬅️ Back to Watchlist", use_container_width=True, type="primary"):
            st.query_params.clear()
            st.rerun()

    with col_add_watch:
        # Determine whether this ticker is actively monitored
        is_in_custom = clean_sym in st.session_state.custom_watchlist_symbols
        is_in_removed = clean_sym in st.session_state.removed_watchlist_symbols
        is_monitored = is_in_custom or (clean_sym in BASE_COMPANY_NAMES and not is_in_removed)

        if is_monitored:
            if st.button(f"🗑️ Remove {clean_sym} from Watchlist", use_container_width=True, type="secondary"):
                if clean_sym in st.session_state.custom_watchlist_symbols:
                    st.session_state.custom_watchlist_symbols.remove(clean_sym)
                if clean_sym not in st.session_state.removed_watchlist_symbols:
                    st.session_state.removed_watchlist_symbols.append(clean_sym)
                # Sync deletion to Supabase
                db_remove_custom_symbol(clean_sym)
                st.toast(f"Removed {clean_sym} from Watchlist.")
                st.rerun()
        else:
            if st.button(f"➕ Add {clean_sym} to Watchlist", use_container_width=True, type="primary"):
                if clean_sym in st.session_state.removed_watchlist_symbols:
                    st.session_state.removed_watchlist_symbols.remove(clean_sym)
                if clean_sym not in st.session_state.custom_watchlist_symbols and clean_sym not in BASE_COMPANY_NAMES:
                    st.session_state.custom_watchlist_symbols.append(clean_sym)
                # Sync addition to Supabase
                db_add_custom_symbol(clean_sym, company_name)
                st.toast(f"✅ Added {clean_sym} to Watchlist!")
                st.rerun()

    with col_switch:
        all_catalog_syms = sorted(list(set(list(EXTENDED_CATALOG.keys()) + st.session_state.custom_watchlist_symbols)))
        searchable_list = [f"{s} — {sanitize_and_resolve_ticker(s)[1]}" for s in all_catalog_syms]
        curr_label = f"{clean_sym} — {company_name}"
        if curr_label not in searchable_list:
            searchable_list.insert(0, curr_label)

        curr_idx = searchable_list.index(curr_label) if curr_label in searchable_list else 0
        new_pick_str = st.selectbox(
            "Switch Stock",
            options=searchable_list,
            index=curr_idx,
            label_visibility="collapsed"
        )
        picked_sym = new_pick_str.split(" — ")[0].strip()
        if picked_sym != clean_sym:
            st.query_params["ticker"] = picked_sym
            st.rerun()

    st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

    with st.spinner(f"Retrieving fundamental data & technical charts for {clean_sym}..."):
        d = fetch_stock_market_details(clean_sym)

    if not d:
        st.error(f"Unable to retrieve market data for {clean_sym}. Please verify the ticker symbol.")
        return

    # 2. Header: Prominent Ticker and Subtitle Company Name
    st.markdown(
        f"""
        <div style="margin-bottom: 12px;">
            <div style="font-size: 2.4rem; font-weight: 800; color: #0f172a; letter-spacing: -0.5px; line-height: 1.1;">
                {d['symbol']}
            </div>
            <div style="font-size: 1.15rem; font-weight: 500; color: #64748b; margin-top: 4px;">
                {d['shortName']}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 3. Live Price & Session Change Badge
    is_positive = d['priceDiff'] >= 0
    color_change = "#16a34a" if is_positive else "#dc2626"
    plus_sign = "+" if is_positive else ""
    st.markdown(
        f"""
        <div style="margin-bottom: 16px;">
            <span style="font-size: 2.2rem; font-weight: 800; color: #0f172a;">${d['currentPrice']:.2f}</span>
            <span style="font-size: 1.05rem; color: #64748b; font-weight: 600; margin-left: 6px;">CAD</span>
            <div style="color: {color_change}; font-size: 1.1rem; font-weight: 700; margin-top: 4px;">
                {plus_sign}${d['priceDiff']:.2f} ({plus_sign}{d['pctDiff']:.2f}%) at close
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 4. Interactive Time Horizon Pill Toggles
    chart_tabs = st.radio(
        "Time Horizon",
        ["1M", "3M", "6M", "1Y", "5Y"],
        index=3,
        horizontal=True,
        label_visibility="collapsed"
    )

    period_map = {"1M": "1mo", "3M": "3mo", "6M": "6mo", "1Y": "1y", "5Y": "5y"}
    hist_data = fetch_stock_chart_history(clean_sym, period=period_map.get(chart_tabs, "1y"), interval="1d")

    # Render TradingView Interactive Area Chart
    render_tradingview_area_chart(hist_data, is_positive=is_positive)

    st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)

    # 5. Key Statistics (Wealthsimple 3x3 Card Grid)
    st.markdown("### Key Statistics")
    st.markdown(
        f"""
        <div class="ws-card">
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px;">
                <div class="ws-stat-tile">
                    <div class="ws-metric-label">Open Price</div>
                    <div class="ws-metric-val">{d['open']}</div>
                </div>
                <div class="ws-stat-tile">
                    <div class="ws-metric-label">Day High</div>
                    <div class="ws-metric-val">{d['high']}</div>
                </div>
                <div class="ws-stat-tile">
                    <div class="ws-metric-label">Day Low</div>
                    <div class="ws-metric-val">{d['low']}</div>
                </div>
                <div class="ws-stat-tile">
                    <div class="ws-metric-label">52 Week High</div>
                    <div class="ws-metric-val">{d['week52High']}</div>
                </div>
                <div class="ws-stat-tile">
                    <div class="ws-metric-label">52 Week Low</div>
                    <div class="ws-metric-val">{d['week52Low']}</div>
                </div>
                <div class="ws-stat-tile">
                    <div class="ws-metric-label">Trading Volume</div>
                    <div class="ws-metric-val">{d['volume']}</div>
                </div>
                <div class="ws-stat-tile">
                    <div class="ws-metric-label">Average Volume (3M)</div>
                    <div class="ws-metric-val">{d['avgVolume']}</div>
                </div>
                <div class="ws-stat-tile">
                    <div class="ws-metric-label">Primary Exchange</div>
                    <div class="ws-metric-val">{d['exchange']}</div>
                </div>
                <div class="ws-stat-tile">
                    <div class="ws-metric-label">Asset Classification</div>
                    <div class="ws-metric-val">Equity / TSX</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 6. Dividends & Financials Sections
    col_div, col_fin = st.columns(2)
    with col_div:
        st.markdown("### Dividends")
        div_badge = f'<span class="ws-badge ws-badge-green">Yield Active</span>' if d['divYieldVal'] > 0 else ''
        st.markdown(
            f"""
            <div class="ws-card">
                <div style="display: flex; flex-direction: column; gap: 14px;">
                    <div class="ws-stat-tile">
                        <div class="ws-metric-label">Annual Dividend Yield {div_badge}</div>
                        <div class="ws-metric-val" style="color: #0284c7;">{d['divYield']}</div>
                    </div>
                    <div class="ws-stat-tile">
                        <div class="ws-metric-label">Distribution Frequency</div>
                        <div class="ws-metric-val">{d['divFrequency']}</div>
                    </div>
                    <div class="ws-stat-tile">
                        <div class="ws-metric-label">Ex-Dividend Date</div>
                        <div class="ws-metric-val">{d['exDivDate']}</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col_fin:
        st.markdown("### Valuation & Financials")
        st.markdown(
            f"""
            <div class="ws-card">
                <div style="display: flex; flex-direction: column; gap: 14px;">
                    <div class="ws-stat-tile">
                        <div class="ws-metric-label">Total Market Capitalization</div>
                        <div class="ws-metric-val">{d['marketCap']}</div>
                    </div>
                    <div class="ws-stat-tile">
                        <div class="ws-metric-label">Shares Outstanding</div>
                        <div class="ws-metric-val">{d['sharesOut']}</div>
                    </div>
                    <div class="ws-stat-tile">
                        <div class="ws-metric-label">Price to Earnings (P/E Ratio)</div>
                        <div class="ws-metric-val">{d['peRatio']}</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # 7. About Company Profile
    st.markdown(f"### About {d['symbol']}")
    st.markdown(
        f"""
        <div class="ws-card">
            <p style="color: #334155; font-size: 0.96rem; line-height: 1.7; margin-bottom: 22px;">
                {d['summary']}
            </p>
            <div style="display: flex; flex-wrap: wrap; gap: 12px; padding-top: 16px; border-top: 1px solid #e2e8f0;">
                {"<a href='" + d['website'] + "' target='_blank' style='text-decoration:none;'><div class='ws-meta-pill' style='border-color:#0284c7; color:#0284c7;'>🔗 <b>Official Website</b></div></a>" if d['website'] else ""}
                <div class="ws-meta-pill">📍 Country: <b>{d['country']}</b></div>
                <div class="ws-meta-pill">🏢 Sector/Industry: <b>{d['industry']}</b></div>
                <div class="ws-meta-pill">👥 Employees: <b>{d['employees']}</b></div>
                <div class="ws-meta-pill">👤 Key Executive: <b>{d['officer']}</b></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

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
    active_ticker = st.query_params.get("ticker")
    if active_ticker:
        render_market_data_page(active_ticker)
        return

    df_raw, scan_time = load_screener_results()

    # 1. Exclude symbols the user explicitly removed
    if not df_raw.empty and st.session_state.removed_watchlist_symbols:
        df_raw = df_raw[~df_raw["Symbol"].isin(st.session_state.removed_watchlist_symbols)].reset_index(drop=True)

    # 2. Inject custom monitored tickers immediately so sidebar filters, counts, and tables stay synchronized
    if not df_raw.empty and st.session_state.custom_watchlist_symbols:
        new_rows = []
        existing_syms = set(df_raw["Symbol"].dropna().unique())
        for cust_sym in st.session_state.custom_watchlist_symbols:
            if cust_sym not in existing_syms and cust_sym not in st.session_state.removed_watchlist_symbols:
                t_data = calculate_on_demand_technicals(cust_sym)
                if t_data:
                    _, company_name = sanitize_and_resolve_ticker(cust_sym)
                    new_rows.append({
                        "Symbol": cust_sym,
                        "Company": company_name,
                        "Price": t_data["price"],
                        "Signal": t_data["signal"],
                        "RSI_14": t_data["rsi_14"],
                        "SMA_50": t_data["sma_50"],
                        "SMA_200": t_data["sma_200"],
                        "SMA_Trend": "Bullish" if t_data["sma_50"] > t_data["sma_200"] else "Bearish",
                        "Rationale": t_data["rationale"]
                    })
        if new_rows:
            df_raw = pd.concat([df_raw, pd.DataFrame(new_rows)], ignore_index=True)

    # 3. Sidebar Header, Autocomplete Lookup & Filters
    with st.sidebar:
        st.markdown(
            f"""
            <div style="display: inline-flex; align-items: center; gap: 6px; margin-bottom: 16px;">
                <h3 style="margin: 0; padding: 0; font-size: 1.45rem; font-weight: 800; color: {text_title}; line-height: 1;">TrendNorth 🇨🇦</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("🔄 Refresh Data Now", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")

        # Top Autocomplete Dropdown Search (Detail Market View)
        st.markdown("**📊 Open Market Data Details**")
        all_catalog_syms = sorted(list(set(list(EXTENDED_CATALOG.keys()) + st.session_state.custom_watchlist_symbols)))
        searchable_options = ["-- Type symbol or company name --"] + [
            f"{sym} — {sanitize_and_resolve_ticker(sym)[1]}" for sym in all_catalog_syms
        ]
        
        selected_stock_label = st.selectbox(
            "Search Ticker or Company",
            options=searchable_options,
            help="Type any symbol (e.g. AC, SHOP, AQN) or company name for suggestions.",
            label_visibility="collapsed"
        )
        if selected_stock_label != "-- Type symbol or company name --":
            target_sym = selected_stock_label.split(" — ")[0].strip()
            st.query_params["ticker"] = target_sym
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

        # Autocomplete Table Search with Dynamic Hints
        st.markdown("**Filter Watchlist Table**")
        active_table_symbols = sorted(list(set(df_raw["Symbol"].dropna().unique()))) if not df_raw.empty else []
        table_filter_options = ["-- All Assets (No Filter) --"] + [
            f"{s} — {sanitize_and_resolve_ticker(s)[1]}" for s in active_table_symbols
        ]

        current_sel = st.session_state.filter_search_select
        sel_idx = table_filter_options.index(current_sel) if current_sel in table_filter_options else 0

        selected_table_filter = st.selectbox(
            "Filter Watchlist Table",
            options=table_filter_options,
            index=sel_idx,
            help="Type any ticker or company name to filter the table.",
            label_visibility="collapsed",
            key="filter_search_select"
        )

        st.markdown("---")
        st.caption("ℹ️ **Educational / Non-Financial Advice Disclaimer**")
        st.caption("TrendNorth is an algorithmic research platform for TSX securities. All indicators and alerts are mathematical representations for self-directed screening and do not constitute financial advice.")

    # 4. Main Title & Session Clock Header
    status_label, status_detail, elapsed_time, time_to_close = get_tsx_market_status()
    scan_date_str = scan_time.strftime("%b %d, %Y — %I:%M %p ET") if scan_time else "Data Pending"
    today_et_str = datetime.now(ET_ZONE).strftime("%A, %B %d, %Y")
    now_time_et_str = datetime.now(ET_ZONE).strftime("%I:%M:%S %p ET")

    st.title("📈 TrendNorth 🇨🇦")
    st.markdown(
        f"""
        <div class="tn-meta-bar" style="margin-top: -12px; margin-bottom: 16px; display: flex; flex-wrap: wrap; gap: 8px;">
            <span>📅 <b>Date:</b> {today_et_str}</span>
            <span>⏰ <b>Live Clock:</b> {now_time_et_str}</span>
            <span>⚡ <b>Engine Scan Data:</b> {scan_date_str}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
    with col_stat1:
        st.metric(label="TSX Status", value=f"● {status_label}")
    with col_stat2:
        st.metric(label="Session Detail", value=status_detail)
    with col_stat3:
        st.metric(label="Counter (Elapsed)", value=elapsed_time)
    with col_stat4:
        st.metric(label="Time to Close", value=time_to_close)

    if df_raw.empty:
        st.warning("Waiting for scan data... Run the GitHub Actions workflow or execute `python ScreenStocksV1.py` locally.")
        return

    buy_all_cnt = len(df_raw[df_raw["Signal"] == "BUY / ACCUMULATE"])
    sell_all_cnt = len(df_raw[df_raw["Signal"] == "SELL / EXIT"])
    trim_all_cnt = len(df_raw[df_raw["Signal"] == "TRIM / TAKE PROFIT"])

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

    # Filter by selected autocomplete symbol
    if selected_table_filter != "-- All Assets (No Filter) --":
        filter_target_sym = selected_table_filter.split(" — ")[0].strip()
        filtered_df = filtered_df[filtered_df["Symbol"] == filter_target_sym]

    has_active_filters = (
        set(selected_signals) != set(available_signals)
        or rsi_range != (0.0, 100.0)
        or sma_trend != "All Trends"
        or selected_table_filter != "-- All Assets (No Filter) --"
    )

    # 5. Interactive Embedded Metric Cards (4 Columns)
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

    # 6. Main Content Tabs
    tab_data, tab_pocket, tab_charts, tab_manual = st.tabs(
        ["📋 Filtered Watchlist", "💼 Pocket Trader", "📊 Market Technicals", "📖 User Manual"]
    )

    # -------------------------------------------------------------------------
    # TAB 1: Filtered Watchlist (Light Minimalist)
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
                if "BUY" in str(val):
                    return "color: #15803d; background-color: rgba(34, 197, 94, 0.14); font-weight: 700; border-radius: 4px;"
                elif "SELL" in str(val):
                    return "color: #b91c1c; background-color: rgba(239, 68, 68, 0.14); font-weight: 700; border-radius: 4px;"
                elif "TRIM" in str(val):
                    return "color: #b45309; background-color: rgba(245, 158, 11, 0.14); font-weight: 700; border-radius: 4px;"
                return "color: #475569;"

            display_df = filtered_df.copy()
            display_df["Asset"] = display_df.apply(
                lambda r: f"{r['Symbol']}  •  {r['Company']} 📊" if pd.notna(r.get("Company")) and r["Company"] != "—" else f"{r['Symbol']} 📊",
                axis=1
            )

            columns_order = [
                "Asset", "Price", "Signal", "RSI_14", "SMA_50", "SMA_200", "Rationale"
            ]
            display_cols = [c for c in columns_order if c in display_df.columns]

            styled_df = (
                display_df[display_cols]
                .style.format({
                    "Price": "${:.2f}",
                    "SMA_50": "${:.2f}",
                    "SMA_200": "${:.2f}",
                    "RSI_14": "{:.1f}",
                })
                .map(signal_styler, subset=["Signal"])
            )

            st.markdown(
                '<div class="tn-table-hint">💡 <b>Click any row</b> to open its TradingView interactive charts, valuation metrics, and technical profile.</div>',
                unsafe_allow_html=True
            )

            event = st.dataframe(
                styled_df,
                column_config={
                    "Asset": st.column_config.TextColumn(
                        "Asset & Security",
                        help="Select any asset to load institutional financial charts and profile",
                        width="large",
                    ),
                    "Price": st.column_config.NumberColumn(
                        "Price (CAD)",
                        format="$%.2f",
                        width="small",
                    ),
                    "Signal": st.column_config.TextColumn(
                        "Signal",
                        width="medium",
                    ),
                    "RSI_14": st.column_config.NumberColumn(
                        "RSI (14D)",
                        format="%.1f",
                        width="small",
                    ),
                    "SMA_50": st.column_config.NumberColumn(
                        "50D SMA",
                        format="$%.2f",
                        width="small",
                    ),
                    "SMA_200": st.column_config.NumberColumn(
                        "200D SMA",
                        format="$%.2f",
                        width="small",
                    ),
                    "Rationale": st.column_config.TextColumn(
                        "Signal Rationale",
                        width="large",
                    ),
                },
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                key="watchlist_table_selection",
            )

            if hasattr(event, "selection") and event.selection and event.selection.rows:
                selected_row_idx = event.selection.rows[0]
                clicked_symbol = filtered_df.iloc[selected_row_idx]["Symbol"]
                st.query_params["ticker"] = clicked_symbol
                st.rerun()

            st.download_button(
                label="📥 Export Filtered Watchlist (CSV)",
                data=filtered_df.to_csv(index=False).encode("utf-8"),
                file_name=f"trendnorth_watchlist_{datetime.now(ET_ZONE).strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )

    # -------------------------------------------------------------------------
    # TAB 2: Pocket Trader (TN-007 Dynamic Tracking)
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

        with st.expander("➕ Add Position to Pocket Trader", expanded=False):
            all_known = sorted(list(set(list(EXTENDED_CATALOG.keys()) + list(df_raw["Symbol"].dropna().unique()) + st.session_state.custom_watchlist_symbols)))
            catalog_options = ["-- Select or Type Any Symbol --"] + [
                f"{s} — {sanitize_and_resolve_ticker(s)[1]}" for s in all_known
            ]

            col_sym, col_dt = st.columns([3, 2])
            with col_sym:
                chosen_pick = st.selectbox(
                    "Select Asset from Catalog",
                    options=catalog_options,
                    index=0,
                    help="Start typing a symbol (e.g. AC, SHOP, AQN) or company name."
                )
            with col_dt:
                custom_date = st.date_input("Entry Date", value=date.today(), key="unified_entry_date")

            selected_sym = ""
            if chosen_pick != "-- Select or Type Any Symbol --":
                selected_sym = chosen_pick.split(" — ")[0].strip()

            raw_input_sym = st.text_input(
                "Or enter custom ticker symbol if not listed above:",
                value=selected_sym,
                placeholder="e.g. AQN.TO, CSU.TO, AAPL"
            ).strip().upper()

            default_p = 10.00
            final_sym = ""
            if raw_input_sym:
                final_sym, comp_name = sanitize_and_resolve_ticker(raw_input_sym)
                if not df_raw.empty:
                    m = df_raw[df_raw["Symbol"] == final_sym]
                    if not m.empty and pd.notna(m["Price"].iloc[0]):
                        default_p = float(m["Price"].iloc[0])
                if default_p == 10.00:
                    t_data = calculate_on_demand_technicals(final_sym)
                    if t_data and t_data.get("price"):
                        default_p = float(t_data["price"])

            col_p, col_sh, col_tg = st.columns(3)
            with col_p:
                custom_price = st.number_input(
                    "Purchase Price (CAD)",
                    min_value=0.01,
                    value=round(default_p, 2),
                    step=0.5,
                    key="unified_entry_price"
                )
            with col_sh:
                custom_shares = st.number_input(
                    "Shares Count",
                    min_value=1,
                    value=10,
                    step=1,
                    key="unified_entry_shares"
                )
            with col_tg:
                custom_gain = st.number_input(
                    "Target Gain ($/sh)",
                    min_value=0.1,
                    value=5.0,
                    step=0.5,
                    key="unified_entry_gain"
                )

            if st.button("➕ Add Position to Pocket Trader", type="primary", use_container_width=True):
                if final_sym:
                    cand = {
                        "Symbol": final_sym,
                        "Buy Date": str(custom_date),
                        "Buy Price": float(custom_price),
                        "Shares": int(custom_shares),
                        "Target Gain": float(custom_gain),
                    }
                    if not is_exact_duplicate(st.session_state.pocket_positions, cand):
                        st.session_state.pocket_positions.append(cand)
                        sync_pocket_to_storage()
                        st.toast(f"✅ Added {final_sym} to your Pocket Trader!")
                        st.rerun()
                    else:
                        st.warning("This exact position is already logged.")
                else:
                    st.error("Please select or enter a valid ticker symbol.")

        if not st.session_state.pocket_positions:
            st.info("No active positions tracked in Pocket Trader yet. Add any TSX/US stock using the form above or upload a CSV below.")
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

                matched_in_batch = False
                if not df_raw.empty:
                    match = df_raw[df_raw["Symbol"] == sym]
                    if not match.empty:
                        cur_price = float(match["Price"].iloc[0])
                        sig = str(match["Signal"].iloc[0])
                        rsi = float(match["RSI_14"].iloc[0])
                        matched_in_batch = True

                if not matched_in_batch:
                    tech = calculate_on_demand_technicals(sym)
                    if tech:
                        cur_price = tech["price"]
                        sig = tech["signal"]
                        rsi = tech["rsi_14"]

                cost_basis = buy_p * shares
                market_val = cur_price * shares
                unrealized_pl = market_val - cost_basis
                unrealized_pct = ((cur_price - buy_p) / buy_p * 100.0) if buy_p > 0 else 0.0
                target_price = buy_p + tgt_gain
                target_reached = cur_price >= target_price

                _, comp_name = sanitize_and_resolve_ticker(sym)
                calc_rows.append({
                    "Index": i,
                    "Symbol": sym,
                    "Company": comp_name,
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
                                    skipped_duplicates = 0

                                    for _, row in imp_df.iterrows():
                                        raw_sym = str(row["Symbol"]).strip().upper()
                                        clean_sym, _ = sanitize_and_resolve_ticker(raw_sym)
                                        cand = {
                                            "Symbol": clean_sym,
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

                                    st.session_state.last_processed_file_id = file_sig
                                    sync_pocket_to_storage()

                                    msg = f"Import complete: {merged_count} position(s) added."
                                    if skipped_duplicates:
                                        msg += f" {skipped_duplicates} duplicate(s) skipped."
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
                        "BUY / ACCUMULATE": "#16a34a",
                        "SELL / EXIT": "#dc2626",
                        "TRIM / TAKE PROFIT": "#d97706",
                        "KEEP / HOLD": "#64748b",
                    },
                    template=plotly_tpl,
                )
                fig_rsi.add_vline(x=40, line_dash="dot", line_color="#16a34a", annotation_text="Pullback (<=40)")
                fig_rsi.add_vline(x=75, line_dash="dot", line_color="#dc2626", annotation_text="Overbought (>=75)")
                fig_rsi.update_layout(
                    paper_bgcolor="#ffffff",
                    plot_bgcolor="#ffffff",
                    xaxis_title="14-Day RSI",
                    yaxis_title="Equities Count",
                    height=420
                )
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
                        "BUY / ACCUMULATE": "#16a34a",
                        "SELL / EXIT": "#dc2626",
                        "TRIM / TAKE PROFIT": "#d97706",
                        "KEEP / HOLD": "#64748b",
                    },
                    template=plotly_tpl,
                )
                fig_scatter.update_layout(
                    paper_bgcolor="#ffffff",
                    plot_bgcolor="#ffffff",
                    xaxis_title="50-Day SMA (CAD)",
                    yaxis_title="Current Price (CAD)",
                    height=420
                )
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
- **On-Demand & Batch Logging:** Track any TSX or US ticker on demand with custom entry date and target price.
- **Target Gain Tracking:** Specify your profit objective (e.g., $10/share). The status badge dynamically turns into **🎯 TARGET REACHED** when prices cross above.
- **Quick Editing:** Use the *Quick Edit Existing Position* drawer to update shares, entry date, buy price, or target price at any time.
- **Privacy-First Storage:** Positions persist in browser local storage and can be exported or merged anytime via CSV files.
                """
            )

        with st.expander("4. Precision Cloud Scheduling (TN-001)", expanded=False):
            st.markdown(
                """
- **Morning Dip Scan (10:32 AM ET):** Webhook trigger executes 62 minutes into regular session to identify early intraday oversold pullbacks.
- **Market Close Scan (4:47 PM ET):** Webhook trigger executes 47 minutes post-close once official daily closing prints and settlements are finalized.
                """
            )

    # -------------------------------------------------------------------------
    # Floating Feedback Popover
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