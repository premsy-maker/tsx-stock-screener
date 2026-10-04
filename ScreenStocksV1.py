import yfinance as yf
import pandas as pd
from tabulate import tabulate
from notifierV1 import send_stock_email

# Canadian TSX Watchlist (V1 core sample)
WATCHLIST = [
    # --- Index / All-in-One ETFs ---
    "XEQT.TO",   # iShares Core Equity ETF Portfolio (100% Equity)
    "XIU.TO",    # iShares S&P/TSX 60 Index ETF

    # --- Financials (Big Banks, Lifecos & Asset Managers) ---
    "RY.TO",     # Royal Bank of Canada
    "TD.TO",     # Toronto-Dominion Bank
    "BMO.TO",    # Bank of Montreal
    "BNS.TO",    # Bank of Nova Scotia
    "CM.TO",     # Canadian Imperial Bank of Commerce
    "NA.TO",     # National Bank of Canada
    "MFC.TO",    # Manulife Financial
    "SLF.TO",    # Sun Life Financial
    "BN.TO",     # Brookfield Corporation
    "BAM.TO",    # Brookfield Asset Management
    "POW.TO",    # Power Corporation of Canada
    "FFH.TO",    # Fairfax Financial Holdings
    "IFC.TO",    # Intact Financial

    # --- Energy (Pipelines & Producers) ---
    "ENB.TO",    # Enbridge
    "TRP.TO",    # TC Energy
    "PPL.TO",    # Pembina Pipeline
    "CNQ.TO",    # Canadian Natural Resources
    "SU.TO",     # Suncor Energy
    "CVE.TO",    # Cenovus Energy
    "IMO.TO",    # Imperial Oil
    "TOU.TO",    # Tourmaline Oil

    # --- Industrials, Rails & Services ---
    "CNR.TO",    # Canadian National Railway
    "CP.TO",     # Canadian Pacific Kansas City
    "WCN.TO",    # Waste Connections
    "WSP.TO",    # WSP Global
    "TRI.TO",    # Thomson Reuters
    "CAE.TO",    # CAE Inc.

    # --- Technology ---
    "SHOP.TO",   # Shopify
    "CSU.TO",    # Constellation Software
    "CLS.TO",    # Celestica
    "GIB-A.TO",  # CGI Inc. (Class A)
    "OTEX.TO",   # OpenText

    # --- Consumer Staples & Discretionary ---
    "ATD.TO",    # Alimentation Couche-Tard
    "DOL.TO",    # Dollarama
    "L.TO",      # Loblaw Companies
    "MRU.TO",    # Metro Inc.
    "WN.TO",     # George Weston
    "QSR.TO",    # Restaurant Brands International (Tim Hortons / BK)
    "CTC-A.TO",  # Canadian Tire
    "MG.TO",     # Magna International
    "GIL.TO",    # Gildan Activewear

    # --- Utilities & Infrastructure ---
    "FTS.TO",    # Fortis Inc.
    "H.TO",      # Hydro One
    "EMA.TO",    # Emera
    "BIP-UN.TO", # Brookfield Infrastructure Partners

    # --- Telecommunications ---
    "T.TO",      # Telus
    "BCE.TO",    # BCE Inc.
    "RCI-B.TO",  # Rogers Communications (Class B)

    # --- Materials, Mining & Fertilizers ---
    "NTR.TO",    # Nutrien
    "ABX.TO",    # Barrick Gold / Mining
    "AEM.TO",    # Agnico Eagle Mines
    "FNV.TO",    # Franco-Nevada
    "WPM.TO",    # Wheaton Precious Metals
    "CCO.TO",    # Cameco
    "TECK-B.TO", # Teck Resources (Class B)
    "FM.TO",     # First Quantum Minerals
    "K.TO",      # Kinross Gold
]
#The RSI (Relative Strength Index) simply measures: Over the last 14 days, were the upward price moves stronger than the downward price moves?
def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = (delta.where(delta > 0, 0.0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs = gain / (loss.replace(0, 0.00001))
    return 100 - (100 / (1 + rs))

def analyze_ticker(ticker: str):
    df = yf.download(ticker, period="1y", interval="1d", progress=False)
    if df.empty or len(df) < 200:
        return None

    close = df['Close'][ticker] if isinstance(df['Close'], pd.DataFrame) else df['Close']

    sma_50 = close.rolling(window=50).mean()
    sma_200 = close.rolling(window=200).mean()
    rsi = calculate_rsi(close, period=14)

    current_price = float(close.iloc[-1])
    current_rsi = float(rsi.iloc[-1])
    current_50 = float(sma_50.iloc[-1])
    current_200 = float(sma_200.iloc[-1])

    # Evaluate state
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
        "Ticker": ticker,
        "Price (CAD)": f"${current_price:.2f}",
        "RSI (14)": f"{current_rsi:.1f}",
        "SMA 50": f"${current_50:.2f}",
        "SMA 200": f"${current_200:.2f}",
        "Signal": signal,
        "Rationale": summary
    }

def main():
    print("Fetching TSX market data and computing signals...\n")
    results = []
    actionable = []

    for ticker in WATCHLIST:
        row = analyze_ticker(ticker)
        if row:
            results.append(row)
            # Collect stocks that are NOT in 'KEEP / HOLD'
            if row["Signal"] != "KEEP / HOLD":
                actionable.append(row)

    # 1. Print full terminal grid
    if results:
        print(tabulate(results, headers="keys", tablefmt="fancy_grid"))
    else:
        print("No data retrieved. Verify your internet connection or ticker symbols.")
        return

    # 2. Trigger the notifier email if any Buy/Sell signals were detected
    if actionable:
        print(f"\nTriggering email for {len(actionable)} actionable signal(s)...")

        html_rows = "".join([
            f"""
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd;"><b>{item['Ticker']}</b></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{item['Price (CAD)']}</td>
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold; color: {'#008000' if 'BUY' in item['Signal'] else '#b30000'};">
                    {item['Signal']}
                </td>
                <td style="padding: 8px; border: 1px solid #ddd;">{item['RSI (14)']}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{item['Rationale']}</td>
            </tr>
            """
            for item in actionable
        ])

        email_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color: #0b3954;">🚨 TSX Market Actionable Alerts</h2>
            <p>The following stocks have met your technical criteria for action:</p>
            <table style="border-collapse: collapse; width: 100%; text-align: left; font-size: 14px;">
                <thead>
                    <tr style="background-color: #f2f2f2;">
                        <th style="padding: 8px; border: 1px solid #ddd;">Ticker</th>
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
        print("\nAll stocks are currently in 'KEEP / HOLD'. No alert email sent.")

# --- REQUIRED ENTRY POINT ---
if __name__ == "__main__":
    main()