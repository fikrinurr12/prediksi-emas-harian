"""
candle_rejection.py
====================
Konversi dari bagian "Candle Rejection" pada indikator Pine Script asli.

Logika asli (Pine Script):
    upperWick = high - max(open, close)
    lowerWick = min(open, close) - low
    candleRange = high - low
    isRejectBuy  = (lowerWick / candleRange) * 100 >= lowerWickThreshold
    isRejectSell = (upperWick / candleRange) * 100 >= upperWickThreshold

Sinyal RS (Reject Sell) muncul di atas candle (high) -> upper wick panjang,
mengindikasikan penolakan harga lebih tinggi (potensi turun).
Sinyal RB (Reject Buy) muncul di bawah candle (low) -> lower wick panjang,
mengindikasikan penolakan harga lebih rendah (potensi naik).
"""

import pandas as pd
import numpy as np


def detect_candle_rejection(
    df: pd.DataFrame,
    upper_wick_threshold: float = 61.0,
    lower_wick_threshold: float = 61.0,
) -> pd.DataFrame:
    """
    Menambahkan kolom deteksi candle rejection ke DataFrame OHLC.

    Parameters
    ----------
    df : DataFrame dengan kolom Open, High, Low, Close
    upper_wick_threshold : persentase minimum upper wick dari candle range
        untuk dianggap sinyal "Reject Sell" (RS)
    lower_wick_threshold : persentase minimum lower wick dari candle range
        untuk dianggap sinyal "Reject Buy" (RB)

    Returns
    -------
    DataFrame asli + kolom baru:
        upper_wick, lower_wick, candle_range,
        upper_wick_pct, lower_wick_pct,
        is_reject_sell (bool), is_reject_buy (bool)
    """
    df = df.copy()

    upper_wick = df["High"] - np.maximum(df["Open"], df["Close"])
    lower_wick = np.minimum(df["Open"], df["Close"]) - df["Low"]
    candle_range = df["High"] - df["Low"]

    # Hindari pembagian dengan nol (candle range = 0, kasus langka tapi mungkin terjadi)
    upper_wick_pct = np.where(candle_range > 0, (upper_wick / candle_range) * 100, 0)
    lower_wick_pct = np.where(candle_range > 0, (lower_wick / candle_range) * 100, 0)

    df["upper_wick"] = upper_wick
    df["lower_wick"] = lower_wick
    df["candle_range"] = candle_range
    df["upper_wick_pct"] = upper_wick_pct
    df["lower_wick_pct"] = lower_wick_pct

    df["is_reject_sell"] = df["upper_wick_pct"] >= upper_wick_threshold
    df["is_reject_buy"] = df["lower_wick_pct"] >= lower_wick_threshold

    return df
