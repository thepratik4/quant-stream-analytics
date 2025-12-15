import asyncio
import threading
from binance import AsyncClient, BinanceSocketManager
from analytics.statistics import add_tick

latest_ticks = {}
lock = threading.Lock()


async def _socket_loop(symbols):
    client = await AsyncClient.create()
    bsm = BinanceSocketManager(client)

    # Use ticker stream (SAFE, throttled by Binance)
    streams = [f"{s.lower()}@ticker" for s in symbols]
    socket = bsm.multiplex_socket(streams)

    async with socket as stream:
        while True:
            msg = await stream.recv()

            if "data" not in msg:
                continue

            data = msg["data"]

            symbol = data["s"]
            price = float(data["c"])   # last price
            qty = float(data["v"])     # rolling volume
            ts = data["E"]             # event time

            with lock:
                latest_ticks[symbol] = {
                    "price": price,
                    "qty": qty,
                    "timestamp": ts
                }
            add_tick(symbol, price, qty, ts)

def start_binance_socket(symbols):
    """
    Stable Binance WebSocket using throttled ticker stream
    """
    def runner():
        asyncio.run(_socket_loop(symbols))

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
