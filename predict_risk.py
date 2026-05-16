"""
predict_risk.py
===============
Prediction API for a SINGLE user.
Dynamically loads the selected features from train_models.py output.

Usage (Python):
    from predict_risk import predict_risk
    result = predict_risk(user_input)

Usage (CLI):
    python predict_risk.py
"""

import os
import json
import warnings
import joblib
import numpy as np
import pandas as pd
import shap

warnings.filterwarnings("ignore")

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")

# ─── Risk thresholds ──────────────────────────────────────────────────────────
THRESHOLDS = {"HIGH": 0.65, "MODERATE": 0.35}


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _risk_level(score: float) -> str:
    if score >= THRESHOLDS["HIGH"]:
        return "HIGH"
    if score >= THRESHOLDS["MODERATE"]:
        return "MODERATE"
    return "LOW"


def _load_models():
    """Load pipeline objects and feature lists from disk (cached)."""
    if not hasattr(_load_models, "_cache"):
        d_model_path = os.path.join(MODELS_DIR, "diabetes_model.pkl")
        c_model_path = os.path.join(MODELS_DIR, "cardiac_model.pkl")
        d_feat_path  = os.path.join(MODELS_DIR, "diabetes_features.pkl")
        c_feat_path  = os.path.join(MODELS_DIR, "cardiac_features.pkl")

        for p in [d_model_path, c_model_path, d_feat_path, c_feat_path]:
            if not os.path.exists(p):
                raise FileNotFoundError(f"Missing: {p}. Run  python train_models.py  first.")

        _load_models._cache = {
            "diabetes":          joblib.load(d_model_path),
            "cardiac":           joblib.load(c_model_path),
            "diabetes_features": joblib.load(d_feat_path),
            "cardiac_features":  joblib.load(c_feat_path),
        }
    return _load_models._cache


def _extract_xgb(pipeline):
    """Pull the raw XGBClassifier out of an imblearn/sklearn Pipeline."""
    for _, step in pipeline.steps:
        if hasattr(step, "get_booster"):
            return step
    raise ValueError("Could not find XGBClassifier in pipeline.")


def _scale_input(pipeline, df: pd.DataFrame) -> np.ndarray:
    """Run only the StandardScaler step on the input DataFrame."""
    for name, step in pipeline.steps:
        if hasattr(step, "transform") and not hasattr(step, "fit_resample"):
            return step.transform(df)
    return df.values


# ══════════════════════════════════════════════════════════════════════════════
#  FEATURE BUILDERS — dynamic, based on selected features
# ══════════════════════════════════════════════════════════════════════════════

# Mapping from user-input keys to feature names (covers common aliases)
_INPUT_ALIASES = {
    "glucose":                      "blood_glucose_level",
    "blood_glucose":                "blood_glucose_level",
    "blood_glucose_level":          "blood_glucose_level",
    "blood_pressure":               "blood_pressure",
    "resting_blood_pressure":       "resting_blood_pressure",
    "bmi":                          "bmi",
    "age":                          "age",
    "sex":                          "sex",
    "gender":                       "gender",
    "pregnancies":                  "pregnancies",
    "insulin":                      "insulin",
    "skin_thickness":               "skin_thickness",
    "diabetes_pedigree_function":   "diabetes_pedigree_function",
    "cholesterol":                  "cholesterol",
    "chest_pain_type":              "chest_pain_type",
    "fasting_blood_sugar":          "fasting_blood_sugar",
    "fasting_blood_sugar_high":     "fasting_blood_sugar",
    "resting_ecg":                  "resting_ecg",
    "max_heart_rate":               "max_heart_rate",
    "exercise_angina":              "exercise_angina",
    "st_depression":                "st_depression",
    "hba1c_level":                  "hba1c_level",
    "hypertension":                 "hypertension",
    "heart_disease":                "heart_disease",
    "smoking_history":              "smoking_history",
}

# Encode mappings for categorical inputs
_SEX_MAP     = {"F": 0, "FEMALE": 0, "0": 0, "M": 1, "MALE": 1, "1": 1}
_SMOKE_MAP   = {"never": 0, "No Info": 1, "former": 2, "not current": 3, "current": 4, "ever": 5}


def _build_row(user: dict, features: list, medians: dict) -> pd.DataFrame:
    """Build a 1-row DataFrame matching the selected feature list."""
    row = {}
    for feat in features:
        # Try to find the value from user input (checking aliases)
        val = None
        for input_key, mapped in _INPUT_ALIASES.items():
            if mapped == feat and input_key in user:
                val = user[input_key]
                break
        # Also try the feature name directly
        if val is None and feat in user:
            val = user[feat]

        # Apply encoding / defaults
        if feat in ("sex", "gender"):
            raw = str(val if val is not None else "M").upper()
            row[feat] = _SEX_MAP.get(raw, 0)
        elif feat == "smoking_history":
            raw = str(val) if val is not None else "No Info"
            row[feat] = _SMOKE_MAP.get(raw, 1)
        elif feat == "pregnancies":
            sex_raw = str(user.get("sex", "M")).upper()
            is_male = sex_raw in ("M", "MALE", "1")
            age = float(user.get("age", 30))
            if is_male or age < 12:
                row[feat] = 0
            else:
                row[feat] = float(val) if val is not None else medians.get(feat, 0)
        elif val is not None:
            row[feat] = float(val)
        else:
            row[feat] = medians.get(feat, 0)

    return pd.DataFrame([row], columns=features)


# ══════════════════════════════════════════════════════════════════════════════
#  SHAP EXPLAINER
# ══════════════════════════════════════════════════════════════════════════════

def _compute_shap_contributions(pipeline, X_scaled: np.ndarray, feature_names: list) -> dict:
    xgb_model = _extract_xgb(pipeline)
    explainer  = shap.TreeExplainer(xgb_model)
    shap_vals  = explainer.shap_values(X_scaled)
    return {feat: round(float(shap_vals[0][i]), 4) for i, feat in enumerate(feature_names)}


# ══════════════════════════════════════════════════════════════════════════════
#  NATURAL-LANGUAGE EXPLANATION
# ══════════════════════════════════════════════════════════════════════════════

_LABEL_MAP = {
    "blood_glucose_level": "blood glucose level",
    "bmi": "BMI", "age": "age", "blood_pressure": "blood pressure",
    "insulin": "insulin level", "skin_thickness": "skin thickness",
    "diabetes_pedigree_function": "family history score",
    "pregnancies": "pregnancy history", "hba1c_level": "HbA1c level",
    "hypertension": "hypertension status", "heart_disease": "heart disease history",
    "smoking_history": "smoking history", "gender": "gender",
    "cholesterol": "cholesterol", "chest_pain_type": "chest pain pattern",
    "max_heart_rate": "max heart rate", "exercise_angina": "exercise-induced angina",
    "st_depression": "ST depression", "resting_ecg": "resting ECG",
    "fasting_blood_sugar": "fasting blood sugar", "sex": "sex",
    "chest_pain": "chest pain", "high_bp": "high blood pressure",
    "high_cholesterol": "high cholesterol", "smoking": "smoking status",
    "obesity": "obesity", "family_history": "family history",
    "shortness_of_breath": "shortness of breath", "fatigue": "fatigue",
    "sedentary_lifestyle": "sedentary lifestyle", "chronic_stress": "chronic stress",
    "has_diabetes": "diabetes status", "resting_blood_pressure": "resting blood pressure",
}


def _explain(user: dict, contributions: dict, risk_score: float, risk_level: str, condition: str) -> str:
    top = sorted(contributions.items(), key=lambda x: abs(x[1]), reverse=True)[:2]
    parts = [_LABEL_MAP.get(f, f.replace("_", " ")) for f, v in top if abs(v) > 0.01]

    severity = {"HIGH": "high", "MODERATE": "moderate", "LOW": "low"}[risk_level]
    if parts:
        return f"Your {' and '.join(parts)} are the main contributors to your {severity} {condition} risk (score: {risk_score:.2f})."
    return f"Overall {condition} risk score is {risk_score:.2f} ({risk_level})."


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN PREDICTION FUNCTION
# ══════════════════════════════════════════════════════════════════════════════

def predict_risk(user_input: dict) -> dict:
    """
    Predict diabetes and cardiac risk for a single user.

    Required keys: glucose (float), cholesterol (float)
    Optional: age, sex, bmi, blood_pressure, insulin, skin_thickness,
              diabetes_pedigree_function, pregnancies, chest_pain_type,
              fasting_blood_sugar, resting_ecg, max_heart_rate,
              exercise_angina, st_depression, hba1c_level, hypertension,
              heart_disease, smoking_history

    Returns dict with "diabetes" and "cardiac" sub-dicts.
    """
    cache = _load_models()

    # ── validate minimum required fields ──────────────────────────────────────
    for req in ("glucose", "cholesterol"):
        if req not in user_input:
            raise ValueError(f"Required field missing: '{req}'")

    results = {}
    for key, condition in [("diabetes", "diabetes"), ("cardiac", "cardiac")]:
        pipeline = cache[key]
        features = cache[f"{key}_features"]
        medians  = getattr(pipeline, "feature_medians_", {})
        base     = getattr(pipeline, "base_risk_", 0.35 if key == "diabetes" else 0.46)

        row    = _build_row(user_input, features, medians)
        score  = float(pipeline.predict_proba(row)[0][1])
        level  = _risk_level(score)

        scaled = _scale_input(pipeline, row)
        contribs = _compute_shap_contributions(pipeline, scaled, features)
        explanation = _explain(user_input, contribs, score, level, condition)

        results[key] = {
            "risk_score":            round(score, 4),
            "risk_level":            level,
            "feature_contributions": contribs,
            "base_risk":             round(base, 4),
            "explanation":           explanation,
        }

    return results


# ══════════════════════════════════════════════════════════════════════════════
#  CLI DEMO
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    sample_user = {
        "age": 35, "sex": "F", "bmi": 32.5, "blood_pressure": 88,
        "glucose": 165, "insulin": 180, "skin_thickness": 35,
        "diabetes_pedigree_function": 0.627, "pregnancies": 1,
        "cholesterol": 240, "chest_pain_type": 2,
        "fasting_blood_sugar": 0, "resting_ecg": 0,
        "max_heart_rate": 150, "exercise_angina": 0, "st_depression": 1.0,
        "hba1c_level": 6.5, "hypertension": 1, "smoking_history": "never",
    }

    print("\n🔍  Running prediction for sample user …\n")
    result = predict_risk(sample_user)
    print(json.dumps(result, indent=2))
