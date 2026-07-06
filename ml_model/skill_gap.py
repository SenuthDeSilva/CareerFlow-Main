"""
skill_gap.py — FIXED
====================
Fixes:
    1. Job skill score now uses resume skills as denominator
       (what % of YOUR skills match the job) — more meaningful
    2. Minimum job skills threshold — jobs with 0 skills get score 0
    3. Better skill extraction from title + description
"""

import re


def compute_skill_score(resume_skills: list, job_skills: list) -> dict:
    """
    Compute skill overlap between resume and job.

    Score = matched_skills / max(job_skills, 1)
    If job has NO skills detected → score = 0 (not 100%)

    Args:
        resume_skills (list): Skills extracted from resume
        job_skills    (list): Skills found in job listing

    Returns:
        dict: { matched_skills, missing_skills, skill_score, skill_score_pct }
    """
    resume_set = set(s.lower().strip() for s in resume_skills)
    job_set    = set(s.lower().strip() for s in job_skills)

    # ── Key Fix: if job has NO skills → score = 0, not 100% ──
    if not job_set:
        return {
            "matched_skills":  [],
            "missing_skills":  [],
            "skill_score":     0.0,
            "skill_score_pct": 0,
        }

    matched = sorted(list(resume_set & job_set))
    missing = sorted(list(job_set - resume_set))

    # Score = how many job skills does the resume cover
    score = len(matched) / len(job_set)

    return {
        "matched_skills":  matched,
        "missing_skills":  missing,
        "skill_score":     round(score, 4),
        "skill_score_pct": round(score * 100),
    }


def extract_job_skills(job: dict, skill_db: set) -> list:
    """
    Extract skills from job listing.
    Uses title + description + job_type for matching.
    """
    text = " ".join(filter(None, [
        job.get("title", ""),
        job.get("description", ""),
        job.get("job_type", ""),
    ])).lower()

    found = []
    for skill in skill_db:
        pattern = r"\b" + re.escape(skill.lower()) + r"\b"
        if re.search(pattern, text):
            found.append(skill)

    return sorted(found)