# Flask App — Prediksi Arah Harga Emas Harian

Aplikasi web untuk menyajikan prediksi arah pergerakan harga emas harian dari model Random Forest + 5 indikator teknikal (SMA, EMA, RSI, STI, PROC), sesuai skripsi "Prediksi Arah Pergerakan Harga Emas Harian Menggunakan Algoritma Random Forest dan Indikator Teknikal".

## Struktur Folder

```
flask_project/
├── app.py                   # Aplikasi Flask utama
├── requirements.txt         # Daftar dependency Python
├── Procfile                 # Perintah start untuk Railway
├── railway.json             # Konfigurasi tambahan Railway
├── model/
│   ├── model_rf_emas.pkl    # Model Random Forest terlatih
│   ├── scaler_emas.pkl      # MinMaxScaler terlatih
│   └── model_metadata.json  # Info fitur, hyperparameter, metrik
├── templates/
│   └── index.html           # Halaman web tampilan prediksi
└── static/
    └── style.css             # Styling halaman
```

## ⚠️ SEBELUM DEPLOY — Langkah Wajib

**File `model/*.pkl` yang disertakan di sini adalah CONTOH** (dilatih untuk menguji aplikasi ini berfungsi dengan benar). **Ganti dengan model hasil training Anda sendiri** dari notebook `prediksi_emas_rf_FINAL.ipynb` di Colab:

1. Jalankan notebook FINAL di Colab sampai selesai (Sel 10 — "Simpan Model").
2. Download 3 file yang otomatis ter-download: `model_rf_emas.pkl`, `scaler_emas.pkl`, `model_metadata.json`.
3. **Timpa** file dengan nama sama di folder `model/` proyek ini.
4. **Cek versi scikit-learn** yang tercetak di Sel 1 notebook Colab (contoh: `scikit-learn version: 1.6.1`).
5. **Buka `requirements.txt`**, ubah baris `scikit-learn==...` supaya **sama persis** dengan versi di poin 4.

Kalau langkah 4-5 dilewatkan, aplikasi kemungkinan besar **gagal start di Railway** dengan error semacam `InconsistentVersionWarning` atau bahkan crash total saat memuat file `.pkl`.

## Menjalankan di Komputer Lokal (opsional, untuk tes dulu)

```bash
cd flask_project
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Buka `http://localhost:5000` di browser.

## Cara Deploy ke Railway

### Opsi A — Lewat GitHub (direkomendasikan)

1. Push folder `flask_project/` ini ke repository GitHub baru.
2. Buka [railway.app](https://railway.app), login, klik **New Project**.
3. Pilih **Deploy from GitHub repo**, pilih repository Anda.
4. Railway otomatis mendeteksi `Procfile`/`railway.json` dan mulai build.
5. Setelah build selesai, buka tab **Settings > Networking**, klik **Generate Domain** untuk mendapat URL publik.
6. Tunggu 1-2 menit, buka URL yang diberikan.

### Opsi B — Lewat Railway CLI

```bash
npm install -g @railway/cli
railway login
cd flask_project
railway init
railway up
railway domain   # untuk generate URL publik
```

## Endpoint yang Tersedia

| Endpoint | Fungsi |
|---|---|
| `GET /` | Halaman web menampilkan prediksi hari ini |
| `GET /api/predict` | Endpoint JSON — prediksi dalam format API |
| `GET /health` | Health check (dipakai Railway untuk memastikan aplikasi hidup) |

Contoh respons `/api/predict`:
```json
{
  "status": "success",
  "data": {
    "tanggal_data": "2026-07-08",
    "harga_close_terakhir": 4370.10,
    "prediksi": "NAIK",
    "probabilitas_naik": 55.98,
    "probabilitas_turun": 44.02,
    "indikator": { "SMA": 0.0018, "EMA": 0.0019, "RSI": 63.25, "STI": 50.04, "PROC": 0.0388 },
    "model_info": { "akurasi_test": 60.24, "f1_score_test": 73.02, "baseline_akurasi": 60.24 }
  }
}
```

## Catatan Penting Soal Konsistensi (Train/Serve Skew)

Fungsi `build_features()` di `app.py` **harus identik** dengan fungsi feature engineering yang dipakai di notebook training. Kalau Anda mengubah rumus indikator (misalnya ganti window N, atau ubah formula RSI) di notebook, **wajib** mengubah `app.py` dengan cara yang sama persis — kalau tidak, prediksi produksi tidak akan konsisten dengan hasil evaluasi skripsi.

## Disclaimer

Aplikasi ini adalah bagian dari penelitian skripsi. Berdasarkan pengujian metodologis yang menyeluruh (dijelaskan di Bab IV skripsi), performa model berada dalam kisaran yang sebanding dengan strategi baseline sederhana. **Ini bukan rekomendasi investasi** — nilai edukatif/akademis adalah tujuan utama aplikasi ini.
