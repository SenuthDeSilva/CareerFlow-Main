"""
train_role_classifier.py
========================
ML Training Pipeline — Career Role Classifier
(Implements all requirements from ML_Model_Design_for_Career_Recommendation_System.docx)

Professional fixes applied:
  - Tech synonym normalization  (ml→machine learning, js→javascript …)
  - Skills field weighted 3x    (strongest role signal)
  - Undersample Software Engineer to 800  (reduce 4638x imbalance)
  - class_weight='balanced'     (penalise minority-class errors more)
  - SMOTE oversampling          (synthetic minority samples, requires imbalanced-learn)
  - Macro F1 reported           (honest per-class performance, not biased by majority)
  - Per-class metrics + confusion matrix saved to training_report.json

Phase 1 — 7 classifiers, 5-fold Stratified CV
Phase 2 — GridSearchCV on LinearSVC C ∈ {0.1, 0.5, 1.0, 5.0, 10.0}

Run:
    python ml_model/train_role_classifier.py
"""

import os
import re
import sys
import json
import warnings

import joblib
import numpy as np
import pandas as pd

from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, f1_score, precision_score, recall_score,
    classification_report, confusion_matrix,
)
from sklearn.model_selection import (
    GridSearchCV, StratifiedKFold, cross_val_predict, train_test_split,
)
from sklearn.naive_bayes import MultinomialNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
from sklearn.svm import LinearSVC
from sklearn.tree import DecisionTreeClassifier

try:
    from imblearn.over_sampling import SMOTE
    from imblearn.pipeline import Pipeline as ImbPipeline
    SMOTE_AVAILABLE = True
except ImportError:
    SMOTE_AVAILABLE = False
    print("[WARN] imbalanced-learn not installed. SMOTE disabled.")
    print("       Run: pip install imbalanced-learn")

warnings.filterwarnings("ignore")

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "saved_models")
DATA_PATH  = os.path.join(BASE_DIR, "Dataset_jotpars.csv")

# Cap dominant class so it doesn't overwhelm minority classes
SE_CAP = 800

STANDARDIZED_ROLES = [
    "Software Engineer", "Backend Developer", "Frontend Developer",
    "Full Stack Developer", "Mobile Developer", "Data Analyst",
    "Data Engineer", "AI/ML Engineer", "DevOps Engineer", "Cloud Engineer",
    "QA Engineer", "Business Analyst", "UI/UX Designer",
    "Security Engineer", "System Administrator", "IT Support",
]


# ── Tech Synonym Normalization ────────────────────────────────────────────────

_SYNONYMS = [
    (r'\bml\b',     'machine learning'),
    (r'\bdl\b',     'deep learning'),
    (r'\bnlp\b',    'natural language processing'),
    (r'\bjs\b',     'javascript'),
    (r'\bts\b',     'typescript'),
    (r'\bk8s\b',    'kubernetes'),
    (r'\baws\b',    'amazon web services'),
    (r'\bgcp\b',    'google cloud platform'),
    (r'\bci/cd\b',  'continuous integration continuous deployment'),
    (r'\bui\b',     'user interface'),
    (r'\bux\b',     'user experience'),
    (r'\bdba\b',    'database administrator'),
    (r'\boop\b',    'object oriented programming'),
    (r'\brest\b',   'restful api'),
    (r'\bapi\b',    'application programming interface'),
]
_compiled_synonyms = [(re.compile(p), r) for p, r in _SYNONYMS]


def normalize_text(text: str) -> str:
    """Lowercase and expand common tech abbreviations."""
    t = str(text).lower()
    for pattern, replacement in _compiled_synonyms:
        t = pattern.sub(replacement, t)
    return t


# ── Role Mapping ──────────────────────────────────────────────────────────────

def map_to_standardized_role(title: str) -> str:
    """Map raw job title to one of 16 standardized IT career roles."""
    t = str(title).lower().strip()

    if any(k in t for k in ["full stack", "fullstack", "full-stack"]):
        return "Full Stack Developer"

    if any(k in t for k in ["android", " ios", "ios developer", "mobile app",
                             "mobile application", "flutter", "react native",
                             "xamarin", "swift developer", "kotlin developer"]):
        return "Mobile Developer"

    if any(k in t for k in ["machine learning", "deep learning",
                             "artificial intelligence", "ai engineer",
                             "data scien", "nlp engineer"]):
        return "AI/ML Engineer"

    if any(k in t for k in ["data engineer", "etl developer", "spark engineer",
                             "aws data"]):
        return "Data Engineer"

    if any(k in t for k in ["data analyst", "business intelligence",
                             "bi analyst", "web analytics", "data analysis"]):
        return "Data Analyst"

    if any(k in t for k in ["devops", "devsecops", "site reliability", " sre ",
                             "jr devops", "cloud devops"]):
        return "DevOps Engineer"

    if any(k in t for k in ["cloud architect", "cloud solution", "cloud backend",
                             "solution architect", "solutions architect",
                             "aws solution", "azure solution", "cloud engineer",
                             "infrastructure architect", "platform specialist",
                             "technical architect", "software architect"]):
        return "Cloud Engineer"

    if any(k in t for k in ["automation engineer", "qa engineer", "qe engineer",
                             "quality assurance", "test engineer", "tester"]):
        return "QA Engineer"

    if any(k in t for k in ["business analyst", "product manager",
                             "scrum master", "project manager",
                             "it manager", "technical project", "it project"]):
        return "Business Analyst"

    if any(k in t for k in ["graphic designer", "web designer", "ux designer",
                             "ui/ux", "game developer", "unity game", "3d designer"]):
        return "UI/UX Designer"

    if any(k in t for k in ["security engineer", "cybersecurity",
                             "penetration", "ethical hack"]):
        return "Security Engineer"

    if any(k in t for k in ["system admin", "sysadmin", "network admin",
                             "network engineer", "network analyst",
                             "system engineer", "it engineer", "hardware engineer",
                             "embedded software", "network support"]):
        return "System Administrator"

    if any(k in t for k in ["it support", "helpdesk", "help desk",
                             "technical support", "support engineer",
                             "desktop support"]):
        return "IT Support"

    if any(k in t for k in ["frontend", "front end", "front-end",
                             "react developer", "react engineer", "react js",
                             "react.js", "angular developer", "angularjs",
                             "vue js", "vue.js", "junior frontend",
                             "senior react", "web developer", "web engineer"]):
        return "Frontend Developer"

    # More specific backend rules — reduces label noise vs "Software Engineer"
    if any(k in t for k in ["backend", "back end", "back-end",
                             "node js", "nodejs", "node.js",
                             "django developer", "flask developer",
                             "fastapi developer", "laravel",
                             "spring boot", "spring developer",
                             "php developer", "php programmer",
                             "java developer", "java backend",
                             ".net developer", "dot net developer",
                             "asp.net developer", "python developer",
                             "magento", "wordpress developer"]):
        return "Backend Developer"

    return "Software Engineer"


# ── Data Preparation ──────────────────────────────────────────────────────────

_IT_KEYWORDS = {
    "software", "developer", "engineer", "programmer", "coder",
    "frontend", "backend", "fullstack", "full stack", "full-stack",
    "web developer", "mobile", "android", "ios", "flutter",
    "data", "analyst", "scientist", "machine learning", "ai ", "ml ",
    "devops", "cloud", "aws", "azure", "gcp", "kubernetes", "docker",
    "qa", "quality", "tester", "automation",
    "security", "cyber", "penetration",
    "network", "sysadmin", "system admin", "it support", "helpdesk",
    "database", "sql", "nosql", "react", "angular", "vue", "node",
    "java", "python", "php", ".net", "ruby", "golang", "scala",
    "ui/ux", "ux designer", "ui designer", "graphic designer",
    "product manager", "scrum", "business analyst", "it project",
    "tech lead", "technical", "infrastructure", "platform",
    "solution architect", "api", "microservices", "blockchain",
}


def _is_it_job(title: str) -> bool:
    t = str(title).lower()
    return any(kw in t for kw in _IT_KEYWORDS)


def load_and_prepare(path: str) -> pd.DataFrame:
    print("\n[1] Loading dataset...")
    df = pd.read_csv(path, encoding="latin-1")
    print(f"    Raw rows      : {len(df)}")

    df = df.rename(columns={"name": "title", "requirment": "skills"})
    df = df.dropna(subset=["title", "description"])
    df = df.drop_duplicates(subset=["title", "description"])
    print(f"    After clean   : {len(df)} rows")

    before_it = len(df)
    df = df[df["title"].apply(_is_it_job)].reset_index(drop=True)
    print(f"    IT jobs only  : {len(df)} rows ({before_it - len(df)} non-IT removed)")

    print("[2] Mapping titles to 16 standardized roles...")
    df["Standardized_Role"] = df["title"].apply(map_to_standardized_role)

    print("[3] Normalizing tech abbreviations (ml→machine learning, js→javascript …)")
    df["desc_norm"]   = df["description"].fillna("").apply(normalize_text)
    df["skills_norm"] = df["skills"].fillna("").apply(normalize_text)
    df["experience"]  = df["experience"].fillna(0).astype(str)

    # Skills repeated 3x: strongest discriminative signal gets more TF-IDF weight
    df["Text"] = (
        df["desc_norm"] + " " +
        df["skills_norm"] + " " + df["skills_norm"] + " " + df["skills_norm"] + " " +
        df["experience"] + " years"
    )

    dist_before = df["Standardized_Role"].value_counts()
    print(f"\n    Distribution before undersampling:")
    for role, cnt in dist_before.items():
        print(f"      {role:<25} : {cnt}")

    # Undersample dominant "Software Engineer" class
    se_count = (df["Standardized_Role"] == "Software Engineer").sum()
    if se_count > SE_CAP:
        df_se    = df[df["Standardized_Role"] == "Software Engineer"].sample(SE_CAP, random_state=42)
        df_other = df[df["Standardized_Role"] != "Software Engineer"]
        df = pd.concat([df_se, df_other]).reset_index(drop=True)
        print(f"\n    Undersampled 'Software Engineer': {se_count} → {SE_CAP}")

    dist_after = df["Standardized_Role"].value_counts()
    print(f"\n    Distribution after undersampling:")
    for role, cnt in dist_after.items():
        print(f"      {role:<25} : {cnt}")
    print(f"\n    Final samples : {len(df)}")

    return df


# ── Model Definitions ─────────────────────────────────────────────────────────
# Note: Linear Regression excluded — this is a classification problem (16 roles).

def get_models() -> dict:
    return {
        "Logistic Regression": LogisticRegression(
            max_iter=2000, C=1.0, solver="lbfgs", class_weight="balanced"
        ),
        "Decision Tree": DecisionTreeClassifier(
            max_depth=15, random_state=42, class_weight="balanced"
        ),
        "Linear SVM (Calibrated)": CalibratedClassifierCV(
            LinearSVC(max_iter=3000, C=1.0, class_weight="balanced"), cv=3
        ),
        "k-NN (cosine)": KNeighborsClassifier(
            n_neighbors=5, metric="cosine", algorithm="brute"
        ),
        "Multinomial NB": MultinomialNB(alpha=0.3),
        "Random Forest": RandomForestClassifier(
            n_estimators=100, random_state=42, n_jobs=-1, class_weight="balanced"
        ),
        "Gradient Boosting": GradientBoostingClassifier(
            n_estimators=100, learning_rate=0.1, max_depth=5, random_state=42
        ),
    }


# ── Pipeline Builder ──────────────────────────────────────────────────────────

def _make_pipeline(clf, use_smote: bool = True) -> Pipeline:
    """TF-IDF → (SMOTE) → classifier. SMOTE applied per fold inside CV."""
    tfidf = TfidfVectorizer(
        max_features=5000, ngram_range=(1, 2),
        stop_words="english", sublinear_tf=True,
    )
    if use_smote and SMOTE_AVAILABLE:
        return ImbPipeline([
            ("tfidf", tfidf),
            ("smote", SMOTE(random_state=42, k_neighbors=3, sampling_strategy='not majority')),
            ("clf",   clf),
        ])
    return Pipeline([("tfidf", tfidf), ("clf", clf)])


# ── Training & Evaluation ─────────────────────────────────────────────────────

def train_and_evaluate(df: pd.DataFrame) -> tuple:
    le = LabelEncoder()
    y  = le.fit_transform(df["Standardized_Role"])

    print(f"\n[4] Training 7 classifiers (5-fold Stratified CV)...")
    print(f"    Samples  : {len(df)}")
    print(f"    Classes  : {len(le.classes_)}")
    print(f"    SMOTE    : {'enabled' if SMOTE_AVAILABLE else 'disabled'}")
    print(f"    Balanced : class_weight=balanced (LR, DT, SVM, RF)")
    print()
    print(f"    {'Model':<30} {'W-Acc':>7} {'W-F1':>7} {'M-F1':>7}")
    print("    " + "-" * 58)

    models    = get_models()
    cv        = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    results   = {}
    best_f1   = -1
    best_name = None

    for name, clf in models.items():
        try:
            pipe   = _make_pipeline(clf, use_smote=True)
            y_pred = cross_val_predict(pipe, df["Text"], y, cv=cv, n_jobs=1)

            acc        = round(accuracy_score(y, y_pred) * 100, 2)
            w_prec     = round(precision_score(y, y_pred, average="weighted", zero_division=0) * 100, 2)
            w_rec      = round(recall_score(y, y_pred, average="weighted", zero_division=0) * 100, 2)
            w_f1       = round(f1_score(y, y_pred, average="weighted", zero_division=0) * 100, 2)
            macro_f1   = round(f1_score(y, y_pred, average="macro",    zero_division=0) * 100, 2)
            macro_prec = round(precision_score(y, y_pred, average="macro", zero_division=0) * 100, 2)
            macro_rec  = round(recall_score(y, y_pred, average="macro",    zero_division=0) * 100, 2)

            results[name] = {
                "accuracy":        acc,
                "precision":       w_prec,
                "recall":          w_rec,
                "f1_score":        w_f1,
                "macro_f1":        macro_f1,
                "macro_precision": macro_prec,
                "macro_recall":    macro_rec,
            }
            print(f"    {name:<30} {acc:>6}%  {w_f1:>6}%  {macro_f1:>6}%")

            if w_f1 > best_f1:
                best_f1   = w_f1
                best_name = name

        except Exception as e:
            print(f"    [WARN] {name} failed: {e}")
            results[name] = {
                "accuracy": 0, "precision": 0, "recall": 0, "f1_score": 0,
                "macro_f1": 0, "macro_precision": 0, "macro_recall": 0,
            }

    print(f"\n[5] Phase 1 best: {best_name} (W-F1={best_f1}%)")
    return results, best_name, le, df


# ── Phase 2 — GridSearchCV Tuning ────────────────────────────────────────────

def phase2_tune_svm(df: pd.DataFrame, le: LabelEncoder) -> dict:
    print("\n[6] Phase 2 — GridSearchCV (LinearSVC, class_weight=balanced)...")
    print("    C values: [0.1, 0.5, 1.0, 5.0, 10.0]")

    X_text = df["Text"].values
    y      = le.transform(df["Standardized_Role"])

    X_train, X_test, y_train, y_test = train_test_split(
        X_text, y, test_size=0.20, random_state=42, stratify=y
    )

    param_grid = {"clf__estimator__C": [0.1, 0.5, 1.0, 5.0, 10.0]}

    if SMOTE_AVAILABLE:
        base_pipe = ImbPipeline([
            ("tfidf", TfidfVectorizer(max_features=5000, ngram_range=(1, 2),
                                      stop_words="english", sublinear_tf=True)),
            ("smote", SMOTE(random_state=42, k_neighbors=3, sampling_strategy='not majority')),
            ("clf",   CalibratedClassifierCV(
                          LinearSVC(max_iter=3000, class_weight="balanced"), cv=3)),
        ])
    else:
        base_pipe = Pipeline([
            ("tfidf", TfidfVectorizer(max_features=5000, ngram_range=(1, 2),
                                      stop_words="english", sublinear_tf=True)),
            ("clf",   CalibratedClassifierCV(
                          LinearSVC(max_iter=3000, class_weight="balanced"), cv=3)),
        ])

    cv_strat = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    grid     = GridSearchCV(base_pipe, param_grid, cv=cv_strat,
                            scoring="f1_weighted", n_jobs=-1, verbose=0)
    grid.fit(X_train, y_train)

    best_C    = grid.best_params_["clf__estimator__C"]
    best_pipe = grid.best_estimator_
    y_pred    = best_pipe.predict(X_test)

    w_f1       = round(f1_score(y_test, y_pred, average="weighted", zero_division=0) * 100, 2)
    w_acc      = round(accuracy_score(y_test, y_pred) * 100, 2)
    w_prec     = round(precision_score(y_test, y_pred, average="weighted", zero_division=0) * 100, 2)
    w_rec      = round(recall_score(y_test, y_pred, average="weighted", zero_division=0) * 100, 2)
    macro_f1   = round(f1_score(y_test, y_pred, average="macro",    zero_division=0) * 100, 2)
    macro_prec = round(precision_score(y_test, y_pred, average="macro", zero_division=0) * 100, 2)
    macro_rec  = round(recall_score(y_test, y_pred, average="macro",    zero_division=0) * 100, 2)

    # Per-class metrics
    cr = classification_report(
        y_test, y_pred, target_names=le.classes_,
        output_dict=True, zero_division=0,
    )
    per_class = {
        role: {
            "precision": round(cr[role]["precision"] * 100, 2),
            "recall":    round(cr[role]["recall"]    * 100, 2),
            "f1_score":  round(cr[role]["f1-score"]  * 100, 2),
            "support":   int(cr[role]["support"]),
        }
        for role in le.classes_ if role in cr
    }

    conf_matrix = confusion_matrix(y_test, y_pred).tolist()

    print(f"    Best C          : {best_C}")
    print(f"    Weighted F1     : {w_f1}%")
    print(f"    Macro F1        : {macro_f1}%   ← honest per-class metric")
    print(f"    Accuracy        : {w_acc}%")

    # Refit on full dataset with best C
    if SMOTE_AVAILABLE:
        final_pipe = ImbPipeline([
            ("tfidf", TfidfVectorizer(max_features=5000, ngram_range=(1, 2),
                                      stop_words="english", sublinear_tf=True)),
            ("smote", SMOTE(random_state=42, k_neighbors=3, sampling_strategy='not majority')),
            ("clf",   CalibratedClassifierCV(
                          LinearSVC(max_iter=3000, C=best_C, class_weight="balanced"), cv=3)),
        ])
    else:
        final_pipe = Pipeline([
            ("tfidf", TfidfVectorizer(max_features=5000, ngram_range=(1, 2),
                                      stop_words="english", sublinear_tf=True)),
            ("clf",   CalibratedClassifierCV(
                          LinearSVC(max_iter=3000, C=best_C, class_weight="balanced"), cv=3)),
        ])
    final_pipe.fit(X_text, y)

    return {
        "best_C":           best_C,
        "f1":               w_f1,
        "accuracy":         w_acc,
        "precision":        w_prec,
        "recall":           w_rec,
        "macro_f1":         macro_f1,
        "macro_precision":  macro_prec,
        "macro_recall":     macro_rec,
        "per_class":        per_class,
        "confusion_matrix": conf_matrix,
        "pipeline":         final_pipe,
    }


# ── Save Best Model ───────────────────────────────────────────────────────────

def save_best_model(model_name: str, df: pd.DataFrame, le: LabelEncoder,
                    results: dict, tuned: dict) -> None:
    print(f"\n[7] Saving model bundle → saved_models/")
    os.makedirs(MODELS_DIR, exist_ok=True)

    bundle = {
        "model":         tuned["pipeline"],
        "label_encoder": le,
        "model_name":    f"Linear SVM Tuned (C={tuned['best_C']})",
        "roles":         le.classes_.tolist(),
        "test_f1":       tuned["f1"],
        "test_accuracy": tuned["accuracy"],
        "n_roles":       len(le.classes_),
        "phase":         "Phase1+2 (balanced + SMOTE + undersample + synonym norm)",
    }
    model_path = os.path.join(MODELS_DIR, "best_role_model.pkl")
    joblib.dump(bundle, model_path)
    print(f"    Saved: {model_path}")

    roles_path = os.path.join(MODELS_DIR, "feature_cols.json")
    with open(roles_path, "w", encoding="utf-8") as f:
        json.dump({"roles": le.classes_.tolist()}, f, indent=2)
    print(f"    Saved: {roles_path}")

    tuned_entry = {
        "accuracy":        tuned["accuracy"],
        "precision":       tuned["precision"],
        "recall":          tuned["recall"],
        "f1_score":        tuned["f1"],
        "macro_f1":        tuned["macro_f1"],
        "macro_precision": tuned["macro_precision"],
        "macro_recall":    tuned["macro_recall"],
    }

    report = {
        "best_model":      f"Linear SVM Tuned (C={tuned['best_C']})",
        "best_f1":         tuned["f1"],
        "best_macro_f1":   tuned["macro_f1"],
        "best_accuracy":   tuned["accuracy"],
        "n_roles":         len(le.classes_),
        "total_samples":   len(df),
        "roles":           le.classes_.tolist(),
        "smote_enabled":   SMOTE_AVAILABLE,
        "se_cap":          SE_CAP,
        "evaluation": {
            **results,
            f"Linear SVM Tuned (C={tuned['best_C']})": tuned_entry,
        },
        "tuned": {
            "best_C":          tuned["best_C"],
            "f1":              tuned["f1"],
            "accuracy":        tuned["accuracy"],
            "precision":       tuned["precision"],
            "recall":          tuned["recall"],
            "macro_f1":        tuned["macro_f1"],
            "macro_precision": tuned["macro_precision"],
            "macro_recall":    tuned["macro_recall"],
        },
        "per_class":        tuned["per_class"],
        "confusion_matrix": {
            "labels":  le.classes_.tolist(),
            "matrix":  tuned["confusion_matrix"],
        },
    }
    report_path = os.path.join(MODELS_DIR, "training_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"    Saved: {report_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 65)
    print("  ML Training Pipeline — Career Role Classifier")
    print("  Fixes: Balanced + SMOTE + Synonyms + Undersample + Macro F1")
    print("=" * 65)

    if not os.path.exists(DATA_PATH):
        print(f"[ERROR] Dataset not found: {DATA_PATH}")
        sys.exit(1)

    df = load_and_prepare(DATA_PATH)

    # Drop roles with too few samples for stratified 5-fold CV + SMOTE (need ≥10)
    role_counts = df["Standardized_Role"].value_counts()
    valid_roles = role_counts[role_counts >= 10].index.tolist()
    dropped = set(df["Standardized_Role"].unique()) - set(valid_roles)
    if dropped:
        print(f"\n    [INFO] Dropping roles with <5 samples: {dropped}")
        df = df[df["Standardized_Role"].isin(valid_roles)].reset_index(drop=True)

    results, best_name, le, df = train_and_evaluate(df)
    tuned = phase2_tune_svm(df, le)
    save_best_model(best_name, df, le, results, tuned)

    print("\n" + "=" * 65)
    print("  Training Complete!")
    print(f"  Phase 1 Best  : {best_name}")
    print(f"    W-F1={results[best_name]['f1_score']}%  M-F1={results[best_name]['macro_f1']}%")
    print(f"  Phase 2 Tuned : SVM C={tuned['best_C']}")
    print(f"    W-F1={tuned['f1']}%  M-F1={tuned['macro_f1']}%  Acc={tuned['accuracy']}%")
    print(f"  Roles trained : {len(le.classes_)}")
    print(f"  SMOTE         : {'enabled' if SMOTE_AVAILABLE else 'disabled'}")
    print("=" * 65)


if __name__ == "__main__":
    main()
