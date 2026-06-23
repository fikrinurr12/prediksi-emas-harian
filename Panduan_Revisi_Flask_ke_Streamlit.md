# Panduan Revisi Proposal: Flask → Streamlit

Dokumen ini berisi bagian-bagian proposal yang perlu disesuaikan jika beralih
dari Flask ke Streamlit, beserta kalimat pengganti yang bisa langsung dipakai
atau didiskusikan dengan pembimbing.

---

## Mengapa perubahan ini diajukan

Disarankan menyampaikan alasan ini secara jujur ke pembimbing (bukan hanya
soal kemudahan, tapi alasan teknis yang konkret):

> "Pada tahap implementasi, ditemukan kendala teknis pada platform hosting
> gratis yang tersedia untuk Flask (Render, Railway, PythonAnywhere) — baik
> berupa permintaan informasi kartu kredit yang tidak konsisten antar akun,
> maupun pembatasan akses jaringan keluar (outbound) yang menghalangi sistem
> mengambil data harga emas secara real-time dari Yahoo Finance. Streamlit
> Community Cloud dipilih sebagai pengganti karena platform ini menyediakan
> hosting gratis tanpa kartu kredit dan tanpa pembatasan akses API eksternal,
> sehingga lebih sesuai dengan kebutuhan sistem yang harus mengambil data
> pasar secara langsung."

---

## Bagian yang perlu direvisi

### 1. Daftar Istilah dan Singkatan (halaman vii)

**Sebelum:**
Tidak ada entri khusus untuk Flask sebagai istilah (Flask disebut di body text).

**Setelah:**
Tidak perlu entri baru di Daftar Istilah, karena "Streamlit" juga nama
proper noun seperti "Flask", "Python", "Pandas" — cukup disebut di body text
sebagaimana istilah lain yang sudah ada.

---

### 2. Bab II, Sub-bab 2.2.23 (sebelumnya "Flask")

**Sebelum:**
> "2.2.23 Flask
> Flask merupakan microframework bawaan python yang cukup ringan, fleksibel,
> dan populer untuk mengembangkan sebuah machine learning kedalam website
> yang fungsionalitas..."

**Setelah (ganti total isi sub-bab, nomor tetap 2.2.23):**
> "2.2.23 Streamlit
> Streamlit merupakan framework berbasis python yang dirancang khusus untuk
> membangun aplikasi web interaktif dari skrip data science dan machine
> learning tanpa memerlukan pengetahuan mendalam tentang HTML, CSS, atau
> JavaScript (Streamlit Inc., 2024). Streamlit bekerja dengan mengeksekusi
> ulang seluruh skrip python dari atas ke bawah setiap kali ada interaksi
> pengguna, lalu me-render komponen antarmuka (tombol, grafik, tabel) secara
> otomatis berdasarkan kode python yang ditulis. Streamlit dipilih dalam
> penelitian ini karena kemudahan integrasinya dengan pustaka data science
> yang sudah digunakan (pandas, scikit-learn, matplotlib), serta ketersediaan
> platform hosting gratis (Streamlit Community Cloud) yang tidak membatasi
> akses jaringan keluar, sehingga mendukung pengambilan data harga emas
> secara real-time dari Yahoo Finance."

---

### 3. Bab II, Sub-bab 2.2.24 "Komponen Website" (Tabel 2.4)

**Sebelum:**
Tabel menyebutkan HTML, CSS, JS sebagai komponen yang disusun manual dalam
aplikasi berbasis Flask.

**Setelah:**
> "2.2.24 Komponen Aplikasi Streamlit
> Streamlit menyediakan komponen antarmuka bawaan (built-in widgets) yang
> dapat langsung dipanggil melalui kode python, tanpa perlu menulis HTML,
> CSS, atau JavaScript secara manual. Komponen-komponen utama yang digunakan
> dalam penelitian ini ditampilkan pada Tabel 2.4."

**Tabel 2.4 (revisi):**

| Komponen | Fungsi |
|---|---|
| `st.metric` | Menampilkan harga emas terkini beserta perubahan harian |
| `st.button` | Tombol untuk memicu proses prediksi |
| `st.dataframe` / `st.bar_chart` | Menampilkan tabel dan grafik feature importance |
| `st.columns` | Mengatur tata letak (layout) antarmuka menjadi beberapa kolom |
| `st.cache_data` | Menyimpan cache hasil pengambilan data agar aplikasi lebih responsif |

---

### 4. Bab III, Sub-bab 3.11.1 "Arsitektur Sistem"

**Sebelum:**
> "Sistem ini dibangun menggunakan framework Flask berbasis python yang
> ringan dan fleksibel. Komponen yang dibutuhkan dalam implementasi sistem
> ini adalah frontend menggunakan html, css, dan javascript yang bisa
> dikustom menggunakan framework flask untuk menangani permintaan dari
> pengguna dan hasil prediksi akan ditampilkan setelah pengguna melakukan
> prediksi."

**Setelah:**
> "Sistem ini dibangun menggunakan framework Streamlit berbasis python.
> Streamlit dipilih karena memungkinkan pengembangan antarmuka web langsung
> dari skrip python yang sama dengan skrip pelatihan model, tanpa memerlukan
> pemisahan kode frontend (HTML/CSS/JavaScript) dan backend secara manual.
> Model Random Forest yang telah dilatih dan disimpan dimuat ke dalam
> aplikasi Streamlit, yang kemudian menangani permintaan prediksi dari
> pengguna serta menampilkan hasilnya secara interaktif, termasuk visualisasi
> feature importance."

---

### 5. Bab III, Gambar 3.3 "Mockup Desain"

**Catatan:** Mockup desain (gradient ungu-biru, layout card) yang sudah ada
di proposal **tidak perlu diganti gambarnya** — cukup ditambahkan keterangan
bahwa implementasi akhir menyesuaikan dengan komponen visual yang tersedia
di Streamlit, yang secara fungsional tetap menampilkan elemen yang sama
(harga terkini, tombol prediksi, grafik feature importance), meski gaya
visualnya menyesuaikan dengan tema bawaan Streamlit.

Kalimat tambahan yang bisa disisipkan setelah Gambar 3.3:

> "Implementasi akhir dapat menyesuaikan elemen visual dengan komponen yang
> tersedia pada framework Streamlit, namun tetap mempertahankan struktur
> informasi yang sama seperti pada mockup di atas: judul sistem, status
> model, harga emas terkini, tombol aksi prediksi, dan visualisasi feature
> importance."

---

## Bagian yang TIDAK perlu diubah

- Judul skripsi — tidak menyebut Flask secara eksplisit, jadi tetap valid.
- Rumusan Masalah, Batasan Masalah, Tujuan — semua tetap relevan karena
  perubahan ini murni di sisi implementasi teknis (tool), bukan di metodologi
  inti (model RF, indikator teknikal, evaluasi).
- BAB I, II.1–II.22, III.1–III.10 — tidak tersentuh.

---

## Saran kalimat singkat untuk disampaikan ke pembimbing

> "Pak/Bu, saat proses implementasi saya menemukan kendala teknis terkait
> hosting gratis untuk Flask (beberapa platform meminta info kartu kredit
> atau membatasi akses internet keluar dari aplikasi). Saya ingin meminta
> izin untuk mengganti framework implementasi dari Flask ke Streamlit, yang
> secara fungsional sama (menampilkan hasil prediksi model di web), tapi
> platform hosting gratisnya lebih reliable untuk kebutuhan sistem yang
   mengambil data real-time. Perubahan ini hanya di Bab II (sub-bab 2.2.23,
> 2.2.24) dan Bab III (sub-bab 3.11.1), tidak mengubah model, indikator,
> atau metodologi inti penelitian."
