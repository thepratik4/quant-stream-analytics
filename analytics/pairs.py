import pandas as pd
import numpy as np
from statsmodels.regression.linear_model import OLS
from statsmodels.tools.tools import add_constant
from statsmodels.tsa.stattools import adfuller


def compute_hedge_ratio(price_a: pd.Series, price_b: pd.Series):
    """
    OLS hedge ratio: price_a ~ beta * price_b
    """
    df = pd.concat([price_a, price_b], axis=1).dropna()
    if len(df) < 10:
        return None

    y = df.iloc[:, 0]
    x = add_constant(df.iloc[:, 1])

    model = OLS(y, x).fit()
    return model.params.iloc[1]


def compute_spread(price_a: pd.Series, price_b: pd.Series, hedge_ratio: float):
    """
    Spread = price_a - hedge_ratio * price_b
    """
    df = pd.concat([price_a, price_b], axis=1).dropna()
    spread = df.iloc[:, 0] - hedge_ratio * df.iloc[:, 1]
    return spread


def compute_zscore(series: pd.Series, window: int = 30):
    """
    Rolling z-score
    """
    mean = series.rolling(window).mean()
    std = series.rolling(window).std()
    zscore = (series - mean) / std
    return zscore


def rolling_correlation(series_a: pd.Series, series_b: pd.Series, window: int = 30):
    """
    Rolling correlation of returns
    """
    returns_a = series_a.pct_change()
    returns_b = series_b.pct_change()
    return returns_a.rolling(window).corr(returns_b)


def adf_test(series: pd.Series):
    """
    Augmented Dickey-Fuller test
    """
    series = series.dropna()
    if len(series) < 20:
        return None

    result = adfuller(series)
    return {
        "adf_stat": result[0],
        "p_value": result[1],
        "is_stationary": result[1] < 0.05
    }
