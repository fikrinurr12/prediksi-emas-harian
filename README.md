# Flask App — Prediksi Arah Harga Emas Harian

Aplikasi web untuk menyajikan prediksi arah pergerakan harga emas harian dari model Random Forest + 5 indikator teknikal (SMA, EMA, RSI, STI, PROC), sesuai skripsi "Prediksi Arah Pergerakan Harga Emas Harian Menggunakan Algoritma Random Forest dan Indikator Teknikal".

## Yang berubah di v3

- **Grafik realtime disederhanakan**: widget TradingView diganti dari "Advanced Chart" (banyak tombol, ada volume bar) ke "Mini Chart" -- tampilan garis tren polos, lebih mudah dibaca sekilas oleh orang awam.
- **Panel "Pengaruh Indikator"** menggantikan ikon robot di section Model -- bar chart persentase kontribusi tiap indikator, dihitung langsung dari `model.feature_importances_` model yang sedang aktif (tidak perlu retraining setiap kali ingin menampilkan ini).
- **Klik nama indikator** untuk popup penjelasan singkat fungsi indikator tersebut.
- **Riwayat Prediksi (SQLite)** -- section baru di landing page yang menampilkan histori prediksi vs hasil aktual, dicatat otomatis setiap kali halaman/​API diakses. Lihat catatan penting di bawah soal Railway.
- Hero section dipadatkan (padding dikurangi) supaya CTA dan kartu prediksi tidak terpotong di layar desktop standar.

## ⚠️ Riwayat Prediksi (SQLite) dan Railway -- WAJIB DIBACA

Riwayat prediksi disimpan di file SQLite lokal (`riwayat_prediksi.db`) lewat modul `db.py`.
**Railway TIDAK menyimpan filesystem secara permanen secara default** -- setiap kali Anda redeploy
atau aplikasi restart, file `.db` ini akan **hilang total** kalau tidak dipasang **Railway Volume**.

Cara memasang Volume di Railway:
1. Buka project Anda di Railway, klik service Flask ini.
2. Tab **Settings > Volumes**, klik **New Volume**.
3. Set mount path, misalnya `/data`.
4. Tambahkan environment variable `DB_PATH=/data/riwayat_prediksi.db` di tab **Variables**.
5. Redeploy. Sekarang riwayat prediksi akan tetap ada walau aplikasi di-restart/redeploy.

Kalau langkah ini dilewati, aplikasi tetap berjalan normal (riwayat cuma akan mulai dari nol lagi
setiap kali ada redeploy) -- tidak fatal, tapi riwayat jangka panjang tidak akan tersimpan.

## Struktur Folder

```
flask_project/
├── app.py                   # Aplikasi Flask utama
├── db.py                    # Modul SQLite untuk riwayat prediksi
├── riwayat_prediksi.db       # Dibuat otomatis saat pertama kali run (jangan commit ke git)
├── requirements.txt         # Daftar dependency Python
├── Procfile                 # Perintah start untuk Railway
├── railway.json             # Konfigurasi tambahan Railway
├── model/
│   ├── model_rf_emas.pkl    # Model Random Forest terlatih
│   ├── scaler_emas.pkl      # MinMaxScaler terlatih
│   └── model_metadata.json  # Info fitur, hyperparameter, metrik, hasil simulasi trading
├── templates/
│   └── index.html           # Halaman web (navbar, hero, model+feature importance, tentang, riwayat, footer)
└── static/
    ├── style.css             # Styling (palet putih/hitam/emas #D4AF37)
    └── script.js             # Navbar on-scroll, fade-up, bar animasi, popup indikator
```

## ⚠️ SEBELUM DEPLOY — Langkah Wajib

**Folder `model/` di sini SUDAH DIISI dengan model hasil training Anda sendiri** (dari `hasil_training_emas.zip` yang Anda jalankan di Colab, akurasi 50,20% / ROC-AUC 0,4975 -- lihat Bagian 0 dokumen revisi PDF). `requirements.txt` juga sudah disamakan ke `scikit-learn==1.6.1` sesuai versi di `model_metadata.json`.

**Kalau Anda retrain lagi nanti** (dapat model baru dari Colab), ulangi langkah ini:

1. Jalankan notebook sampai selesai (bagian "Simpan Model, Scaler, Metadata").
2. Download `hasil_training_emas.zip` yang otomatis ter-download -- di dalamnya ada folder `model/` (3 file) dan `figures/` (16 gambar untuk Bab III/IV).
3. **Timpa** 3 file di folder `model/` proyek Flask ini dengan yang baru.
4. **Cek versi scikit-learn** yang tercetak di sel pertama notebook Colab (contoh: `scikit-learn version: 1.6.1`).
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

Contoh respons `/api/predict` (angka riil dari model yang sedang aktif per 11 Juli 2026):
```json
{
  "status": "success",
  "data": {
    "tanggal_data": "2026-07-11",
    "harga_close_terakhir": 4104.10,
    "harga_open": 4122.30,
    "harga_high": 4125.80,
    "harga_low": 4090.60,
    "harga_idr_gram_estimasi": 2381694,
    "perubahan_persen": -0.64,
    "prediksi": "NAIK",
    "probabilitas_naik": 61.79,
    "probabilitas_turun": 38.21,
    "indikator": { "SMA": -0.0026, "EMA": -0.0016, "RSI": 56.63, "STI": 37.86, "PROC": 0.0042 },
    "feature_importance": [
      { "nama": "SMA", "persen": 23.1 }, { "nama": "EMA", "persen": 22.7 },
      { "nama": "RSI", "persen": 18.6 }, { "nama": "STI", "persen": 18.1 }, { "nama": "PROC", "persen": 17.5 }
    ],
    "model_info": { "akurasi_test": 50.20, "f1_score_test": 61.49, "baseline_akurasi": 56.22, "roc_auc": 0.4975 },
    "trading_sim": { "return_strategi_persen": 8.38, "return_buyhold_persen": -4.87, "...": "lihat model_metadata.json untuk field lengkap" },
    "riwayat": [ { "tanggal_dibuat": "2026-07-10", "prediksi_arah": "TURUN", "benar": 0, "...": "lihat db.py" } ],
    "akurasi_riwayat": 0.0,
    "jumlah_riwayat_resolved": 1
  }
}
```
Catatan: `akurasi_test` sengaja ditampilkan **berdampingan** dengan `baseline_akurasi`, bukan sendirian --
supaya siapa pun yang memakai API ini langsung tahu apakah model benar-benar lebih baik dari tebakan
mayoritas atau tidak (saat ini TIDAK -- 50,20% vs 56,22%). `akurasi_riwayat` berbeda dari `akurasi_test`:
`akurasi_test` adalah akurasi historis di data uji (bulan Juni-Juli 2026 ke belakang), sedangkan
`akurasi_riwayat` adalah akurasi LIVE yang baru mulai terkumpul sejak fitur SQLite ini aktif --
jangan disamakan, dan jangan simpulkan apa pun dari `akurasi_riwayat` sebelum datanya cukup banyak
(idealnya puluhan hari, bukan segelintir hari pertama).

## Catatan Penting Soal Konsistensi (Train/Serve Skew)

Fungsi `build_features()` di `app.py` **harus identik** dengan fungsi feature engineering yang dipakai di notebook training. Kalau Anda mengubah rumus indikator (misalnya ganti window N, atau ubah formula RSI) di notebook, **wajib** mengubah `app.py` dengan cara yang sama persis — kalau tidak, prediksi produksi tidak akan konsisten dengan hasil evaluasi skripsi.

## Disclaimer

Aplikasi ini adalah bagian dari penelitian skripsi. Berdasarkan pengujian metodologis yang menyeluruh (dijelaskan di Bab IV skripsi), performa model berada dalam kisaran yang sebanding dengan strategi baseline sederhana. **Ini bukan rekomendasi investasi** — nilai edukatif/akademis adalah tujuan utama aplikasi ini.
