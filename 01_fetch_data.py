"""
01_fetch_data.py
=================
Tahap: 3.4 Pengumpulan Data (Bab III Metodologi)

Mengambil data historis harga emas (Gold Futures, ticker GC=F) dari Yahoo
Finance menggunakan pustaka yfinance, dengan interval harian selama 5 tahun
ke belakang. Atribut yang diambil: Open, High, Low, Close, Volume.

Cara jalankan:
    python 01_fetch_data.py

Catatan:
    - Jalankan script ini di komputer/server yang punya akses internet normal
      ke domain query1.finance.yahoo.com / query2.finance.yahoo.com.
    - Hasil disimpan ke data/gold_raw.csv
"""

import yfinance as yf
import pandas as pd
import os

# ----------------------------------------------------------------------
# Konfigurasi
# ----------------------------------------------------------------------
TICKER = "GC=F"          # Gold Futures (COMEX). Alternatif: "GLD" (ETF emas)
PERIOD = "5y"             # 5 tahun ke belakang, sesuai Tabel 3.1
INTERVAL = "1d"           # Interval harian, sesuai Tabel 3.1
OUTPUT_PATH = "data/gold_raw.csv"


def fetch_gold_data(ticker: str = TICKER, period: str = PERIOD, interval: str = INTERVAL) -> pd.DataFrame:
    """Mengunduh data historis emas dari Yahoo Finance."""
    print(f"Mengunduh data {ticker} | periode={period} | interval={interval} ...")

    df = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False)

    if df.empty:
        raise ValueError(
            f"Data kosong untuk ticker '{ticker}'. "
            "Cek koneksi internet atau coba ticker alternatif seperti 'GLD'."
        )

    # yfinance versi terbaru kadang mengembalikan MultiIndex kolom (Price, Ticker)
    # saat hanya 1 ticker diminta. Kita ratakan supaya jadi kolom biasa.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.reset_index()  # 'Date' jadi kolom biasa, bukan index

    # Pastikan urutan kolom konsisten: Date, Open, High, Low, Close, Volume
    expected_cols = ["Date", "Open", "High", "Low", "Close", "Volume"]
    df = df[[c for c in expected_cols if c in df.columns]]

    print(f"Berhasil mengunduh {len(df)} baris data.")
    print(f"Rentang tanggal: {df['Date'].min()} s.d. {df['Date'].max()}")

    return df


def main():
    os.makedirs("data", exist_ok=True)

    df = fetch_gold_data()

    df.to_csv(OUTPUT_PATH, index=False)
    print(f"\nData mentah disimpan ke: {OUTPUT_PATH}")
    print("\nPreview 5 baris pertama:")
    print(df.head())
    print("\nPreview 5 baris terakhir:")
    print(df.tail())
    print("\nInfo missing value per kolom:")
    print(df.isna().sum())


if __name__ == "__main__":
    main()
