"""
Flask App - Prediksi Arah Pergerakan Harga Emas Harian
Skripsi: Prediksi Arah Pergerakan Harga Emas Harian Menggunakan Algoritma
         Random Forest dan Indikator Teknikal
Penyusun: Muhammad Fikri Nursyahbani - 202251159

PENTING: Fungsi build_features() di bawah ini HARUS SAMA PERSIS dengan
fungsi feature engineering yang dipakai saat training model (notebook FINAL).
Kalau salah satu diubah, yang lain WAJIB ikut diubah -- kalau tidak,
prediksi di produksi tidak akan konsisten dengan hasil training (train/serve skew).
"""

import os
import json
import joblib
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import date, timedelta
from flask import Flask, render_template, jsonify

app = Flask(__name__)

# ============================================================
# 1. Muat model, scaler, dan metadata SEKALI saat aplikasi start
# ============================================================
MODEL_DIR = os.path.join(os.path.dirname(__file__), "model")

model = joblib.load(os.path.join(MODEL_DIR, "model_rf_emas.pkl"))
scaler = joblib.load(os.path.join(MODEL_DIR, "scaler_emas.pkl"))

with open(os.path.join(MODEL_DIR, "model_metadata.json")) as f:
    metadata = json.load(f)

FEATURES = metadata["features_order"]
N = metadata["indicator_window_N"]
TICKER = "GC=F"

print(f"[STARTUP] Model dimuat. Fitur: {FEATURES} | Window N={N}")
print(f"[STARTUP] Akurasi test (dari training): {metadata['test_metrics']['accuracy']:.4f}")


# ============================================================
# 2. Feature Engineering -- HARUS IDENTIK dengan notebook training
# ============================================================
def build_features(df, N=14):
    """
    Menghitung 5 indikator teknikal (Tabel 3.2 skripsi):
    SMA, EMA, RSI, STI (Stochastic Oscillator), PROC.
    Formula ini identik dengan yang dipakai di notebook FINAL training.
    """
    df = df.copy()

    # SMA & EMA: relatif terhadap harga (stasioner)
    sma_raw = df["Close"].rolling(window=N).mean()
    ema_raw = df["Close"].ewm(span=N, adjust=False).mean()
    df["SMA"] = df["Close"] / sma_raw - 1
    df["EMA"] = df["Close"] / ema_raw - 1

    # RSI (rumus baku)
    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=N).mean()
    avg_loss = loss.rolling(window=N).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))

    # STI (Stochastic Oscillator)
    lowest_low = df["Low"].rolling(window=N).min()
    highest_high = df["High"].rolling(window=N).max()
    df["STI"] = (df["Close"] - lowest_low) / (highest_high - lowest_low) * 100

    # PROC (Price Rate of Change)
    df["PROC"] = (df["Close"] - df["Close"].shift(N)) / df["Close"].shift(N)

    return df


def fetch_latest_data(lookback_days=60):
    """
    Ambil data emas terbaru dari Yahoo Finance.
    lookback_days perlu cukup panjang supaya rolling window (N=14) punya
    data yang cukup untuk dihitung pada baris paling akhir.
    """
    end_date = date.today().isoformat()
    start_date = (date.today() - timedelta(days=lookback_days)).isoformat()

    raw = yf.download(TICKER, start=start_date, end=end_date, interval="1d", progress=False)
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)

    df = raw.reset_index()
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").reset_index(drop=True)
    df = df.dropna(subset=["Open", "High", "Low", "Close"]).drop_duplicates(subset=["Date"]).reset_index(drop=True)
    return df


def get_prediction():
    """
    Alur lengkap: ambil data terbaru -> hitung indikator -> normalisasi -> prediksi.
    Mengembalikan dict berisi hasil prediksi & data pendukung untuk ditampilkan.
    """
    df = fetch_latest_data()
    df = build_features(df, N)

    df_valid = df.dropna(subset=FEATURES).reset_index(drop=True)
    if len(df_valid) == 0:
        raise ValueError("Data tidak cukup untuk menghitung indikator. Coba lagi nanti.")

    latest_row = df_valid.iloc[[-1]]
    X_latest = latest_row[FEATURES]
    X_latest_scaled = scaler.transform(X_latest)

    pred = int(model.predict(X_latest_scaled)[0])
    proba = model.predict_proba(X_latest_scaled)[0]

    # kurs acuan HANYA untuk tampilan (konversi USD/oz -> perkiraan Rp/gram), bukan fitur model
    KURS_USD_IDR = 18050
    GRAM_PER_OZ = 31.1035
    harga_usd_oz = float(latest_row["Close"].values[0])
    harga_idr_gram_estimasi = harga_usd_oz * KURS_USD_IDR / GRAM_PER_OZ

    idx_latest = df_valid.index[-1]
    if idx_latest > 0:
        prev_close = float(df_valid.loc[idx_latest - 1, "Close"])
        perubahan_persen = (harga_usd_oz / prev_close - 1) * 100
    else:
        perubahan_persen = 0.0

    trading_sim = metadata.get("trading_simulation")  # None kalau metadata lama (belum ada simulasi)

    return {
        "tanggal_data": latest_row["Date"].dt.strftime("%Y-%m-%d").values[0],
        "harga_close_terakhir": round(harga_usd_oz, 2),
        "harga_open": round(float(latest_row["Open"].values[0]), 2),
        "harga_high": round(float(latest_row["High"].values[0]), 2),
        "harga_low": round(float(latest_row["Low"].values[0]), 2),
        "harga_idr_gram_estimasi": round(harga_idr_gram_estimasi, 0),
        "perubahan_persen": round(perubahan_persen, 2),
        "prediksi": "NAIK" if pred == 1 else "TURUN",
        "prediksi_kode": pred,
        "probabilitas_naik": round(float(proba[1]) * 100, 2),
        "probabilitas_turun": round(float(proba[0]) * 100, 2),
        "indikator": {feat: round(float(latest_row[feat].values[0]), 4) for feat in FEATURES},
        "model_info": {
            "akurasi_test": round(metadata["test_metrics"]["accuracy"] * 100, 2),
            "f1_score_test": round(metadata["test_metrics"]["f1_score"] * 100, 2),
            "baseline_akurasi": round(metadata["baseline_accuracy"] * 100, 2),
            "roc_auc": round(metadata["test_metrics"].get("roc_auc", 0), 4),
        },
        "trading_sim": trading_sim,
    }


# ============================================================
# 3. Routes
# ============================================================
@app.route("/")
def index():
    """Halaman utama - menampilkan prediksi hari ini dalam bentuk web sederhana."""
    try:
        hasil = get_prediction()
        return render_template("index.html", hasil=hasil, error=None)
    except Exception as e:
        return render_template("index.html", hasil=None, error=str(e))


@app.route("/api/predict")
def api_predict():
    """Endpoint JSON - untuk dipakai programatik (mis. dipanggil dari aplikasi lain)."""
    try:
        hasil = get_prediction()
        return jsonify({"status": "success", "data": hasil})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/health")
def health():
    """Health check endpoint - dipakai Railway untuk memastikan aplikasi hidup."""
    return jsonify({"status": "ok", "model_loaded": model is not None})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
