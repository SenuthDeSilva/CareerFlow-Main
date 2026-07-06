"""
xai_engine.py
=============
Phase 5 — XAI (Explainable AI) Main Engine.

Combines SHAP + LIME explanations for every job recommendation,
generating human-readable explanations for WHY each job was recommended.

Usage:
    python xai/xai_engine.py --resume-id 1 --top 5
    python xai/xai_engine.py --resume-id 1 --job-id 42
"""

import os
import sys
import json
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xai.shap_explainer import explain_recommendation
from xai.lime_explainer import explain_with_lime
from database.db_config import SessionLocal, text as sql_text

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "xai", "output")


# ─────────────────────────────────────────────────────────────
# Database Helpers
# ─────────────────────────────────────────────────────────────

def get_resume(resume_id: int) -> dict:
    db = SessionLocal()
    try:
        result = db.execute(
            sql_text("SELECT * FROM resumes WHERE id = :id"), {"id": resume_id}
        ).fetchone()
        if not result: return {}
        row = dict(result._mapping)
        row["hard_skills"] = json.loads(row.get("hard_skills") or "[]")
        row["soft_skills"] = json.loads(row.get("soft_skills") or "[]")
        row["all_skills"]  = json.loads(row.get("all_skills")  or "[]")
        return row
    finally:
        db.close()


def get_recommendations(resume_id: int, top_n: int = 5) -> list:
    db = SessionLocal()
    try:
        results = db.execute(sql_text("""
            SELECT * FROM recommendations
            WHERE resume_id = :rid
            ORDER BY rank ASC
            LIMIT :n
        """), {"rid": resume_id, "n": top_n}).fetchall()
        recs = []
        for r in results:
            row = dict(r._mapping)
            row["matched_skills"] = json.loads(row.get("matched_skills") or "[]")
            row["missing_skills"] = json.loads(row.get("missing_skills") or "[]")
            recs.append(row)
        return recs
    finally:
        db.close()


def get_job(job_id: int) -> dict:
    db = SessionLocal()
    try:
        result = db.execute(
            sql_text("SELECT * FROM jobs WHERE id = :id"), {"id": job_id}
        ).fetchone()
        return dict(result._mapping) if result else {}
    finally:
        db.close()


def save_explanations(resume_id: int, explanations: list, candidate: str):
    """Save XAI explanations to JSON file."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    fname = f"xai_resume{resume_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    fpath = os.path.join(OUTPUT_DIR, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump({
            "resume_id":    resume_id,
            "candidate":    candidate,
            "generated_at": datetime.now().isoformat(),
            "explanations": explanations,
        }, f, indent=2, ensure_ascii=False)
    print(f"✓  XAI report saved: {fpath}")
    return fpath


# ─────────────────────────────────────────────────────────────
# Main XAI Engine
# ─────────────────────────────────────────────────────────────

def explain_recommendations(resume_id: int, top_n: int = 5) -> list:
    """
    Generate SHAP + LIME explanations for top N job recommendations.

    Args:
        resume_id (int): Resume ID from DB
        top_n     (int): Number of recommendations to explain

    Returns:
        list: Full explanations for each recommended job
    """
    print("\n" + "="*60)
    print("🔍  XAI Engine — Phase 5 (SHAP + LIME)")
    print("="*60)

    # Load resume
    resume = get_resume(resume_id)
    if not resume:
        print(f"✗  Resume ID {resume_id} not found.")
        return []

    candidate = resume.get("candidate_name") or resume.get("email", "Unknown")
    print(f"\n📄  Candidate : {candidate}")
    print(f"    Skills    : {len(resume.get('all_skills', []))}")

    # Load recommendations
    recommendations = get_recommendations(resume_id, top_n)
    if not recommendations:
        print("✗  No recommendations found. Run Phase 4 first.")
        return []

    print(f"\n💼  Explaining top {len(recommendations)} recommendations...\n")

    all_explanations = []

    for rec in recommendations:
        job_id = rec.get("job_id")
        job    = get_job(job_id) if job_id else {}

        print(f"  [{rec.get('rank')}] {rec.get('job_title')} @ {rec.get('company')}")

        # ── SHAP Explanation ──────────────────────────────────
        shap_result = explain_recommendation(resume, job, rec)

        # ── LIME Explanation ──────────────────────────────────
        lime_result = explain_with_lime(
            resume, job, rec.get("tfidf_score", 0.0)
        )

        # ── Combined Explanation ──────────────────────────────
        explanation = {
            "rank":             rec.get("rank"),
            "job_id":           job_id,
            "job_title":        rec.get("job_title"),
            "company":          rec.get("company"),
            "source":           rec.get("source"),
            "hybrid_score_pct": round((rec.get("hybrid_score", 0) * 100), 1),

            # SHAP results
            "shap": {
                "summary":           shap_result.get("summary"),
                "why_recommended":   shap_result.get("why_recommended"),
                "improvement_tips":  shap_result.get("improvement_tips"),
                "top_positive":      shap_result.get("top_positive_factors"),
                "top_negative":      shap_result.get("top_negative_factors"),
                "feature_values":    shap_result.get("feature_values"),
                "contributions":     shap_result.get("shap_contributions"),
            },

            # LIME results
            "lime": {
                "explanation":       lime_result.get("explanation"),
                "top_keywords":      lime_result.get("top_resume_keywords", [])[:8],
                "job_keywords":      lime_result.get("top_job_keywords", [])[:8],
                "shared_keywords":   lime_result.get("shared_keywords", []),
                "keyword_matches":   lime_result.get("keyword_match_count", 0),
            },

            # Skill gap summary
            "skill_gap": {
                "matched": rec.get("matched_skills", []),
                "missing": rec.get("missing_skills", []),
            },
        }

        all_explanations.append(explanation)

        # Print summary
        print(f"       Match    : {explanation['hybrid_score_pct']}%")
        print(f"       Summary  : {shap_result.get('summary')}")
        for reason in shap_result.get("why_recommended", [])[:2]:
            print(f"       ✅ {reason}")
        for tip in shap_result.get("improvement_tips", [])[:1]:
            print(f"       ❌ {tip}")
        if lime_result.get("explanation"):
            print(f"       🔑 {lime_result['explanation'][:100]}...")
        print()

    # Save to JSON
    save_explanations(resume_id, all_explanations, candidate)

    print(f"\n{'='*60}")
    print(f"✅  XAI Explanations Complete!")
    print(f"    SHAP: Feature contribution analysis")
    print(f"    LIME: Keyword importance analysis")
    print(f"    Jobs explained: {len(all_explanations)}")
    print(f"{'='*60}\n")

    return all_explanations


# ── CLI ───────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="XAI Engine — Phase 5")
    parser.add_argument("--resume-id", type=int, required=True)
    parser.add_argument("--top",       type=int, default=5)
    args = parser.parse_args()

    explain_recommendations(resume_id=args.resume_id, top_n=args.top)