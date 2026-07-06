"""
role_predictor.py
=================
Runtime Career Role Predictor

Loads the pre-trained classifier from saved_models/best_role_model.pkl
and predicts the standardized IT career role from resume text.

Usage (CLI):
    python ml_model/role_predictor.py --predict "Python, Django, Machine Learning, TensorFlow"
    python ml_model/role_predictor.py --predict "React, Angular, TypeScript, CSS" --top 3
    python ml_model/role_predictor.py --report
"""

import os
import sys
import json
import argparse

import joblib

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "saved_models")
MODEL_PATH = os.path.join(MODELS_DIR, "best_role_model.pkl")

_cached_bundle = None


# ── Model Loading ─────────────────────────────────────────────────────────────

def load_model() -> dict:
    """Load trained model bundle from saved_models/. Cache after first load."""
    global _cached_bundle
    if _cached_bundle is not None:
        return _cached_bundle

    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"Trained model not found at {MODEL_PATH}. "
            f"Run: python ml_model/train_role_classifier.py"
        )

    bundle = joblib.load(MODEL_PATH)
    _cached_bundle = bundle
    return bundle


def is_model_available() -> bool:
    return os.path.exists(MODEL_PATH)


# ── Prediction ────────────────────────────────────────────────────────────────

def predict_role(resume_text: str, top_n: int = 3) -> dict:
    """
    Predict the standardized IT career role from resume text.

    Args:
        resume_text: Raw text extracted from the resume.
        top_n:       Number of top predictions to return.

    Returns:
        {
          "predicted_role": "AI/ML Engineer",
          "confidence": 87.3,
          "top_predictions": [
              {"role": "AI/ML Engineer", "confidence": 87.3},
              {"role": "Data Engineer",  "confidence": 8.1},
              ...
          ],
          "model_used": "Logistic Regression"
        }
    """
    if not resume_text or not resume_text.strip():
        return {
            "predicted_role":  "Software Engineer",
            "confidence":      0.0,
            "top_predictions": [{"role": "Software Engineer", "confidence": 0.0}],
            "model_used":      "fallback",
        }

    try:
        bundle = load_model()
        model  = bundle["model"]
        le     = bundle["label_encoder"]
        name   = bundle.get("model_name", "unknown")
        roles  = bundle.get("roles", le.classes_.tolist())

        # Support both bundle formats:
        # 1. notebook format  → separate 'vectorizer' + classifier 'model'
        # 2. pipeline format  → 'model' is a full sklearn Pipeline
        if "vectorizer" in bundle:
            X = bundle["vectorizer"].transform([resume_text])
        else:
            X = [resume_text]  # Pipeline handles vectorization internally

        proba = model.predict_proba(X)[0]

        # Top-N predictions
        top_idx = proba.argsort()[::-1][:top_n]
        top_preds = [
            {
                "role":       roles[i],
                "confidence": round(float(proba[i]) * 100, 1),
            }
            for i in top_idx
        ]

        return {
            "predicted_role":  top_preds[0]["role"],
            "confidence":      top_preds[0]["confidence"],
            "top_predictions": top_preds,
            "model_used":      name,
        }

    except Exception as e:
        print(f"[role_predictor] Prediction error: {e}")
        return {
            "predicted_role":  "Software Engineer",
            "confidence":      0.0,
            "top_predictions": [{"role": "Software Engineer", "confidence": 0.0}],
            "model_used":      "fallback",
        }


# ── Report ────────────────────────────────────────────────────────────────────

def print_report():
    """Print training evaluation report from saved_models/training_report.json."""
    report_path = os.path.join(MODELS_DIR, "training_report.json")
    if not os.path.exists(report_path):
        print("Training report not found. Run train_role_classifier.py first.")
        return

    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    print("\n" + "=" * 65)
    print("  Career Role Classifier — Evaluation Report")
    print("=" * 65)
    print(f"  Best Model   : {report.get('best_model', 'Unknown')}")

    # Handle both new format (best_f1) and old format (test_f1)
    best_f1 = report.get("best_f1") or report.get("test_f1", 0)
    if best_f1 and float(best_f1) <= 1.0:
        best_f1 = round(float(best_f1) * 100, 2)
    print(f"  Best F1      : {best_f1}%")
    print(f"  Total Samples: {report.get('total_samples', 'N/A')}")

    roles = report.get("roles", [])
    print(f"  Roles Trained: {len(roles)}")
    print()
    print(f"  {'Model':<30} {'Accuracy':>10} {'Precision':>10} {'Recall':>10} {'F1':>10}")
    print("  " + "-" * 65)

    # New format: evaluation is a dict
    evaluation = report.get("evaluation", {})
    if isinstance(evaluation, dict):
        for model_name, metrics in evaluation.items():
            print(
                f"  {model_name:<30} "
                f"{metrics.get('accuracy', 0):>9}%  "
                f"{metrics.get('precision', 0):>9}%  "
                f"{metrics.get('recall', 0):>9}%  "
                f"{metrics.get('f1_score', 0):>9}%"
            )
    else:
        # Old format: results is a list
        for entry in report.get("results", []):
            def pct(v): return round(float(v or 0) * 100, 2) if float(v or 0) <= 1.0 else round(float(v or 0), 2)
            print(
                f"  {entry.get('model',''):<30} "
                f"{pct(entry.get('cv_accuracy',0)):>9}%  "
                f"{pct(entry.get('cv_precision',0)):>9}%  "
                f"{pct(entry.get('cv_recall',0)):>9}%  "
                f"{pct(entry.get('cv_f1',0)):>9}%"
            )
    print("=" * 65 + "\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Career Role Predictor")
    parser.add_argument("--predict", type=str, help="Resume text or skill list to predict role for")
    parser.add_argument("--top",     type=int, default=3, help="Number of top predictions (default: 3)")
    parser.add_argument("--report",  action="store_true", help="Show evaluation report")
    args = parser.parse_args()

    if args.report:
        print_report()

    elif args.predict:
        result = predict_role(args.predict, top_n=args.top)
        print(f"\n  Input        : {args.predict[:80]}")
        print(f"  Predicted    : {result['predicted_role']} ({result['confidence']}%)")
        print(f"  Model Used   : {result['model_used']}")
        print("\n  Top Predictions:")
        for p in result["top_predictions"]:
            print(f"    {p['role']:<25} {p['confidence']:>6}%")
        print()

    else:
        parser.print_help()
