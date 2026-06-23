"""
03_train_model.py
==================
Tahap: 3.7 Pembuatan Model, 3.8 Pelatihan Model, 3.9 Evaluasi Model,
       3.10 Simpan Model (Bab III Metodologi)

PENTING - catatan metodologis:
    Data harga finansial bersifat time series (berurutan secara waktu).
    K-Fold Cross Validation standar (sklearn.model_selection.KFold) mengacak
    data secara acak, sehingga model bisa "melihat" data dari masa depan saat
    training -> ini disebut data leakage dan membuat akurasi terlihat bagus
    secara palsu.

    Script ini menggunakan TimeSeriesSplit, varian K-Fold yang menjaga urutan
    waktu (fold validasi selalu берasal dari periode SETELAH fold training).
    Ini ekuivalen secara konsep dengan Tabel 2.2 Penerapan Validasi Silang di
    skripsi, hanya saja diadaptasi agar valid untuk data time series.

Input : data/gold_processed.csv (hasil dari 02_preprocessing.py)
Output: models/rf_model.pkl, models/scaler.pkl, models/feature_importance.csv

Cara jalankan:
    python 03_train_model.py
"""

import pandas as pd
import numpy as np
import joblib
import os
import json

from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report
)

INPUT_PATH = "data/gold_processed.csv"
MODEL_DIR = "models"

FEATURE_COLS = ["SMA", "EMA", "RSI", "STI", "PROC"]
TARGET_COL = "Target"

# Sesuai Tabel 3.3 Parameter Model
PARAM_GRID = {
    "n_estimators": [100, 200, 300],
    "max_depth": [10, 20, None],
    "min_samples_split": [2, 5],
    "min_samples_leaf": [1, 2],
    "max_features": ["sqrt", "log2"],  # catatan: 'auto' sudah dihapus di sklearn >=1.3
}


def load_data():
    if not os.path.exists(INPUT_PATH):
        raise FileNotFoundError(
            f"'{INPUT_PATH}' tidak ditemukan. Jalankan 01_fetch_data.py dan "
            "02_preprocessing.py dahulu."
        )
    return pd.read_csv(INPUT_PATH)


def temporal_train_test_split(df: pd.DataFrame, test_size: float = 0.2):
    """
    3.5 Pembagian Data: splitting temporal 80:20.
    Data diurutkan berdasarkan tanggal, lalu dipotong sehingga data uji
    selalu berada SETELAH data latih secara waktu (tidak diacak).
    """
    df = df.sort_values("Date").reset_index(drop=True)
    split_idx = int(len(df) * (1 - test_size))

    train_df = df.iloc[:split_idx]
    test_df = df.iloc[split_idx:]

    print(f"Data latih : {len(train_df)} baris "
          f"({train_df['Date'].min()} s.d. {train_df['Date'].max()})")
    print(f"Data uji   : {len(test_df)} baris "
          f"({test_df['Date'].min()} s.d. {test_df['Date'].max()})")

    return train_df, test_df


def main():
    df = load_data()
    train_df, test_df = temporal_train_test_split(df, test_size=0.2)

    X_train_raw = train_df[FEATURE_COLS]
    y_train = train_df[TARGET_COL]
    X_test_raw = test_df[FEATURE_COLS]
    y_test = test_df[TARGET_COL]

    # ------------------------------------------------------------------
    # 3.6.4 Normalisasi Data
    # Scaler HANYA di-fit pada data latih, lalu dipakai untuk transform
    # data uji. Ini mencegah data leakage dari informasi data uji.
    # ------------------------------------------------------------------
    scaler = MinMaxScaler()
    X_train = scaler.fit_transform(X_train_raw)
    X_test = scaler.transform(X_test_raw)

    # ------------------------------------------------------------------
    # 3.8.3 Hyperparameter Tuning + 3.8.4 Validasi Silang
    # TimeSeriesSplit menjaga urutan waktu antar fold.
    # ------------------------------------------------------------------
    print("\nMemulai hyperparameter tuning dengan TimeSeriesSplit (n_splits=5)...")
    tscv = TimeSeriesSplit(n_splits=5)

    rf = RandomForestClassifier(random_state=42, n_jobs=-1)

    grid_search = GridSearchCV(
        estimator=rf,
        param_grid=PARAM_GRID,
        cv=tscv,
        scoring="accuracy",
        n_jobs=-1,
        verbose=1,
    )
    grid_search.fit(X_train, y_train)

    best_model = grid_search.best_estimator_
    print(f"\nParameter terbaik: {grid_search.best_params_}")
    print(f"Akurasi validasi silang terbaik (rata-rata fold): {grid_search.best_score_:.4f}")

    # ------------------------------------------------------------------
    # 3.9 Evaluasi Model pada data uji (data yang belum pernah dilihat model)
    # ------------------------------------------------------------------
    y_pred = best_model.predict(X_test)

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    cm = confusion_matrix(y_test, y_pred)

    print("\n" + "=" * 50)
    print("HASIL EVALUASI MODEL PADA DATA UJI")
    print("=" * 50)
    print(f"Akurasi   : {acc:.4f}")
    print(f"Presisi   : {prec:.4f}")
    print(f"Recall    : {rec:.4f}")
    print(f"F1-Score  : {f1:.4f}")
    print("\nConfusion Matrix:")
    print(cm)
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=["Turun (0)", "Naik (1)"]))

    # ------------------------------------------------------------------
    # 2.2.12 Feature Importance (Mean Decrease Impurity / MDI bawaan RF)
    # ------------------------------------------------------------------
    importances = best_model.feature_importances_
    fi_df = pd.DataFrame({
        "Feature": FEATURE_COLS,
        "Importance": importances
    }).sort_values("Importance", ascending=False).reset_index(drop=True)

    print("\nFeature Importance (MDI):")
    print(fi_df)

    # ------------------------------------------------------------------
    # 3.10 Simpan Model
    # ------------------------------------------------------------------
    os.makedirs(MODEL_DIR, exist_ok=True)

    joblib.dump(best_model, os.path.join(MODEL_DIR, "rf_model.pkl"))
    joblib.dump(scaler, os.path.join(MODEL_DIR, "scaler.pkl"))
    fi_df.to_csv(os.path.join(MODEL_DIR, "feature_importance.csv"), index=False)

    metrics = {
        "accuracy": acc,
        "precision": prec,
        "recall": rec,
        "f1_score": f1,
        "confusion_matrix": cm.tolist(),
        "best_params": grid_search.best_params_,
        "cv_best_score": grid_search.best_score_,
        "feature_columns": FEATURE_COLS,
        "train_size": len(train_df),
        "test_size": len(test_df),
    }
    with open(os.path.join(MODEL_DIR, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"\nModel disimpan ke: {MODEL_DIR}/rf_model.pkl")
    print(f"Scaler disimpan ke: {MODEL_DIR}/scaler.pkl")
    print(f"Feature importance disimpan ke: {MODEL_DIR}/feature_importance.csv")
    print(f"Metrik evaluasi disimpan ke: {MODEL_DIR}/metrics.json")


if __name__ == "__main__":
    main()
