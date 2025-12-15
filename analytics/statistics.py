import pandas as pd
import time
from collections import defaultdict, deque
from threading import Lock

# Rolling tick buffer
# Each symbol → deque of (timestamp, price, qty)
TICK_BUFFER = defaultdict(lambda: deque(maxlen=10_000))
buffer_lock = Lock()


def add_tick(symbol, price, qty, timestamp_ms):
    """
    Add a tick to rolling buffer
    """
    with buffer_lock:
        TICK_BUFFER[symbol].append(
            {
                "timestamp": pd.to_datetime(timestamp_ms, unit="ms"),
                "price": price,
                "qty": qty
            }
        )


def get_tick_dataframe(symbol):
    """
    Convert tick buffer to pandas DataFrame
    """
    with buffer_lock:
        data = list(TICK_BUFFER[symbol])

    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)
    df.set_index("timestamp", inplace=True)
    df.sort_index(inplace=True)
    return df


def resample_ohlc(symbol, timeframe="1s"):
    """
    Resample ticks to OHLCV
    timeframe: '1s', '1min', '5min'
    """
    df = get_tick_dataframe(symbol)

    if df.empty:
        return pd.DataFrame()

    ohlc = df["price"].resample(timeframe).ohlc()
    volume = df["qty"].resample(timeframe).sum()

    result = ohlc.copy()
    result["volume"] = volume

    # Drop incomplete candles
    result.dropna(inplace=True)

    return result
