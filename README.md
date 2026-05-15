# SIPsense

**Market Sentiment & SIP Analytics Dashboard** — Analyze 5 years of Nifty 50 and Gold performance, simulate market sentiment, and model real-world SIP compounding.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-red)
![License](https://img.shields.io/badge/License-MIT-green)

## Overview

SIPsense is a data analytics portfolio project that:

- Downloads **5 years** of daily closing prices for **Nifty 50** (`^NSEI`) and **Gold futures** (`GC=F`) via `yfinance`
- Generates **synthetic but realistic daily sentiment scores** (-1.0 to 1.0) with deliberate **market shocks**
- Simulates monthly **SIP investments** (₹5,000 each in Nifty and Gold on the 1st trading day of every month)
- Computes **30-day rolling volatility** and **sentiment impact** on Nifty after severe negative news

## Dashboard Preview

Run the app locally to explore:

- **KPIs:** Total invested, portfolio value, absolute return, current Nifty price
- **SIP growth chart** over 5 years
- **Nifty vs sentiment** dual-axis chart with shock highlights
- **Insights:** Average Nifty move 3 days after severe sentiment shocks

## Project Structure

```
SIPsense/
├── data_pipeline.py      # yfinance download + sentiment simulation → market_data.csv
├── analysis_engine.py    # SIP math, volatility, sentiment impact
├── app.py                # Streamlit dashboard
├── market_data.csv       # Generated dataset (or run pipeline to create)
├── requirements.txt
└── README.md
```

## Quick Start

### 1. Clone & setup

```bash
git clone https://github.com/<your-username>/SIPsense.git
cd SIPsense
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Generate data (optional if `market_data.csv` exists)

```bash
python data_pipeline.py
```

### 3. Run dashboard

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

## How It Works

### Data Pipeline

- Fetches aligned trading-day prices (weekends/holidays excluded automatically)
- Forward-fills short gaps for missing sessions
- Sentiment uses mean-reverting noise + macro drift + random severe shocks (score &lt; -0.8)

### SIP Calculation

Each month on the **first available trading day**:

- Invest ₹5,000 in Nifty 50 → units = amount / price
- Invest ₹5,000 in Gold → units = amount / price
- Portfolio value = (Nifty units × Nifty price) + (Gold units × Gold price)

### Analytics

| Metric | Description |
|--------|-------------|
| **30-Day Rolling Volatility** | Annualized from daily log returns (√252 scaling) |
| **Sentiment Impact** | Avg % Nifty change 3 days after sentiment &lt; -0.8 |

## Tech Stack

- **Python** — pandas, numpy
- **yfinance** — market data
- **Streamlit** — web UI
- **Plotly** — interactive charts

## Disclaimer

This project is for **educational and portfolio purposes only**. Sentiment scores are **synthetic**, not real news data. Not financial advice.

## Author

Built as a Data Analytics portfolio project demonstrating ETL, financial math, and interactive visualization.
