"""
terbang_terjun.py
==================
Konversi dari bagian "Terbang Terjun" pada indikator Pine Script asli.

Logika asli (Pine Script):
    1. Hitung linear regression oscillator manual atas N bar terakhir
       (bukan least-squares biasa, tapi formula spesifik di kode asli):

           m = (n*sum_xy - sum_x*sum_y) / (n*sum_x_squared - sum_x*sum_x)
           c = (sum_y - m*sum_x) / n
           oscillator = -(m * bar_index + c)

       Catatan: rumus ini menghitung slope (m) dan intercept (c) dari regresi
       linear y=src terhadap x=index_relatif (0..n-1, dengan i=0 adalah bar
       PALING BARU karena pengindeksan Pine Script mundur/look-back), lalu
       diproyeksikan balik ke bar_index dan dibalik tandanya (*-1).

    2. Normalisasi z-score atas 100 bar:
           oscillator_norm = (oscillator - SMA(oscillator, 100)) / StDev(oscillator, 100)

    3. Sinyal SELL: crossunder(osc, osc[2]) DAN osc > upper_threshold
       Sinyal BUY : crossover(osc, osc[2]) DAN osc < lower_threshold

    4. ATR(14) dipakai untuk menentukan jarak label dari harga (murni visual
       di Pine Script, tidak relevan untuk versi Python non-visual, tetap
       disediakan sebagai kolom referensi).
"""

import pandas as pd
import numpy as np


def _linear_regression_oscillator(src: np.ndarray, n: int) -> np.ndarray:
    """
    Replikasi rumus linear_regression_osc_original dari Pine Script.

    Untuk setiap titik i (i >= n-1), regresi dihitung memakai n nilai
    src[i-n+1 .. i], dengan pengindeksan x = 0..n-1 di mana x=0 berkorespondensi
    dengan candle PALING BARU dalam jendela tersebut (meniru cara Pine Script
    mengakses src[0], src[1], ... src[n-1] mundur dari bar saat ini).
    """
    length = len(src)
    result = np.full(length, np.nan)

    x_arr = np.arange(n)  # 0, 1, ..., n-1
    sum_x = x_arr.sum()
    sum_x_squared = (x_arr ** 2).sum()
    denom = n * sum_x_squared - sum_x * sum_x

    if denom == 0:
        return result

    for i in range(n - 1, length):
        # window mundur dari bar i: src[i], src[i-1], ..., src[i-n+1]
        # ini sesuai src[0], src[1], ..., src[n-1] di Pine Script (relatif ke bar i)
        window = src[i - n + 1: i + 1][::-1]  # dibalik agar window[0] = src[i] (bar terbaru)

        sum_y = window.sum()
        sum_xy = (x_arr * window).sum()

        m = (n * sum_xy - sum_x * sum_y) / denom
        c = (sum_y - m * sum_x) / n

        # oscillator = -(m * bar_index + c), tapi karena bar_index absolut
        # tidak relevan untuk hasil relatif/normalisasi, kita pakai i sebagai
        # proxy bar_index (konsisten karena dipakai di rumus yang sama setiap saat)
        result[i] = -(m * i + c)

    return result


def detect_terbang_terjun(
    df: pd.DataFrame,
    length: int = 20,
    upper_threshold: float = 1.5,
    lower_threshold: float = -1.5,
    norm_window: int = 100,
    atr_window: int = 14,
) -> pd.DataFrame:
    """
    Menambahkan kolom oscillator Terbang Terjun dan sinyal BUY/SELL.

    Parameters
    ----------
    df : DataFrame dengan kolom Open, High, Low, Close
    length : panjang window regresi linear (default 20, sesuai kode asli)
    upper_threshold, lower_threshold : ambang sinyal sesuai kode asli (1.5 / -1.5)
    norm_window : window untuk normalisasi z-score (default 100)
    atr_window : window untuk ATR (default 14)

    Returns
    -------
    DataFrame asli + kolom baru:
        linreg_osc_raw, linreg_osc_norm,
        atr,
        is_sell_signal, is_buy_signal
    """
    df = df.copy()
    close = df["Close"].values.astype(float)

    # 1. Oscillator mentah
    osc_raw = _linear_regression_oscillator(close, length)
    df["linreg_osc_raw"] = osc_raw

    # 2. Normalisasi z-score atas norm_window bar
    osc_series = pd.Series(osc_raw)
    rolling_mean = osc_series.rolling(window=norm_window).mean()
    rolling_std = osc_series.rolling(window=norm_window).std()
    osc_norm = (osc_series - rolling_mean) / rolling_std
    df["linreg_osc_norm"] = osc_norm.values

    # 3. ATR (referensi, untuk jarak label visual di versi Pine Script asli)
    high, low, prev_close = df["High"].values, df["Low"].values, df["Close"].shift(1).values
    tr = np.maximum(
        high - low,
        np.maximum(np.abs(high - prev_close), np.abs(low - prev_close))
    )
    atr = pd.Series(tr).rolling(window=atr_window).mean()
    df["atr"] = atr.values

    # 4. Deteksi crossover/crossunder terhadap osc_norm[i-2] (shift 2, sesuai kode asli)
    osc_shifted2 = osc_norm.shift(2)

    crossunder = (osc_norm < osc_shifted2) & (osc_norm.shift(1) >= osc_shifted2.shift(1))
    crossover = (osc_norm > osc_shifted2) & (osc_norm.shift(1) <= osc_shifted2.shift(1))

    df["is_sell_signal"] = crossunder & (osc_norm > upper_threshold)
    df["is_buy_signal"] = crossover & (osc_norm < lower_threshold)

    return df
