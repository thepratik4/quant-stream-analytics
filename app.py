from dash import Dash, html, dcc, Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
import os
from datetime import datetime
from ingestion.binance_ws import start_binance_socket, latest_ticks, lock
import plotly.graph_objects as go
from analytics.statistics import resample_ohlc
from analytics.pairs import (
    compute_hedge_ratio,
    compute_spread,
    compute_zscore,
    rolling_correlation
)
from storage.db import init_db, insert_ohlc


# Start WebSocket ingestion
# Start WebSocket ingestion
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "AVAXUSDT"]
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "AVAXUSDT"]
start_binance_socket(SYMBOLS)

# Initialize Database
init_db()

def get_coin_icon(symbol):
    """
    Get icon URL from GitHub repository
    """
    base = symbol.lower().replace("usdt", "")
    return f"https://raw.githubusercontent.com/spothq/cryptocurrency-icons/master/32/icon/{base}.png"

# Generate rich options for dropdowns
SYMBOL_OPTIONS = []
for s in SYMBOLS:
    SYMBOL_OPTIONS.append({
        "label": html.Div([
            html.Img(src=get_coin_icon(s), style={"height": 20, "marginRight": 10}),
            html.Span(s)
        ], style={"display": "flex", "alignItems": "center"}),
        "value": s
    })

app = Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])

app.layout = dbc.Container([
    # ---- Header ----
    dbc.Row([
        dbc.Col(html.H1("Quant Analytics Dashboard", className="text-center mb-4"), width=12)
    ], className="mt-4"),

    # ---- Controls ----
    dbc.Row([
        dbc.Col([
            html.Div([
                html.Label("Symbol 1"),
                dcc.Dropdown(
                    id="symbol-1-dropdown",
                    options=SYMBOL_OPTIONS,
                    value="BTCUSDT",
                    clearable=False
                )
            ])
        ], width=12, md=4),
        dbc.Col([
            html.Div([
                html.Label("Symbol 2"),
                dcc.Dropdown(
                    id="symbol-2-dropdown",
                    options=SYMBOL_OPTIONS,
                    value="ETHUSDT",
                    clearable=False
                )
            ])
        ], width=12, md=4),
        dbc.Col([
            html.Div([
                html.Label("Timeframe"),
                dcc.Dropdown(
                    id="timeframe-dropdown",
                    options=[
                        {"label": "1 Second", "value": "1s"},
                        {"label": "1 Minute", "value": "1min"},
                        {"label": "5 Minutes", "value": "5min"}
                    ],
                    value="1s",
                    clearable=False
                )
            ])
        ], width=12, md=4),
    ], className="glass-card control-bar"),

    # ---- Alerts ----
    dbc.Row([
        dbc.Col(html.Div(id="alert-box"), width=12)
    ]),

    # ---- Top Section: Prices & Stats ----
    dbc.Row([
        # Live Prices
        dbc.Col([
            html.Div([
                html.H4("Live Feed", className="mb-3"),
                html.Div(id="live-prices")
            ], className="glass-card", style={"height": "100%"})
        ], width=12, md=4),

        # Pair Stats
        dbc.Col([
            html.Div([
                html.H4("Pair Statistics", className="mb-3"),
                html.Div(id="pair-stats-table")
            ], className="glass-card", style={"height": "100%"})
        ], width=12, md=8),
    ]),

    # ---- Main Chart ----
    dbc.Row([
        dbc.Col([
            html.Div([
                dcc.Graph(id="price-chart", style={"height": "500px"})
            ], className="glass-card")
        ], width=12)
    ]),
    
    # ---- Analytics Charts ----
    dbc.Row([
        dbc.Col(dcc.Graph(id="spread-chart"), width=12, lg=4),
        dbc.Col(dcc.Graph(id="zscore-chart"), width=12, lg=4),
        dbc.Col(dcc.Graph(id="corr-chart"), width=12, lg=4),
    ]),

    # Hidden Interval
    dcc.Interval(
        id="interval",
        interval=2000,
        n_intervals=0
    ),

    # Hidden Div for stats table (legacy or moved)
    html.Div(id="stats-table", style={"display": "none"}) 

], fluid=True, className="dashboard-container")


@app.callback(
    Output("alert-box", "children"),
    Output("live-prices", "children"),
    Output("stats-table", "children"),
    Output("price-chart", "figure"),
    Output("pair-stats-table", "children"),
    Output("spread-chart", "figure"),
    Output("zscore-chart", "figure"),
    Output("corr-chart", "figure"),
    Input("interval", "n_intervals"),
    Input("symbol-1-dropdown", "value"),
    Input("symbol-2-dropdown", "value"),
    Input("timeframe-dropdown", "value")
)
def update_dashboard(n, sym1, sym2, timeframe):

    # -------- Live prices --------
    rows = []
    with lock:
        # Sort by timestamp descending
        sorted_ticks = sorted(latest_ticks.items(), key=lambda item: item[1]['timestamp'], reverse=True)
        
        for symbol, data in sorted_ticks:
            price_fmt = f"${data['price']:,.2f}"
            qty_fmt = f"{data['qty']:.4f}"
            
            # Convert timestamp (assuming ms)
            ts_ms = data.get('timestamp')
            time_str = "N/A"
            if ts_ms:
                dt_obj = datetime.fromtimestamp(ts_ms / 1000.0)
                time_str = dt_obj.strftime("%H:%M:%S")
            
            # Icon
            icon_url = get_coin_icon(symbol)

            rows.append(
                html.Tr([
                    html.Td([
                        html.Img(src=icon_url, style={"height": "20px", "marginRight": "10px"}),
                        symbol
                    ], style={"fontWeight": "bold", "color": "#00ADB5", "display": "flex", "alignItems": "center"}),
                    html.Td(price_fmt),
                    html.Td(qty_fmt),
                    html.Td(time_str, style={"color": "#888"})
                ])
            )

    if rows:
        live_prices = html.Table([
            html.Thead(
                html.Tr([html.Th("Symbol"), html.Th("Price"), html.Th("Qty"), html.Th("Time")])
            ),
            html.Tbody(rows)
        ], className="table table-dark table-sm table-hover mb-0", style={"fontSize": "0.9rem"})
    else:
        live_prices = "Waiting for live data..."

    # Empty placeholders
    empty_fig = go.Figure()
    alert_div = html.Div("")
    empty_table = html.Div()

    # -------- Resampled data --------
    df1 = resample_ohlc(sym1, timeframe)
    df2 = resample_ohlc(sym2, timeframe)

    if df1.empty or df2.empty:
        return alert_div, live_prices, empty_table, empty_fig, empty_table, empty_fig, empty_fig, empty_fig

    # Persist data asynchronously-ish (SQLite is fast enough for this scale)
    try:
        insert_ohlc(df1, sym1, timeframe)
        insert_ohlc(df2, sym2, timeframe)
    except Exception as e:
        print(f"DB Error: {e}")

    close1 = df1["close"]
    close2 = df2["close"]

    # -------- Price chart --------
    price_fig = go.Figure()
    price_fig.add_trace(go.Scatter(
        x=close1.index,
        y=close1,
        name=sym1
    ))
    price_fig.add_trace(go.Scatter(
        x=close2.index,
        y=close2,
        name=sym2,
        yaxis="y2"
    ))
    price_fig.update_layout(
        title=f"Prices ({timeframe})",
        yaxis2=dict(overlaying="y", side="right"),
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#e0e0e0"}
    )

    # -------- Statistics --------
    stats = []
    for symbol, df in [(sym1, df1), (sym2, df2)]:
        close = df["close"]
        stats.append(
            html.Tr([
                html.Td(symbol),
                html.Td(f"{close.mean():.2f}"),
                html.Td(f"{close.std():.2f}"),
                html.Td(f"{close.min():.2f}"),
                html.Td(f"{close.max():.2f}")
            ])
        )

    stats_table = html.Table([
        html.Thead(
            html.Tr([html.Th("Symbol"), html.Th("Mean"), html.Th("Std"), html.Th("Min"), html.Th("Max")])
        ),
        html.Tbody(stats)
    ], className="table table-dark table-hover mb-0")

    # -------- Analytics --------
    hedge_ratio = compute_hedge_ratio(close1, close2)
    if hedge_ratio is None:
        return alert_div, live_prices, stats_table, price_fig, empty_table, empty_fig, empty_fig, empty_fig

    spread = compute_spread(close1, close2, hedge_ratio)
    zscore = compute_zscore(spread, window=30)
    corr = rolling_correlation(close1, close2, window=30)
    
    # -------- Pair Summary Stats --------
    last_spread = spread.iloc[-1]
    spread_mean = spread.mean()
    spread_std = spread.std()
    last_z = zscore.iloc[-1] if not zscore.empty else 0
    last_corr = corr.iloc[-1] if not corr.empty else 0

    pair_stats_content = html.Table([
        html.Thead(
            html.Tr([
                html.Th("Metric"), html.Th("Value")
            ])
        ),
        html.Tbody([
            html.Tr([html.Td("Hedge Ratio"), html.Td(f"{hedge_ratio:.4f}")]),
            html.Tr([html.Td("Spread (Last)"), html.Td(f"{last_spread:.4f}")]),
            html.Tr([html.Td("Spread Mean"), html.Td(f"{spread_mean:.4f}")]),
            html.Tr([html.Td("Spread Std"), html.Td(f"{spread_std:.4f}")]),
            html.Tr([html.Td("Z-Score (Last)"), html.Td(f"{last_z:.2f}")]),
            html.Tr([html.Td("Correlation (Last 30)"), html.Td(f"{last_corr:.2f}")]),
        ])
    ], className="table table-borderless text-light mb-0")

    # -------- Spread chart --------
    spread_fig = go.Figure()
    spread_fig.add_trace(go.Scatter(
        x=spread.index,
        y=spread,
        name="Spread"
    ))
    spread_fig.update_layout(
        title=f"Spread (Hedge Ratio: {hedge_ratio:.4f})",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )

    # -------- Z-score chart --------
    z_fig = go.Figure()
    z_fig.add_trace(go.Scatter(
        x=zscore.index,
        y=zscore,
        name="Z-score"
    ))
    z_fig.add_hline(y=2, line_dash="dash", line_color="red")
    z_fig.add_hline(y=-2, line_dash="dash", line_color="red")
    z_fig.update_layout(
        title="Z-score",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )

    # -------- Alert logic --------
    alert_message = ""
    alert_style = {}

    z_clean = zscore.dropna()
    if not z_clean.empty:
        latest_z = z_clean.iloc[-1]
        if latest_z > 2:
            alert_message = dbc.Alert(f"🔴 Overbought Alert: Z-score = {latest_z:.2f}", color="danger")
        elif latest_z < -2:
            alert_message = dbc.Alert(f"🟢 Oversold Alert: Z-score = {latest_z:.2f}", color="success")

    alert_div = html.Div(alert_message)

    # -------- Correlation chart --------
    corr_fig = go.Figure()
    corr_fig.add_trace(go.Scatter(
        x=corr.index,
        y=corr,
        name="Rolling Correlation"
    ))
    corr_fig.update_layout(
        title="Rolling Correlation",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )

    return (
        alert_div,
        live_prices,
        stats_table,
        price_fig,
        pair_stats_content,
        spread_fig,
        z_fig,
        corr_fig
    )




if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port)
    #app.run(debug=True)

# port = int(os.environ.get("PORT", 8050))
#     app.run(host="0.0.0.0", port=port)

