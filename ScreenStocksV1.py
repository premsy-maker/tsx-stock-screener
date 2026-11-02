import os
from datetime import datetime, timezone
import yfinance as yf
import pandas as pd
from tabulate import tabulate
from notifierV1 import send_stock_email
import numpy as np

# Load .env file automatically when executing locally
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Supabase Client Import
try:
    from supabase import create_client, Client
except ImportError:
    create_client = None

WATCHLIST = {
    # --- Index / All-in-One ETFs ---
    "XEQT.TO": "iShares Core Equity ETF Portfolio",
    "XIU.TO": "iShares S&P/TSX 60 Index ETF",

    # --- Financials ---
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

    # --- Energy ---
    "ENB.TO": "Enbridge",
    "TRP.TO": "TC Energy",
    "PPL.TO": "Pembina Pipeline",
    "CNQ.TO": "Canadian Natural Resources",
    "SU.TO": "Suncor Energy",
    "CVE.TO": "Cenovus Energy",
    "IMO.TO": "Imperial Oil",
    "TOU.TO": "Tourmaline Oil",

    # --- Industrials, Rails & Services ---
    "CNR.TO": "Canadian National Railway",
    "CP.TO": "Canadian Pacific Kansas City",
    "WCN.TO": "Waste Connections",
    "WSP.TO": "WSP Global",
    "TRI.TO": "Thomson Reuters",
    "CAE.TO": "CAE Inc.",

    # --- Technology ---
    "SHOP.TO": "Shopify",
    "CSU.TO": "Constellation Software",
    "CLS.TO": "Celestica",
    "GIB-A.TO": "CGI Inc.",
    "OTEX.TO": "OpenText",

    # --- Consumer Staples & Discretionary ---
    "ATD.TO": "Alimentation Couche-Tard",
    "DOL.TO": "Dollarama",
    "L.TO": "Loblaw Companies",
    "MRU.TO": "Metro Inc.",
    "WN.TO": "George Weston",
    "QSR.TO": "Restaurant Brands International",
    "CTC-A.TO": "Canadian Tire",
    "MG.TO": "Magna International",
    "GIL.TO": "Gildan Activewear",

    # --- Utilities & Infrastructure ---
    "FTS.TO": "Fortis Inc.",
    "H.TO": "Hydro One",
    "EMA.TO": "Emera",
    "BIP-UN.TO": "Brookfield Infrastructure Partners",

    # --- Telecommunications ---
    "T.TO": "Telus",
    "BCE.TO": "BCE Inc.",
    "RCI-B.TO": "Rogers Communications",

    # --- Materials, Mining & Fertilizers ---
    "NTR.TO": "Nutrien",
    "ABX.TO": "Barrick Gold / Mining",
    "AEM.TO": "Agnico Eagle Mines",
    "FNV.TO": "Franco-Nevada",
    "WPM.TO": "Wheaton Precious Metals",
    "CCO.TO": "Cameco",
    "TECK-B.TO": "Teck Resources",
    "FM.TO": "First Quantum Minerals",
    "K.TO": "Kinross Gold",
}

def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = (delta.where(delta > 0, 0.0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs = gain / (loss.replace(0, 0.00001))
    return 100 - (100 / (1 + rs))

def calculate_atr(df: pd.DataFrame, symbol: str, period: int = 14) -> float:
    """
    Calculates the 14-period Average True Range (ATR).
    Safely handles both SingleIndex and MultiIndex yfinance DataFrames.
    """
    try:
        if isinstance(df.columns, pd.MultiIndex):
            high = df['High'][symbol]
            low = df['Low'][symbol]
            close = df['Close'][symbol]
        else:
            high = df['High']
            low = df['Low']
            close = df['Close']
            
        if len(close) < period + 1:
            return np.nan

        prev_close = close.shift(1)
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()

        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        # Wilder's Exponential Smoothing for ATR
        atr = true_range.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
        return float(atr.iloc[-1])
    except Exception:
        return np.nan

def analyze_symbol(symbol: str, company_name: str):
    df = yf.download(symbol, period="1y", interval="1d", progress=False)
    if df.empty or len(df) < 200:
        return None

    close = df['Close'][symbol] if isinstance(df['Close'], pd.DataFrame) else df['Close']

    sma_50 = close.rolling(window=50).mean()
    sma_200 = close.rolling(window=200).mean()
    rsi = calculate_rsi(close, period=14)

    current_price = float(close.iloc[-1])
    current_rsi = float(rsi.iloc[-1])
    current_50 = float(sma_50.iloc[-1])
    current_200 = float(sma_200.iloc[-1])

    # Determine SMA trend
    sma_trend = "Bullish (50 > 200)" if current_50 >= current_200 else "Bearish (50 < 200)"

    # Evaluate signal state
    if current_50 > current_200 and current_rsi <= 40:
        signal = "BUY / ACCUMULATE"
        summary = "Bullish trend + Pullback dip"
    elif current_50 < current_200:
        signal = "SELL / EXIT"
        summary = "Death cross (Bearish trend)"
    elif current_rsi >= 75:
        signal = "TRIM / TAKE PROFIT"
        summary = "Overextended momentum"
    else:
        signal = "KEEP / HOLD"
        summary = "Trading within baseline"

    # --- TN-005: Volatility & Stop-Loss Engine (ATR) ---
    atr_val = calculate_atr(df, symbol=symbol, period=14)
    if not np.isnan(atr_val) and atr_val > 0:
        atr_14 = round(atr_val, 2)
        # Stop-loss: 2x ATR below current price (model invalidation)
        stop_level_atr = round(max(0.01, current_price - (2 * atr_val)), 2)
        # Swing target: 3x ATR above current price
        target_atr = round(current_price + (3 * atr_val), 2)
    else:
        atr_14 = None
        stop_level_atr = None
        target_atr = None

    return {
        "Symbol": symbol,
        "Company": company_name,
        "Price": round(current_price, 2),
        "RSI_14": round(current_rsi, 1),
        "SMA_50": round(current_50, 2),
        "SMA_200": round(current_200, 2),
        "SMA_Trend": sma_trend,
        "Signal": signal,
        "Rationale": summary,
        "ATR_14": atr_14,
        "Stop_Level_ATR": stop_level_atr,
        "Target_ATR": target_atr
    }

def fetch_custom_watchlist() -> dict:
    """Fetches user-added custom tickers from Supabase to include in the automated scan."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")

    if not url or not key or create_client is None:
        return {}

    try:
        supabase: Client = create_client(url, key)
        res = supabase.table("custom_watchlist").select("symbol, company").execute()
        if res.data:
            return {
                row["symbol"]: (row["company"] if row.get("company") else row["symbol"])
                for row in res.data
            }
    except Exception as e:
        print(f"⚠️ Warning: Could not retrieve custom_watchlist from Supabase: {e}")
    return {}

def push_to_supabase(df: pd.DataFrame):
    url = os.environ.get("SUPABASE_URL")
    # Prefer secret service key for writes, fallback to anon key if configured
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")

    if not url or not key:
        print("⚠️ Supabase credentials not found in environment. Skipping DB upload.")
        return

    if create_client is None:
        print("⚠️ Supabase library not installed. Run 'pip install supabase'. Skipping DB upload.")
        return

    try:
        supabase: Client = create_client(url, key)

        db_df = df.copy()
        rename_map = {
            "Symbol": "symbol",
            "Company": "company",
            "Price": "price",
            "Signal": "signal",
            "RSI_14": "rsi_14",
            "SMA_50": "sma_50",
            "SMA_200": "sma_200",
            "SMA_Trend": "sma_trend",
            "Rationale": "rationale",
            "ATR_14": "atr_14",
            "Stop_Level_ATR": "stop_level_atr",
            "Target_ATR": "target_atr"
        }
        db_df.rename(columns=rename_map, inplace=True)

        # Stamp all rows with an identical UTC scan timestamp
        scan_time = datetime.now(timezone.utc).isoformat()
        db_df["scan_timestamp"] = scan_time

        cols_to_keep = [
            "scan_timestamp", "symbol", "company", "price",
            "signal", "rsi_14", "sma_50", "sma_200", "sma_trend", "rationale",
            "atr_14", "stop_level_atr", "target_atr"
        ]
        valid_cols = [c for c in cols_to_keep if c in db_df.columns]
        
        # Replace NaN / NaT with None so JSON serialization succeeds
        cleaned_df = db_df[valid_cols].where(pd.notnull(db_df[valid_cols]), None)
        records = cleaned_df.to_dict(orient="records")

        supabase.table("screener_results").insert(records).execute()
        print(f"✅ Successfully inserted {len(records)} records into Supabase table 'screener_results'.")
    except Exception as e:
        print(f"❌ Error inserting records to Supabase: {e}")

def main():
    print("Fetching TSX market data and computing signals...\n")
    
    # 1. Fetch user-added symbols from Supabase and union with baseline 59
    custom_tickers = fetch_custom_watchlist()
    full_watchlist = {**WATCHLIST, **custom_tickers}
    print(f"📊 Scanning {len(full_watchlist)} total assets ({len(WATCHLIST)} baseline + {len(custom_tickers)} custom additions)...")

    results = []
    actionable = []

    for symbol, company_name in full_watchlist.items():
        row = analyze_symbol(symbol, company_name)
        if row:
            results.append(row)
            # Collect stocks that are NOT in 'KEEP / HOLD'
            if row["Signal"] != "KEEP / HOLD":
                actionable.append(row)

    # 2. Print full terminal grid, save CSV, and push to Supabase
    if results:
        results_df = pd.DataFrame(results)
        
        # Keep CSV write intact as a reliable local fallback
        results_df.to_csv("screener_results.csv", index=False)
        
        # Push to Supabase Cloud Database
        push_to_supabase(results_df)

        print(tabulate(results, headers="keys", tablefmt="fancy_grid"))
    else:
        print("No data retrieved. Verify your internet connection or symbols.")
        return

    # 3. Trigger the notifier email if any Buy/Sell signals were detected
    if actionable:
        print(f"\nTriggering email for {len(actionable)} actionable signal(s)...")

        html_rows = "".join([
            f"""
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd;"><b>{item['Symbol']}</b></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{item['Company']}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">${item['Price']:.2f}</td>
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold; color: {'#008000' if 'BUY' in item['Signal'] else '#b30000'};">
                    {item['Signal']}
                </td>
                <td style="padding: 8px; border: 1px solid #ddd;">{item['RSI_14']}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{f"${item['ATR_14']:.2f}" if item['ATR_14'] else "N/A"}</td>
                <td style="padding: 8px; border: 1px solid #ddd; color: #b30000;">{f"${item['Stop_Level_ATR']:.2f}" if item['Stop_Level_ATR'] else "N/A"}</td>
                <td style="padding: 8px; border: 1px solid #ddd; color: #008000;">{f"${item['Target_ATR']:.2f}" if item['Target_ATR'] else "N/A"}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{item['Rationale']}</td>
            </tr>
            """
            for item in actionable
        ])

        email_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color: #0b3954;">🚨 TSX Market Actionable Alerts</h2>
            <p>The following symbols have met your technical criteria for action (with ATR Volatility Bands):</p>
            <table style="border-collapse: collapse; width: 100%; text-align: left; font-size: 13px;">
                <thead>
                    <tr style="background-color: #f2f2f2;">
                        <th style="padding: 8px; border: 1px solid #ddd;">Symbol</th>
                        <th style="padding: 8px; border: 1px solid #ddd;">Company</th>
                        <th style="padding: 8px; border: 1px solid #ddd;">Price</th>
                        <th style="padding: 8px; border: 1px solid #ddd;">Signal</th>
                        <th style="padding: 8px; border: 1px solid #ddd;">RSI</th>
                        <th style="padding: 8px; border: 1px solid #ddd;">14D ATR</th>
                        <th style="padding: 8px; border: 1px solid #ddd;">Stop Level (2x ATR)</th>
                        <th style="padding: 8px; border: 1px solid #ddd;">Target (3x ATR)</th>
                        <th style="padding: 8px; border: 1px solid #ddd;">Rationale</th>
                    </tr>
                </thead>
                <tbody>
                    {html_rows}
                </tbody>
            </table>
            <br>
            <p style="font-size: 11px; color: #777;">
                Disclaimer: TrendNorth is an educational research tool. ATR stop levels and price targets represent mathematical volatility models and do not constitute financial advice.
            </p>
        </body>
        </html>
        """

        send_stock_email(
            subject=f"🚨 TSX Screener: {len(actionable)} Actionable Signal(s)",
            html_body=email_html
        )
    else:
        print("\nAll symbols are currently in 'KEEP / HOLD'. No alert email sent.")

# --- REQUIRED ENTRY POINT ---
if __name__ == "__main__":
    main()