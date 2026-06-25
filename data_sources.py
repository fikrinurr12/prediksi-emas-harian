"""
data_sources.py
================
Modul pengambilan data harga emas dengan strategi berlapis:
    1. Cache disk (kalau masih segar, < 30 menit)
    2. Yahoo Finance via yfinance (sumber utama, sesuai Tabel 3.1 proposal)
    3. Twelve Data API (fallback, hanya dipakai kalau Yahoo Finance gagal
       total setelah beberapa kali percobaan -- misalnya karena rate limit)
    4. Cache disk lama (walau sudah agak basi, lebih baik daripada error)

Catatan akademis: Yahoo Finance via yfinance tetap menjadi sumber data utama
sesuai proposal skripsi. Twelve Data hanya berperan sebagai mekanisme
ketahanan (fallback) di sisi implementasi sistem, bukan pengganti sumber
data penelitian.
"""

import os
import time
import random
import pandas as pd
import requests

import yfinance as yf

# ----------------------------------------------------------------------
# Konfigurasi
# ----------------------------------------------------------------------
TICKER_YFINANCE = "GC=F"        # Gold Futures di Yahoo Finance
SYMBOL_TWELVEDATA = "XAU/USD"   # Gold spot di Twelve Data

CACHE_FILE = os.path.join("data", "cache_harga_emas.csv")
CACHE_MAX_AGE_SECONDS = 1800    # 30 menit


# ----------------------------------------------------------------------
# Cache disk
# ----------------------------------------------------------------------
def _read_disk_cache(allow_stale: bool = False):
    """
    Baca cache dari file.

    allow_stale=False (default): hanya kembalikan data kalau masih segar
        (< CACHE_MAX_AGE_SECONDS). Kembalikan None kalau basi/tidak ada.
    allow_stale=True: kembalikan data kapan saja file itu ada, walau sudah
        lama -- dipakai sebagai upaya terakhir saat semua sumber data gagal.
    """
    if not os.path.exists(CACHE_FILE):
        return None

    if not allow_stale:
        file_age = time.time() - os.path.getmtime(CACHE_FILE)
        if file_age > CACHE_MAX_AGE_SECONDS:
            return None

    try:
        df = pd.read_csv(CACHE_FILE)
        df["Date"] = pd.to_datetime(df["Date"])
        return df
    except Exception:
        return None


def _write_disk_cache(df: pd.DataFrame):
    try:
        os.makedirs("data", exist_ok=True)
        df.to_csv(CACHE_FILE, index=False)
    except Exception:
        pass


def get_cache_age_minutes():
    """Mengembalikan umur cache dalam menit, atau None kalau belum ada cache."""
    if not os.path.exists(CACHE_FILE):
        return None
    return (time.time() - os.path.getmtime(CACHE_FILE)) / 60


# ----------------------------------------------------------------------
# Sumber 1: Yahoo Finance (utama)
# ----------------------------------------------------------------------
def _fetch_from_yfinance(lookback_days: int = 60, max_retries: int = 3) -> pd.DataFrame:
    """
    Mengambil data dari Yahoo Finance dengan retry + exponential backoff.
    Melempar exception kalau semua percobaan gagal.
    """
    base_delay = 3
    last_error = None

    for attempt in range(max_retries):
        try:
            df = yf.download(TICKER_YFINANCE, period=f"{lookback_days}d", interval="1d",
                              auto_adjust=True, progress=False)

            if df.empty:
                raise ValueError("Data kosong dari Yahoo Finance.")

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            df = df.reset_index()
            return df

        except Exception as e:
            last_error = e
            error_text = str(e).lower()

            is_retryable = (
                "rate" in error_text
                or "too many requests" in error_text
                or "timeout" in error_text
                or "connection" in error_text
            )

            if is_retryable and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1.5)
                time.sleep(delay)
                continue
            else:
                break

    raise ConnectionError(f"Yahoo Finance gagal: {last_error}")


# ----------------------------------------------------------------------
# Sumber 2: Twelve Data (fallback)
# ----------------------------------------------------------------------
def _fetch_from_twelvedata(api_key: str, lookback_days: int = 60) -> pd.DataFrame:
    """
    Mengambil data harga emas (XAU/USD) dari Twelve Data sebagai cadangan
    ketika Yahoo Finance tidak bisa diakses.

    Mengembalikan DataFrame dengan kolom yang sama persis dengan yfinance
    (Date, Open, High, Low, Close, Volume) supaya kompatibel dengan
    fungsi indikator teknikal yang sudah ada.
    """
    if not api_key:
        raise ValueError("API key Twelve Data tidak tersedia.")

    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": SYMBOL_TWELVEDATA,
        "interval": "1day",
        "outputsize": min(lookback_days, 5000),
        "apikey": api_key,
    }

    response = requests.get(url, params=params, timeout=15)
    data = response.json()

    if data.get("status") == "error" or "values" not in data:
        error_message = data.get("message", "Respons tidak valid dari Twelve Data.")
        raise ConnectionError(f"Twelve Data gagal: {error_message}")

    records = data["values"]

    df = pd.DataFrame(records)
    df = df.rename(columns={
        "datetime": "Date",
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume",
    })

    # Twelve Data mengembalikan data terbaru di baris pertama -> urutkan
    # ulang menjadi kronologis (lama ke baru), sama seperti yfinance
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").reset_index(drop=True)

    numeric_cols = ["Open", "High", "Low", "Close"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Twelve Data kadang tidak menyediakan volume untuk pasangan forex/komoditas
    if "Volume" not in df.columns:
        df["Volume"] = 0
    else:
        df["Volume"] = pd.to_numeric(df["Volume"], errors="coerce").fillna(0)

    df = df[["Date", "Open", "High", "Low", "Close", "Volume"]]

    return df


# ----------------------------------------------------------------------
# Fungsi utama: coba semua sumber secara berurutan
# ----------------------------------------------------------------------
def get_latest_gold_data(lookback_days: int = 60, twelvedata_api_key: str = None):
    """
    Mengambil data harga emas terbaru dengan urutan prioritas:
        1. Cache disk segar (< 30 menit)
        2. Yahoo Finance
        3. Twelve Data (kalau API key disediakan)
        4. Cache disk lama (walau basi)

    Mengembalikan tuple: (DataFrame, sumber_data: str)
    sumber_data salah satu dari: "cache", "yfinance", "twelvedata", "cache_basi"

    Melempar ConnectionError kalau semua sumber gagal dan tidak ada cache.
    """
    # 1. Cache segar
    cached_df = _read_disk_cache(allow_stale=False)
    if cached_df is not None:
        return cached_df, "cache"

    # 2. Yahoo Finance
    try:
        df = _fetch_from_yfinance(lookback_days=lookback_days)
        _write_disk_cache(df)
        return df, "yfinance"
    except Exception as yf_error:
        yfinance_error = yf_error

    # 3. Twelve Data (fallback)
    if twelvedata_api_key:
        try:
            df = _fetch_from_twelvedata(twelvedata_api_key, lookback_days=lookback_days)
            _write_disk_cache(df)
            return df, "twelvedata"
        except Exception as td_error:
            twelvedata_error = td_error
    else:
        twelvedata_error = "API key Twelve Data tidak diset."

    # 4. Cache lama walau basi, sebagai upaya terakhir
    stale_df = _read_disk_cache(allow_stale=True)
    if stale_df is not None:
        return stale_df, "cache_basi"

    raise ConnectionError(
        f"Semua sumber data gagal. "
        f"Yahoo Finance: {yfinance_error}. "
        f"Twelve Data: {twelvedata_error}. "
        f"Tidak ada cache tersimpan sebagai cadangan."
    )
