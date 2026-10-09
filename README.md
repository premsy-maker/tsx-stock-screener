# 📈 Bay Street Pulse (v1.0-beta)

> Automated momentum and technical trend monitoring engine for Canadian large-cap equities and core benchmark ETFs listed on the Toronto Stock Exchange (TSX).

---

## 📌 Overview

**Bay Street Pulse** is a decoupled Python screening engine and Streamlit analytics dashboard designed to monitor technical trends across high-liquidity TSX equities. 

By analyzing simple moving average relationships and momentum oscillators, the platform transforms daily price data into rule-based market classifications (`BUY / ACCUMULATE`, `SELL / EXIT`, `TRIM / TAKE PROFIT`, `KEEP / HOLD`) and automatically dispatches email alerts when actionable technical triggers occur.

---

## 🎯 Key Problems Solved

* **Eliminates Manual Chart Screening:** Removes the need to manually review dozens of technical charts daily by aggregating 59 liquid Canadian assets into an instant multi-dimensional view.
* **Removes Emotional Bias:** Replaces subjective market sentiment and FOMO with deterministic, quantitative rules.
* **Timely Opportunity Discovery:** Flags high-conviction structural inflection points—such as value pullbacks within primary bull trends or macro trend breakdowns—as soon as daily market bars settle.

---

## 🏗️ Architecture

The application is structured into decoupled components:

```text
tsx-stock-screener/
│
├── .github/workflows/
│   └── screener_cron.yml   # Scheduled GitHub Actions pipeline (runs twice daily)
├── .streamlit/
│   └── config.toml          # Dashboard theme styling
├── ScreenStocksV1.py        # Core analytics engine & signal calculation
├── notifierV1.py            # SMTP dispatch for actionable alerts & feedback
├── app.py                   # Interactive Streamlit analytics dashboard
├── requirements.txt         # Runtime dependencies
└── screener_results.csv     # Persisted scan dataset (Symbol, Price, SMAs, RSI, Signals)
