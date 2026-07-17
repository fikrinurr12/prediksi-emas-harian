"""
db.py - Penyimpanan riwayat prediksi memakai SQLite.

PENTING soal deploy di Railway:
Filesystem Railway itu EPHEMERAL secara default -- setiap kali redeploy/restart,
seluruh isi filesystem (termasuk file .db ini) DIHAPUS BERSIH kalau tidak dipasang
Volume. Supaya riwayat prediksi tidak hilang, WAJIB pasang Railway Volume dan arahkan
DB_PATH ke path di dalam volume tersebut (lihat README.md bagian "Riwayat Prediksi (SQLite)").

Catatan desain: tanggal_target TIDAK dihitung sebagai "tanggal_dibuat + 1 hari kalender",
karena pasar emas tutup di akhir pekan/libur -- kalau tanggal_dibuat jatuh di hari Jumat,
hari berikutnya yang sebenarnya adalah Senin, bukan Sabtu. Sebagai gantinya, tanggal_target
diisi belakangan saat resolusi: hari bursa PERTAMA setelah tanggal_dibuat yang datanya
sudah tersedia.
"""

import os
import sqlite3
from datetime import datetime

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "riwayat_prediksi.db"))


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS prediksi_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tanggal_dibuat TEXT NOT NULL UNIQUE,  -- tanggal data (T) saat prediksi dibuat
                tanggal_target TEXT,                  -- diisi belakangan: hari bursa berikutnya yg sebenarnya
                harga_close_saat_prediksi REAL NOT NULL,
                prediksi_arah TEXT NOT NULL,          -- 'NAIK' / 'TURUN'
                probabilitas REAL NOT NULL,
                harga_close_aktual_target REAL,
                benar INTEGER,                        -- 1 / 0 / NULL (belum diketahui)
                dicatat_pada TEXT NOT NULL
            )
        """)
        conn.commit()


def catat_dan_resolusi_prediksi(tanggal_dibuat, harga_close_saat_prediksi,
                                 prediksi_arah, probabilitas, df_riwayat_harga):
    """
    1. Simpan prediksi baru untuk tanggal_dibuat (idempotent -- 1 baris per tanggal data).
    2. Untuk semua baris LAMA yang belum punya outcome: cari hari bursa PERTAMA setelah
       tanggal_dibuat baris itu yang datanya sudah ada di df_riwayat_harga, lalu isi
       tanggal_target + harga_close_aktual_target + benar.

    df_riwayat_harga: DataFrame dengan kolom Date, Close, terurut naik berdasarkan tanggal.
    """
    init_db()
    harga_series = df_riwayat_harga.sort_values("Date").reset_index(drop=True)

    with get_conn() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO prediksi_log
               (tanggal_dibuat, harga_close_saat_prediksi, prediksi_arah, probabilitas, dicatat_pada)
               VALUES (?, ?, ?, ?, ?)""",
            (tanggal_dibuat, harga_close_saat_prediksi, prediksi_arah, probabilitas,
             datetime.now().isoformat()),
        )
        conn.commit()

        belum_resolusi = conn.execute(
            "SELECT * FROM prediksi_log WHERE harga_close_aktual_target IS NULL"
        ).fetchall()

        for row in belum_resolusi:
            tgl_dibuat = row["tanggal_dibuat"]
            setelah = harga_series[harga_series["Date"] > tgl_dibuat]
            if len(setelah) == 0:
                continue  # hari bursa berikutnya belum ada datanya -- coba lagi nanti
            baris_berikutnya = setelah.iloc[0]
            tanggal_target = baris_berikutnya["Date"].strftime("%Y-%m-%d") \
                if hasattr(baris_berikutnya["Date"], "strftime") else str(baris_berikutnya["Date"])[:10]
            harga_aktual = float(baris_berikutnya["Close"])
            arah_aktual = "NAIK" if harga_aktual > row["harga_close_saat_prediksi"] else "TURUN"
            benar = 1 if arah_aktual == row["prediksi_arah"] else 0
            conn.execute(
                """UPDATE prediksi_log SET tanggal_target = ?, harga_close_aktual_target = ?,
                   benar = ? WHERE id = ?""",
                (tanggal_target, harga_aktual, benar, row["id"]),
            )
        conn.commit()


def ambil_riwayat(limit=14):
    init_db()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM prediksi_log ORDER BY tanggal_dibuat DESC LIMIT ?", (limit,)
        ).fetchall()
    riwayat = [dict(r) for r in rows]

    total_resolved = [r for r in riwayat if r["benar"] is not None]
    akurasi_riwayat = (
        round(100 * sum(r["benar"] for r in total_resolved) / len(total_resolved), 1)
        if total_resolved else None
    )
    return riwayat, akurasi_riwayat, len(total_resolved)
