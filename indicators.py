"""
indicators.py
=============
Implementasi rumus indikator teknikal sesuai Bab II Landasan Teori:
    2.2.13 Simple Moving Average (SMA)        - persamaan (2)
    2.2.14 Exponential Moving Average (EMA)   - persamaan (3), (4)
    2.2.15 Relative Strength Index (RSI)      - persamaan (5)
    2.2.16 Stochastic Oscillator (STI)        - persamaan (6)
    2.2.17 Price Rate of Change (PROC)        - persamaan (7)

Semua fungsi menerima pandas Series/DataFrame dan mengembalikan pandas Series,
supaya mudah digabungkan langsung sebagai kolom baru.
"""

import pandas as pd
import numpy as np


def simple_moving_average(close: pd.Series, window: int = 14) -> pd.Series:
    """
    SMA = (sum of closing price selama n periode) / n
    Persamaan (2).
    """
    return close.rolling(window=window).mean()


def exponential_moving_average(close: pd.Series, window: int = 14) -> pd.Series:
    """
    EMA = K * (Close_today - EMA_prev) + EMA_prev,  K = 2 / (N + 1)
    Persamaan (3) dan (4).

    Catatan: pandas .ewm(span=N, adjust=False) secara matematis identik
    dengan rumus rekursif EMA klasik tersebut.
    """
    return close.ewm(span=window, adjust=False).mean()


def relative_strength_index(close: pd.Series, window: int = 14) -> pd.Series:
    """
    RSI = (rata-rata kenaikan / rata-rata penurunan) * 100, lalu dinormalisasi
    ke skala 0-100 menggunakan rumus standar Wilder.
    Persamaan (5), dengan penyesuaian standar agar berada di rentang 0-100
    (RSI = 100 - 100/(1+RS) dimana RS = avg_gain/avg_loss).
    """
    delta = close.diff()

    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)  # hindari div-by-zero
    rsi = 100 - (100 / (1 + rs))

    return rsi


def stochastic_oscillator(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    """
    STI = ((Close_today - Lowest_low) / (Highest_high - Lowest_low)) * 100
    Persamaan (6).
    """
    lowest_low = low.rolling(window=window).min()
    highest_high = high.rolling(window=window).max()

    sti = ((close - lowest_low) / (highest_high - lowest_low)) * 100
    return sti


def price_rate_of_change(close: pd.Series, window: int = 9) -> pd.Series:
    """
    PROC = (Close_t - Close_(t-x)) / Close_(t-x)
    Persamaan (7).
    """
    return close.pct_change(periods=window)


def add_all_indicators(df: pd.DataFrame, sma_window=14, ema_window=14,
                        rsi_window=14, sto_window=14, proc_window=9) -> pd.DataFrame:
    """
    Menambahkan kolom SMA, EMA, RSI, STI, PROC ke dataframe OHLCV.
    Sesuai Tabel 3.2 Feature Engineering.
    """
    df = df.copy()

    df["SMA"] = simple_moving_average(df["Close"], window=sma_window)
    df["EMA"] = exponential_moving_average(df["Close"], window=ema_window)
    df["RSI"] = relative_strength_index(df["Close"], window=rsi_window)
    df["STI"] = stochastic_oscillator(df["High"], df["Low"], df["Close"], window=sto_window)
    df["PROC"] = price_rate_of_change(df["Close"], window=proc_window)

    return df
