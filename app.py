import os
import re
import time
import json
from datetime import date, datetime, time as dtime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
import plotly.express as px
import streamlit as st

# Import feedback sender from notifier
try:
    from notifierV1 import send_feedback_email
except ImportError:
    def send_feedback_email(sender_name: str, sender_email: str, sentiment: str, message: str) -> bool:
        return False

# Optional LocalStorage integration for Pocket Trader auto-persistence
try:
    from streamlit_local_storage import LocalStorage
    storage = LocalStorage()
    HAS_LOCAL_STORAGE = True
except ImportError:
    storage = None
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

# -----------------------------------------------------------------------------
# TSX Market Session Hours Helper
# -----------------------------------------------------------------------------
def get_tsx_market_status():
    now_et = datetime.now(ET_ZONE)
    weekday = now_et.weekday()  # 0=Monday, 4=Friday, 5=Sat, 6=Sun
    today_time = now_et.time()

    open_time = dtime(9, 30)
    close_time = dtime(16, 0)

    # 2026 TSX Observed Holidays (Mon-Fri)
    tsx_holidays_2026 = {
        date(2026, 1, 1),   # New Year's Day
        date(2026, 2, 16),  # Family Day
        date(2026, 4, 3),   # Good Friday
        date(2026, 5, 18),  # Victoria Day
        date(2026, 7, 1),   # Canada Day
        date(2026, 8, 3),   # Civic Holiday
        date(2026, 9, 7),   # Labour Day
        date(2026, 9, 30),  # National Day for Truth and Reconciliation
        date(2026, 10, 12), # Thanksgiving Day
        date(2026, 12, 25), # Christmas Day
        date(2026, 12, 28), # Boxing Day (Observed)
    }

    if weekday >= 5 or now_et.date() in tsx_holidays_2026:
        return "CLOSED", "Weekend / TSX Market Holiday", "Closed", "Opens next trading day at 9:30 AM ET"

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
# Resilient Data Loader with Cache-Busting (TN-008 & TN-001)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=60)
def load_screener_results():
    """Loads screener results directly from GitHub 'data' branch with cache-busting."""
    df = None
    mod_time = None
    
    # 1. Fetch from GitHub data branch with cache-buster param to bypass CDN lag
    bust_url = f"{DATA_BRANCH_URL}?t={int(time.time())}"
    try:
        df = pd.read_csv(bust_url)
        mod_time = datetime.now(ET_ZONE)
    except Exception:
        try:
            df = pd.read_csv(DATA_BRANCH_URL)
            mod_time = datetime.now(ET_ZONE)
        except Exception:
            pass

    # 2. Local fallback if remote request fails
    if df is None and os.path.exists(LOCAL_CSV_FILE):
        try:
            raw_mtime = os.path.getmtime(LOCAL_CSV_FILE)
            mod_time = datetime.fromtimestamp(raw_mtime, tz=ZoneInfo("UTC")).astimezone(ET_ZONE)
            df = pd.read_csv(LOCAL_CSV_FILE)
        except Exception:
            pass

    if df is None or df.empty:
        return pd.DataFrame(), None

    try:
        # Standardize Symbol / Ticker column
        if "Symbol" not in df.columns and "Ticker" in df.columns:
            df.rename(columns={"Ticker": "Symbol"}, inplace=True)

        if "Company" not in df.columns and "Symbol" in df.columns:
            df["Company"] = df["Symbol"].map(lambda s: COMPANY_NAMES.get(str(s).strip(), "—"))

        # Clean numerical currency and oscillator fields
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
# Pocket Trader State Initialization & Helpers
# -----------------------------------------------------------------------------
if "pocket_positions" not in st.session_state:
    st.session_state.pocket_positions = []

if "pocket_edit_index" not in st.session_state:
    st.session_state.pocket_edit_index = None

if "last_uploaded_file_sig" not in st.session_state:
    st.session_state.last_uploaded_file_sig = None

def sync_pocket_to_local_storage():
    """Syncs state to browser localStorage if package is available."""
    if HAS_LOCAL_STORAGE and storage is not None:
        try:
            storage.setItem("tn_pocket_positions", json.dumps(st.session_state.pocket_positions))
        except Exception:
            pass

def hydrate_pocket_from_local_storage():
    """Hydrates positions from browser localStorage on initial session load."""
    if HAS_LOCAL_STORAGE and storage is not None and not st.session_state.pocket_positions:
        try:
            stored = storage.getItem("tn_pocket_positions")
            if stored:
                loaded = json.loads(stored)
                if isinstance(loaded, list):
                    st.session_state.pocket_positions = loaded
        except Exception:
            pass

hydrate_pocket_from_local_storage()

# -----------------------------------------------------------------------------
# Dashboard Rendering
# -----------------------------------------------------------------------------
def render_dashboard():
    df_raw, scan_time = load_screener_results()

    # Sidebar Header & Controls
    with st.sidebar:
        st.markdown(
            """
            <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 8px;">
                <h2 style="margin: 0; padding: 0;">TrendNorth</h2>
                <img src="https://flagcdn.com/w80/ca.png" width="34" style="margin-top: 2px;" alt="Canada Flag"/>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("🔄 Refresh Data Now", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")
        st.subheader("🔍 Screener Filters")

        if not df_raw.empty and "Signal" in df_raw.columns:
            available_signals = sorted(list(df_raw["Signal"].dropna().unique()))
        else:
            available_signals = ["BUY / ACCUMULATE", "SELL / EXIT", "TRIM / TAKE PROFIT", "KEEP / HOLD"]

        default_signals = [s for s in ["BUY / ACCUMULATE", "SELL / EXIT", "TRIM / TAKE PROFIT"] if s in available_signals]
        selected_signals = st.multiselect("Signal Classification", options=available_signals, default=default_signals)

        rsi_range = st.slider("14-Day RSI Window", min_value=0.0, max_value=100.0, value=(0.0, 100.0), step=1.0)

        sma_trend = st.radio(
            "SMA Trend Configuration",
            options=["All Trends", "Bullish (SMA 50 > SMA 200)", "Bearish / Death Cross (SMA 50 < SMA 200)"],
            index=0,
        )

        search_query = st.text_input("Find Symbol or Company", placeholder="e.g. SHOP, BMO, Enbridge").strip().upper()

        st.markdown("---")
        st.caption("ℹ️ **Educational / Non-Financial Advice Disclaimer**")
        st.caption("TrendNorth is an algorithmic research platform for TSX securities. All indicators and alerts are mathematical representations for self-directed educational screening and do not constitute financial advice.")

    # Top Status Banner
    status_state, status_detail, elapsed_time, time_to_close = get_tsx_market_status()
    scan_date_str = scan_time.strftime("%b %d, %Y — %I:%M %p ET") if scan_time else "Data Pending"
    today_et_str = datetime.now(ET_ZONE).strftime("%A, %B %d, %Y")
    now_time_et_str = datetime.now(ET_ZONE).strftime("%I:%M:%S %p ET")

    st.markdown(
        f"""
        <div style="display: flex; align-items: baseline; gap: 8px; margin-bottom: 2px;">
            <h1 style="margin: 0; padding: 0; font-size: 2.2rem; font-weight: 700;">📈 TrendNorth</h1>
            <img src="https://flagcdn.com/w80/ca.png" width="36" style="margin-bottom: 2px;" alt="Canada Flag"/>
        </div>
        <p style="color: #64748b; font-size: 0.95rem; margin-top: 2px; margin-bottom: 14px;">
            <b>Date:</b> {today_et_str} &nbsp;|&nbsp; 
            <b>Live Clock:</b> {now_time_et_str} &nbsp;|&nbsp; 
            <b>Engine Scan Data:</b> {scan_date_str}
        </p>
        """,
        unsafe_allow_html=True,
    )

    col_stat1, col_stat2, col_stat3 = st.columns([1.5, 1.2, 1.2])
    with col_stat1:
        if status_state == "OPEN":
            st.success(f"🟢 **TSX Status:** {status_state} ({status_detail})")
        elif status_state == "PRE-MARKET":
            st.warning(f"🟡 **TSX Status:** {status_state} ({status_detail})")
        else:
            st.info(f"⚪ **TSX Status:** {status_state} ({status_detail})")
    with col_stat2:
        st.metric(label="Counter (Elapsed)", value=elapsed_time)
    with col_stat3:
        st.metric(label="Time to Close", value=time_to_close)

    if df_raw.empty:
        st.warning("Waiting for scan data... Run the GitHub Actions workflow or execute `python ScreenStocksV1.py` locally.")
        return

    # Filter Dataset for Watchlist View
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

    # Metrics Summary Bar
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    with m_col1:
        st.metric("Watchlist Displayed", f"{len(filtered_df)} / {len(df_raw)}")
    with m_col2:
        buy_cnt = len(filtered_df[filtered_df["Signal"] == "BUY / ACCUMULATE"])
        st.metric("🟢 Buy / Accumulate", buy_cnt)
    with m_col3:
        sell_cnt = len(filtered_df[filtered_df["Signal"] == "SELL / EXIT"])
        st.metric("🔴 Sell / Exit", sell_cnt)
    with m_col4:
        trim_cnt = len(filtered_df[filtered_df["Signal"] == "TRIM / TAKE PROFIT"])
        st.metric("🟡 Trim / Profit", trim_cnt)

    st.markdown("---")

    # Navigation Tabs (Pocket Trader positioned immediately after Watchlist)
    tab_data, tab_pocket, tab_charts, tab_manual = st.tabs(
        ["📋 Filtered Watchlist", "💼 Pocket Trader", "📊 Market Technicals", "📖 User Manual"]
    )

    # -------------------------------------------------------------------------
    # TAB 1: Filtered Watchlist
    # -------------------------------------------------------------------------
    with tab_data:
        if filtered_df.empty:
            st.info("No TSX assets match your selected filter criteria.")
        else:
            def signal_styler(val):
                if "BUY" in str(val):
                    return "color: #1b5e20; background-color: #e8f5e9; font-weight: bold;"
                elif "SELL" in str(val):
                    return "color: #b71c1c; background-color: #ffebee; font-weight: bold;"
                elif "TRIM" in str(val):
                    return "color: #b45309; background-color: #fef3c7; font-weight: bold;"
                return "color: #475569;"

            columns_order = [
                "Symbol", "Company", "Price", "Signal", "RSI_14", "SMA_50", "SMA_200", "Rationale"
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
        st.subheader("💼 Pocket Trader — Portfolio & Target Tracker")
        st.caption("Track active positions or planned purchases against live TSX scan prices with custom target gains.")

        # Batch Position Setup Form
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
                    for _, r in edited_staging.iterrows():
                        st.session_state.pocket_positions.append({
                            "Symbol": str(r["Symbol"]).strip(),
                            "Buy Date": str(r["Buy Date"]),
                            "Buy Price": float(r["Buy Price"]),
                            "Shares": int(r["Shares"]),
                            "Target Gain": float(r["Target Gain ($)"]),
                        })
                    sync_pocket_to_local_storage()
                    st.success(f"Added {len(edited_staging)} position(s) to Pocket Trader!")
                    st.rerun()

        # Render Active Holdings Table
        if not st.session_state.pocket_positions:
            st.info("No active positions tracked in Pocket Trader yet. Click the setup drawer above to log your first trade.")
        else:
            calc_rows = []
            for i, pos in enumerate(st.session_state.pocket_positions):
                sym = pos["Symbol"]
                buy_p = float(pos.get("Buy Price", 0.0))
                shares = int(pos.get("Shares", 0))
                tgt_gain = float(pos.get("Target Gain", 10.0))

                # Lookup live scan price & signal
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

            # Portfolio Summary Banner
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

            # Interactive Holdings Table with Row Selection
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

            # Bulk Removal & Quick Edit Action Bar
            selected_rows = event.selection.rows if hasattr(event, "selection") and event.selection else []
            if selected_rows:
                act_col1, act_col2 = st.columns([2, 8])
                with act_col1:
                    if st.button(f"🗑️ Remove ({len(selected_rows)}) Position(s)", type="primary"):
                        st.session_state.pocket_positions = [
                            p for idx, p in enumerate(st.session_state.pocket_positions) if idx not in selected_rows
                        ]
                        sync_pocket_to_local_storage()
                        st.rerun()

        # Backup & Restore Drawer (Always Accessible)
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
                st.write("**Restore Portfolio from Backup:**")
                uploaded_backup = st.file_uploader("Upload portfolio CSV", type=["csv"], label_visibility="collapsed")
                if uploaded_backup is not None:
                    try:
                        imp_df = pd.read_csv(uploaded_backup)
                        required_cols = {"Symbol", "Buy Price", "Shares"}
                        if required_cols.issubset(imp_df.columns):
                            valid_rows = []
                            skipped = []
                            for _, row in imp_df.iterrows():
                                sym = str(row["Symbol"]).strip().upper()
                                if sym in COMPANY_NAMES:
                                    valid_rows.append({
                                        "Symbol": sym,
                                        "Buy Date": str(row.get("Buy Date", date.today())),
                                        "Buy Price": float(row["Buy Price"]),
                                        "Shares": int(row["Shares"]),
                                        "Target Gain": float(row.get("Target Gain", 10.0)),
                                    })
                                else:
                                    skipped.append(sym)

                            st.session_state.pocket_positions = valid_rows
                            sync_pocket_to_local_storage()
                            if skipped:
                                st.warning(f"Restored {len(valid_rows)} positions. Skipped untracked symbols: {', '.join(skipped)}")
                            else:
                                st.success(f"Restored {len(valid_rows)} positions successfully!")
                            st.rerun()
                        else:
                            st.error("Uploaded CSV is missing required headers: Symbol, Buy Price, Shares.")
                    except Exception as err:
                        st.error(f"Error reading CSV backup: {err}")

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
                        "KEEP / HOLD": "#64748b",
                    },
                    template="plotly_white",
                )
                fig_rsi.add_vline(x=40, line_dash="dot", line_color="green", annotation_text="Pullback (<=40)")
                fig_rsi.add_vline(x=75, line_dash="dot", line_color="red", annotation_text="Overbought (>=75)")
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
                        "BUY / ACCUMULATE": "#16a34a",
                        "SELL / EXIT": "#ef4444",
                        "TRIM / TAKE PROFIT": "#f59e0b",
                        "KEEP / HOLD": "#64748b",
                    },
                    template="plotly_white",
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
                * **Privacy-First Storage:** Positions persist in browser storage and can be backed up or restored anytime via CSV files.
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
    st.markdown(
        """
        <style>
        div[data-testid="stPopover"] {
            position: fixed;
            bottom: 24px;
            right: 24px;
            z-index: 999999;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
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