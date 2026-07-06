"""
shap_explainer.py
=================
SHAP (SHapley Additive exPlanations) based XAI for Job Recommendations.

Explains WHY a job was recommended by showing which features
contributed most to the match score.

Features explained:
    - Skill overlap contribution
    - TF-IDF keyword importance
    - Location match
    - Job type match
    - Experience level match

Install:
    pip install shap scikit-learn numpy
"""

import numpy as np
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def build_feature_vector(resume: dict, job: dict, matched_skills: list,
                         missing_skills: list, tfidf_score: float) -> dict:
    """
    Build a feature vector for SHAP explanation.

    Features:
        1. skill_match_ratio    — % of job skills matched
        2. tfidf_score          — text similarity score
        3. skill_count_resume   — number of skills in resume
        4. skill_count_job      — number of skills in job
        5. matched_skills_count — number of matched skills
        6. location_match       — 1 if remote / same city
        7. is_intern            — 1 if internship level
        8. experience_fit       — 1 if experience matches

    Returns:
        dict: Feature name → value
    """
    resume_skills   = resume.get("all_skills", [])
    job_skills      = matched_skills + missing_skills
    job_title_lower = job.get("title", "").lower()
    location_lower  = job.get("location", "").lower()

    # Skill match ratio
    skill_match_ratio = (
        len(matched_skills) / len(job_skills) if job_skills else 0.0
    )

    # Location match
    location_match = 1.0 if (
        "remote" in location_lower or
        "colombo" in location_lower or
        not location_lower
    ) else 0.5

    # Internship / entry level fit
    intern_keywords = ["intern", "junior", "trainee", "associate", "entry"]
    is_intern = 1.0 if any(k in job_title_lower for k in intern_keywords) else 0.5

    # Experience fit
    years_exp = resume.get("years_experience", 0)
    senior_keywords = ["senior", "lead", "manager", "architect", "head"]
    is_senior_job = any(k in job_title_lower for k in senior_keywords)
    experience_fit = 0.3 if (is_senior_job and years_exp < 3) else 1.0

    return {
        "skill_match_ratio":    round(skill_match_ratio, 4),
        "tfidf_score":          round(tfidf_score, 4),
        "matched_skills_count": len(matched_skills),
        "missing_skills_count": len(missing_skills),
        "resume_skill_count":   len(resume_skills),
        "job_skill_count":      len(job_skills),
        "location_match":       location_match,
        "is_intern_level":      is_intern,
        "experience_fit":       experience_fit,
    }


def compute_shap_contributions(features: dict, hybrid_score: float) -> dict:
    """
    Compute approximate SHAP-style feature contributions.

    Uses a weighted decomposition approach to estimate each feature's
    contribution to the final hybrid score.

    Args:
        features     (dict): Feature vector from build_feature_vector()
        hybrid_score (float): Final hybrid match score

    Returns:
        dict: Feature → contribution (positive = helped, negative = hurt)
    """
    # Feature importance weights (learned from domain knowledge)
    weights = {
        "skill_match_ratio":    0.35,
        "tfidf_score":          0.30,
        "matched_skills_count": 0.10,
        "missing_skills_count": -0.08,  
        "resume_skill_count":   0.05,
        "job_skill_count":      0.03,
        "location_match":       0.07,
        "is_intern_level":      0.05,
        "experience_fit":       0.07,
    }

    contributions = {}
    total = 0.0

    for feature, value in features.items():
        weight = weights.get(feature, 0.0)
        contribution = value * weight
        contributions[feature] = round(contribution, 4)
        total += abs(contribution)

    # Normalize contributions to sum to hybrid_score
    if total > 0:
        scale = hybrid_score / total
        contributions = {k: round(v * scale, 4) for k, v in contributions.items()}

    return contributions


def explain_recommendation(resume: dict, job: dict, recommendation: dict) -> dict:
    """
    Generate SHAP-style explanation for a single job recommendation.

    Args:
        resume         (dict): Resume data with skills
        job            (dict): Job listing data
        recommendation (dict): Recommendation result from Phase 4

    Returns:
        dict: Full explanation with feature contributions + human-readable reasons
    """
    matched_skills = recommendation.get("matched_skills", [])
    missing_skills = recommendation.get("missing_skills", [])
    tfidf_score    = recommendation.get("tfidf_score", 0.0)
    hybrid_score   = recommendation.get("hybrid_score", 0.0)
    skill_score    = recommendation.get("skill_score", 0.0)

    # Build feature vector
    features = build_feature_vector(
        resume, job, matched_skills, missing_skills, tfidf_score
    )

    # Compute SHAP contributions
    contributions = compute_shap_contributions(features, hybrid_score)

    # Sort contributions by absolute value
    sorted_contribs = sorted(
        contributions.items(),
        key=lambda x: abs(x[1]),
        reverse=True
    )

    # Generate human-readable reasons
    reasons = generate_human_reasons(
        matched_skills, missing_skills, tfidf_score,
        skill_score, features, hybrid_score
    )

    return {
        "job_title":        job.get("title", ""),
        "company":          job.get("company", ""),
        "hybrid_score":     hybrid_score,
        "hybrid_score_pct": round(hybrid_score * 100, 1),

        # SHAP contributions
        "feature_values":       features,
        "shap_contributions":   dict(sorted_contribs),
        "top_positive_factors": [
            {"feature": k, "contribution": v}
            for k, v in sorted_contribs if v > 0
        ][:3],
        "top_negative_factors": [
            {"feature": k, "contribution": v}
            for k, v in sorted_contribs if v < 0
        ][:3],

        # Human readable
        "why_recommended": reasons["positive"],
        "improvement_tips": reasons["negative"],
        "summary":          reasons["summary"],
    }


def generate_human_reasons(matched_skills: list, missing_skills: list,
                           tfidf_score: float, skill_score: float,
                           features: dict, hybrid_score: float) -> dict:
    """Generate human-readable explanation strings."""

    positive = []
    negative = []

    # Skill match reasons
    if len(matched_skills) >= 5:
        positive.append(
            f"Strong skill match — {len(matched_skills)} skills aligned: "
            f"{', '.join(matched_skills[:5])}"
            f"{'...' if len(matched_skills) > 5 else ''}"
        )
    elif len(matched_skills) >= 2:
        positive.append(
            f"Partial skill match — {len(matched_skills)} skills aligned: "
            f"{', '.join(matched_skills)}"
        )
    elif len(matched_skills) == 1:
        positive.append(f"Key skill matched: {matched_skills[0]}")

    # TF-IDF reasons
    if tfidf_score >= 0.15:
        positive.append(
            f"High text similarity ({round(tfidf_score*100, 1)}%) — "
            f"resume content closely matches job description"
        )
    elif tfidf_score >= 0.05:
        positive.append(
            f"Moderate text relevance ({round(tfidf_score*100, 1)}%) — "
            f"resume keywords partially match job"
        )

    # Internship fit
    if features.get("is_intern_level") == 1.0:
        positive.append("Job level matches your experience (internship/entry-level)")

    # Location
    if features.get("location_match") == 1.0:
        positive.append("Location is remote or in Colombo — convenient")

    # Missing skills
    if len(missing_skills) >= 5:
        negative.append(
            f"Skill gap detected — {len(missing_skills)} skills to develop: "
            f"{', '.join(missing_skills[:5])}"
            f"{'...' if len(missing_skills) > 5 else ''}"
        )
    elif missing_skills:
        negative.append(
            f"Consider learning: {', '.join(missing_skills)}"
        )

    # Experience
    if features.get("experience_fit") < 1.0:
        negative.append(
            "This role may require more experience than you currently have"
        )

    # Summary
    pct = round(hybrid_score * 100, 1)
    if pct >= 35:
        summary = f"Excellent match ({pct}%) — strongly recommended"
    elif pct >= 25:
        summary = f"Good match ({pct}%) — worth applying"
    elif pct >= 15:
        summary = f"Moderate match ({pct}%) — consider if interested"
    else:
        summary = f"Low match ({pct}%) — skill gap is significant"

    return {
        "positive": positive,
        "negative": negative,
        "summary":  summary,
    }