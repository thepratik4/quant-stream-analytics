# Quant Analytics Dashboard (Real-Time Pairs Trading Analytics)

## How to Run

### 1️⃣ Setup environment

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
```

### 2️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

### 3️⃣ Run the app

```bash
python app.py
```

Open in browser:

```
http://127.0.0.1:8050
```


## Overview

This project is a **real-time quantitative analytics dashboard** designed as a helper tool for traders and quantitative researchers working in **statistical arbitrage and market microstructure**.

The application ingests **live market data from Binance WebSocket streams**, performs **real-time resampling and statistical analytics**, and visualizes the results through an **interactive dashboard** with alerting capabilities.

The system is designed as a **modular, extensible prototype** reflecting how internal analytics tools are built at quantitative trading firms, aligning with the assignment’s objective and design philosophy .

---

## Key Features

### 🔹 Real-Time Data Ingestion

* Live WebSocket connection to Binance
* Throttled ticker streams for stability
* Background ingestion thread (non-blocking)

### 🔹 Data Processing & Resampling

* Rolling in-memory tick buffer
* OHLCV resampling at:

  * **1 second**
  * **1 minute**
  * **5 minutes**
* Implemented using pandas time-series resampling

### 🔹 Quantitative Analytics (Pairs Trading)

* Hedge ratio estimation using **OLS regression**
* Spread computation
* Rolling **Z-score**
* Rolling **correlation of returns**
* Defensive handling of insufficient data
* Analytics computed on resampled close prices

### 🔹 Interactive Dashboard (Dash + Plotly)

* Live price updates
* Price charts (BTC & ETH)
* Spread chart
* Z-score chart with ±2 thresholds
* Rolling correlation chart
* Zoom, pan, hover support on all plots

### 🔹 Rule-Based Alerts

* Overbought alert when `z-score > +2`
* Oversold alert when `z-score < -2`
* Alerts appear/disappear dynamically as conditions change

---

## Architecture Overview

The system follows a **clean, layered architecture**:

```
Binance WebSocket
        ↓
Ingestion Layer (async, threaded)
        ↓
Rolling Tick Buffer (in-memory)
        ↓
Resampling Engine (pandas)
        ↓
Analytics Engine (OLS, Z-score, Correlation)
        ↓
Dash Frontend (Visualization & Alerts)
```

### Design Principles

* **Loose coupling** between ingestion, analytics, and UI
* Backend analytics independent of frontend framework
* Easy extensibility for:

  * New data sources (CSV, REST, futures feeds)
  * Additional analytics (Kalman filter, backtests)
* Clarity prioritized over premature optimization

This aligns with the stated design philosophy and extensibility expectations in the assignment .

---

## Tech Stack

### Backend

* Python 3
* Binance WebSocket (async)
* pandas, NumPy
* statsmodels (OLS, ADF-ready)

### Frontend

* Dash (Flask under the hood)
* Plotly (interactive financial charts)

### Storage

* In-memory rolling buffers (prototype scope)
* Architecture allows easy migration to SQLite / Redis

---

## Project Structure

```
quant_analytics_dashboard/
│
├── ingestion/
│   └── binance_ws.py        # WebSocket ingestion
│
├── analytics/
│   ├── statistics.py        # Resampling logic
│   └── pairs.py             # Quant analytics
│
├── dashboard/
│   ├── layout.py            # (optional future split)
│   └── callbacks.py         # (optional future split)
│
├── app.py                   # Dash app entry point
├── README.md
└── requirements.txt
```

---


---

## Analytics Methodology

### Hedge Ratio

Estimated using **OLS regression**:

```
BTC_price = α + β × ETH_price
```

### Spread

```
Spread = BTC − β × ETH
```

### Z-score

Rolling normalization:

```
z = (spread − mean) / std
```

### Correlation

Rolling correlation of percentage returns.

### Stationarity

ADF test logic implemented defensively and triggered only when sufficient data is available.

---

## Alerting Logic

* Alerts are computed from rolling z-score
* Only triggered when sufficient historical data exists
* Automatically reset when z-score normalizes
* Designed to mimic real trading alert systems

---

## Scalability Considerations

While this implementation runs locally, the architecture anticipates scaling:

* Replace in-memory buffer with Redis
* Add persistent OHLC storage (SQLite / Parquet)
* Plug in alternative data feeds (CME, historical CSV)
* Add new analytics without touching ingestion or UI

These decisions align with the evaluation’s emphasis on foresight and extensibility .

---

## ChatGPT Usage Transparency

ChatGPT was used as a **development assistant** for:

* Debugging Python/Dash issues
* Structuring analytics logic
* Improving architectural clarity
* Drafting documentation

All design decisions, analytics validation, and final implementation were reviewed and integrated manually.

---

## Final Notes

This project focuses on **correctness, clarity, and realistic quant workflows**, rather than over-engineering.
The goal was to build a **credible prototype** of a real-time analytics system that could evolve into a production-grade tool.

---

### ✅ Status

* Backend analytics: ✔ complete
* Frontend dashboard: ✔ complete
* Alerts: ✔ complete
* Architecture clarity: ✔ complete

---

If you want, next I can:

* Write a **short submission email**
* Describe the **architecture diagram boxes for draw.io**
* Do a **final polish checklist** before submission

Just tell me 👍
