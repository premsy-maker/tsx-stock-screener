import json
import os
import re
import time
from datetime import date, datetime, time as dtime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
import plotly.express as px
import streamlit as st

# Optional Browser LocalStorage integration
try:
    from streamlit_local_storage import LocalStorage
    localS = LocalStorage()
except Exception:
    localS = None

# Import feedback sender from notifier
try:
    from notifierV1 import send_feedback_email
except ImportError:
    def send_feedback_email(sender_name: str, sender_email: str, sentiment: str, message: str) -> bool:
        return False

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
    initial_sidebar_state="expanded"
)

# Global CSS for Floating Feedback Button & Upload Button Alignment
st.markdown(
    """
    <style>
    /* Floating Feedback Popover in bottom-right */
    div[data-testid="stPopover"] {
        position: fixed;
        bottom: 24px;
        right: 24px;
        z-index: 999999;
    }
    div[data-testid="stPopover"] > button {
        background-color: #0f172a;
        color: #ffffff;
        border-radius: 24px;
        padding: 8px 18px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
        border: 1px solid rgba(255, 255, 255, 0.15);
        font-weight: 600;
    }
    div[data-testid="stPopover"] > button:hover {
        background-color: #1e293b;
        color: #ffffff;
        border-color: #38bdf8;
    }

    /* Clean height & label suppression for aligned file uploader */
    div[data-testid="stFileUploader"] > section {
        padding: 4px 12px !important;
        min-height: 42px !important;
        border-radius: 6px !important;
    }
    div[data-testid="stFileUploader"] section small {
        display: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Core Watchlist Company Names Mapping (59 TSX Assets)
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
    "K.TO": "Kinross Gold"
}

# -----------------------------------------------------------------------------
# TSX Market Status & Holiday Calculation Helper
# -----------------------------------------------------------------------------
def get_tsx_market_status(now_et: datetime):
    today = now_et.date()
    year = today.year

    def get_nth_weekday_of_month(yr, mo, weekday, n):
        first_day = date(yr, mo, 1)
        day_diff = (weekday - first_day.weekday()) % 7
        return first_day + timedelta(days=day_diff + (n - 1) * 7)

    # Good Friday calculation
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

    holidays = {
        date(year, 1, 1): "New Year's Day",
        get_nth_weekday_of_month(year, 2, 0, 3): "Family Day",
        good_friday: "Good Friday",
        date(year, 5, 24) - timedelta(days=(date(year, 5, 24).weekday())): "Victoria Day",
        date(year, 7, 1): "Canada Day",
        get_nth_weekday_of_month(year, 8, 0, 1): "Civic Holiday",
        get_nth_weekday_of_month(year, 9, 0, 1): "Labour Day",
        date(year, 9, 30): "National Day for Truth and Reconciliation",
        get_nth_weekday_of_month(year, 10, 0, 2): "Thanksgiving",
        date(year, 12, 25): "Christmas Day",
        date(year, 12, 26): "Boxing Day"
    }

    observed_holidays = {}
    for hol_date, name in holidays.items():
        if hol_date.weekday() == 5:
            observed_holidays[hol_date + timedelta(days=2)] = f"{name} (Observed)"
        elif hol_date.weekday() == 6:
            observed_holidays[hol_date + timedelta(days=1)] = f"{name} (Observed)"
        else:
            observed_holidays[hol_date] = name

    if today.weekday() >= 5:
        return ("CLOSED", "#ef4444", "00:00:00", "--:--:--", "Weekend")

    if today in observed_holidays:
        return ("CLOSED", "#ef4444", "00:00:00", "--:--:--", observed_holidays[today])

    market_open = dtime(9, 30, 0)
    market_close = dtime(16, 0, 0)
    current_time = now_et.time()

    if market_open <= current_time < market_close:
        open_dt = datetime.combine(today, market_open, tzinfo=ET_ZONE)
        close_dt = datetime.combine(today, market_close, tzinfo=ET_ZONE)

        elapsed_secs = int((now_et - open_dt).total_seconds())
        rem_secs = int((close_dt - now_et).total_seconds())

        e_hrs, e_mins, e_secs = elapsed_secs // 3600, (elapsed_secs % 3600) // 60, elapsed_secs % 60
        r_hrs, r_mins, r_secs = rem_secs // 3600, (rem_secs % 3600) // 60, rem_secs % 60

        return ("OPEN", "#16a34a", f"{e_hrs:02d}:{e_mins:02d}:{e_secs:02d}", f"{r_hrs:02d}:{r_mins:02d}:{r_secs:02d}", None)
    else:
        return ("CLOSED", "#ef4444", "00:00:00", "--:--:--", "Outside Regular Hours")

# -----------------------------------------------------------------------------
# Data Loader (Cache-Busting Remote GitHub 'data' Branch + Local Fallback)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=60)
def load_screener_results():
    df = None
    mod_time = None

    # Append a cache-buster query parameter to force GitHub's CDN to return the latest commit
    cache_buster_url = f"{DATA_BRANCH_URL}?nocache={int(time.time())}"

    # 1. Primary: Fetch fresh CSV from remote 'data' branch
    try:
        df = pd.read_csv(cache_buster_url)
        mod_time = datetime.now(ET_ZONE)
    except Exception:
        try:
            df = pd.read_csv(DATA_BRANCH_URL)
            mod_time = datetime.now(ET_ZONE)
        except Exception:
            pass

    # 2. Secondary: Fallback to local file only if remote is unreachable
    if df is None and os.path.exists(LOCAL_CSV_FILE):
        try:
            raw_mtime = os.path.getmtime(LOCAL_CSV_FILE)
            mod_time = datetime.fromtimestamp(raw_mtime, tz=ZoneInfo("UTC")).astimezone(ET_ZONE)
            df = pd.read_csv(LOCAL_CSV_FILE)
        except Exception:
            pass

    if df is None:
        return pd.DataFrame(), None

    try:
        # Standardize Symbol & Company columns
        if "Symbol" not in df.columns and "Ticker" in df.columns:
            df.rename(columns={"Ticker": "Symbol"}, inplace=True)

        if "Company" not in df.columns and "Symbol" in df.columns:
            df["Company"] = df["Symbol"].map(lambda s: COMPANY_NAMES.get(str(s).strip(), "—"))

        # If the CSV has an embedded Scan_Date or Timestamp column, prioritize that
        for date_col_candidate in ["Scan_Date", "Scan Date", "Date", "Scan_Timestamp", "Timestamp"]:
            if date_col_candidate in df.columns:
                try:
                    first_val = str(df[date_col_candidate].dropna().iloc[0]).strip()
                    parsed_dt = pd.to_datetime(first_val)
                    if parsed_dt.tzinfo is None:
                        mod_time = parsed_dt.replace(tzinfo=ET_ZONE)
                    else:
                        mod_time = parsed_dt.astimezone(ET_ZONE)
                    break
                except Exception:
                    pass

        # Clean numerical currency/metrics columns
        for col in ["Price", "RSI_14", "SMA_50", "SMA_200"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace("$", "", regex=False).str.replace(",", "", regex=False).str.strip()
                df[col] = pd.to_numeric(df[col], errors="coerce")

        return df, mod_time
    except Exception as e:
        st.error(f"Error processing screener data: {e}")
        return pd.DataFrame(), None

# -----------------------------------------------------------------------------
# Pocket Trader Session State Initialization & LocalStorage Hydration
# -----------------------------------------------------------------------------
STORAGE_KEY = "tn_pocket_positions_v1"

if "pocket_positions" not in st.session_state:
    st.session_state.pocket_positions = []

# Hydrate from LocalStorage on initial load if session state is empty
if localS is not None and not st.session_state.pocket_positions:
    try:
        saved_raw = localS.getItem(STORAGE_KEY)
        if saved_raw:
            if isinstance(saved_raw, str):
                saved_list = json.loads(saved_raw)
            elif isinstance(saved_raw, list):
                saved_list = saved_raw
            else:
                saved_list = []
            if isinstance(saved_list, list) and saved_list:
                st.session_state.pocket_positions = saved_list
    except Exception:
        pass

def save_to_browser_storage():
    """Helper to sync session positions into client-side browser storage."""
    if localS is not None:
        try:
            localS.setItem(STORAGE_KEY, json.dumps(st.session_state.pocket_positions))
        except Exception:
            pass

# -----------------------------------------------------------------------------
# Sidebar: Controls & Branding
# -----------------------------------------------------------------------------
st.sidebar.markdown(
    """<div style="display: flex; align-items: center; gap: 6px; margin-bottom: 12px;">
<span style="font-size: 1.6rem; font-weight: 800; color: #0f172a; letter-spacing: -0.5px;">TrendNorth</span>
<img src="https://flagcdn.com/w80/ca.png" width="30" height="15" 
     alt="Canada" 
     style="border-radius: 2px; vertical-align: middle; box-shadow: 0 1px 3px rgba(0,0,0,0.3); display: inline-block;">
</div>""",
    unsafe_allow_html=True
)

if st.sidebar.button("🔄 Refresh Data Now", help="Clear memory cache and reload CSV"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Screener Filters")

selected_signals = st.sidebar.multiselect(
    "Signal Classification",
    options=["BUY / ACCUMULATE", "SELL / EXIT", "TRIM / TAKE PROFIT", "KEEP / HOLD"],
    default=["BUY / ACCUMULATE", "SELL / EXIT", "TRIM / TAKE PROFIT"]
)

rsi_min, rsi_max = st.sidebar.slider(
    "14-Day RSI Window",
    min_value=0.0,
    max_value=100.0,
    value=(0.0, 100.0),
    step=1.0
)

trend_filter = st.sidebar.radio(
    "SMA Trend Configuration",
    options=["All Trends", "Bullish (SMA 50 > SMA 200)", "Bearish / Death Cross (SMA 50 < SMA 200)"],
    index=0
)

search_term = st.sidebar.text_input("Find Symbol or Company", "").strip().upper()

st.sidebar.markdown("---")
st.sidebar.caption("**Disclaimer:** For educational & informational analysis only. Not financial advice.")

# -----------------------------------------------------------------------------
# Main Dashboard
# -----------------------------------------------------------------------------
def render_dashboard():
    df_raw, scan_time = load_screener_results()

    if df_raw is None or df_raw.empty:
        st.warning("Waiting for scan data... Run `python ScreenStocksV1.py` locally or trigger the GitHub Actions workflow.")
        return

    df = df_raw.copy()

    # Main Header with Tight Canadian Flag Alignment
    header_html = """<div style="display: flex; align-items: center; gap: 8px; margin-bottom: 2px;">
<span style="font-size: 2.25rem; font-weight: 800; color: #0f172a; letter-spacing: -0.6px; line-height: 1.1;">📈 TrendNorth</span>
<img src="https://flagcdn.com/w80/ca.png" 
     width="36" 
     height="18" 
     alt="Canada Flag" 
     style="border-radius: 3px; box-shadow: 0 1px 4px rgba(0,0,0,0.28); display: inline-block; margin-top: 2px;">
</div>"""
    st.markdown(header_html, unsafe_allow_html=True)

    now_et = datetime.now(ET_ZONE)
    today_display = now_et.strftime("%A, %B %d, %Y")
    last_refreshed_time = now_et.strftime("%I:%M:%S %p ET")
    scan_timestamp_str = scan_time.strftime("%b %d, %Y — %I:%M %p ET") if scan_time else "Awaiting scan"

    tsx_status, status_color, session_counter, remaining_counter, holiday_reason = get_tsx_market_status(now_et)
    reason_badge = f"&nbsp;<span style='font-size: 11px; color: #94a3b8; font-weight: 400;'>({holiday_reason})</span>" if holiday_reason else ""

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

    # Filter Watchlist
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

    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Watchlist Displayed", f"{len(filtered_df)} / {len(df)}")
    col2.metric("🟢 Buy / Accumulate", len(df[df["Signal"] == "BUY / ACCUMULATE"]))
    col3.metric("🔴 Sell / Exit", len(df[df["Signal"] == "SELL / EXIT"]))
    col4.metric("🟡 Trim / Profit", len(df[df["Signal"] == "TRIM / TAKE PROFIT"]))

    # Ordered Tabs
    tab_data, tab_pocket, tab_charts, tab_manual = st.tabs(
        ["📋 Filtered Watchlist", "💼 Pocket Trader", "📊 Market Technicals", "📖 User Manual"]
    )

    # -------------------------------------------------------------------------
    # TAB 1: Filtered Watchlist
    # -------------------------------------------------------------------------
    with tab_data:
        if filtered_df.empty:
            st.info("No assets match your current filters. Adjust your filters in the sidebar.")
        else:
            def signal_styler(val):
                if "BUY" in str(val):
                    return "color: #1b5e20; background-color: #e8f5e9; font-weight: bold;"
                elif "SELL" in str(val):
                    return "color: #b71c1c; background-color: #ffebee; font-weight: bold;"
                elif "TRIM" in str(val):
                    return "color: #b45309; background-color: #fef3c7; font-weight: bold;"
                return "color: #475569;"

            columns_order = ["Symbol", "Company", "Price", "Signal", "RSI_14", "SMA_50", "SMA_200", "Rationale"]
            display_cols = [c for c in columns_order if c in filtered_df.columns]

            styled_df = (
                filtered_df[display_cols]
                .style
                .format({
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
                mime="text/csv"
            )

    # -------------------------------------------------------------------------
    # TAB 2: Pocket Trader (Two-Column Compact Header with Auto-Save Notice)
    # -------------------------------------------------------------------------
    with tab_pocket:
        hdr_col, notice_col = st.columns([3, 2])

        with hdr_col:
            st.subheader("💼 Pocket Trader — Portfolio & Target Tracker")
            st.caption("Track retrospective purchases or manage forward-looking profit targets against live TSX scans.")

        with notice_col:
            st.markdown(
                """
                <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-left: 4px solid #3b82f6; 
                            padding: 8px 12px; border-radius: 6px; font-size: 11.5px; line-height: 1.45; color: #475569; margin-top: 4px;">
                    <div style="font-weight: 700; color: #0f172a; margin-bottom: 2px;">💾 Browser Auto-Save Active</div>
                    Positions save to this browser. <b>Data clears if:</b> cookies/site data are wiped, incognito is used, or you switch devices.
                    <div style="margin-top: 3px; color: #0369a1; font-weight: 500;">👉 Export CSV periodically for offline backup.</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        all_symbols = sorted(df["Symbol"].dropna().unique().tolist())

        # Exact duplicate detection helper (Checks all 5 purchase fields)
        def is_exact_duplicate(existing_list, candidate):
            return any(
                pos["Symbol"] == candidate["Symbol"] and
                str(pos["Buy Date"]) == str(candidate["Buy Date"]) and
                abs(float(pos["Buy Price"]) - float(candidate["Buy Price"])) < 0.001 and
                int(pos["Shares"]) == int(candidate["Shares"]) and
                abs(float(pos["Target Gain"]) - float(candidate["Target Gain"])) < 0.001
                for pos in existing_list
            )

        # 1. Multi-Symbol Batch Entry Form
        with st.expander("➕ Log Single or Multiple Positions (Batch Setup)", expanded=False):
            st.markdown("**Step 1:** Select one or multiple TSX symbols to add:")
            chosen_symbols = st.multiselect(
                "Choose Symbol(s)",
                options=all_symbols,
                default=[],
                placeholder="Search or pick symbols (e.g. BAM.TO, SHOP.TO, RY.TO)..."
            )

            if chosen_symbols:
                st.markdown("**Step 2:** Customize entry parameters for your chosen symbols below:")
                today_val = datetime.now(ET_ZONE).date()

                draft_rows = []
                for s in chosen_symbols:
                    p_match = df.loc[df["Symbol"] == s, "Price"].values
                    live_p = float(p_match[0]) if len(p_match) > 0 and pd.notna(p_match[0]) else 100.0
                    draft_rows.append({
                        "Symbol": s,
                        "Purchase Date": today_val,
                        "Purchase Price (CAD)": round(live_p, 2),
                        "Shares": 10,
                        "Target Profit / Share (CAD)": 10.00
                    })

                draft_df = pd.DataFrame(draft_rows)

                edited_df = st.data_editor(
                    draft_df,
                    column_config={
                        "Symbol": st.column_config.TextColumn(disabled=True),
                        "Purchase Date": st.column_config.DateColumn(format="YYYY-MM-DD", required=True),
                        "Purchase Price (CAD)": st.column_config.NumberColumn(min_value=0.01, format="$%.2f", step=0.50),
                        "Shares": st.column_config.NumberColumn(min_value=1, step=1),
                        "Target Profit / Share (CAD)": st.column_config.NumberColumn(min_value=0.10, format="$%.2f", step=0.50),
                    },
                    use_container_width=True,
                    hide_index=True,
                    key="batch_data_editor"
                )

                if st.button(f"➕ Add All ({len(chosen_symbols)}) Positions to Pocket Trader", type="primary"):
                    added_count = 0
                    duplicate_items = []

                    for _, r in edited_df.iterrows():
                        candidate = {
                            "Symbol": str(r["Symbol"]),
                            "Buy Date": str(r["Purchase Date"]),
                            "Buy Price": float(r["Purchase Price (CAD)"]),
                            "Shares": int(r["Shares"]),
                            "Target Gain": float(r["Target Profit / Share (CAD)"]),
                            "Horizon Days": 60
                        }

                        if is_exact_duplicate(st.session_state.pocket_positions, candidate):
                            duplicate_items.append(f"{candidate['Symbol']} ({candidate['Buy Date']} @ ${candidate['Buy Price']:.2f})")
                        else:
                            st.session_state.pocket_positions.append(candidate)
                            added_count += 1

                    if added_count > 0:
                        save_to_browser_storage()
                        st.success(f"✅ Added {added_count} position(s) to Pocket Trader!")
                    if duplicate_items:
                        st.warning(f"⚠️ Skipped {len(duplicate_items)} duplicate position(s) already in portfolio: {', '.join(duplicate_items)}")

                    if added_count > 0:
                        st.rerun()

        # 2. Portfolio Calculations & Valuation
        has_positions = bool(st.session_state.pocket_positions)

        if not has_positions:
            st.info("Pocket Trader is currently empty. Use the '➕ Log Single or Multiple Positions' section above to add stocks, or upload an existing CSV below.")
            port_df = pd.DataFrame()
        else:
            portfolio_rows = []
            today_date = datetime.now(ET_ZONE).date()

            for idx, pos in enumerate(st.session_state.pocket_positions):
                sym = pos["Symbol"]
                buy_price = pos["Buy Price"]
                shares = pos["Shares"]
                target_gain = pos["Target Gain"]
                target_price = buy_price + target_gain

                try:
                    b_date = datetime.strptime(str(pos["Buy Date"]), "%Y-%m-%d").date()
                    days_held = (today_date - b_date).days
                except Exception:
                    days_held = 0

                match = df[df["Symbol"] == sym]
                if not match.empty:
                    curr_price = match["Price"].values[0]
                    curr_signal = match["Signal"].values[0]
                    comp_name = match["Company"].values[0] if "Company" in match.columns else COMPANY_NAMES.get(sym, "—")
                else:
                    curr_price = buy_price
                    curr_signal = "DATA PENDING"
                    comp_name = COMPANY_NAMES.get(sym, "—")

                dollar_pnl = (curr_price - buy_price) * shares
                pct_pnl = ((curr_price - buy_price) / buy_price) * 100 if buy_price > 0 else 0.0
                total_val = curr_price * shares

                if curr_price >= target_price:
                    status_badge = "🎯 TARGET REACHED"
                else:
                    progress_pct = max(0.0, min(100.0, ((curr_price - buy_price) / target_gain) * 100))
                    status_badge = f"⏳ {progress_pct:.0f}% to Target"

                portfolio_rows.append({
                    "_internal_id": idx,
                    "Symbol": sym,
                    "Company": comp_name,
                    "Shares": shares,
                    "Buy Date": pos["Buy Date"],
                    "Days Held": days_held,
                    "Buy Price": buy_price,
                    "Current Price": curr_price,
                    "Target Price": target_price,
                    "Net P&L ($)": dollar_pnl,
                    "Net P&L (%)": pct_pnl,
                    "Total Value": total_val,
                    "Target Status": status_badge,
                    "TrendNorth Signal": curr_signal
                })

            port_df = pd.DataFrame(portfolio_rows)

            # Portfolio Summary KPI Row
            p_col1, p_col2, p_col3, p_col4 = st.columns(4)
            total_invested = sum(r["Buy Price"] * r["Shares"] for r in portfolio_rows)
            total_current = sum(r["Total Value"] for r in portfolio_rows)
            total_dollar_pnl = total_current - total_invested
            total_pct_pnl = (total_dollar_pnl / total_invested * 100) if total_invested > 0 else 0.0
            targets_hit = sum(1 for r in portfolio_rows if "TARGET REACHED" in r["Target Status"])

            p_col1.metric("Total Portfolio Value", f"${total_current:,.2f}")
            p_col2.metric("Total Unrealized P&L ($)", f"${total_dollar_pnl:,.2f}", delta=f"{total_dollar_pnl:,.2f}")
            p_col3.metric("Total Return (%)", f"{total_pct_pnl:.2f}%", delta=f"{total_pct_pnl:.2f}%")
            p_col4.metric("Targets Achieved", f"{targets_hit} / {len(portfolio_rows)}")

            st.markdown("---")

            # -----------------------------------------------------------------
            # 3. Interactive Multi-Select Position Table (Rich Formatted View)
            # -----------------------------------------------------------------
            st.markdown("##### Active Holdings & Target Tracking")
            st.caption("💡 *Select row checkboxes on the left to remove positions. Use the **✏️ Quick Edit** tool below to modify values.*")

            display_cols = [
                "Symbol", "Company", "Shares", "Buy Date", "Days Held",
                "Buy Price", "Current Price", "Target Price",
                "Net P&L ($)", "Net P&L (%)", "Target Status", "TrendNorth Signal"
            ]

            def pocket_styler(val):
                if "TARGET REACHED" in str(val) or "BUY" in str(val):
                    return "color: #16a34a; font-weight: bold;"
                elif "SELL" in str(val) or ("-" in str(val) and "$" in str(val)):
                    return "color: #dc2626; font-weight: bold;"
                elif "TRIM" in str(val):
                    return "color: #d97706; font-weight: bold;"
                return ""

            styled_port = (
                port_df[display_cols]
                .style
                .format({
                    "Buy Price": "${:.2f}",
                    "Current Price": "${:.2f}",
                    "Target Price": "${:.2f}",
                    "Net P&L ($)": "${:+.2f}",
                    "Net P&L (%)": "{:+.2f}%",
                    "Days Held": "{:d} d",
                })
                .map(pocket_styler, subset=["Net P&L ($)", "Net P&L (%)", "Target Status", "TrendNorth Signal"])
            )

            selection_event = st.dataframe(
                styled_port,
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="multi-row"
            )

            selected_row_indices = selection_event.selection.get("rows", [])

            # Contextual Bulk Action Bar (if rows selected)
            if selected_row_indices:
                b_col1, b_col2, _ = st.columns([2, 1, 3])
                with b_col1:
                    if st.button(f"🗑️ Remove ({len(selected_row_indices)}) Selected Position(s)", type="primary"):
                        for r_idx in sorted(selected_row_indices, reverse=True):
                            st.session_state.pocket_positions.pop(r_idx)
                        save_to_browser_storage()
                        st.success(f"Removed {len(selected_row_indices)} position(s).")
                        st.rerun()
                with b_col2:
                    if st.button("✕ Deselect All"):
                        st.rerun()

            # -----------------------------------------------------------------
            # 4. Quick Edit Drawer for Strategy & Corrections
            # -----------------------------------------------------------------
            with st.expander("✏️ Quick Edit Existing Position", expanded=False):
                st.caption("Safely modify shares, buy price, purchase date, or profit targets without removing the position.")

                edit_options = [
                    f"{r['_internal_id']}: {r['Symbol']} ({r['Company']}) — Bought: {r['Buy Date']} (${r['Buy Price']:.2f})"
                    for r in portfolio_rows
                ]

                chosen_edit_label = st.selectbox("Select position to edit:", options=edit_options, key="edit_pos_select")
                selected_pos_id = int(chosen_edit_label.split(":")[0])
                current_edit_pos = st.session_state.pocket_positions[selected_pos_id]

                try:
                    cur_bdate = datetime.strptime(str(current_edit_pos["Buy Date"]), "%Y-%m-%d").date()
                except Exception:
                    cur_bdate = today_date

                ec1, ec2, ec3, ec4 = st.columns(4)
                with ec1:
                    edit_shares = st.number_input("Shares", min_value=1, value=int(current_edit_pos["Shares"]), step=1, key="e_shares")
                with ec2:
                    edit_bdate = st.date_input("Buy Date", value=cur_bdate, key="e_bdate")
                with ec3:
                    edit_bprice = st.number_input("Buy Price (CAD)", min_value=0.01, value=float(current_edit_pos["Buy Price"]), step=0.50, format="%.2f", key="e_bprice")
                with ec4:
                    cur_target_price = float(current_edit_pos["Buy Price"]) + float(current_edit_pos["Target Gain"])
                    edit_tprice = st.number_input("Target Price (CAD)", min_value=0.01, value=cur_target_price, step=0.50, format="%.2f", key="e_tprice")

                if st.button(f"💾 Save Changes to {current_edit_pos['Symbol']}", type="primary"):
                    st.session_state.pocket_positions[selected_pos_id]["Shares"] = int(edit_shares)
                    st.session_state.pocket_positions[selected_pos_id]["Buy Date"] = str(edit_bdate)
                    st.session_state.pocket_positions[selected_pos_id]["Buy Price"] = float(edit_bprice)
                    st.session_state.pocket_positions[selected_pos_id]["Target Gain"] = max(0.10, float(edit_tprice) - float(edit_bprice))
                    save_to_browser_storage()
                    st.success(f"Updated position details for {current_edit_pos['Symbol']}!")
                    st.rerun()

        # ---------------------------------------------------------------------
        # 5. Portfolio Backup & Restore (Always Visible & Merging)
        # ---------------------------------------------------------------------
        st.markdown("---")
        st.markdown("##### 📁 Portfolio Backup & Restore")
        st.caption("Import a CSV backup to merge into your tracker, or export your full portfolio to a local CSV file.")

        c_exp, c_imp = st.columns(2)

        with c_exp:
            if has_positions and not port_df.empty:
                export_csv = port_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "📥 Export Portfolio (CSV)",
                    data=export_csv,
                    file_name="pocket_trader_portfolio.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.button("📥 Export Portfolio (CSV)", disabled=True, use_container_width=True, help="Add or import positions first to export.")

        with c_imp:
            uploaded_portfolio = st.file_uploader(
                "Upload Portfolio CSV",
                type=["csv"],
                label_visibility="collapsed",
                help="Upload a valid Pocket Trader CSV file (Max 2MB)"
            )

            # Security, Universe & Schema Validation Checks
            if uploaded_portfolio is not None:
                file_sig = f"{uploaded_portfolio.name}_{uploaded_portfolio.size}"

                # Check if this exact file was already imported this session
                if st.session_state.get("last_uploaded_file_sig") == file_sig:
                    st.info(f"ℹ️ **{uploaded_portfolio.name}** has already been imported. All positions are currently up to date.")
                else:
                    MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024
                    file_bytes = uploaded_portfolio.getvalue()

                    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
                        st.error("🚨 Security Alert: File size exceeds the 2MB limit.")
                    elif not uploaded_portfolio.name.lower().endswith(".csv"):
                        st.error("🚨 Invalid file type. Only `.csv` files are accepted.")
                    else:
                        try:
                            decoded_str = file_bytes.decode("utf-8")
                            if "\x00" in decoded_str:
                                raise ValueError("Binary / executable content detected.")

                            imp_df = pd.read_csv(uploaded_portfolio)

                            clean_cols = {c.strip().lower(): c for c in imp_df.columns}

                            sym_col = clean_cols.get("symbol") or clean_cols.get("ticker")
                            buy_price_col = clean_cols.get("buy price") or clean_cols.get("price") or clean_cols.get("cost")
                            shares_col = clean_cols.get("shares") or clean_cols.get("qty") or clean_cols.get("quantity")
                            date_col = clean_cols.get("buy date") or clean_cols.get("date") or clean_cols.get("purchase date")

                            if not (sym_col and buy_price_col and shares_col):
                                st.error("Invalid format: CSV must at minimum contain 'Symbol', 'Buy Price', and 'Shares' columns.")
                            else:
                                imported_count = 0
                                duplicate_count = 0
                                skipped_symbols = []

                                for _, row in imp_df.iterrows():
                                    raw_sym = str(row[sym_col]).strip().upper()
                                    if raw_sym.startswith(("=", "+", "-", "@")):
                                        raw_sym = raw_sym.lstrip("=+-@")

                                    # Check against 59 tracked TSX equities
                                    if raw_sym not in all_symbols:
                                        skipped_symbols.append(raw_sym)
                                        continue

                                    b_price = float(row[buy_price_col])
                                    shs = int(row[shares_col])
                                    b_date = str(row[date_col]) if date_col and pd.notna(row[date_col]) else str(datetime.now(ET_ZONE).date())

                                    t_gain = 10.0
                                    if "target gain" in clean_cols and pd.notna(row[clean_cols["target gain"]]):
                                        t_gain = float(row[clean_cols["target gain"]])
                                    elif "target price" in clean_cols and pd.notna(row[clean_cols["target price"]]):
                                        t_gain = max(0.10, float(row[clean_cols["target price"]]) - b_price)

                                    candidate_pos = {
                                        "Symbol": raw_sym,
                                        "Buy Date": b_date,
                                        "Buy Price": b_price,
                                        "Shares": shs,
                                        "Target Gain": t_gain,
                                        "Horizon Days": 60
                                    }

                                    # Row duplication check (exact match on all 5 attributes)
                                    if is_exact_duplicate(st.session_state.pocket_positions, candidate_pos):
                                        duplicate_count += 1
                                    else:
                                        st.session_state.pocket_positions.append(candidate_pos)
                                        imported_count += 1

                                # Record this file upload signature
                                st.session_state["last_uploaded_file_sig"] = file_sig
                                save_to_browser_storage()

                                if imported_count > 0:
                                    st.success(f"✅ Successfully imported and merged {imported_count} position(s)!")
                                if duplicate_count > 0:
                                    st.warning(f"⚠️ {duplicate_count} position(s) were skipped because exact duplicate records already exist in your portfolio.")
                                if skipped_symbols:
                                    st.warning(
                                        f"⚠️ {len(skipped_symbols)} position(s) skipped (outside 59 tracked TSX equities): {', '.join(sorted(set(skipped_symbols)))}"
                                    )
                                st.rerun()

                        except UnicodeDecodeError:
                            st.error("🚨 Unreadable file format. Please upload a valid UTF-8 CSV.")
                        except Exception as e:
                            st.error(f"🚨 Security/Parse error: Unable to load file ({e})")

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
                        "SELL / EXIT": "#ef4444",
                        "TRIM / TAKE PROFIT": "#f59e0b",
                        "KEEP / HOLD": "#64748b"
                    },
                    template="plotly_white"
                )
                fig_rsi.add_vline(x=40, line_dash="dot", line_color="green", annotation_text="Pullback (<=40)")
                fig_rsi.add_vline(x=75, line_dash="dot", line_color="red", annotation_text="Overbought (>=75)")
                fig_rsi.update_layout(xaxis_title="14-Day RSI", yaxis_title="Equities Count", height=430)
                st.plotly_chart(fig_rsi, use_container_width=True)

            with chart_col2:
                st.subheader("Price vs. 50-Day Moving Average")
                hover_data = {"Company": True, "RSI_14": True} if "Company" in filtered_df.columns else {"RSI_14": True}
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
                        "KEEP / HOLD": "#64748b"
                    },
                    template="plotly_white"
                )
                fig_spread.update_layout(xaxis_title="50-Day SMA (CAD)", yaxis_title="Current Price (CAD)", height=430)
                st.plotly_chart(fig_spread, use_container_width=True)

    # -------------------------------------------------------------------------
    # TAB 4: User Manual (With Pocket Trader Documentation)
    # -------------------------------------------------------------------------
    with tab_manual:
        st.markdown("""
        ### 📖 TrendNorth Operational Manual & Documentation

        #### 1. Introduction
        TrendNorth is an automated quantitative screening dashboard tracking large-cap Canadian equities and core ETFs listed on the Toronto Stock Exchange (TSX). It computes institutional-grade momentum and moving average indicators to systematically highlight actionable swing trading opportunities.

        #### 2. What Business Problem Does TrendNorth Solve?
        Individual Canadian retail investors often suffer from **market noise, emotional bias, and screen fatigue**. 
        - Most mainstream screeners are heavily US-centric and flood users with thousands of speculative penny stocks.
        - TrendNorth isolates **59 highly liquid TSX sector leaders and core index ETFs**, applying deterministic technical rules to clearly distinguish between pullbacks worth accumulating versus structural breakdowns worth exiting.

        #### 3. Technical Indicator Definitions
        - **14-Day RSI (Relative Strength Index):** Momentum oscillator bounded between 0 and 100.
          - $\mathbf{\le 40}$ **(Oversold / Dip):** Highlights a pullback during a strong broader trend.
          - $\mathbf{\ge 75}$ **(Overbought):** Indicates overextended short-term momentum where trimming profits is prudent.
        - **50-Day SMA (Simple Moving Average):** Medium-term baseline trend (~10 weeks of trading).
        - **200-Day SMA:** Long-term institutional dividing line between secular bull and bear markets (~40 weeks).
        - **Signal Rationales:**
          - **BUY / ACCUMULATE:** Bullish trend ($\text{SMA}_{50} > \text{SMA}_{200}$) accompanied by a temporary pullback ($\text{RSI}_{14} \le 40$).
          - **SELL / EXIT:** Structural breakdown ($\text{SMA}_{50} < \text{SMA}_{200}$) known as a Death Cross.
          - **TRIM / TAKE PROFIT:** Extreme overextended momentum ($\text{RSI}_{14} \ge 75$).
          - **KEEP / HOLD:** Asset is healthy and trading within normal baseline volatility.

        #### 4. Refresh Frequency & Pipeline Schedule
        - Scans run twice daily via headless serverless runners:
          - **Morning Market Open Scan:** 10:32 AM EDT (post-opening volatility resolution).
          - **After Market Close Scan:** 04:47 PM EDT (captures confirmed daily closing candles).

        #### 5. 💼 Pocket Trader (Portfolio & Target Execution Companion)
        Pocket Trader bridges the gap between signal discovery and active trade management:
        - **Retrospective Health Checks:** Enter shares purchased months ago at past prices. Pocket Trader continuously tracks your cumulative net P&L and contrasts your gain with live TrendNorth signals (e.g. flagging `TRIM` when RSI overheats).
        - **Forward-Looking Target Milestones:** Enter target gains (e.g., +$10.00/share). The engine highlights progress toward your target on every scan and marks **`🎯 TARGET REACHED`** when your threshold is crossed.
        - **Multi-Symbol Batch Staging:** Add multiple watchlist candidates simultaneously using editable grids.
        - **Multiple Purchase Tranches:** Track multiple purchases of the same stock acquired at different dates or prices.
        - **Position Quick-Edit & Tuning:** Correct quantities, entry prices, or target profit goals anytime via the **Quick Edit** panel.
        - **Curated TSX Universe:** Pocket Trader strictly validates entries against TrendNorth's 59 core TSX sector leaders to guarantee valid institutional data, daily SMAs, and momentum signals.
        - **Browser Auto-Save & Privacy:** Your positions are saved automatically to your browser's client storage. Export your portfolio to a local CSV anytime and reload it on your next visit with one click.

        #### 6. Data Latency & Source
        - Market pricing data is sourced via Yahoo Finance with standard ~15-minute exchange latency. TrendNorth is engineered for daily swing and positional trend monitoring, not high-frequency intraday scalping.
        """)

render_dashboard()

# -----------------------------------------------------------------------------
# Floating User Feedback Popover (Bottom-Right Anchored)
# -----------------------------------------------------------------------------
with st.popover("💬 Submit Feedback"):
    st.markdown("#### Send Us Feedback")
    st.caption("Help improve TrendNorth with bug reports or feature suggestions.")

    if st.session_state.get("feedback_sent_success", False):
        st.success("✅ Thank you! Your feedback has already been received.")
    else:
        fb_name = st.text_input("Your Name", max_chars=50, placeholder="e.g. Alex")
        fb_email = st.text_input("Your Email", max_chars=80, placeholder="name@domain.com")
        fb_sentiment = st.selectbox(
            "Topic",
            ["Feature Suggestion", "Bug Report", "Data Inaccuracy", "General Feedback"]
        )
        fb_message = st.text_area(
            "Your Comments",
            max_chars=600,
            placeholder="Describe your suggestion or issue..."
        )

        hp_bot = st.text_input("Leave empty", label_visibility="collapsed", key="honeypot_trap")

        def is_valid_email(addr: str) -> bool:
            return bool(re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", addr.strip()))

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
            elif any(link in fb_message.lower() for link in ["http://", "https://", "www."]):
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
                            message=fb_message.strip()
                        )
                        if success:
                            st.session_state.feedback_sent_success = True
                            st.session_state.last_fb_time = time.time()
                            st.success("Thank you! Your feedback has been sent directly to the team.")
                            st.rerun()
                        else:
                            st.error("Could not send feedback at this time. Please try again later.")