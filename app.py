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
start_binance_socket(["BTCUSDT", "ETHUSDT"])

app = Dash(__name__)

app.layout = html.Div([
    html.H1("Quant Analytics Dashboard"),
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
    Output("price-chart", "figure"),
    Output("spread-chart", "figure"),
    Output("zscore-chart", "figure"),
    Output("corr-chart", "figure"),
    Input("interval", "n_intervals")
)
def update_dashboard(n):

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

    # -------- Resampled data --------
    btc_df = resample_ohlc("BTCUSDT", "1s")
    eth_df = resample_ohlc("ETHUSDT", "1s")

    if btc_df.empty or eth_df.empty:
        return alert_div, live_prices, empty_fig, empty_fig, empty_fig, empty_fig

    btc_close = btc_df["close"]
    eth_close = eth_df["close"]

    # -------- Price chart --------
    price_fig = go.Figure()
    price_fig.add_trace(go.Scatter(
        x=btc_close.index,
        y=btc_close,
        name="BTCUSDT"
    ))
    price_fig.add_trace(go.Scatter(
        x=eth_close.index,
        y=eth_close,
        name="ETHUSDT",
        yaxis="y2"
    ))
    price_fig.update_layout(
        title="Prices (1s)",
        yaxis2=dict(overlaying="y", side="right")
    )

    # -------- Analytics --------
    hedge_ratio = compute_hedge_ratio(btc_close, eth_close)
    if hedge_ratio is None:
        return alert_div, live_prices, price_fig, empty_fig, empty_fig, empty_fig

    spread = compute_spread(btc_close, eth_close, hedge_ratio)
    zscore = compute_zscore(spread, window=30)
    corr = rolling_correlation(btc_close, eth_close, window=30)

    # -------- Spread chart --------
    spread_fig = go.Figure()
    spread_fig.add_trace(go.Scatter(
        x=spread.index,
        y=spread,
        name="Spread"
    ))
    spread_fig.update_layout(title="Spread")

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
            alert_style = {"color": "red"}
        elif latest_z < -2:
            alert_message = f"🟢 Oversold Alert: Z-score = {latest_z:.2f}"
            alert_style = {"color": "green"}

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
        price_fig,
        spread_fig,
        z_fig,
        corr_fig
    )




if __name__ == "__main__":

    app.run(debug=True)


