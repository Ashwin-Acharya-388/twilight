"""
insurance_matcher.py
====================
Maps a user's risk output from predict_risk.py to the most suitable
insurance plans in the catalogue.

Usage:
    from insurance_matcher import match_plans
    plans = match_plans(risk_output, user_profile)

The function returns a list of plan dicts ranked by suitability_score.
"""

from __future__ import annotations
import json

# ══════════════════════════════════════════════════════════════════════════════
#  PLAN CATALOGUE  (seed data – 20 plans across health / life / critical)
#  Fields: id, name, type, insurer, premium_range (₹/yr), coverage_limit (₹),
#          key_coverages, exclusions, eligibility_age, waiting_period_months
# ══════════════════════════════════════════════════════════════════════════════

PLAN_CATALOGUE: list[dict] = [
    # ── Diabetes-focused ──────────────────────────────────────────────────────
    {
        "id": "D001",
        "name": "DiaCare 360",
        "type": "health",
        "insurer": "Star Health",
        "premium_range": (8_000, 18_000),
        "coverage_limit": 1_000_000,
        "key_coverages": ["diabetes_hospitalisation", "insulin_costs", "dialysis", "eye_complications"],
        "exclusions": ["cosmetic_surgery", "self_harm"],
        "eligibility_age": (18, 65),
        "waiting_period_months": 0,            # day-1 cover for diabetes
        "tags": ["diabetes"],
    },
    {
        "id": "D002",
        "name": "SugarShield Plus",
        "type": "health",
        "insurer": "Niva Bupa",
        "premium_range": (10_000, 22_000),
        "coverage_limit": 2_000_000,
        "key_coverages": ["diabetes_hospitalisation", "neuropathy", "retinopathy", "kidney_disease"],
        "exclusions": ["pre_existing_30_days", "war"],
        "eligibility_age": (21, 70),
        "waiting_period_months": 0,
        "tags": ["diabetes"],
    },
    {
        "id": "D003",
        "name": "GlucoSafe Family",
        "type": "health",
        "insurer": "HDFC ERGO",
        "premium_range": (15_000, 30_000),
        "coverage_limit": 5_000_000,
        "key_coverages": ["diabetes_hospitalisation", "family_floater", "preventive_checkups"],
        "exclusions": ["cosmetic_surgery"],
        "eligibility_age": (18, 65),
        "waiting_period_months": 12,
        "tags": ["diabetes", "family"],
    },

    # ── Cardiac-focused ───────────────────────────────────────────────────────
    {
        "id": "C001",
        "name": "HeartGuard Critical",
        "type": "critical_illness",
        "insurer": "ICICI Lombard",
        "premium_range": (12_000, 25_000),
        "coverage_limit": 5_000_000,
        "key_coverages": ["bypass_surgery", "angioplasty", "heart_attack", "stroke"],
        "exclusions": ["pre_existing_90_days", "alcohol_related"],
        "eligibility_age": (18, 65),
        "waiting_period_months": 3,
        "tags": ["cardiac"],
    },
    {
        "id": "C002",
        "name": "CardioShield Pro",
        "type": "critical_illness",
        "insurer": "Bajaj Allianz",
        "premium_range": (9_000, 20_000),
        "coverage_limit": 2_500_000,
        "key_coverages": ["heart_attack", "bypass_surgery", "valve_replacement", "pacemaker"],
        "exclusions": ["congenital_diseases", "war"],
        "eligibility_age": (21, 60),
        "waiting_period_months": 3,
        "tags": ["cardiac"],
    },
    {
        "id": "C003",
        "name": "HeartFirst Floater",
        "type": "health",
        "insurer": "Care Health",
        "premium_range": (20_000, 45_000),
        "coverage_limit": 10_000_000,
        "key_coverages": ["cardiac_hospitalisation", "ecg", "angiography", "rehab"],
        "exclusions": ["cosmetic_surgery", "self_harm"],
        "eligibility_age": (18, 70),
        "waiting_period_months": 0,
        "tags": ["cardiac", "family"],
    },

    # ── Dual (Diabetes + Cardiac) ─────────────────────────────────────────────
    {
        "id": "DC001",
        "name": "MetroHealth Comprehensive",
        "type": "health",
        "insurer": "Max Bupa",
        "premium_range": (18_000, 40_000),
        "coverage_limit": 5_000_000,
        "key_coverages": ["diabetes_hospitalisation", "cardiac_hospitalisation", "cancer", "stroke"],
        "exclusions": ["pre_existing_6_months", "war"],
        "eligibility_age": (18, 65),
        "waiting_period_months": 6,
        "tags": ["diabetes", "cardiac", "comprehensive"],
    },
    {
        "id": "DC002",
        "name": "LifeMax Critical 32",
        "type": "critical_illness",
        "insurer": "Tata AIA",
        "premium_range": (20_000, 60_000),
        "coverage_limit": 20_000_000,
        "key_coverages": ["32_critical_illnesses", "cancer", "cardiac", "diabetes_complications", "stroke"],
        "exclusions": ["pre_existing_90_days", "self_harm"],
        "eligibility_age": (18, 65),
        "waiting_period_months": 3,
        "tags": ["diabetes", "cardiac", "cancer", "comprehensive"],
    },

    # ── Cancer-focused ────────────────────────────────────────────────────────
    {
        "id": "CA001",
        "name": "CancerShield 360",
        "type": "critical_illness",
        "insurer": "Star Health",
        "premium_range": (8_000, 20_000),
        "coverage_limit": 5_000_000,
        "key_coverages": ["chemotherapy", "radiation", "surgery", "bone_marrow_transplant"],
        "exclusions": ["skin_cancer", "pre_existing_90_days"],
        "eligibility_age": (18, 65),
        "waiting_period_months": 3,
        "tags": ["cancer"],
    },
    {
        "id": "CA002",
        "name": "OncoCare Premier",
        "type": "critical_illness",
        "insurer": "HDFC Life",
        "premium_range": (15_000, 35_000),
        "coverage_limit": 10_000_000,
        "key_coverages": ["all_cancer_stages", "immunotherapy", "targeted_therapy", "palliative_care"],
        "exclusions": ["pre_existing_2_years"],
        "eligibility_age": (21, 60),
        "waiting_period_months": 6,
        "tags": ["cancer"],
    },

    # ── General / Top-up ──────────────────────────────────────────────────────
    {
        "id": "G001",
        "name": "HealthFirst Basic",
        "type": "health",
        "insurer": "New India Assurance",
        "premium_range": (4_000, 10_000),
        "coverage_limit": 500_000,
        "key_coverages": ["hospitalisation", "daycare", "ambulance"],
        "exclusions": ["cosmetic_surgery", "dental", "vision"],
        "eligibility_age": (18, 60),
        "waiting_period_months": 30,
        "tags": ["general"],
    },
    {
        "id": "G002",
        "name": "FamilyFirst Floater",
        "type": "health",
        "insurer": "United India",
        "premium_range": (8_000, 18_000),
        "coverage_limit": 1_000_000,
        "key_coverages": ["hospitalisation", "maternity", "newborn", "preventive_checkups"],
        "exclusions": ["pre_existing_4_years", "war"],
        "eligibility_age": (18, 65),
        "waiting_period_months": 30,
        "tags": ["general", "family"],
    },
    {
        "id": "G003",
        "name": "SuperTopUp 20L",
        "type": "health",
        "insurer": "Oriental Insurance",
        "premium_range": (3_000, 8_000),
        "coverage_limit": 2_000_000,
        "key_coverages": ["top_up_above_3L", "hospitalisation", "icu"],
        "exclusions": ["pre_existing_2_years"],
        "eligibility_age": (18, 70),
        "waiting_period_months": 12,
        "tags": ["general", "topup"],
    },

    # ── Senior / High-risk ────────────────────────────────────────────────────
    {
        "id": "S001",
        "name": "SeniorCare Plus",
        "type": "health",
        "insurer": "Niva Bupa",
        "premium_range": (25_000, 60_000),
        "coverage_limit": 5_000_000,
        "key_coverages": ["no_pre_existing_exclusion", "diabetes", "cardiac", "orthopaedic", "cancer"],
        "exclusions": ["cosmetic_surgery"],
        "eligibility_age": (60, 80),
        "waiting_period_months": 0,
        "tags": ["diabetes", "cardiac", "cancer", "senior"],
    },
    {
        "id": "S002",
        "name": "ElderShield Comprehensive",
        "type": "health",
        "insurer": "Star Health",
        "premium_range": (20_000, 50_000),
        "coverage_limit": 3_000_000,
        "key_coverages": ["senior_no_sub_limits", "cataract", "joint_replacement", "dialysis"],
        "exclusions": ["self_harm", "war"],
        "eligibility_age": (60, 80),
        "waiting_period_months": 0,
        "tags": ["diabetes", "cardiac", "senior"],
    },

    # ── Life ──────────────────────────────────────────────────────────────────
    {
        "id": "L001",
        "name": "Term Life 1Cr",
        "type": "life",
        "insurer": "LIC",
        "premium_range": (8_000, 15_000),
        "coverage_limit": 10_000_000,
        "key_coverages": ["death_benefit", "accidental_death_rider", "disability_waiver"],
        "exclusions": ["suicide_1year", "war"],
        "eligibility_age": (18, 60),
        "waiting_period_months": 0,
        "tags": ["general", "life"],
    },
    {
        "id": "L002",
        "name": "CritPlus Term",
        "type": "life",
        "insurer": "HDFC Life",
        "premium_range": (12_000, 28_000),
        "coverage_limit": 20_000_000,
        "key_coverages": ["death_benefit", "critical_illness_rider", "disability_rider", "waiver_on_diagnosis"],
        "exclusions": ["suicide_1year", "pre_existing_extreme"],
        "eligibility_age": (18, 65),
        "waiting_period_months": 0,
        "tags": ["cardiac", "cancer", "life"],
    },

    # ── Women's health ────────────────────────────────────────────────────────
    {
        "id": "W001",
        "name": "WomenFirst Health",
        "type": "health",
        "insurer": "Care Health",
        "premium_range": (7_000, 16_000),
        "coverage_limit": 2_000_000,
        "key_coverages": ["maternity", "cervical_cancer", "breast_cancer", "gestational_diabetes"],
        "exclusions": ["cosmetic_surgery", "infertility"],
        "eligibility_age": (18, 55),
        "waiting_period_months": 9,
        "tags": ["diabetes", "cancer", "women"],
    },
    {
        "id": "W002",
        "name": "SheShield Critical",
        "type": "critical_illness",
        "insurer": "Bajaj Allianz",
        "premium_range": (6_000, 14_000),
        "coverage_limit": 1_000_000,
        "key_coverages": ["breast_cancer", "ovarian_cancer", "heart_attack_women", "stroke"],
        "exclusions": ["pre_existing_90_days"],
        "eligibility_age": (18, 60),
        "waiting_period_months": 3,
        "tags": ["cancer", "cardiac", "women"],
    },
]


# ══════════════════════════════════════════════════════════════════════════════
#  SCORING LOGIC
# ══════════════════════════════════════════════════════════════════════════════

def _tag_relevance(plan: dict, diabetes_level: str, cardiac_level: str) -> float:
    """
    Returns a base relevance score based on condition flags in the plan tags.
    """
    score = 0.0
    tags  = plan.get("tags", [])

    risk_weight = {"HIGH": 1.0, "MODERATE": 0.6, "LOW": 0.2}

    if "diabetes" in tags:
        score += risk_weight.get(diabetes_level, 0)
    if "cardiac" in tags:
        score += risk_weight.get(cardiac_level, 0)
    if "comprehensive" in tags:
        score += 0.2
    if "general" in tags:
        score += 0.1

    return min(score, 1.0)


def _age_penalty(plan: dict, age: int) -> float:
    """Returns 0 if eligible, small penalty near edge, 1 if completely ineligible."""
    lo, hi = plan.get("eligibility_age", (0, 99))
    if lo <= age <= hi:
        return 0.0
    return 1.0   # hard filter – will be excluded


def _waiting_period_penalty(plan: dict, risk_level: str) -> float:
    """High-risk users should prefer plans with short/no waiting periods."""
    wp = plan.get("waiting_period_months", 12)
    if risk_level == "HIGH" and wp > 6:
        return 0.3
    if risk_level == "MODERATE" and wp > 24:
        return 0.15
    return 0.0


def _feature_boost(plan: dict, feature_contributions: dict, threshold: float = 0.05) -> float:
    """
    Boost plans that explicitly cover what SHAP says is risky.
    e.g. high glucose SHAP → boost plans covering diabetes_hospitalisation.
    """
    coverage = plan.get("key_coverages", [])
    boost = 0.0

    shap_to_coverage = {
        "glucose":             "diabetes_hospitalisation",
        "insulin":             "insulin_costs",
        "diabetes_pedigree_function": "diabetes_hospitalisation",
        "cholesterol":         "cardiac_hospitalisation",
        "exercise_angina":     "bypass_surgery",
        "st_depression":       "angioplasty",
        "chest_pain_type":     "cardiac_hospitalisation",
    }

    for feat, cov_keyword in shap_to_coverage.items():
        contrib = abs(feature_contributions.get(feat, 0))
        if contrib >= threshold and cov_keyword in coverage:
            boost += contrib * 0.5      # proportional to how important that feature was

    return min(boost, 0.3)


def _suitability_score(
    plan: dict,
    diabetes_level: str,
    cardiac_level: str,
    age: int,
    d_contributions: dict,
    c_contributions: dict,
) -> float:
    tag_score   = _tag_relevance(plan, diabetes_level, cardiac_level)
    age_pen     = _age_penalty(plan, age)
    wait_pen    = _waiting_period_penalty(plan, max(diabetes_level, cardiac_level, key=lambda x: ["LOW","MODERATE","HIGH"].index(x)))
    feat_boost  = _feature_boost(plan, {**d_contributions, **c_contributions})

    raw = tag_score + feat_boost - wait_pen
    if age_pen > 0:
        return 0.0   # completely ineligible

    return round(min(max(raw, 0.0), 1.0), 4)


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

def match_plans(
    risk_output: dict,
    user_profile: dict | None = None,
    top_n: int = 5,
) -> list[dict]:
    """
    Parameters
    ----------
    risk_output   : output dict from predict_risk.predict_risk()
    user_profile  : optional dict with keys like age, sex, annual_income
    top_n         : how many plans to return (default 5)

    Returns
    -------
    List of plan dicts, each enriched with:
        suitability_score   (float 0-1)
        recommendation_reason (str)
    """
    if user_profile is None:
        user_profile = {}

    age = int(user_profile.get("age", risk_output.get("diabetes", {}).get("feature_contributions", {}).get("age", 35) or 35))

    d_level = risk_output.get("diabetes", {}).get("risk_level", "LOW")
    c_level = risk_output.get("cardiac",  {}).get("risk_level", "LOW")
    d_contribs = risk_output.get("diabetes", {}).get("feature_contributions", {})
    c_contribs = risk_output.get("cardiac",  {}).get("feature_contributions", {})

    scored = []
    for plan in PLAN_CATALOGUE:
        score = _suitability_score(plan, d_level, c_level, age, d_contribs, c_contribs)
        if score == 0.0:
            continue   # ineligible

        reason = _build_reason(plan, d_level, c_level, d_contribs, c_contribs)
        scored.append({**plan, "suitability_score": score, "recommendation_reason": reason})

    scored.sort(key=lambda x: x["suitability_score"], reverse=True)
    return scored[:top_n]


def _build_reason(plan, d_level, c_level, d_contribs, c_contribs) -> str:
    tags = plan.get("tags", [])
    reasons = []

    if "diabetes" in tags and d_level in ("HIGH", "MODERATE"):
        reasons.append(f"covers diabetes-related hospitalisation ({d_level.lower()} diabetes risk)")
    if "cardiac" in tags and c_level in ("HIGH", "MODERATE"):
        reasons.append(f"covers cardiac events ({c_level.lower()} cardiac risk)")
    if plan.get("waiting_period_months", 12) == 0:
        reasons.append("day-one coverage with no waiting period")
    if "comprehensive" in tags:
        reasons.append("covers multiple conditions in one plan")

    top_d = sorted(d_contribs.items(), key=lambda x: abs(x[1]), reverse=True)
    if top_d and abs(top_d[0][1]) > 0.05:
        feat = top_d[0][0].replace("_", " ")
        reasons.append(f"matched to your elevated {feat} risk factor")

    return "; ".join(reasons).capitalize() + "." if reasons else "General coverage suitable for your profile."


# ══════════════════════════════════════════════════════════════════════════════
#  CLI DEMO
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Mock risk output (as if returned by predict_risk)
    mock_risk = {
        "diabetes": {
            "risk_score": 0.73,
            "risk_level": "HIGH",
            "feature_contributions": {
                "glucose": 0.28, "bmi": 0.15, "age": 0.10,
                "blood_pressure": 0.02, "insulin": 0.01, "diabetes_pedigree_function": 0.08,
                "skin_thickness": 0.03, "pregnancies": 0.00,
            },
            "base_risk": 0.35,
            "explanation": "High glucose and BMI are main contributors.",
        },
        "cardiac": {
            "risk_score": 0.21,
            "risk_level": "LOW",
            "feature_contributions": {
                "age": 0.05, "cholesterol": 0.08, "blood_pressure": 0.02,
                "chest_pain_type": -0.03, "max_heart_rate": -0.02,
                "exercise_angina": 0.11, "st_depression": 0.00,
                "fasting_blood_sugar_high": 0.00, "resting_ecg": 0.00, "sex": 0.00,
            },
            "base_risk": 0.46,
            "explanation": "Cholesterol slightly elevated but overall low risk.",
        },
    }

    plans = match_plans(mock_risk, user_profile={"age": 35}, top_n=5)
    print("\n🏥  Top Recommended Insurance Plans:\n")
    for i, p in enumerate(plans, 1):
        print(f"{i}. [{p['suitability_score']:.2f}] {p['name']} ({p['insurer']}) — {p['type']}")
        print(f"   ₹{p['premium_range'][0]:,} – ₹{p['premium_range'][1]:,}/yr  |  Cover: ₹{p['coverage_limit']:,}")
        print(f"   ✅ {p['recommendation_reason']}\n")
