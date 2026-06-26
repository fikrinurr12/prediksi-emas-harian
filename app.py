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

from flask import Flask, render_template, jsonify, request
import pandas as pd
import numpy as np
import joblib
import json
import os
from datetime import datetime

from indicators import add_all_indicators
from data_sources import get_latest_gold_data, get_cache_age_minutes
from candle_kejepit import detect_candle_kejepit
from candle_rejection import detect_candle_rejection
from terbang_terjun import detect_terbang_terjun

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


def _get_twelvedata_api_key():
    """
    Ambil API key Twelve Data dari environment variable. Di Railway, ini
    diset lewat dashboard Variables, BUKAN ditulis langsung di kode (supaya
    tidak ter-commit ke GitHub).
    """
    return os.environ.get("TWELVEDATA_API_KEY", None)


def predict_next_direction():
    """
    Mengambil data emas terbaru, menghitung indikator teknikal, lalu
    memprediksi arah pergerakan hari berikutnya menggunakan model RF
    yang sudah dilatih.
    """
    api_key = _get_twelvedata_api_key()
    raw_df, data_source = get_latest_gold_data(lookback_days=60, twelvedata_api_key=api_key)

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
        "data_source": data_source,
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


@app.route("/eksperimen")
def eksperimen_pola_candle():
    """
    Halaman TERPISAH dari sistem prediksi utama. Murni eksplorasi pola
    candlestick (Candle Kejepit, Candle Rejection, Terbang Terjun),
    BUKAN bagian dari model Random Forest di halaman utama.
    """
    return render_template("eksperimen.html")


@app.route("/api/eksperimen/pola-candle")
def api_pola_candle():
    """
    Menghitung ketiga pola candlestick atas data emas terbaru, dan
    mengembalikan ringkasan + sinyal 10 terbaru untuk masing-masing pola.
    """
    try:
        lookback_days = int(request.args.get("lookback_days", 180))
        upper_wick = float(request.args.get("upper_wick", 61))
        lower_wick = float(request.args.get("lower_wick", 61))
        tt_length = int(request.args.get("tt_length", 20))
        tt_upper = float(request.args.get("tt_upper", 1.5))
        tt_lower = float(request.args.get("tt_lower", -1.5))

        api_key = _get_twelvedata_api_key()
        raw_df, data_source = get_latest_gold_data(
            lookback_days=lookback_days, twelvedata_api_key=api_key
        )

        df_kejepit = detect_candle_kejepit(raw_df)
        df_rejection = detect_candle_rejection(
            raw_df, upper_wick_threshold=upper_wick, lower_wick_threshold=lower_wick
        )
        df_tt = detect_terbang_terjun(
            raw_df, length=tt_length, upper_threshold=tt_upper, lower_threshold=tt_lower
        )

        def _last_signals(df, mask_col_list, cols):
            mask = df[mask_col_list[0]].copy()
            for col in mask_col_list[1:]:
                mask = mask | df[col]
            subset = df.loc[mask, cols].tail(10).copy()
            # Konversi Timestamp & numpy types ke tipe JSON-friendly
            if "Date" in subset.columns:
                subset["Date"] = subset["Date"].astype(str)
            return subset.to_dict(orient="records")

        kejepit_signals = _last_signals(
            df_kejepit,
            ["is_bullish_kejepit", "is_bearish_kejepit"],
            ["Date", "Close", "is_bullish_kejepit", "is_bearish_kejepit",
             "zone_high", "zone_low", "box_color"],
        )
        rejection_signals = _last_signals(
            df_rejection,
            ["is_reject_sell", "is_reject_buy"],
            ["Date", "Close", "upper_wick_pct", "lower_wick_pct",
             "is_reject_sell", "is_reject_buy"],
        )
        tt_signals = _last_signals(
            df_tt,
            ["is_sell_signal", "is_buy_signal"],
            ["Date", "Close", "linreg_osc_norm", "is_sell_signal", "is_buy_signal"],
        )

        # Data untuk grafik oscillator Terbang Terjun
        tt_chart = df_tt[["Date", "linreg_osc_norm"]].dropna().copy()
        tt_chart["Date"] = tt_chart["Date"].astype(str)

        result = {
            "data_source": data_source,
            "n_candles": len(raw_df),
            "candle_kejepit": {
                "n_bullish": int(df_kejepit["is_bullish_kejepit"].sum()),
                "n_bearish": int(df_kejepit["is_bearish_kejepit"].sum()),
                "signals": kejepit_signals,
            },
            "candle_rejection": {
                "n_reject_sell": int(df_rejection["is_reject_sell"].sum()),
                "n_reject_buy": int(df_rejection["is_reject_buy"].sum()),
                "signals": rejection_signals,
            },
            "terbang_terjun": {
                "n_sell": int(df_tt["is_sell_signal"].sum()),
                "n_buy": int(df_tt["is_buy_signal"].sum()),
                "signals": tt_signals,
                "chart": tt_chart.to_dict(orient="records"),
            },
        }
        return jsonify({"success": True, "data": result})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


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
