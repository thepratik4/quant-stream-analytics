import sqlite3
import os
import pandas as pd
from contextlib import contextmanager

DB_NAME = "market_data.db"

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """
    Initialize the SQLite database and create the ohlc_data table if it doesn't exist.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ohlc_data (
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                UNIQUE(symbol, timeframe, timestamp)
            )
        ''')
        conn.commit()
        print(f"Database {DB_NAME} initialized.")

def insert_ohlc(df: pd.DataFrame, symbol: str, timeframe: str):
    """
    Insert resampled OHLC data into the database.
    
    Args:
        df: DataFrame with datetime index and columns [open, high, low, close, volume]
        symbol: e.g., 'BTCUSDT'
        timeframe: e.g., '1s', '1m'
    """
    if df.empty:
        return

    # Prepare data for insertion
    records = []
    for ts, row in df.iterrows():
        records.append((
            symbol,
            timeframe,
            ts.strftime('%Y-%m-%d %H:%M:%S'),
            row['open'],
            row['high'],
            row['low'],
            row['close'],
            row['volume']
        ))

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.executemany('''
            INSERT OR IGNORE INTO ohlc_data 
            (symbol, timeframe, timestamp, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', records)
        conn.commit()
