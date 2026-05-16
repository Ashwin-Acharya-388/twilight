# 🏥 Healthcare Risk Scoring — ML Layer

## Project Structure

```
project/
├── train_models.py           # Train both models, save to models/
├── predict_risk.py           # Single-user prediction API (with SHAP)
├── insurance_matcher.py      # Map risk scores → insurance plan recommendations
├── models/
│   ├── diabetes_model.pkl    # XGBoost pipeline (scaler + SMOTE + classifier)
│   ├── cardiac_model.pkl     # XGBoost pipeline (scaler + SMOTE + classifier)
│   ├── diabetes_features.pkl # Feature name list
│   └── cardiac_features.pkl  # Feature name list
├── data/
│   ├── diabetes_data.csv     # Pima Indians / Kaggle diabetes CSV → rename here
│   └── cardiac_data.csv      # UCI Heart Disease CSV → rename here
└── notebooks/
    └── model_exploration.ipynb   # SHAP visualizations, ROC curves, exploration
```

---

## Setup

### 1. Install dependencies

```bash
pip install xgboost scikit-learn imbalanced-learn shap joblib pandas numpy matplotlib seaborn
```

### 2. Place your datasets

Rename your downloaded CSVs:
- `diabetes_data.csv` → place in `data/`  (Pima Indians or Kaggle Diabetes Prediction)
- `cardiac_data.csv`  → place in `data/`  (UCI Heart Disease — Cleveland or Kaggle variant)

The loader handles both naming conventions automatically.

### 3. Train the models

```bash
python train_models.py
```

This will:
- Load and preprocess both datasets
- Apply SMOTE to handle class imbalance
- Run RandomizedSearchCV (30 iterations, 5-fold CV) for each model
- Print AUC + classification report
- Save 4 `.pkl` files to `models/`

Expected training time: ~3–8 minutes depending on hardware.

### 4. Run a prediction

```bash
python predict_risk.py
```

Or in your backend:

```python
from predict_risk import predict_risk

user = {
    # Shared
    "age": 35,
    "sex": "F",
    "bmi": 32.5,
    "blood_pressure": 88,

    # Diabetes-specific (glucose is required)
    "glucose": 165,
    "insulin": 180,
    "skin_thickness": 35,
    "diabetes_pedigree_function": 0.627,
    "pregnancies": 1,

    # Cardiac-specific (cholesterol is required)
    "cholesterol": 240,
    "chest_pain_type": 2,
    "fasting_blood_sugar_high": 0,
    "resting_ecg": 0,
    "max_heart_rate": 150,
    "exercise_angina": 0,
    "st_depression": 1.0,
}

result = predict_risk(user)
print(result["diabetes"]["risk_score"])    # e.g. 0.73
print(result["diabetes"]["risk_level"])    # HIGH / MODERATE / LOW
print(result["diabetes"]["explanation"])   # Plain-English reason
print(result["diabetes"]["feature_contributions"])  # SHAP per-feature dict
```

### 5. Get insurance plan matches

```python
from insurance_matcher import match_plans

plans = match_plans(result, user_profile={"age": 35}, top_n=5)
for p in plans:
    print(p["name"], p["suitability_score"], p["recommendation_reason"])
```

---

## Output Format

```json
{
  "diabetes": {
    "risk_score": 0.73,
    "risk_level": "HIGH",
    "feature_contributions": {
      "glucose": 0.28,
      "bmi": 0.15,
      "age": 0.10,
      "blood_pressure": 0.02,
      "insulin": 0.01,
      "diabetes_pedigree_function": 0.08,
      "skin_thickness": 0.03,
      "pregnancies": 0.0
    },
    "base_risk": 0.35,
    "explanation": "Your glucose level of 165 mg/dL and BMI of 32.5 are the main contributors to your high diabetes risk."
  },
  "cardiac": {
    "risk_score": 0.21,
    "risk_level": "LOW",
    "feature_contributions": {
      "age": 0.05,
      "cholesterol": 0.08,
      "blood_pressure": 0.02,
      "chest_pain_type": -0.03,
      "max_heart_rate": -0.02,
      "exercise_angina": 0.11
    },
    "base_risk": 0.46,
    "explanation": "Your cholesterol levels are slightly elevated but overall low cardiac risk."
  }
}
```

---

## Risk Thresholds

| Score       | Level    |
|-------------|----------|
| ≥ 0.65      | HIGH     |
| 0.35 – 0.65 | MODERATE |
| < 0.35      | LOW      |

---

## Missing Value Handling

| Feature                    | Rule                                                     |
|----------------------------|----------------------------------------------------------|
| `pregnancies`              | Set to 0 if user is male or age < 12                    |
| `insulin`                  | Imputed with dataset median                              |
| `skin_thickness`           | Imputed with dataset median                              |
| `diabetes_pedigree_function` | Default 0.5                                            |
| `chest_pain_type`          | Default 0 (typical angina)                              |
| `fasting_blood_sugar_high` | Default 0 (normal)                                      |
| `resting_ecg`              | Default 0 (normal)                                      |
| `max_heart_rate`           | Default 150 bpm                                         |
| `exercise_angina`          | Default 0 (no)                                          |
| `st_depression`            | Default 0.0                                             |

---

## Datasets

| Model    | Dataset                        | Source                          |
|----------|--------------------------------|---------------------------------|
| Diabetes | Pima Indians Diabetes          | Kaggle / UCI                    |
| Cardiac  | UCI Heart Disease (Cleveland)  | Kaggle UCI Heart Disease        |
# twilight
