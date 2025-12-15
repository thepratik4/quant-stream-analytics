from dash import Dash, html, dcc, Input, Output
from ingestion.binance_ws import start_binance_socket, latest_ticks, lock

# Start WebSocket ingestion
start_binance_socket(["BTCUSDT", "ETHUSDT"])

app = Dash(__name__)

app.layout = html.Div([
    html.H1("Quant Analytics Dashboard"),

    html.Div(id="live-prices"),

    dcc.Interval(
        id="interval",
        interval=1000,  # 1 second
        n_intervals=0
    )
])

@app.callback(
    Output("live-prices", "children"),
    Input("interval", "n_intervals")
)
def update_prices(n):
    rows = []

    with lock:
        for symbol, data in latest_ticks.items():
            rows.append(
                html.P(
                    f"{symbol} | Price: {data['price']} | Qty: {data['qty']}"
                )
            )

    if not rows:
        return "Waiting for live data..."

    return rows


if __name__ == "__main__":
    app.run(debug=True)
