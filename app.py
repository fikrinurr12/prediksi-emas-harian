"""
Flask App - Prediksi Arah Pergerakan Harga Emas Harian
Skripsi: Prediksi Arah Pergerakan Harga Emas Harian Menggunakan Algoritma
         Random Forest dan Indikator Teknikal
Penyusun: Muhammad Fikri Nursyahbani - 202251159

PENTING: Fungsi build_features() di bawah ini HARUS SAMA PERSIS dengan
fungsi feature engineering yang dipakai saat training model (notebook FINAL).
Kalau salah satu diubah, yang lain WAJIB ikut diubah -- kalau tidak,
prediksi di produksi tidak akan konsisten dengan hasil training (train/serve skew).

Catatan revisi:
- Penyimpanan riwayat prediksi via SQLite (db.py) DIHAPUS. Fitur itu sebelumnya
  aktif di backend tapi tidak pernah disebut di Bab III/IV skripsi maupun
  ditampilkan di halaman web -- jadi lebih konsisten dihapus daripada dibiarkan
  jadi kode "mati" yang tidak sesuai naskah.
- Jendela grafik 7-hari sekarang berlabuh pada tanggal DATA TERAKHIR yang benar-benar
  tersedia (bukan tanggal kalender hari ini) -- lihat komentar FIX v5 di get_prediction().
"""

import os
import json
import joblib
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import date, timedelta, datetime
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

PENJELASAN_INDIKATOR = {
    "SMA": "Simple Moving Average -- rata-rata harga selama 20 hari terakhir (tren jangka panjang). "
           "Kalau harga sekarang jauh di atas rata-rata ini, itu tanda tren sedang menguat.",
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
    df = df.copy()

    sma_raw = df["Close"].rolling(window=n_long).mean()
    ema_raw = df["Close"].ewm(span=n_long, adjust=False).mean()
    df["SMA"] = df["Close"] / sma_raw - 1
    df["EMA"] = df["Close"] / ema_raw - 1

    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=n_short).mean()
    avg_loss = loss.rolling(window=n_short).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))
    df["RSI"] = df["RSI"].fillna(100)

    lowest_low = df["Low"].rolling(window=n_short).min()
    highest_high = df["High"].rolling(window=n_short).max()
    df["STI"] = (df["Close"] - lowest_low) / (highest_high - lowest_low) * 100

    df["PROC"] = (df["Close"] - df["Close"].shift(n_short)) / df["Close"].shift(n_short)

    return df


def fetch_usd_idr_rate(fallback=18050):
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

    CATATAN (bug "chart tidak update ke hari terbaru"): kalau chart selalu berhenti
    di tanggal yang sama walau sudah beberapa hari berlalu, kemungkinan besar
    PENYEBABNYA BUKAN di logika jendela grafik (app.py sudah berlabuh ke tanggal
    data TERAKHIR yang tersedia, bukan tanggal kalender -- itu sudah benar), tapi
    yf.download() itu sendiri yang menerima data usang dari Yahoo. Ini gejala umum
    yfinance yang dideploy di host cloud (Railway/Render/Heroku, dsb): IP datacenter
    sering kena rate-limit/served cache basi oleh Yahoo. Fungsi ini sekarang:
      1. Mencetak rentang tanggal MENTAH yang diterima (sebelum diproses apa pun) ke
         log, supaya bisa dicek lewat `railway logs` apakah masalahnya di Yahoo
         (log akan menunjukkan tanggal lama) atau di kode ini (log menunjukkan
         tanggal baru, tapi tampil di web tetap lama -> baru itu bug kode).
      2. Kalau data yang diterima "terlalu usang" (lebih dari LAG_MAKSIMAL_HARI hari
         kalender di belakang hari ini -- angka ini sengaja dilonggarkan untuk
         akomodasi akhir pekan/libur bursa), dicoba SEKALI LAGI lewat jalur berbeda
         (yf.Ticker(...).history(), bukan yf.download()) sebagai fallback, karena
         keduanya kadang punya perilaku cache/rate-limit yang tidak identik.
    """
    LAG_MAKSIMAL_HARI = 4  # weekend biasa = 2 hari; beri jarak sedikit lebih longgar

    end_date = date.today().isoformat()
    start_date = (date.today() - timedelta(days=lookback_days)).isoformat()

    raw = yfb.download(TICKER, start=start_date, end=end_date, interval="1d", progress=False)
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)

    df = raw.reset_index()
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").reset_index(drop=True)
    df = df.dropna(subset=["Open", "High", "Low", "Close"]).drop_duplicates(subset=["Date"]).reset_index(drop=True)

    tgl_terakhir = df["Date"].max() if len(df) else None
    print(f"[FETCH] yf.download({TICKER}) -> {len(df)} baris, tanggal terakhir mentah: {tgl_terakhir}")

    lag_hari = (pd.Timestamp(date.today()) - tgl_terakhir).days if tgl_terakhir is not None else 999
    if lag_hari > LAG_MAKSIMAL_HARI:
        print(f"[WARN] Data dari yf.download() tertinggal {lag_hari} hari -- kemungkinan Yahoo "
              f"menyajikan respons usang/di-cache ke IP server ini. Mencoba fallback via "
              f"yf.Ticker().history() ...")
        try:
            raw2 = yf.Ticker(TICKER).history(period=f"{lookback_days}d", interval="1d")
            raw2 = raw2.reset_index()
            raw2["Date"] = pd.to_datetime(raw2["Date"]).dt.tz_localize(None)
            raw2 = raw2.sort_values("Date").reset_index(drop=True)
            raw2 = raw2.dropna(subset=["Open", "High", "Low", "Close"]).drop_duplicates(subset=["Date"]).reset_index(drop=True)
            tgl_terakhir2 = raw2["Date"].max() if len(raw2) else None
            print(f"[FETCH-FALLBACK] yf.Ticker().history() -> {len(raw2)} baris, "
                  f"tanggal terakhir: {tgl_terakhir2}")
            if tgl_terakhir2 is not None and (tgl_terakhir is None or tgl_terakhir2 > tgl_terakhir):
                df = raw2[["Date", "Open", "High", "Low", "Close", "Volume"]]
                print("[FETCH-FALLBACK] Dipakai -- lebih baru dari hasil yf.download().")
            else:
                print("[FETCH-FALLBACK] Tidak lebih baru dari yf.download() -- tetap pakai data awal. "
                      "Kalau ini terus terjadi berhari-hari, sumbernya di sisi Yahoo/jaringan Railway, "
                      "bukan di kode. Coba redeploy/restart service, atau cek lagi beberapa jam kemudian.")
        except Exception as e:
            print(f"[FETCH-FALLBACK] Gagal: {e} -- tetap pakai hasil yf.download() di atas.")

    return df


def get_latest_complete_row(df):
    if len(df) == 0:
        return df
    today = pd.Timestamp(date.today())
    if df["Date"].iloc[-1] >= today:
        df = df.iloc[:-1].reset_index(drop=True)
    return df


def get_prediction():
    df = fetch_latest_data()
    df = get_latest_complete_row(df)
    df = build_features(df, N_LONG, N_SHORT)

    df_valid = df.dropna(subset=FEATURES).reset_index(drop=True)
    if len(df_valid) == 0:
        raise ValueError("Data tidak cukup untuk menghitung indikator. Coba lagi nanti.")

    latest_row = df_valid.iloc[[-1]]
    X_latest = latest_row[FEATURES]
    X_latest_scaled = scaler.transform(X_latest)

    pred = int(model.predict(X_latest_scaled)[0])
    proba = model.predict_proba(X_latest_scaled)[0]

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

    trading_sim = metadata.get("trading_simulation")

    # FIX v5 (bug "3 hari terakhir kosong / tidak auto-update ke hari ini"): sebelumnya window
    # kalender dihitung mundur dari `date.today()` (tanggal kalender SERVER), padahal df_valid
    # sudah membuang bar "hari ini" (get_latest_complete_row) DAN Yahoo Finance kadang baru
    # mempublikasikan bar harian GC=F beberapa jam setelah sesi tutup. Akibatnya, kalau window
    # dihitung dari tanggal kalender hari ini, 1-3 hari TERAKHIR di jendela bisa kosong bukan
    # karena weekend/libur (itu wajar, sudah diberi shading abu-abu oleh holidayShading di
    # script.js), melainkan karena data hari itu memang belum terbit dari Yahoo saat endpoint
    # ini dipanggil -- terlihat seperti "macet"/"tidak auto-update" padahal sumbernya sendiri
    # belum terbit.
    #
    # Perbaikan: jendela grafik sekarang berlabuh pada TANGGAL DATA TERAKHIR yang benar-benar ada
    # di df_valid (bukan tanggal kalender hari ini). Begitu Yahoo menerbitkan bar baru, endpoint
    # ini otomatis ikut maju (karena df_valid berubah tiap fetch), sehingga grafik selalu
    # menampilkan 7 hari kalender terakhir yang datanya sudah pasti tersedia -- tidak ada lagi
    # hari kosong di ujung kanan akibat lag publikasi data. Weekend/libur di TENGAH jendela tetap
    # tampil apa adanya (itu bukan bug, itu memang hari tanpa perdagangan).
    CHART_LOOKBACK_HARI_KALENDER = 7
    end_date = df_valid["Date"].max()
    start_date = end_date - pd.Timedelta(days=CHART_LOOKBACK_HARI_KALENDER - 1)

    full_days = pd.date_range(start=start_date, end=end_date, freq="D")
    chart_series = df_valid.set_index("Date")["Close"].reindex(full_days)

    chart_data = {
        "labels": full_days.strftime("%d %b").tolist(),
        "harga": [None if pd.isna(v) else round(float(v), 2) for v in chart_series.tolist()],
        "ticker": TICKER,
        "data_per": end_date.strftime("%d %b %Y"),
        "dicek_pada": datetime.now().strftime("%d %b %Y, %H:%M"),
    }

    mdi_raw = model.feature_importances_
    feature_importance = sorted(
        [{"nama": feat, "persen": round(float(val) * 100, 1)} for feat, val in zip(FEATURES, mdi_raw)],
        key=lambda x: x["persen"], reverse=True,
    )

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
    }


# ============================================================
# 3. Routes
# ============================================================
@app.route("/")
def index():
    try:
        hasil = get_prediction()
        return render_template("index.html", hasil=hasil, error=None)
    except Exception as e:
        return render_template("index.html", hasil=None, error=str(e))


@app.route("/api/predict")
def api_predict():
    try:
        hasil = get_prediction()
        return jsonify({"status": "success", "data": hasil})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/health")
def health():
    return jsonify({"status": "ok", "model_loaded": model is not None})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
