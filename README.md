# Gold Predictor

Sistem Prediksi Arah Pergerakan Harga Emas Harian menggunakan Random Forest
dan Indikator Teknikal (SMA, EMA, RSI, Stochastic Oscillator, PROC), berbasis
web dengan Flask.

> Proyek ini adalah implementasi dari skripsi:
> **"Prediksi Arah Pergerakan Harga Emas Harian Menggunakan Algoritma Random
> Forest dan Indikator Teknikal Berbasis Web"**

---

## Struktur Folder

```
gold-predictor/
├── app.py                      # Aplikasi Flask utama
├── indicators.py               # Implementasi rumus indikator teknikal
├── 01_fetch_data.py            # Tahap 3.4: Pengumpulan data dari yfinance
├── 02_preprocessing.py         # Tahap 3.6: Pembersihan, feature eng., pelabelan
├── 03_train_model.py           # Tahap 3.7-3.10: Training, evaluasi, simpan model
├── requirements.txt            # Daftar dependency Python
├── Procfile                    # Untuk Render / Railway
├── runtime.txt                 # Versi Python untuk hosting
├── data/
│   ├── gold_raw.csv            # Data mentah hasil fetch (dibuat otomatis)
│   └── gold_processed.csv      # Data siap latih (dibuat otomatis)
├── models/
│   ├── rf_model.pkl            # Model Random Forest terlatih
│   ├── scaler.pkl              # MinMaxScaler terlatih
│   ├── feature_importance.csv  # Hasil feature importance (MDI)
│   └── metrics.json            # Metrik evaluasi (akurasi, presisi, dll)
├── templates/
│   └── index.html              # Halaman utama (sesuai mockup Gambar 3.3)
└── static/
    ├── css/style.css
    └── js/main.js
```

---

## A. Setup Lokal (Langkah demi Langkah)

### 1. Buat virtual environment (opsional tapi disarankan)

```bash
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows
```

### 2. Install dependency

```bash
pip install -r requirements.txt
```

### 3. Ambil data emas 5 tahun terakhir

```bash
python 01_fetch_data.py
```

Ini akan membuat `data/gold_raw.csv`. Pastikan komputer punya akses internet
normal (tidak diblokir firewall kampus/kantor ke domain `*.finance.yahoo.com`).

Jika `GC=F` (Gold Futures) bermasalah, coba ganti `TICKER` di
`01_fetch_data.py` menjadi `"GLD"` (ETF emas, data lebih stabil tersedia).

### 4. Jalankan preprocessing

```bash
python 02_preprocessing.py
```

Ini akan:
- Membersihkan data (duplikat, nilai kosong)
- Menghitung 5 indikator teknikal (SMA, EMA, RSI, STI, PROC)
- Memberi label biner (1 = naik, 0 = turun) untuk hari berikutnya
- Menyimpan hasil ke `data/gold_processed.csv`

### 5. Latih model

```bash
python 03_train_model.py
```

Ini akan:
- Membagi data 80:20 secara temporal (urut waktu, tidak diacak)
- Melakukan normalisasi MinMaxScaler (fit hanya pada data latih)
- Melakukan GridSearchCV dengan TimeSeriesSplit (5-fold) untuk hyperparameter
  tuning sesuai Tabel 3.3
- Mengevaluasi model pada data uji (akurasi, presisi, recall, F1, confusion
  matrix)
- Menghitung feature importance (MDI)
- Menyimpan model ke `models/rf_model.pkl`, scaler ke `models/scaler.pkl`

**Catatan penting:** Script ini menggunakan `TimeSeriesSplit`, bukan `KFold`
biasa. Ini sengaja, karena data harga finansial bersifat berurutan waktu —
KFold acak bisa menyebabkan model "melihat" data masa depan saat training
(data leakage), yang membuat akurasi terlihat bagus secara palsu. Jika ingin
membahas ini di Bab III/IV skripsi, ini poin metodologis yang baik untuk
disebutkan sebagai penyempurnaan dari rencana awal.

### 6. Jalankan aplikasi Flask

```bash
python app.py
```

Buka browser ke `http://127.0.0.1:5000`

---

## B. Re-training Berkala

Karena harga emas terus berubah, sebaiknya model dilatih ulang secara
berkala (misalnya setiap beberapa minggu) supaya tetap relevan. Cukup
ulangi langkah 3-5 di atas.

---

## C. Deploy ke GitHub

```bash
git init
git add .
git commit -m "Initial commit: Gold Predictor system"
git branch -M main
git remote add origin https://github.com/USERNAME/gold-predictor.git
git push -u origin main
```

**Penting:** Pastikan file `models/rf_model.pkl` dan `models/scaler.pkl`
ikut di-push (jangan masukkan ke `.gitignore`), karena hosting butuh file
ini untuk menjalankan prediksi tanpa training ulang di server.

Jika file model berukuran besar (>50MB) dan GitHub menolak push, pertimbangkan
[Git LFS](https://git-lfs.github.com/) atau kurangi `n_estimators` di
`03_train_model.py`.

---

## D. Deploy ke Render

1. Buka [render.com](https://render.com), buat akun (bisa login dengan GitHub).
2. Klik **New +** → **Web Service**.
3. Hubungkan repository GitHub `gold-predictor`.
4. Isi konfigurasi:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
   - **Instance Type:** Free
5. Klik **Create Web Service**. Render akan otomatis build & deploy.
6. Setelah selesai, kamu akan dapat URL publik seperti
   `https://gold-predictor.onrender.com`

**Catatan:** Free tier Render akan "tidur" (sleep) setelah 15 menit tanpa
aktivitas, dan butuh sekitar 30-60 detik untuk bangun kembali saat diakses.
Ini normal untuk free tier, cukup untuk keperluan demo skripsi.

---

## E. Deploy ke Railway (alternatif)

1. Buka [railway.app](https://railway.app), login dengan GitHub.
2. Klik **New Project** → **Deploy from GitHub repo**.
3. Pilih repository `gold-predictor`.
4. Railway otomatis mendeteksi `Procfile` dan `requirements.txt`.
5. Setelah deploy selesai, klik **Settings** → **Generate Domain** untuk
   mendapatkan URL publik.

---

## F. Deploy ke PythonAnywhere (alternatif)

1. Buka [pythonanywhere.com](https://www.pythonanywhere.com), buat akun gratis.
2. Buka tab **Consoles** → buka **Bash console**.
3. Clone repository:
   ```bash
   git clone https://github.com/USERNAME/gold-predictor.git
   cd gold-predictor
   pip install --user -r requirements.txt
   ```
4. Buka tab **Web** → **Add a new web app** → pilih **Flask** → Python 3.11.
5. Edit konfigurasi WSGI file (`/var/www/USERNAME_pythonanywhere_com_wsgi.py`)
   agar mengarah ke `app.py`:
   ```python
   import sys
   path = '/home/USERNAME/gold-predictor'
   if path not in sys.path:
       sys.path.append(path)

   from app import app as application
   ```
6. Klik **Reload** pada tab Web. Aplikasi bisa diakses di
   `https://USERNAME.pythonanywhere.com`

---

## G. Troubleshooting Umum

| Masalah | Solusi |
|---|---|
| `yfinance` gagal fetch data (403/empty) | Coba ganti ticker ke `"GLD"`, atau cek koneksi internet/firewall |
| Model akurasi rendah (~50%) | Normal di awal; coba tambah data historis, atau tuning ulang `PARAM_GRID` |
| Render/Railway gagal build | Cek `requirements.txt`, pastikan versi compatible; cek log build |
| Prediksi error di server tapi jalan di lokal | Biasanya karena rate-limit yfinance dari IP server; tambahkan retry/delay |
| File model terlalu besar untuk GitHub | Kurangi `n_estimators`, atau gunakan Git LFS |

---

## H. Catatan untuk Bab III Skripsi

Jika ada penyesuaian teknis dari rencana awal proposal (misalnya penggunaan
`TimeSeriesSplit` alih-alih `KFold` standar untuk validasi silang), ini wajar
terjadi pada tahap implementasi dan sebaiknya didokumentasikan di Bab III
sebagai bagian dari proses penyempurnaan metodologi, dengan penjelasan
alasan teknis (mencegah data leakage pada data time series).
