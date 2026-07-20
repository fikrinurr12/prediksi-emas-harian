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
N_LONG = metadata["indicator_window_N_long"]
N_SHORT = metadata["indicator_window_N_short"]
TICKER = "GC=F"

# Penjelasan ringkas tiap indikator -- dipakai untuk popup "klik nama indikator" di landing page.
PENJELASAN_INDIKATOR = {
    "SMA": "Simple Moving Average -- rata-rata harga selama 14 hari terakhir. Kalau harga sekarang "
           "jauh di atas rata-rata ini, itu tanda tren sedang menguat.",
    "EMA": "Exponential Moving Average -- mirip SMA, tapi memberi bobot lebih besar ke harga "
           "terbaru, sehingga lebih cepat bereaksi terhadap perubahan tren dibanding SMA.",
    "RSI": "Relative Strength Index -- mengukur seberapa kuat kenaikan dibanding penurunan harga "
           "dalam 14 hari terakhir, skala 0-100. Di atas 70 biasa disebut 'jenuh beli' (overbought), "
           "di bawah 30 disebut 'jenuh jual' (oversold).",
    "STI": "Stochastic Oscillator -- membandingkan harga penutupan hari ini dengan rentang "
           "harga tertinggi/terendah 14 hari terakhir, skala 0-100. Dipakai untuk mendeteksi "
           "potensi pembalikan arah tren.",
    "PROC": "Price Rate of Change -- persentase perubahan harga dibanding 14 hari sebelumnya. "
            "Nilai positif besar berarti harga naik cepat; negatif besar berarti turun cepat.",
}

print(f"[STARTUP] Model dimuat. Fitur: {FEATURES} | Window N_long={N_LONG}, N_short={N_SHORT}")
print(f"[STARTUP] Akurasi test (dari training): {metadata['test_metrics']['accuracy']:.4f}")


# ============================================================
# 2. Feature Engineering -- HARUS IDENTIK dengan notebook training
# ============================================================
def build_features(df, n_long=20, n_short=14):
    """
    Menghitung 5 indikator teknikal (Tabel 3.2 skripsi, revisi window ganda):
    SMA & EMA pakai jendela n_long (tren jangka panjang),
    RSI, STI, PROC pakai jendela n_short (momentum jangka pendek).
    Formula ini identik dengan yang dipakai di notebook FINAL training.
    """
    df = df.copy()

    # SMA & EMA -- jendela panjang (tren)
    sma_raw = df["Close"].rolling(window=n_long).mean()
    ema_raw = df["Close"].ewm(span=n_long, adjust=False).mean()
    df["SMA"] = df["Close"] / sma_raw - 1
    df["EMA"] = df["Close"] / ema_raw - 1

    # RSI -- jendela pendek (rumus baku)
    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=n_short).mean()
    avg_loss = loss.rolling(window=n_short).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))
    df["RSI"] = df["RSI"].fillna(100)  # FIX: avg_loss=0 -> RSI=100, bukan NaN

    # STI -- jendela pendek
    lowest_low = df["Low"].rolling(window=n_short).min()
    highest_high = df["High"].rolling(window=n_short).max()
    df["STI"] = (df["Close"] - lowest_low) / (highest_high - lowest_low) * 100

    # PROC -- jendela pendek
    df["PROC"] = (df["Close"] - df["Close"].shift(n_short)) / df["Close"].shift(n_short)

    return df


def fetch_usd_idr_rate(fallback=18050):
    """
    Ambil kurs USD/IDR terkini dari Yahoo Finance (ticker USDIDR=X).
    Kalau fetch gagal (jaringan, ticker down, dsb), pakai `fallback` supaya
    kegagalan ambil kurs TIDAK pernah membuat seluruh halaman prediksi error --
    ini cuma angka tampilan, bukan bagian dari model, jadi wajar didegradasi
    dengan lembut (graceful fallback) alih-alih ikut melempar exception.
    Return: (rate: float, is_live: bool)
    """
    try:
        raw = yf.download("USDIDR=X", period="5d", interval="1d", progress=False)
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)
        raw = raw.dropna(subset=["Close"])
        if len(raw) == 0:
            return float(fallback), False
        rate = float(raw["Close"].iloc[-1])
        if not np.isfinite(rate) or rate <= 0:
            return float(fallback), False
        return rate, True
    except Exception as e:
        print(f"[WARN] Gagal ambil kurs USD/IDR live, pakai fallback {fallback}: {e}")
        return float(fallback), False


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


def get_latest_complete_row(df):
    """
    FIX (train/serve skew): GC=F (emas berjangka) berdagang hampir 24 jam/hari
    lewat CME Globex. Selama sesi hari ini masih berjalan, baris "hari ini"
    yang dikembalikan yfinance itu LIVE -- Open/High/Low/Close-nya terus
    berubah tergantung jam berapa endpoint ini dipanggil. Model dilatih di
    atas bar harian yang SUDAH FINAL (closing price akhir sesi), jadi kalau
    baris live ini tetap dipakai untuk hitung indikator, prediksi bisa
    berubah-ubah dalam hari yang sama cuma karena harga masih bergerak --
    bukan karena ada sinyal baru yang valid.

    Solusi: buang baris "hari ini" (Date >= hari ini) SEBELUM feature
    engineering, supaya baris terakhir yang dipakai selalu bar yang sudah
    settle, dan prediksi stabil sepanjang hari sampai bar berikutnya final.
    """
    if len(df) == 0:
        return df
    today = pd.Timestamp(date.today())
    if df["Date"].iloc[-1] >= today:
        df = df.iloc[:-1].reset_index(drop=True)
    return df


def get_prediction():
    """
    Alur lengkap: ambil data terbaru -> hitung indikator -> normalisasi -> prediksi.
    Mengembalikan dict berisi hasil prediksi & data pendukung untuk ditampilkan.
    """
    df = fetch_latest_data()
    df = get_latest_complete_row(df)  # FIX: buang bar "hari ini" kalau masih live/belum final
    df = build_features(df, N_LONG, N_SHORT)

    df_valid = df.dropna(subset=FEATURES).reset_index(drop=True)
    if len(df_valid) == 0:
        raise ValueError("Data tidak cukup untuk menghitung indikator. Coba lagi nanti.")

    latest_row = df_valid.iloc[[-1]]
    X_latest = latest_row[FEATURES]
    X_latest_scaled = scaler.transform(X_latest)

    pred = int(model.predict(X_latest_scaled)[0])
    proba = model.predict_proba(X_latest_scaled)[0]

    # kurs acuan HANYA untuk tampilan (konversi USD/oz -> perkiraan Rp/gram), bukan fitur model.
    # FIX: sebelumnya angka tetap (18050) yang ditulis manual di kode -- sekarang diambil live
    # dari Yahoo Finance (USDIDR=X), dengan fallback ke angka tetap kalau fetch-nya gagal supaya
    # kegagalan ambil kurs tidak pernah menjatuhkan seluruh halaman prediksi.
    KURS_USD_IDR, kurs_live = fetch_usd_idr_rate(fallback=18050)
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

    # --- Data grafik harga: dari sumber & instrumen YANG SAMA dengan yang dipakai model (GC=F via yfinance) ---
    # Sengaja TIDAK memakai widget TradingView (yang defaultnya menampilkan OANDA:XAUUSD, emas spot dari
    # broker forex) -- itu instrumen berbeda dari GC=F (kontrak berjangka COMEX) yang jadi dasar prediksi
    # model. Memakai data yang sama menghindari kebingungan "kok grafik naik tapi modelnya bilang turun".
    # FIX v3: sebelumnya window dihitung dari "N baris data TRADING terakhir"
    # (mis. 30 baris), lalu direntangkan ke kalender -- tapi kalau ada weekend/
    # libur di dalam N baris itu, rentang kalendernya melar tidak terduga
    # (30 baris trading bisa jadi 40+ hari kalender). Sekarang window dihitung
    # LANGSUNG dari kalender: N hari kalender ke belakang dari tanggal data
    # terakhir, baru diisi harga dari df_valid untuk tanggal yang ada datanya.
    # Ini menjamin jumlah hari yang ditampilkan selalu persis N, bukan kira-kira.
    # FIX v4: sebelumnya end_date dihitung dari TANGGAL DATA TERAKHIR YANG ADA
    # (df_valid["Date"].max()) -- jadi kalau ini weekend/libur (belum ada bar
    # baru), jendela grafik "macet" di hari bursa terakhir dan tidak ikut maju
    # ke tanggal kalender hari ini. Sekarang end_date = tanggal HARI INI yang
    # sebenarnya, supaya jendela selalu bergeser tiap hari; hari yang belum
    # ada datanya (termasuk hari ini sendiri kalau belum ada bar) otomatis
    # jadi None lewat reindex di bawah -- bukan disembunyikan/macet.
    CHART_LOOKBACK_HARI_KALENDER = 7
    end_date = pd.Timestamp(date.today())
    start_date = end_date - pd.Timedelta(days=CHART_LOOKBACK_HARI_KALENDER - 1)

    full_days = pd.date_range(start=start_date, end=end_date, freq="D")
    chart_series = df_valid.set_index("Date")["Close"].reindex(full_days)

    chart_data = {
        "labels": full_days.strftime("%d %b").tolist(),
        "harga": [None if pd.isna(v) else round(float(v), 2) for v in chart_series.tolist()],
        "ticker": TICKER,
    }

    # Feature importance -- langsung dari model yang sudah di-pickle, TIDAK perlu retraining.
    mdi_raw = model.feature_importances_  # array sejajar dengan FEATURES, jumlahnya = 1.0
    feature_importance = sorted(
        [{"nama": feat, "persen": round(float(val) * 100, 1)} for feat, val in zip(FEATURES, mdi_raw)],
        key=lambda x: x["persen"], reverse=True,
    )

    # --- Catat prediksi hari ini ke SQLite, dan resolusi prediksi lama yang tanggal targetnya sudah lewat ---
    tanggal_dibuat = latest_row["Date"].dt.strftime("%Y-%m-%d").values[0]

    return {
        "tanggal_data": tanggal_dibuat,
        "harga_close_terakhir": round(harga_usd_oz, 2),
        "harga_open": round(float(latest_row["Open"].values[0]), 2),
        "harga_high": round(float(latest_row["High"].values[0]), 2),
        "harga_low": round(float(latest_row["Low"].values[0]), 2),
        "harga_idr_gram_estimasi": round(harga_idr_gram_estimasi, 0),
        "kurs_usd_idr": round(KURS_USD_IDR, 0),
        "kurs_live": kurs_live,
        "perubahan_persen": round(perubahan_persen, 2),
        "prediksi": "NAIK" if pred == 1 else "TURUN",
        "prediksi_kode": pred,
        "probabilitas_naik": round(float(proba[1]) * 100, 2),
        "probabilitas_turun": round(float(proba[0]) * 100, 2),
        "indikator": {feat: round(float(latest_row[feat].values[0]), 4) for feat in FEATURES},
        "feature_importance": feature_importance,
        "penjelasan_indikator": PENJELASAN_INDIKATOR,
        "model_info": {
            "akurasi_test": round(metadata["test_metrics"]["accuracy"] * 100, 2),
            "f1_score_test": round(metadata["test_metrics"]["f1_score"] * 100, 2),
            "baseline_akurasi": round(metadata["baseline_accuracy"] * 100, 2),
            "roc_auc": round(metadata["test_metrics"].get("roc_auc", 0), 4),
        },
        "trading_sim": trading_sim,
        "chart": chart_data,
        "riwayat": riwayat,
        "akurasi_riwayat": akurasi_riwayat,
        "jumlah_riwayat_resolved": jumlah_riwayat_resolved,
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
