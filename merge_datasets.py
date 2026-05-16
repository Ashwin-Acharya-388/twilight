"""
merge_datasets.py
=================
Combines diabetes and cardiac datasets into unified CSVs.
Run:  python merge_datasets.py
"""

import os
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)


def merge_diabetes():
    """Merge PIMA (768 rows) and Modern (100k rows) diabetes datasets."""
    print("=" * 60)
    print("  Merging Diabetes Datasets")
    print("=" * 60)

    # ── Load PIMA ─────────────────────────────────────────────────────────────
    pima = pd.read_csv(os.path.join(BASE_DIR, "The Original PIMA Dataset .csv"))
    pima.columns = pima.columns.str.strip()
    pima.rename(columns={
        "Pregnancies": "pregnancies",
        "Glucose": "blood_glucose_level",
        "BloodPressure": "blood_pressure",
        "SkinThickness": "skin_thickness",
        "Insulin": "insulin",
        "BMI": "bmi",
        "DiabetesPedigreeFunction": "diabetes_pedigree_function",
        "Age": "age",
        "Outcome": "diabetes",
    }, inplace=True)
    pima["source"] = "pima"

    # ── Load Modern ───────────────────────────────────────────────────────────
    modern = pd.read_csv(os.path.join(BASE_DIR, "diabetes_prediction_dataset.csv"))
    modern.columns = [c.strip().lower().replace(" ", "_") for c in modern.columns]
    modern["source"] = "modern"

    # ── Combine ───────────────────────────────────────────────────────────────
    combined = pd.concat([pima, modern], ignore_index=True, sort=False)
    feat_cols = [c for c in combined.columns if c != "source"]
    before = len(combined)
    combined.drop_duplicates(subset=feat_cols, keep="first", inplace=True)
    print(f"  Removed {before - len(combined)} duplicate rows")

    # ── Validation ────────────────────────────────────────────────────────────
    print(f"  Shape: {combined.shape}")
    print(f"  Columns: {combined.columns.tolist()}")
    print(f"  Source: {combined['source'].value_counts().to_dict()}")
    print(f"  Target: {combined['diabetes'].value_counts().to_dict()}")
    missing = combined.isnull().sum()
    for col in missing[missing > 0].index:
        print(f"    Missing {col}: {missing[col]} ({missing[col]/len(combined)*100:.1f}%)")

    out = os.path.join(DATA_DIR, "combined_diabetes_data.csv")
    combined.to_csv(out, index=False)
    print(f"  ✅ Saved {out} ({len(combined)} rows)\n")
    return combined


def merge_cardiac():
    """Merge UCI (303 rows) and Risk PI (70k rows) cardiac datasets."""
    print("=" * 60)
    print("  Merging Cardiac Datasets")
    print("=" * 60)

    # ── Load UCI ──────────────────────────────────────────────────────────────
    uci = pd.read_csv(os.path.join(BASE_DIR, "heart.csv"))
    uci.columns = uci.columns.str.strip()
    uci.rename(columns={
        "cp": "chest_pain_type", "trestbps": "resting_blood_pressure",
        "chol": "cholesterol", "fbs": "fasting_blood_sugar",
        "restecg": "resting_ecg", "thalach": "max_heart_rate",
        "exang": "exercise_angina", "oldpeak": "st_depression",
        "slope": "st_slope", "ca": "num_vessels", "thal": "thalassemia",
    }, inplace=True)
    uci["source"] = "uci"

    # ── Load Risk PI ──────────────────────────────────────────────────────────
    risk = pd.read_csv(os.path.join(
        BASE_DIR, "Heart Disease Risk Prediction Dataset",
        "heart_disease_risk_dataset_earlymed.csv"
    ))
    risk.columns = risk.columns.str.strip()
    risk.rename(columns={
        "Chest_Pain": "chest_pain", "Shortness_of_Breath": "shortness_of_breath",
        "Fatigue": "fatigue", "Palpitations": "palpitations",
        "Dizziness": "dizziness", "Swelling": "swelling",
        "Pain_Arms_Jaw_Back": "pain_arms_jaw_back",
        "Cold_Sweats_Nausea": "cold_sweats_nausea",
        "High_BP": "high_bp", "High_Cholesterol": "high_cholesterol",
        "Diabetes": "has_diabetes", "Smoking": "smoking",
        "Obesity": "obesity", "Sedentary_Lifestyle": "sedentary_lifestyle",
        "Family_History": "family_history", "Chronic_Stress": "chronic_stress",
        "Gender": "sex", "Age": "age", "Heart_Risk": "target",
    }, inplace=True)
    risk["source"] = "risk_pi"

    # ── Combine ───────────────────────────────────────────────────────────────
    combined = pd.concat([uci, risk], ignore_index=True, sort=False)
    feat_cols = [c for c in combined.columns if c != "source"]
    before = len(combined)
    combined.drop_duplicates(subset=feat_cols, keep="first", inplace=True)
    print(f"  Removed {before - len(combined)} duplicate rows")

    print(f"  Shape: {combined.shape}")
    print(f"  Columns: {combined.columns.tolist()}")
    print(f"  Source: {combined['source'].value_counts().to_dict()}")
    print(f"  Target: {combined['target'].value_counts().to_dict()}")
    missing = combined.isnull().sum()
    for col in missing[missing > 0].index:
        print(f"    Missing {col}: {missing[col]} ({missing[col]/len(combined)*100:.1f}%)")

    out = os.path.join(DATA_DIR, "combined_cardiac_data.csv")
    combined.to_csv(out, index=False)
    print(f"  ✅ Saved {out} ({len(combined)} rows)\n")
    return combined


if __name__ == "__main__":
    print("\n🔗 Starting dataset merge...\n")
    merge_diabetes()
    merge_cardiac()
    print("🎉 All datasets merged!\n")
