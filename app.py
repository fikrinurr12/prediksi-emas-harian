"""
app.py
======
Aplikasi Flask untuk Sistem Prediksi Arah Pergerakan Harga Emas Harian.
Sesuai Bab III 3.11 Implementasi Website.

Routing:
    GET  /                -> halaman utama (dashboard prediksi)
    GET  /api/predict      -> menjalankan prediksi terbaru & mengembalikan JSON
    GET  /api/feature-importance -> mengembalikan data feature importance

Cara jalankan lokal:
    python app.py
    lalu buka http://127.0.0.1:5000
"""

from flask import Flask, render_template, jsonify
import pandas as pd
import numpy as np
import joblib
import json
import os
from datetime import datetime

import yfinance as yf
from indicators import add_all_indicators

app = Flask(__name__)

MODEL_DIR = "models"
FEATURE_COLS = ["SMA", "EMA", "RSI", "STI", "PROC"]
TICKER = "GC=F"

# ----------------------------------------------------------------------
# Load model, scaler, dan metrik sekali saja saat aplikasi start
# (bukan setiap request, supaya cepat)
# ----------------------------------------------------------------------
_model = None
_scaler = None
_metrics = None
_feature_importance = None


def load_artifacts():
    global _model, _scaler, _metrics, _feature_importance

    model_path = os.path.join(MODEL_DIR, "rf_model.pkl")
    scaler_path = os.path.join(MODEL_DIR, "scaler.pkl")
    metrics_path = os.path.join(MODEL_DIR, "metrics.json")
    fi_path = os.path.join(MODEL_DIR, "feature_importance.csv")

    if not os.path.exists(model_path):
        raise FileNotFoundError(
            "Model belum ditemukan. Jalankan 01_fetch_data.py, "
            "02_preprocessing.py, lalu 03_train_model.py terlebih dahulu."
        )

    _model = joblib.load(model_path)
    _scaler = joblib.load(scaler_path)

    with open(metrics_path) as f:
        _metrics = json.load(f)

    _feature_importance = pd.read_csv(fi_path)


def get_latest_gold_data(lookback_days: int = 60) -> pd.DataFrame:
    """
    Mengambil data emas terbaru dari Yahoo Finance secukupnya untuk
    menghitung indikator teknikal (butuh histori beberapa hari ke belakang
    karena SMA/EMA/RSI/STI/PROC adalah rolling window).
    """
    df = yf.download(TICKER, period=f"{lookback_days}d", interval="1d",
                      auto_adjust=True, progress=False)

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.reset_index()
    return df


def predict_next_direction():
    """
    Mengambil data emas terbaru, menghitung indikator teknikal, lalu
    memprediksi arah pergerakan hari berikutnya menggunakan model RF
    yang sudah dilatih.
    """
    raw_df = get_latest_gold_data()
    df = add_all_indicators(raw_df)
    df = df.dropna().reset_index(drop=True)

    if df.empty:
        raise ValueError("Tidak cukup data untuk menghitung indikator teknikal.")

    latest_row = df.iloc[[-1]]
    X_latest = latest_row[FEATURE_COLS]
    X_latest_scaled = _scaler.transform(X_latest)

    pred = _model.predict(X_latest_scaled)[0]
    pred_proba = _model.predict_proba(X_latest_scaled)[0]

    current_price = float(latest_row["Close"].values[0])
    last_date = pd.to_datetime(latest_row["Date"].values[0])

    # Hitung perubahan harga harian terakhir untuk ditampilkan di dashboard
    if len(df) >= 2:
        prev_close = float(df.iloc[-2]["Close"])
        change = current_price - prev_close
        change_pct = (change / prev_close) * 100
    else:
        change, change_pct = 0.0, 0.0

    result = {
        "prediction": "Naik" if pred == 1 else "Turun",
        "prediction_code": int(pred),
        "confidence": float(max(pred_proba)) * 100,
        "probability_naik": float(pred_proba[1]) * 100,
        "probability_turun": float(pred_proba[0]) * 100,
        "current_price": round(current_price, 2),
        "price_change": round(change, 2),
        "price_change_pct": round(change_pct, 2),
        "last_update": last_date.strftime("%d %B %Y"),
        "indicators": {
            "SMA": round(float(latest_row["SMA"].values[0]), 2),
            "EMA": round(float(latest_row["EMA"].values[0]), 2),
            "RSI": round(float(latest_row["RSI"].values[0]), 2),
            "STI": round(float(latest_row["STI"].values[0]), 2),
            "PROC": round(float(latest_row["PROC"].values[0]), 4),
        }
    }
    return result


@app.route("/")
def index():
    return render_template(
        "index.html",
        accuracy=round(_metrics["accuracy"] * 100, 1)
    )


@app.route("/api/predict")
def api_predict():
    try:
        result = predict_next_direction()
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/feature-importance")
def api_feature_importance():
    try:
        fi = _feature_importance.copy()
        total = fi["Importance"].sum()
        fi["Percentage"] = (fi["Importance"] / total * 100).round(1)

        data = fi[["Feature", "Percentage"]].to_dict(orient="records")
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/metrics")
def api_metrics():
    try:
        return jsonify({"success": True, "data": _metrics})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# Load model saat module diimpor (dibutuhkan baik untuk run lokal maupun
# saat dijalankan oleh Gunicorn di server produksi)
load_artifacts()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
