# Flask App — Prediksi Arah Harga Emas Harian

Aplikasi web untuk menyajikan prediksi arah pergerakan harga emas harian dari model Random Forest + 5 indikator teknikal (SMA, EMA, RSI, STI, PROC), sesuai skripsi "Prediksi Arah Pergerakan Harga Emas Harian Menggunakan Algoritma Random Forest dan Indikator Teknikal".

## Yang berubah di revisi ini

- **Riwayat Prediksi (SQLite) dihapus.** Fitur ini sebelumnya berjalan di backend (`db.py`) tapi tidak pernah disebut di Bab III/IV skripsi maupun ditampilkan di halaman web -- jadi ada kode yang "hidup" tapi tidak sesuai naskah. Dihapus supaya kode yang dilampirkan benar-benar mencerminkan apa yang ditulis di skripsi. Konsekuensinya: tidak perlu lagi memasang Railway Volume atau environment variable `DB_PATH`.
- **Bug grafik "3 hari terakhir kosong / tidak auto-update"** diperbaiki. Sebelumnya jendela 7-hari grafik dihitung mundur dari tanggal kalender *hari ini* di server, padahal bar "hari ini" memang sengaja dibuang (supaya tidak memakai data GC=F yang masih live/belum settle) dan Yahoo Finance kadang baru menerbitkan bar harian beberapa jam setelah sesi tutup -- sehingga 1-3 hari terakhir bisa tampak kosong padahal itu bukan hari libur. Sekarang jendela grafik berlabuh pada **tanggal data terakhir yang benar-benar tersedia** (bukan tanggal kalender hari ini), jadi otomatis mengikuti begitu Yahoo menerbitkan bar baru. Hari libur bursa yang sungguhan (weekend, dsb.) tetap tampil sebagai bayangan abu-abu di grafik -- itu bukan bug.
- **Responsivitas mobile diperbaiki.** Root cause "tembus layar" sebelumnya: beberapa CSS Grid (`.hero`, `.ohlc-grid`, `.stat-grid`, dst.) tidak memakai `minmax(0, ...)` pada kolomnya, sehingga elemen dengan teks/angka lebar (mis. `$4,155.10`) bisa memaksa grid track melebar melebihi kontainer dan mendorong layar horizontal-scroll di HP. Perbaikan: seluruh grid utama sekarang pakai `minmax(0,1fr)`, ditambah breakpoint baru `max-width:480px` yang mengecilkan padding/font dan mengubah `.ohlc-grid` dari 4 kolom jadi 2 kolom di layar sempit. Grafik sekarang diberi ukuran lewat `aspect-ratio` CSS (bukan atribut `height` tetap di tag `<canvas>`), dan `overflow-x:hidden` dipasang di `html`/`body` sebagai lapisan pengaman terakhir.

## Struktur Folder

```
flask_project/
├── app.py                   # Aplikasi Flask utama (tanpa SQLite)
├── requirements.txt         # Daftar dependency Python
├── Procfile                 # Perintah start untuk Railway
├── railway.json             # Konfigurasi tambahan Railway
├── model/
│   ├── model_rf_emas.pkl    # Model Random Forest terlatih
│   ├── scaler_emas.pkl      # MinMaxScaler terlatih
│   └── model_metadata.json  # Info fitur, hyperparameter, metrik, hasil simulasi trading
├── templates/
│   └── index.html           # Halaman web (navbar, hero, model+feature importance, tentang, footer)
└── static/
    ├── style.css             # Styling (palet putih/hitam/emas #D4AF37), sudah responsif
    └── script.js             # Navbar on-scroll, fade-up, bar animasi, popup indikator, grafik
```

## ⚠️ SEBELUM DEPLOY — Langkah Wajib

Kalau Anda melatih ulang model dari notebook (`prediksi_emas_v3.ipynb`), ulangi langkah ini:

1. Jalankan notebook sampai selesai (bagian "Simpan Model, Scaler, Metadata").
2. Download `hasil_training_emas.zip` yang otomatis ter-download -- di dalamnya ada folder `model/` (3 file) dan `figures/` (untuk Bab III/IV).
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

Contoh bentuk respons `/api/predict` (nilai contoh, akan berbeda sesuai model yang aktif):
```json
{
  "status": "success",
  "data": {
    "tanggal_data": "2026-07-20",
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
    "model_info": { "akurasi_test": 52.82, "f1_score_test": 58.36, "baseline_akurasi": 56.05, "roc_auc": 0.5127 },
    "trading_sim": { "return_strategi_persen": 9.03, "return_buyhold_persen": -4.87, "...": "lihat model_metadata.json untuk field lengkap" },
    "chart": { "labels": ["...": "7 hari kalender terakhir yang datanya tersedia"], "data_per": "20 Jul 2026" }
  }
}
```
Catatan: `akurasi_test` sengaja ditampilkan **berdampingan** dengan `baseline_akurasi`, bukan sendirian -- supaya siapa pun yang memakai API ini langsung tahu apakah model benar-benar lebih baik dari tebakan mayoritas atau tidak.

## Catatan Penting Soal Konsistensi (Train/Serve Skew)

Fungsi `build_features()` di `app.py` **harus identik** dengan fungsi feature engineering yang dipakai di notebook training. Kalau Anda mengubah rumus indikator (misalnya ganti window N, atau ubah formula RSI) di notebook, **wajib** mengubah `app.py` dengan cara yang sama persis — kalau tidak, prediksi produksi tidak akan konsisten dengan hasil evaluasi skripsi.

## Disclaimer

Aplikasi ini adalah bagian dari penelitian skripsi. Berdasarkan pengujian metodologis yang menyeluruh (dijelaskan di Bab IV skripsi, termasuk walk-forward validation multi-jendela di notebook `v3`), performa model berada dalam kisaran yang sebanding dengan strategi baseline sederhana. **Ini bukan rekomendasi investasi** — nilai edukatif/akademis adalah tujuan utama aplikasi ini.
