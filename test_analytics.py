import time
from ingestion.binance_ws import start_binance_socket
from analytics.statistics import resample_ohlc
from analytics.pairs import (
    compute_hedge_ratio,
    compute_spread,
    compute_zscore,
    rolling_correlation,
    adf_test
)

start_binance_socket(["BTCUSDT", "ETHUSDT"])

print("Collecting data...")
time.sleep(20)

btc = resample_ohlc("BTCUSDT", "1s")["close"]
eth = resample_ohlc("ETHUSDT", "1s")["close"]

beta = compute_hedge_ratio(btc, eth)
print("Hedge Ratio:", beta)

spread = compute_spread(btc, eth, beta)
z = compute_zscore(spread)

corr = rolling_correlation(btc, eth)
adf = adf_test(spread)

print("\nLatest Spread:", spread.iloc[-1])
print("Latest Z-score:", z.iloc[-1])
print("Latest Rolling Corr:", corr.iloc[-1])
print("ADF Test:", adf)
