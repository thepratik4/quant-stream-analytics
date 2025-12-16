from dash import Dash, html, dcc, Input, Output
from ingestion.binance_ws import start_binance_socket, latest_ticks, lock
import plotly.graph_objects as go
from analytics.statistics import resample_ohlc
from analytics.pairs import (
    compute_hedge_ratio,
    compute_spread,
    compute_zscore,
    rolling_correlation
)


# Start WebSocket ingestion
# Start WebSocket ingestion
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "AVAXUSDT"]
start_binance_socket(SYMBOLS)

app = Dash(__name__)

app.layout = html.Div([
    html.H1("Quant Analytics Dashboard"),
    
    html.Div([
        html.Div([
            html.Label("Symbol 1"),
            dcc.Dropdown(
                id="symbol-1-dropdown",
                options=[{"label": s, "value": s} for s in SYMBOLS],
                value="BTCUSDT",
                clearable=False
            )
        ], style={"display": "inline-block", "width": "200px", "marginRight": "20px"}),

        html.Div([
            html.Label("Symbol 2"),
            dcc.Dropdown(
                id="symbol-2-dropdown",
                options=[{"label": s, "value": s} for s in SYMBOLS],
                value="ETHUSDT",
                clearable=False
            )
        ], style={"display": "inline-block", "width": "200px", "marginRight": "20px"}),

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
        ], style={"display": "inline-block", "width": "200px"}),
    ], style={"padding": "20px", "borderBottom": "1px solid #ddd"}),

    html.Div(
        id="alert-box",
        style={
            "padding": "10px",
            "marginBottom": "20px",
            "fontWeight": "bold",
            "fontSize": "18px"
        }
    ),

    html.Div(id="live-prices"),

    dcc.Graph(id="price-chart"),
    
    html.Div(id="stats-table"),  # Table for Mean, Std, Min, Max
    
    html.H3("Pair Summary Stats", style={"textAlign": "center"}),
    html.Div(id="pair-stats-table"),

    dcc.Graph(id="spread-chart"),
    dcc.Graph(id="zscore-chart"),
    dcc.Graph(id="corr-chart"),

    dcc.Interval(
        id="interval",
        interval=2000,  # 2 seconds (safer for analytics)
        n_intervals=0
    )
])


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
        for symbol, data in latest_ticks.items():
            rows.append(
                html.P(
                    f"{symbol} | Price: {data['price']} | Qty: {data['qty']}"
                )
            )

    live_prices = rows if rows else "Waiting for live data..."

    # Empty placeholders
    empty_fig = go.Figure()
    alert_div = html.Div("")
    empty_table = html.Div()

    # -------- Resampled data --------
    df1 = resample_ohlc(sym1, timeframe)
    df2 = resample_ohlc(sym2, timeframe)

    if df1.empty or df2.empty:
        return alert_div, live_prices, empty_table, empty_fig, empty_table, empty_fig, empty_fig, empty_fig

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
        yaxis2=dict(overlaying="y", side="right")
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
    ], style={"width": "50%", "margin": "20px auto", "border": "1px solid black", "textAlign": "center"})

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
    ], style={"width": "50%", "margin": "20px auto", "border": "1px solid black", "textAlign": "center"})

    # -------- Spread chart --------
    spread_fig = go.Figure()
    spread_fig.add_trace(go.Scatter(
        x=spread.index,
        y=spread,
        name="Spread"
    ))
    spread_fig.update_layout(title=f"Spread (Hedge Ratio: {hedge_ratio:.4f})")

    # -------- Z-score chart --------
    z_fig = go.Figure()
    z_fig.add_trace(go.Scatter(
        x=zscore.index,
        y=zscore,
        name="Z-score"
    ))
    z_fig.add_hline(y=2, line_dash="dash", line_color="red")
    z_fig.add_hline(y=-2, line_dash="dash", line_color="red")
    z_fig.update_layout(title="Z-score")

    # -------- Alert logic --------
    alert_message = ""
    alert_style = {}

    z_clean = zscore.dropna()
    if not z_clean.empty:
        latest_z = z_clean.iloc[-1]
        if latest_z > 2:
            alert_message = f"🔴 Overbought Alert: Z-score = {latest_z:.2f}"
            alert_style = {"color": "red", "fontWeight": "bold"}
        elif latest_z < -2:
            alert_message = f"🟢 Oversold Alert: Z-score = {latest_z:.2f}"
            alert_style = {"color": "green", "fontWeight": "bold"}

    alert_div = html.Div(alert_message, style=alert_style)

    # -------- Correlation chart --------
    corr_fig = go.Figure()
    corr_fig.add_trace(go.Scatter(
        x=corr.index,
        y=corr,
        name="Rolling Correlation"
    ))
    corr_fig.update_layout(title="Rolling Correlation")

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

    app.run(debug=True)


