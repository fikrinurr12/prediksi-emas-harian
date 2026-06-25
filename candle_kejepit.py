"""
candle_kejepit.py
==================
Konversi dari bagian "Candle Kejepit" pada indikator Pine Script asli.

PENTING: Logika pelabelan di bawah ini SENGAJA dipertahankan persis sama
dengan kode Pine Script asli, termasuk penamaan variabel yang terlihat
"terbalik" (isBearish dikomentari sebagai "Pola Beli", lalu warnanya
dibalik lagi saat assign box). Ini bukan kesalahan konversi -- ini
mereplikasi behaviour yang sudah divalidasi langsung oleh pengguna di
TradingView. Jangan "diperbaiki" tanpa konfirmasi ulang ke pemilik kode.

Pola dideteksi dari 5 candle berurutan (indeks relatif terhadap candle
saat ini, c1=candle 1 bar lalu, c5=candle 5 bar lalu):
    isBearish (asli disebut "Pola Beli / Hijau terjepit"):
        c5 < o5 and c4 < o4 and c3 > o3 and c2 < o2 and c1 < o1
        (4 candle merah mengapit 1 candle hijau di tengah)
    isBullish (asli disebut "Pola Jual / Merah terjepit"):
        c5 > o5 and c4 > o4 and c3 < o3 and c2 > o2 and c1 > o1
        (4 candle hijau mengapit 1 candle merah di tengah)

Lalu warna box akhir (sesuai kode asli):
    boxColor = isBullish ? sellColor : buyColor

Area candle ke-3 (yang terjepit di tengah, c3/o3/h3/l3) dipakai sebagai
batas atas-bawah box zona.
"""

import pandas as pd
import numpy as np


def detect_candle_kejepit(df: pd.DataFrame) -> pd.DataFrame:
    """
    Mendeteksi pola candle kejepit pada setiap baris (memakai 5 candle
    candle saat ini dan 4 candle sebelumnya: index i-4 s.d. i).

    Parameters
    ----------
    df : DataFrame dengan kolom Open, High, Low, Close, terurut kronologis
         (lama -> baru), index default 0..n-1

    Returns
    -------
    DataFrame asli + kolom baru:
        is_bearish_kejepit : bool -- pola "isBearish" sesuai kode asli
        is_bullish_kejepit : bool -- pola "isBullish" sesuai kode asli
        zone_high, zone_low : float -- batas box dari candle ke-3 (tengah)
        box_color : str -- "sell" atau "buy" sesuai pembalikan warna di kode asli
    """
    df = df.copy()

    o = df["Open"].values
    c = df["Close"].values
    h = df["High"].values
    l = df["Low"].values

    n = len(df)
    is_bearish = np.zeros(n, dtype=bool)
    is_bullish = np.zeros(n, dtype=bool)
    zone_high = np.full(n, np.nan)
    zone_low = np.full(n, np.nan)

    # Butuh minimal 5 candle (index i-4 sampai i) untuk evaluasi pola.
    # c1..c5 di Pine Script adalah close[1]..close[5] relatif terhadap bar
    # SAAT INI (bar real-time belum closed). Untuk data historis yang
    # semuanya sudah closed, kita petakan:
    #   candle "saat ini" (bar paling baru dalam jendela) -> index i
    #   c1 = close di i-1 (1 bar sebelumnya)
    #   c2 = close di i-2
    #   c3 = close di i-3  <- candle tengah yang "terjepit"
    #   c4 = close di i-4
    #   c5 = close di i-5
    # Sehingga butuh index i-5 s.d. i-1 tersedia -> mulai dari index 5.
    for i in range(5, n):
        c1, o1 = c[i - 1], o[i - 1]
        c2, o2 = c[i - 2], o[i - 2]
        c3, o3 = c[i - 3], o[i - 3]
        c4, o4 = c[i - 4], o[i - 4]
        c5, o5 = c[i - 5], o[i - 5]
        h3, l3 = h[i - 3], l[i - 3]

        bearish = (c5 < o5) and (c4 < o4) and (c3 > o3) and (c2 < o2) and (c1 < o1)
        bullish = (c5 > o5) and (c4 > o4) and (c3 < o3) and (c2 > o2) and (c1 > o1)

        if bullish:
            is_bullish[i] = True
            zone_high[i] = h3
            zone_low[i] = l3
        elif bearish:
            is_bearish[i] = True
            zone_high[i] = h3
            zone_low[i] = l3

    df["is_bearish_kejepit"] = is_bearish
    df["is_bullish_kejepit"] = is_bullish
    df["zone_high"] = zone_high
    df["zone_low"] = zone_low

    # Sesuai kode asli: boxColor = isBullish ? sellColor : buyColor
    box_color = np.where(is_bullish, "sell", np.where(is_bearish, "buy", None))
    df["box_color"] = box_color

    return df


def resample_to_timeframe(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """
    Meresample data OHLCV harian/menitan ke timeframe lain, sebagai
    pengganti request.security() multi-timeframe di Pine Script.

    rule mengikuti format pandas resample, contoh: "15min", "1h", "4h", "1D"
    """
    df = df.copy()
    df = df.set_index("Date")

    resampled = df.resample(rule).agg({
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum",
    }).dropna()

    resampled = resampled.reset_index()
    return resampled
