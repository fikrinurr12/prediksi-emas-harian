# Gold Predictor (Streamlit)

Sistem Prediksi Arah Pergerakan Harga Emas Harian menggunakan Random Forest
dan Indikator Teknikal (SMA, EMA, RSI, Stochastic Oscillator, PROC), berbasis
web dengan Streamlit.

> Versi Streamlit dari sistem ini. Untuk versi Flask, lihat folder/repo
> `gold-predictor` (tanpa suffix `-streamlit`).

---

## Struktur Folder

```
gold-predictor-streamlit/
├── app.py                      # Aplikasi Streamlit utama
├── indicators.py               # Implementasi rumus indikator teknikal
├── 01_fetch_data.py            # Tahap 3.4: Pengumpulan data dari yfinance
├── 02_preprocessing.py         # Tahap 3.6: Pembersihan, feature eng., pelabelan
├── 03_train_model.py           # Tahap 3.7-3.10: Training, evaluasi, simpan model
├── requirements.txt            # Daftar dependency Python
├── data/                       # Data mentah & hasil preprocessing (dibuat otomatis)
└── models/                     # Model, scaler, feature importance (dibuat otomatis)
```

---

## A. Setup & Training Lokal

Langkah 1-5 **identik** dengan versi Flask (lihat README versi Flask untuk
detail lengkap tiap tahap):

```bash
pip install -r requirements.txt
python 01_fetch_data.py
python 02_preprocessing.py
python 03_train_model.py
```

Setelah selesai, folder `models/` akan terisi `rf_model.pkl`, `scaler.pkl`,
`feature_importance.csv`, `metrics.json`.

**Alternatif:** Jika sudah training di Google Colab (`Gold_Predictor.ipynb`),
cukup download 4 file tersebut dan letakkan di folder `models/` di sini —
tidak perlu training ulang.

---

## B. Jalankan Aplikasi Streamlit Lokal

```bash
streamlit run app.py
```

Browser akan otomatis terbuka ke `http://localhost:8501`

---

## B.1 (Baru) Setup Fallback Twelve Data (Opsional, Disarankan)

Yahoo Finance via `yfinance` adalah sumber data utama sesuai proposal, tetapi
kadang mengalami rate limit terutama saat di-deploy di platform cloud yang
menggunakan shared IP (seperti Streamlit Community Cloud). Untuk mengatasi
ini, sistem dilengkapi fallback otomatis ke Twelve Data.

**Cara setup:**

1. Daftar gratis di [twelvedata.com](https://twelvedata.com) (tidak perlu
   kartu kredit), dapatkan API key dari dashboard.
2. **Untuk lokal:** copy `.streamlit/secrets.toml.example` menjadi
   `.streamlit/secrets.toml`, isi `TWELVEDATA_API_KEY` dengan key asli.
3. **Untuk Streamlit Community Cloud:** buka dashboard app → menu (...) →
   Settings → Secrets → paste isi berikut (dengan key asli):
   ```toml
   TWELVEDATA_API_KEY = "key_asli_kamu"
   ```

**Cara kerja fallback (urutan otomatis):**
1. Cek cache disk (kalau ada data yang masih segar, < 30 menit) → langsung pakai
2. Coba Yahoo Finance (dengan retry otomatis 3x, exponential backoff)
3. Kalau Yahoo Finance gagal total → coba Twelve Data (kalau API key diset)
4. Kalau semua gagal → pakai cache lama (walau sudah agak basi) sebagai upaya terakhir
5. Kalau benar-benar semua gagal dan tidak ada cache → tampilkan pesan error
   yang jelas dengan tombol "Coba Lagi"

Sistem akan menampilkan badge "Sumber Data" di dashboard supaya transparan
data yang ditampilkan berasal dari mana (Cache / Yahoo Finance / Twelve Data).

Tanpa API key Twelve Data, sistem tetap berfungsi normal (hanya fallback ke
Twelve Data yang tidak aktif) — cocok untuk yang ingin tetap 100% murni
mengandalkan Yahoo Finance sesuai proposal awal.

## C. Deploy ke GitHub

```bash
git init
git add .
git commit -m "Initial commit: Gold Predictor (Streamlit version)"
git branch -M main
git remote add origin https://github.com/USERNAME/gold-predictor-streamlit.git
git push -u origin main
```

**Penting:** Pastikan `models/rf_model.pkl` dan `models/scaler.pkl` ikut
di-push (jangan dimasukkan ke `.gitignore`), karena aplikasi butuh file ini
untuk berjalan tanpa training ulang di server.

---

## D. Deploy ke Streamlit Community Cloud (Gratis, Tanpa Kartu Kredit)

1. Buka [share.streamlit.io](https://share.streamlit.io)
2. Login dengan akun GitHub
3. Klik **Create app** → **From existing repo**
4. Pilih repository `gold-predictor-streamlit`
5. Isi:
   - **Branch:** `main`
   - **Main file path:** `app.py`
6. Klik **Deploy**

Setelah beberapa menit, aplikasi akan online dengan URL seperti
`https://USERNAME-gold-predictor-streamlit.streamlit.app`

**Keunggulan dibanding Render/Railway/PythonAnywhere:**
- Tidak perlu kartu kredit sama sekali
- Tidak ada pembatasan akses outbound ke API eksternal (yfinance bisa
  diakses dengan bebas)
- Tidak ada sleep policy yang agresif (meski tetap ada "app sleeping" untuk
  inactivity jangka sangat lama, tinggal klik untuk wake up)

---

## E. Troubleshooting

| Masalah | Solusi |
|---|---|
| `yfinance` gagal fetch data | Coba ganti `TICKER` di `app.py` dan script lain ke `"GLD"` |
| Model tidak ditemukan saat run `streamlit run app.py` | Pastikan sudah jalankan 01-03 atau pindahkan model dari Colab ke folder `models/` |
| Deploy gagal di Streamlit Cloud | Cek log di dashboard Streamlit Cloud, biasanya karena versi package di `requirements.txt` tidak cocok |
| Halaman lambat saat pertama dibuka | Normal — `st.cache_data` dan `st.cache_resource` butuh load sekali di awal, setelah itu lebih cepat |

---

## F. Catatan untuk Skripsi

Pergantian dari Flask ke Streamlit dilakukan pada tahap implementasi karena
kendala teknis pada platform hosting gratis untuk Flask (permintaan info
kartu kredit yang tidak konsisten, serta pembatasan akses jaringan keluar
yang menghambat pengambilan data real-time). Streamlit Community Cloud
dipilih sebagai pengganti karena mendukung kebutuhan sistem secara penuh
tanpa kendala tersebut. Lihat dokumen `Panduan_Revisi_Flask_ke_Streamlit.md`
untuk detail penyesuaian Bab II dan Bab III proposal.
