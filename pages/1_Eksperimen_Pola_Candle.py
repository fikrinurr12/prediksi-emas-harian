"""
pages/1_Eksperimen_Pola_Candle.py
===================================
Halaman TERPISAH dari sistem prediksi utama (Random Forest + 5 indikator
teknikal). Halaman ini menampilkan eksperimen tambahan: deteksi pola
candlestick (Candle Kejepit, Candle Rejection, Terbang Terjun) yang
dikonversi dari indikator Pine Script.

PENTING: Ini BUKAN bagian dari model prediksi utama skripsi. Halaman ini
murni eksplorasi/eksperimen tambahan, dipisahkan secara sengaja dari
halaman utama (app.py) supaya tidak tercampur dengan sistem yang sudah
sesuai proposal.
"""

import streamlit as st
import pandas as pd
import os

from candle_kejepit import detect_candle_kejepit, resample_to_timeframe
from candle_rejection import detect_candle_rejection
from terbang_terjun import detect_terbang_terjun
from data_sources import get_latest_gold_data

st.set_page_config(
    page_title="Eksperimen Pola Candle",
    page_icon="🕯️",
    layout="wide",
)

st.title("🕯️ Eksperimen Pola Candlestick")

st.warning(
    "⚠️ **Halaman eksperimen, bukan bagian dari model prediksi utama.** "
    "Konten di halaman ini terpisah dari sistem Random Forest + 5 indikator "
    "teknikal pada halaman utama, dan murni untuk eksplorasi tambahan."
)


# ----------------------------------------------------------------------
# Ambil data emas (reuse fungsi yang sama dengan halaman utama, jadi
# konsisten sumber datanya dan ikut memanfaatkan cache + fallback yang sama)
# ----------------------------------------------------------------------
def _get_twelvedata_api_key():
    try:
        return st.secrets.get("TWELVEDATA_API_KEY", None)
    except Exception:
        return None


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_gold_data_for_experiment(lookback_days: int = 180):
    api_key = _get_twelvedata_api_key()
    return get_latest_gold_data(lookback_days=lookback_days, twelvedata_api_key=api_key)


# ----------------------------------------------------------------------
# Sidebar: kontrol parameter
# ----------------------------------------------------------------------
st.sidebar.header("⚙️ Pengaturan Eksperimen")

lookback_days = st.sidebar.slider(
    "Jumlah hari data historis", min_value=60, max_value=365, value=180, step=30
)

timeframe_option = st.sidebar.selectbox(
    "Timeframe Candle Kejepit",
    options=["Harian (asli)", "4 Jam (resample)", "1 Jam (resample)"],
    index=0,
)

st.sidebar.subheader("Candle Rejection")
upper_wick_threshold = st.sidebar.slider("Upper Wick Threshold (%)", 30, 90, 61)
lower_wick_threshold = st.sidebar.slider("Lower Wick Threshold (%)", 30, 90, 61)

st.sidebar.subheader("Terbang Terjun")
tt_length = st.sidebar.slider("Length (window regresi)", 10, 50, 20)
tt_upper = st.sidebar.slider("Upper Threshold", 0.5, 3.0, 1.5, step=0.1)
tt_lower = st.sidebar.slider("Lower Threshold", -3.0, -0.5, -1.5, step=0.1)


# ----------------------------------------------------------------------
# Load data
# ----------------------------------------------------------------------
try:
    with st.spinner("Mengambil data harga emas..."):
        raw_df, data_source = fetch_gold_data_for_experiment(lookback_days=lookback_days)

    source_labels = {
        "cache": "Cache (≤30 menit)",
        "yfinance": "Live dari Yahoo Finance",
        "twelvedata": "Live dari Twelve Data (cadangan)",
        "cache_basi": "Cache lama (semua sumber gagal)",
    }
    st.caption(f"📡 Sumber data: {source_labels.get(data_source, data_source)} | "
               f"{len(raw_df)} candle harian dimuat")

except ConnectionError as e:
    st.error("Gagal mengambil data harga emas. Coba muat ulang halaman beberapa saat lagi.")
    with st.expander("Detail teknis"):
        st.code(str(e))
    st.stop()


# ----------------------------------------------------------------------
# Resample sesuai pilihan timeframe (untuk Candle Kejepit)
# ----------------------------------------------------------------------
resample_map = {
    "Harian (asli)": None,
    "4 Jam (resample)": "4h",
    "1 Jam (resample)": "1h",
}
resample_rule = resample_map[timeframe_option]

if resample_rule is not None:
    st.info(
        f"ℹ️ Data di-resample ke {timeframe_option}. Karena Yahoo Finance hanya "
        f"menyediakan data harian untuk jangka panjang, resample ke timeframe "
        f"lebih pendek dari data harian **tidak menghasilkan candle baru yang "
        f"valid** -- fitur ini lebih bermakna jika sumber data aslinya sudah "
        f"berinterval jam. Gunakan opsi ini dengan kesadaran akan batasan ini."
    )
    df_for_kejepit = raw_df  # tetap pakai harian, resample candle/jam butuh sumber data jam asli
else:
    df_for_kejepit = raw_df


# ----------------------------------------------------------------------
# Jalankan ketiga deteksi
# ----------------------------------------------------------------------
df_kejepit = detect_candle_kejepit(df_for_kejepit)
df_rejection = detect_candle_rejection(
    raw_df,
    upper_wick_threshold=upper_wick_threshold,
    lower_wick_threshold=lower_wick_threshold,
)
df_tt = detect_terbang_terjun(
    raw_df,
    length=tt_length,
    upper_threshold=tt_upper,
    lower_threshold=tt_lower,
)


# ----------------------------------------------------------------------
# Tampilkan ringkasan dalam 3 kolom/tab
# ----------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["🟥🟩 Candle Kejepit", "🕯️ Candle Rejection", "📈 Terbang Terjun"])

with tab1:
    st.subheader("Candle Kejepit")
    st.caption(
        "Pola 5 candle berurutan: 1 candle 'terjepit' di tengah, diapit oleh "
        "candle dengan arah berlawanan di kedua sisinya."
    )

    n_bullish = df_kejepit["is_bullish_kejepit"].sum()
    n_bearish = df_kejepit["is_bearish_kejepit"].sum()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Pola Terdeteksi (Box Jual)", f"{n_bullish}x")
    with col2:
        st.metric("Pola Terdeteksi (Box Beli)", f"{n_bearish}x")

    last_signals = df_kejepit[
        df_kejepit["is_bullish_kejepit"] | df_kejepit["is_bearish_kejepit"]
    ].tail(10)

    if len(last_signals) > 0:
        st.write("**10 sinyal terakhir:**")
        display_cols = ["Date", "Close", "is_bullish_kejepit", "is_bearish_kejepit",
                         "zone_high", "zone_low", "box_color"]
        st.dataframe(last_signals[display_cols], use_container_width=True, hide_index=True)
    else:
        st.write("Belum ada pola terdeteksi pada rentang data ini.")

with tab2:
    st.subheader("Candle Rejection")
    st.caption(
        "Mendeteksi candle dengan wick (ekor) yang panjang relatif terhadap "
        "range candle, mengindikasikan penolakan harga (rejection)."
    )

    n_rs = df_rejection["is_reject_sell"].sum()
    n_rb = df_rejection["is_reject_buy"].sum()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Sinyal RS (Reject Sell)", f"{n_rs}x")
    with col2:
        st.metric("Sinyal RB (Reject Buy)", f"{n_rb}x")

    last_rejections = df_rejection[
        df_rejection["is_reject_sell"] | df_rejection["is_reject_buy"]
    ].tail(10)

    if len(last_rejections) > 0:
        st.write("**10 sinyal terakhir:**")
        display_cols = ["Date", "Close", "upper_wick_pct", "lower_wick_pct",
                         "is_reject_sell", "is_reject_buy"]
        st.dataframe(last_rejections[display_cols], use_container_width=True, hide_index=True)
    else:
        st.write("Belum ada sinyal rejection pada rentang data ini.")

with tab3:
    st.subheader("Terbang Terjun")
    st.caption(
        "Oscillator berbasis regresi linear yang dinormalisasi (z-score), "
        "mendeteksi potensi pembalikan momentum harga."
    )

    n_sell = df_tt["is_sell_signal"].sum()
    n_buy = df_tt["is_buy_signal"].sum()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Sinyal SELL", f"{n_sell}x")
    with col2:
        st.metric("Sinyal BUY", f"{n_buy}x")

    st.write("**Grafik oscillator (dinormalisasi):**")
    chart_data = df_tt[["Date", "linreg_osc_norm"]].dropna().set_index("Date")
    st.line_chart(chart_data)

    last_tt_signals = df_tt[
        df_tt["is_sell_signal"] | df_tt["is_buy_signal"]
    ].tail(10)

    if len(last_tt_signals) > 0:
        st.write("**10 sinyal terakhir:**")
        display_cols = ["Date", "Close", "linreg_osc_norm", "is_sell_signal", "is_buy_signal"]
        st.dataframe(last_tt_signals[display_cols], use_container_width=True, hide_index=True)
    else:
        st.write("Belum ada sinyal Terbang Terjun pada rentang data ini.")


# ----------------------------------------------------------------------
# Export gabungan
# ----------------------------------------------------------------------
st.divider()
st.subheader("📥 Unduh Hasil Lengkap")

df_combined = raw_df.copy()
df_combined["is_bullish_kejepit"] = df_kejepit["is_bullish_kejepit"]
df_combined["is_bearish_kejepit"] = df_kejepit["is_bearish_kejepit"]
df_combined["is_reject_sell"] = df_rejection["is_reject_sell"]
df_combined["is_reject_buy"] = df_rejection["is_reject_buy"]
df_combined["linreg_osc_norm"] = df_tt["linreg_osc_norm"]
df_combined["is_tt_sell_signal"] = df_tt["is_sell_signal"]
df_combined["is_tt_buy_signal"] = df_tt["is_buy_signal"]

csv_bytes = df_combined.to_csv(index=False).encode("utf-8")
st.download_button(
    label="⬇️ Download CSV Hasil Eksperimen",
    data=csv_bytes,
    file_name="hasil_eksperimen_pola_candle.csv",
    mime="text/csv",
)

st.caption(
    "Catatan: Halaman ini dan ketiga pola di atas sepenuhnya independen dari "
    "model Random Forest pada halaman utama. Tidak ada data atau hasil dari "
    "halaman ini yang dipakai sebagai input model prediksi."
)
