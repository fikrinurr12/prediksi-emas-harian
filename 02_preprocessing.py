"""
02_preprocessing.py
====================
Tahap: 3.6 Preprocessing (Bab III Metodologi)
    3.6.1 Pembersihan Data
    3.6.2 Feature Engineering
    3.6.3 Pelabelan Data
    (3.6.4 Normalisasi Data dilakukan terpisah saat training, lihat 03_train_model.py,
     supaya scaler hanya di-fit pada data latih dan tidak terjadi data leakage)

Input : data/gold_raw.csv      (hasil dari 01_fetch_data.py)
Output: data/gold_processed.csv

Cara jalankan:
    python 02_preprocessing.py
"""

import pandas as pd
import os
from indicators import add_all_indicators

INPUT_PATH = "data/gold_raw.csv"
OUTPUT_PATH = "data/gold_processed.csv"


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """3.6.1 Pembersihan Data: handle duplikat & data hilang."""
    before = len(df)

    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").reset_index(drop=True)

    df = df.drop_duplicates(subset="Date", keep="last")

    # Baris dengan OHLC kosong dibuang (biasanya hari libur pasar / data error)
    df = df.dropna(subset=["Open", "High", "Low", "Close"])

    after = len(df)
    print(f"Pembersihan data: {before} baris -> {after} baris "
          f"({before - after} baris dihapus karena duplikat/kosong)")

    return df


def feature_engineering(df: pd.DataFrame) -> pd.DataFrame:
    """3.6.2 Feature Engineering: tambahkan SMA, EMA, RSI, STI, PROC."""
    df = add_all_indicators(df)
    print("Indikator teknikal ditambahkan: SMA, EMA, RSI, STI, PROC")
    return df


def label_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    3.6.3 Pelabelan Data:
    Label = 1 jika Close hari ini > Close hari sebelumnya (harga naik)
    Label = 0 jika Close hari ini <= Close hari sebelumnya (harga turun/tetap)

    Target diprediksi adalah arah pergerakan hari BERIKUTNYA, sehingga label
    di-shift -1 (label pada baris t menjelaskan apakah harga t+1 naik/turun
    dibandingkan harga t).
    """
    df = df.copy()
    df["Price_Change"] = df["Close"].diff()
    df["Target_Today"] = (df["Price_Change"] > 0).astype(int)

    # Geser label ke atas: baris t pakai label dari t+1, supaya fitur hari ini
    # digunakan untuk memprediksi arah esok hari (sesuai batasan masalah no.5)
    df["Target"] = df["Target_Today"].shift(-1)

    df = df.drop(columns=["Price_Change", "Target_Today"])

    return df


def main():
    if not os.path.exists(INPUT_PATH):
        raise FileNotFoundError(
            f"'{INPUT_PATH}' tidak ditemukan. Jalankan 01_fetch_data.py dahulu."
        )

    df = pd.read_csv(INPUT_PATH)

    df = clean_data(df)
    df = feature_engineering(df)
    df = label_data(df)

    # Baris awal akan memiliki NaN karena rolling window (SMA/EMA/RSI/dst
    # butuh N hari sebelumnya), dan baris terakhir NaN karena shift(-1).
    # Baris-baris ini dibuang karena tidak bisa dipakai untuk training.
    before = len(df)
    df = df.dropna().reset_index(drop=True)
    after = len(df)
    print(f"Baris dengan NaN (akibat rolling window & label shift) dihapus: "
          f"{before} -> {after}")

    df["Target"] = df["Target"].astype(int)

    os.makedirs("data", exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)

    print(f"\nData siap latih disimpan ke: {OUTPUT_PATH}")
    print(f"Jumlah baris akhir: {len(df)}")
    print(f"Distribusi label -> Naik (1): {(df['Target']==1).sum()}, "
          f"Turun (0): {(df['Target']==0).sum()}")
    print("\nPreview:")
    print(df.tail())


if __name__ == "__main__":
    main()
