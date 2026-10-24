import os
from datetime import datetime, timezone
import yfinance as yf
import pandas as pd
from tabulate import tabulate
from notifierV1 import send_stock_email

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

    return {
        "Symbol": symbol,
        "Company": company_name,
        "Price": round(current_price, 2),
        "RSI_14": round(current_rsi, 1),
        "SMA_50": round(current_50, 2),
        "SMA_200": round(current_200, 2),
        "SMA_Trend": sma_trend,
        "Signal": signal,
        "Rationale": summary
    }

def push_to_supabase(df: pd.DataFrame):
    url = os.environ.get("SUPABASE_URL")
    # Prefer secret service key for writes, fallback to key if configured
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
            "Rationale": "rationale"
        }
        db_df.rename(columns=rename_map, inplace=True)

        # Stamp all rows with an identical UTC scan timestamp
        scan_time = datetime.now(timezone.utc).isoformat()
        db_df["scan_timestamp"] = scan_time

        cols_to_keep = [
            "scan_timestamp", "symbol", "company", "price",
            "signal", "rsi_14", "sma_50", "sma_200", "sma_trend", "rationale"
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
    results = []
    actionable = []

    for symbol, company_name in WATCHLIST.items():
        row = analyze_symbol(symbol, company_name)
        if row:
            results.append(row)
            # Collect stocks that are NOT in 'KEEP / HOLD'
            if row["Signal"] != "KEEP / HOLD":
                actionable.append(row)

    # 1. Print full terminal grid, save CSV, and push to Supabase
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

    # 2. Trigger the notifier email if any Buy/Sell signals were detected
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
                <td style="padding: 8px; border: 1px solid #ddd;">{item['Rationale']}</td>
            </tr>
            """
            for item in actionable
        ])

        email_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color: #0b3954;">🚨 TSX Market Actionable Alerts</h2>
            <p>The following symbols have met your technical criteria for action:</p>
            <table style="border-collapse: collapse; width: 100%; text-align: left; font-size: 14px;">
                <thead>
                    <tr style="background-color: #f2f2f2;">
                        <th style="padding: 8px; border: 1px solid #ddd;">Symbol</th>
                        <th style="padding: 8px; border: 1px solid #ddd;">Company</th>
                        <th style="padding: 8px; border: 1px solid #ddd;">Price</th>
                        <th style="padding: 8px; border: 1px solid #ddd;">Signal</th>
                        <th style="padding: 8px; border: 1px solid #ddd;">RSI (14)</th>
                        <th style="padding: 8px; border: 1px solid #ddd;">Rationale</th>
                    </tr>
                </thead>
                <tbody>
                    {html_rows}
                </tbody>
            </table>
            <br>
            <p style="font-size: 12px; color: #777;">Generated by your automated TSX Screener.</p>
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