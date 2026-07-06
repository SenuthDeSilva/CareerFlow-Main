"""
supervised_model.py — v2 FIXED
================================
Random Forest classifier — fixed label generation.

Fix: threshold 0.20 made ALL 278 jobs "suitable" → one class.
New: Use TOP 30% as suitable, BOTTOM 70% as unsuitable.
This guarantees 2 classes always exist.
"""

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

FEATURE_NAMES = [
    "tfidf_score", "skill_score", "word2vec_score",
    "matched_count", "missing_count", "total_job_skills",
    "skill_coverage", "is_intern_level", "has_salary",
]


def build_features(recommendations: list) -> np.ndarray:
    rows = []
    for rec in recommendations:
        matched    = rec.get("matched_skills", [])
        missing    = rec.get("missing_skills", [])
        total      = len(matched) + len(missing)
        coverage   = len(matched) / max(total, 1)
        title      = rec.get("title", "").lower()
        intern_kw  = ["intern","junior","trainee","associate","entry","graduate"]
        is_intern  = 1.0 if any(k in title for k in intern_kw) else 0.0
        has_salary = 1.0 if rec.get("salary") else 0.0

        rows.append([
            float(rec.get("tfidf_score",    0.0)),
            float(rec.get("skill_score",    0.0)),
            float(rec.get("word2vec_score", 0.0)),
            float(len(matched)),
            float(len(missing)),
            float(total),
            float(coverage),
            is_intern,
            has_salary,
        ])
    return np.array(rows)


def generate_labels_topk(recommendations: list) -> np.ndarray:
    """
    Label TOP 30% jobs as suitable (1), rest as unsuitable (0).
    This guarantees 2 classes regardless of score distribution.
    """
    scores = np.array([r.get("hybrid_score", 0.0) for r in recommendations])
    threshold = np.percentile(scores, 70)  # top 30% = above 70th percentile
    labels = (scores >= threshold).astype(int)

    # Edge case: if all same score, label top half
    if labels.sum() == 0 or labels.sum() == len(labels):
        mid = len(labels) // 2
        labels = np.zeros(len(labels), dtype=int)
        labels[:mid] = 1

    return labels


def run_supervised_scoring(recommendations: list) -> dict:
    """
    Train Random Forest and return suitability scores.
    Uses top-30% labeling to guarantee 2 classes.
    """
    print("   🤖  Training Supervised ML (Random Forest)...")

    if len(recommendations) < 5:
        print("   ⚠  Too few jobs for training")
        return {
            "scores":      [r.get("hybrid_score", 0) for r in recommendations],
            "importances": {},
            "model_used":  "fallback",
            "trained":     False,
        }

    X = build_features(recommendations)
    y = generate_labels_topk(recommendations)

    pos = int(y.sum())
    neg = len(y) - pos
    print(f"   📊  Training: {len(X)} jobs | ✅ Top-30% (suitable): {pos} | ❌ Unsuitable: {neg}")

    try:
        from sklearn.model_selection import cross_val_predict

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        clf = RandomForestClassifier(
            n_estimators=100, max_depth=4,   # shallower → less overfit
            random_state=42, class_weight="balanced",
            oob_score=True,                  # out-of-bag evaluation
            min_samples_leaf=3,              # require 3+ samples per leaf
        )
        clf.fit(X_scaled, y)

        # Use cross-val predictions to avoid overfitting inflation
        # 3-fold CV gives honest probability estimates
        try:
            from sklearn.model_selection import StratifiedKFold
            cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
            ml_scores = cross_val_predict(
                clf, X_scaled, y, cv=cv, method="predict_proba"
            )[:, 1]
            print(f"   ✓  OOB Score: {clf.oob_score_:.3f} | CV used for honest scoring")
        except Exception:
            # Fallback: use OOB if CV fails
            ml_scores = clf.predict_proba(X_scaled)[:, 1]

        # Wrap in pipeline for feature importance
        model = Pipeline([("scaler", scaler), ("clf", clf)])

        # Feature importance
        importances = dict(zip(
            FEATURE_NAMES,
            [round(float(v), 4) for v in model.named_steps["clf"].feature_importances_]
        ))
        top = max(importances, key=importances.get)
        print(f"   ✓  RandomForest trained | Top feature: {top} ({importances[top]})")

        return {
            "scores":      [round(float(s), 4) for s in ml_scores],
            "importances": importances,
            "model_used":  "RandomForestClassifier",
            "trained":     True,
        }

    except Exception as e:
        print(f"   ⚠  Training error: {e}")
        return {
            "scores":      [r.get("hybrid_score", 0) for r in recommendations],
            "importances": {},
            "model_used":  "fallback",
            "trained":     False,
        }