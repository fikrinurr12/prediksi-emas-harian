"""
app.py
======
Aplikasi Streamlit untuk Sistem Prediksi Arah Pergerakan Harga Emas Harian.
Sesuai Bab III 3.11 Implementasi Website (versi Streamlit).

Cara jalankan lokal:
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import joblib
import json
import os
from datetime import datetime

import yfinance as yf
from indicators import add_all_indicators

# ----------------------------------------------------------------------
# Konfigurasi halaman
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="Gold Predictor",
    page_icon="🥇",
    layout="centered",
)

MODEL_DIR = "models"
FEATURE_COLS = ["SMA", "EMA", "RSI", "STI", "PROC"]
TICKER = "GC=F"

FEATURE_LABELS = {
    "SMA": "SMA (Simple Moving Average)",
    "EMA": "EMA (Exponential Moving Average)",
    "RSI": "RSI (Relative Strength Index)",
    "STI": "STI (Stochastic Oscillator)",
    "PROC": "PROC (Price Rate of Change)",
}


# ----------------------------------------------------------------------
# Load model & artifacts (cache supaya tidak reload setiap interaksi)
# ----------------------------------------------------------------------
@st.cache_resource
def load_model_artifacts():
    model_path = os.path.join(MODEL_DIR, "rf_model.pkl")
    scaler_path = os.path.join(MODEL_DIR, "scaler.pkl")
    metrics_path = os.path.join(MODEL_DIR, "metrics.json")
    fi_path = os.path.join(MODEL_DIR, "feature_importance.csv")

    if not os.path.exists(model_path):
        return None, None, None, None

    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)

    with open(metrics_path) as f:
        metrics = json.load(f)

    feature_importance = pd.read_csv(fi_path)

    return model, scaler, metrics, feature_importance


# ----------------------------------------------------------------------
# Ambil data emas terbaru (cache 15 menit supaya tidak spam request)
# ----------------------------------------------------------------------
@st.cache_data(ttl=900)
def get_latest_gold_data(lookback_days: int = 60) -> pd.DataFrame:
    df = yf.download(TICKER, period=f"{lookback_days}d", interval="1d",
                      auto_adjust=True, progress=False)

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.reset_index()
    return df


def run_prediction(model, scaler):
    raw_df = get_latest_gold_data()
    df = add_all_indicators(raw_df)
    df = df.dropna().reset_index(drop=True)

    if df.empty:
        raise ValueError("Tidak cukup data untuk menghitung indikator teknikal.")

    latest_row = df.iloc[[-1]]
    X_latest = latest_row[FEATURE_COLS]
    X_latest_scaled = scaler.transform(X_latest)

    pred = model.predict(X_latest_scaled)[0]
    pred_proba = model.predict_proba(X_latest_scaled)[0]

    current_price = float(latest_row["Close"].values[0])
    last_date = pd.to_datetime(latest_row["Date"].values[0])

    if len(df) >= 2:
        prev_close = float(df.iloc[-2]["Close"])
        change = current_price - prev_close
        change_pct = (change / prev_close) * 100
    else:
        change, change_pct = 0.0, 0.0

    return {
        "prediction": "Naik" if pred == 1 else "Turun",
        "prediction_code": int(pred),
        "confidence": float(max(pred_proba)) * 100,
        "probability_naik": float(pred_proba[1]) * 100,
        "probability_turun": float(pred_proba[0]) * 100,
        "current_price": round(current_price, 2),
        "price_change": round(change, 2),
        "price_change_pct": round(change_pct, 2),
        "last_update": last_date.strftime("%d %B %Y"),
    }


# ----------------------------------------------------------------------
# Custom CSS (mendekati tema gradient ungu-biru pada mockup proposal)
# ----------------------------------------------------------------------
st.markdown("""
<style>
.main-header {
    background: linear-gradient(135deg, #6d4fc4, #4f7fc4);
    padding: 28px 24px;
    border-radius: 14px;
    color: white;
    text-align: center;
    margin-bottom: 16px;
}
.main-header h1 {
    margin: 0 0 6px 0;
    font-size: 1.4rem;
}
.main-header p {
    margin: 0;
    opacity: 0.9;
    font-size: 0.9rem;
}
.disclaimer-box {
    background: #fff8e6;
    border: 1px solid #f0deab;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 0.82rem;
    color: #7a5b00;
    margin-top: 10px;
}
.insight-box {
    background: #eef0fb;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 0.82rem;
    color: #444;
    margin-top: 10px;
}
</style>
""", unsafe_allow_html=True)


# ----------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------
model, scaler, metrics, feature_importance = load_model_artifacts()

accuracy_display = f"{metrics['accuracy']*100:.1f}%" if metrics else "N/A"

st.markdown(f"""
<div class="main-header">
    <h1>🛡️ Sistem Prediksi Arah Pergerakan Harga Emas</h1>
    <p>Menggunakan Random Forest &amp; Indikator Teknikal untuk Prediksi Harian</p>
</div>
""", unsafe_allow_html=True)

col_badge1, col_badge2 = st.columns(2)
with col_badge1:
    if model is not None:
        st.success("✅ Model Aktif", icon="✅")
    else:
        st.error("⚠️ Model belum ditemukan")
with col_badge2:
    st.info(f"📊 Akurasi {accuracy_display}")

if model is None:
    st.warning(
        "Model belum tersedia. Jalankan `01_fetch_data.py`, `02_preprocessing.py`, "
        "lalu `03_train_model.py` terlebih dahulu, dan letakkan hasilnya di folder `models/`."
    )
    st.stop()


# ----------------------------------------------------------------------
# Harga emas terkini
# ----------------------------------------------------------------------
st.subheader("💰 Harga Emas Hari Ini (USD/oz)")

try:
    result = run_prediction(model, scaler)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            label="Harga Terkini",
            value=f"${result['current_price']:,.2f}",
            delta=f"{result['price_change']:+.2f} ({result['price_change_pct']:+.2f}%)"
        )
    with col2:
        st.metric(label="Update Terakhir", value=result["last_update"])
    with col3:
        st.metric(label="Status", value="Live dari Yahoo Finance")

except Exception as e:
    st.error(f"Gagal mengambil data harga emas: {e}")
    st.stop()


# ----------------------------------------------------------------------
# Tombol prediksi
# ----------------------------------------------------------------------
st.subheader("📈 Prediksi Harga Emas")

if st.button("🔄 Prediksi Arah Harga", use_container_width=True, type="primary"):
    with st.spinner("Memproses prediksi..."):
        is_up = result["prediction_code"] == 1

        if is_up:
            st.success(f"📈 Prediksi: Harga Naik (keyakinan {result['confidence']:.1f}%)")
        else:
            st.error(f"📉 Prediksi: Harga Turun (keyakinan {result['confidence']:.1f}%)")

        col_a, col_b = st.columns(2)
        with col_a:
            st.write("**Probabilitas Naik**")
            st.progress(result["probability_naik"] / 100)
            st.caption(f"{result['probability_naik']:.1f}%")
        with col_b:
            st.write("**Probabilitas Turun**")
            st.progress(result["probability_turun"] / 100)
            st.caption(f"{result['probability_turun']:.1f}%")

st.markdown("""
<div class="disclaimer-box">
⚠️ <strong>Disclaimer:</strong> Hasil prediksi ini adalah alat bantu analisis.
Keputusan investasi sepenuhnya menjadi tanggung jawab Anda.
</div>
""", unsafe_allow_html=True)


# ----------------------------------------------------------------------
# Feature Importance
# ----------------------------------------------------------------------
st.subheader("📊 Feature Importance Analysis")
st.caption("Kontribusi setiap indikator terhadap prediksi")

fi_display = feature_importance.copy()
total_importance = fi_display["Importance"].sum()
fi_display["Percentage"] = (fi_display["Importance"] / total_importance * 100).round(1)
fi_display["Label"] = fi_display["Feature"].map(FEATURE_LABELS).fillna(fi_display["Feature"])
fi_display = fi_display.sort_values("Percentage", ascending=False)

for _, row in fi_display.iterrows():
    col_label, col_bar, col_pct = st.columns([2, 3, 1])
    with col_label:
        st.write(row["Label"])
    with col_bar:
        st.progress(row["Percentage"] / 100)
    with col_pct:
        st.write(f"{row['Percentage']}%")

top_feature = fi_display.iloc[0]
st.markdown(f"""
<div class="insight-box">
💡 <strong>Insight:</strong> {top_feature['Label']} memiliki kontribusi tertinggi
({top_feature['Percentage']}%) dalam menentukan arah pergerakan harga emas harian.
</div>
""", unsafe_allow_html=True)


# ----------------------------------------------------------------------
# Tentang Sistem
# ----------------------------------------------------------------------
st.subheader("ℹ️ Tentang Sistem")
st.write("""
Sistem ini menggunakan algoritma **Random Forest Classifier** yang dilatih
dengan lima indikator teknikal: *Simple Moving Average (SMA)*,
*Exponential Moving Average (EMA)*, *Relative Strength Index (RSI)*,
*Stochastic Oscillator (STI)*, dan *Price Rate of Change (PROC)*
untuk memprediksi arah pergerakan harga emas harian (naik/turun).
""")

st.divider()
st.caption("Skripsi — Program Studi Teknik Informatika, Universitas Muria Kudus, 2026")
