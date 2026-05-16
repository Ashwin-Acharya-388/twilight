"""
train_models.py
===============
Trains two XGBoost models with feature selection:
  1. Diabetes model  — Combined PIMA + Modern dataset
  2. Cardiac model   — Combined UCI + Risk PI dataset

Workflow:
  1. Load merged datasets (from merge_datasets.py)
  2. Train initial model on ALL features → extract importance
  3. Select top K features → retrain final model
  4. Save model + selected features to models/

Run:  python train_models.py
"""

import os
import warnings
import joblib
import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split, RandomizedSearchCV, StratifiedKFold
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, roc_auc_score, accuracy_score
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline
import xgboost as xgb

warnings.filterwarnings("ignore")

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(BASE_DIR, "data")
MODELS_DIR = os.path.join(BASE_DIR, "models")
os.makedirs(MODELS_DIR, exist_ok=True)

DIABETES_CSV = os.path.join(DATA_DIR, "combined_diabetes_data.csv")
CARDIAC_CSV  = os.path.join(DATA_DIR, "combined_cardiac_data.csv")

# ─── XGBoost hyperparameter search space ─────────────────────────────────────
XGB_PARAM_DIST = {
    "classifier__n_estimators":      [100, 200, 300],
    "classifier__max_depth":         [3, 4, 5, 6],
    "classifier__learning_rate":     [0.01, 0.05, 0.1, 0.2],
    "classifier__subsample":         [0.7, 0.8, 1.0],
    "classifier__colsample_bytree":  [0.7, 0.8, 1.0],
    "classifier__min_child_weight":  [1, 3, 5],
    "classifier__gamma":             [0, 0.1, 0.2],
    "classifier__reg_alpha":         [0, 0.1, 0.5],
    "classifier__reg_lambda":        [1, 1.5, 2],
}


# ══════════════════════════════════════════════════════════════════════════════
#  DATA LOADERS
# ══════════════════════════════════════════════════════════════════════════════

def load_diabetes_data() -> tuple[pd.DataFrame, pd.Series]:
    """Load combined diabetes CSV and return (X_all_features, y)."""
    df = pd.read_csv(DIABETES_CSV)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # ── find target ───────────────────────────────────────────────────────────
    target_col = next(
        (c for c in df.columns if c in ["diabetes", "outcome", "target", "label"]), None
    )
    if target_col is None:
        raise ValueError(f"No target column found. Columns: {df.columns.tolist()}")

    y = df[target_col].astype(int)

    # ── drop non-feature columns ──────────────────────────────────────────────
    drop = [target_col, "source"]
    X = df.drop(columns=[c for c in drop if c in df.columns])

    # ── encode categoricals ───────────────────────────────────────────────────
    if "gender" in X.columns:
        X["gender"] = X["gender"].map({"Female": 0, "Male": 1, "Other": 2}).fillna(0).astype(int)
    if "smoking_history" in X.columns:
        smoke_map = {"never": 0, "No Info": 1, "former": 2, "not current": 3, "current": 4, "ever": 5}
        X["smoking_history"] = X["smoking_history"].map(smoke_map).fillna(1).astype(int)

    # ── replace physiologically impossible zeros with NaN ─────────────────────
    for col in ["blood_glucose_level", "blood_pressure", "skin_thickness", "insulin", "bmi"]:
        if col in X.columns:
            X[col] = X[col].replace(0, np.nan)

    print(f"[Diabetes] Loaded {len(df)} rows, {X.shape[1]} features")
    print(f"  Class balance: {y.value_counts().to_dict()}\n")
    return X, y


def load_cardiac_data() -> tuple[pd.DataFrame, pd.Series]:
    """Load combined cardiac CSV and return (X_all_features, y)."""
    df = pd.read_csv(CARDIAC_CSV)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # ── find target ───────────────────────────────────────────────────────────
    target_col = next(
        (c for c in df.columns if c in ["target", "outcome", "heart_risk", "heartdisease", "label"]), None
    )
    if target_col is None:
        raise ValueError(f"No target column found. Columns: {df.columns.tolist()}")

    y = (df[target_col] > 0).astype(int)

    # ── drop non-feature columns ──────────────────────────────────────────────
    drop = [target_col, "source"]
    X = df.drop(columns=[c for c in drop if c in df.columns])

    # ── encode text categoricals if present ───────────────────────────────────
    if "chest_pain_type" in X.columns and X["chest_pain_type"].dtype == object:
        X["chest_pain_type"] = X["chest_pain_type"].map({"ATA": 1, "NAP": 2, "ASY": 3, "TA": 0}).fillna(0).astype(int)
    if "exercise_angina" in X.columns and X["exercise_angina"].dtype == object:
        X["exercise_angina"] = X["exercise_angina"].map({"Y": 1, "N": 0}).fillna(0).astype(int)
    if "sex" in X.columns and X["sex"].dtype == object:
        X["sex"] = X["sex"].map({"M": 1, "F": 0}).fillna(0).astype(int)

    print(f"[Cardiac] Loaded {len(df)} rows, {X.shape[1]} features")
    print(f"  Class balance: {y.value_counts().to_dict()}\n")
    return X, y


# ══════════════════════════════════════════════════════════════════════════════
#  FEATURE SELECTION + TRAINING
# ══════════════════════════════════════════════════════════════════════════════

def train_with_feature_selection(X, y, model_name="model", top_k=10):
    """
    Train model on all features, select top K, retrain on subset.

    Returns:
        dict: {
            'model': trained ImbPipeline (on top features),
            'features': list of selected feature names,
            'accuracy_full': float,
            'accuracy_top': float,
            'auc_top': float,
            'all_importances': dict of feature:importance
        }
    """
    feature_names = X.columns.tolist()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # ══════════════════════════════════════════════════════════════════════════
    # STEP 1: Quick model on ALL features (for importance ranking)
    # ══════════════════════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print(f"  STEP 1: {model_name} — training on ALL {len(feature_names)} features")
    print(f"{'='*60}")

    scale_pos = (y_train == 0).sum() / max((y_train == 1).sum(), 1)

    # Impute NaN before fitting (merged datasets have cross-source NaN)
    imputer = SimpleImputer(strategy="median")
    X_train_imp = pd.DataFrame(imputer.fit_transform(X_train), columns=feature_names, index=X_train.index)
    X_test_imp  = pd.DataFrame(imputer.transform(X_test), columns=feature_names, index=X_test.index)

    model_full = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.1,
        objective="binary:logistic",
        eval_metric="auc",
        scale_pos_weight=scale_pos,
        random_state=42,
        n_jobs=-1,
    )
    model_full.fit(X_train_imp, y_train)

    y_pred_full = model_full.predict(X_test_imp)
    accuracy_full = accuracy_score(y_test, y_pred_full)
    print(f"  ✅ Full model accuracy: {accuracy_full:.4f}")

    # ══════════════════════════════════════════════════════════════════════════
    # STEP 2: Extract feature importances, select top K
    # ══════════════════════════════════════════════════════════════════════════
    importances = model_full.feature_importances_
    feat_imp = sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True)

    print(f"\n  📊 Feature importance ranking for {model_name}:")
    for i, (feat, imp) in enumerate(feat_imp):
        marker = " ◀" if i < top_k else ""
        print(f"     {i+1:2d}. {feat:30s} {imp:.4f}{marker}")

    top_features = [f for f, _ in feat_imp[:top_k]]
    print(f"\n  🎯 Selected top {top_k}: {top_features}")

    # ══════════════════════════════════════════════════════════════════════════
    # STEP 3: Retrain on top K with full pipeline (SMOTE + tuning)
    # ══════════════════════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print(f"  STEP 3: {model_name} — retraining on TOP {top_k} features")
    print(f"{'='*60}")

    X_train_top = X_train_imp[top_features]
    X_test_top  = X_test_imp[top_features]

    minority_count = y_train.value_counts().min()
    k_neighbors = min(5, minority_count - 1) if minority_count > 1 else 1

    smote_ratio = 0.3 if model_name == "Diabetes" else 'auto'
    classifier_scale_pos = 1.0 if model_name == "Diabetes" else scale_pos

    pipeline = ImbPipeline([
        ("imputer",    SimpleImputer(strategy="median")),
        ("scaler",     StandardScaler()),
        ("smote",      SMOTE(random_state=42, k_neighbors=k_neighbors, sampling_strategy=smote_ratio)),
        ("classifier", xgb.XGBClassifier(
            objective="binary:logistic",
            eval_metric="auc",
            scale_pos_weight=classifier_scale_pos,
            random_state=42,
            n_jobs=-1,
        )),
    ])

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    search = RandomizedSearchCV(
        pipeline,
        param_distributions=XGB_PARAM_DIST,
        n_iter=30,
        scoring="roc_auc",
        cv=cv,
        random_state=42,
        n_jobs=-1,
        verbose=1,
    )
    # Feed raw (un-imputed) top features — pipeline's imputer handles NaN
    X_train_raw_top = X_train[top_features]
    X_test_raw_top  = X_test[top_features]
    search.fit(X_train_raw_top, y_train)

    best = search.best_estimator_
    y_pred_top = best.predict(X_test_raw_top)
    y_prob_top = best.predict_proba(X_test_raw_top)[:, 1]
    accuracy_top = accuracy_score(y_test, y_pred_top)
    auc_top = roc_auc_score(y_test, y_prob_top)

    print(f"\n  Best params: {search.best_params_}")
    print(f"  ✅ Top-{top_k} model accuracy: {accuracy_top:.4f}")
    print(f"  ✅ Top-{top_k} model AUC:      {auc_top:.4f}")
    diff = accuracy_full - accuracy_top
    print(f"  📉 Accuracy change: {diff:+.4f} ({diff/max(accuracy_full,1e-9)*100:+.1f}%)")
    print(f"\n  Classification Report:\n{classification_report(y_test, y_pred_top)}")

    # ── attach metadata to pipeline ──────────────────────────────────────────
    try:
        best.feature_names_in_ = top_features
    except AttributeError:
        best.__dict__["feature_names_in_"] = top_features
    best.feature_medians_  = X_train_top.median().to_dict()
    best.base_risk_        = float(y.mean())

    return {
        "model":            best,
        "features":         top_features,
        "accuracy_full":    accuracy_full,
        "accuracy_top":     accuracy_top,
        "auc_top":          auc_top,
        "all_importances":  dict(feat_imp),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print("\n🔧  Starting model training with feature selection …\n")

    # ── Diabetes ──────────────────────────────────────────────────────────────
    X_d, y_d = load_diabetes_data()
    d_result = train_with_feature_selection(X_d, y_d, model_name="Diabetes", top_k=10)
    joblib.dump(d_result["model"],    os.path.join(MODELS_DIR, "diabetes_model.pkl"))
    joblib.dump(d_result["features"], os.path.join(MODELS_DIR, "diabetes_features.pkl"))
    print(f"\n✅  Saved diabetes_model.pkl + diabetes_features.pkl")

    # ── Cardiac ───────────────────────────────────────────────────────────────
    X_c, y_c = load_cardiac_data()
    c_result = train_with_feature_selection(X_c, y_c, model_name="Cardiac", top_k=10)
    joblib.dump(c_result["model"],    os.path.join(MODELS_DIR, "cardiac_model.pkl"))
    joblib.dump(c_result["features"], os.path.join(MODELS_DIR, "cardiac_features.pkl"))
    print(f"\n✅  Saved cardiac_model.pkl + cardiac_features.pkl")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  TRAINING SUMMARY")
    print(f"{'='*60}")
    print(f"  Diabetes: full={d_result['accuracy_full']:.4f} → top10={d_result['accuracy_top']:.4f}  AUC={d_result['auc_top']:.4f}")
    print(f"  Cardiac:  full={c_result['accuracy_full']:.4f} → top10={c_result['accuracy_top']:.4f}  AUC={c_result['auc_top']:.4f}")
    print(f"\n  Diabetes features: {d_result['features']}")
    print(f"  Cardiac features:  {c_result['features']}")
    print(f"\n🎉  All models trained and saved to models/\n")


if __name__ == "__main__":
    main()
