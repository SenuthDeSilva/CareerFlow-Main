"""
lime_explainer.py — FIXED
=========================
Fix: cosine_similarity returns 2D array → use [0][0] to get scalar
"""

import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def get_stopwords() -> set:
    return {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
        "for", "of", "with", "by", "from", "is", "are", "was", "were",
        "be", "been", "being", "have", "has", "had", "do", "does", "did",
        "will", "would", "could", "should", "may", "might", "shall",
        "this", "that", "these", "those", "it", "its", "we", "you", "he",
        "she", "they", "i", "me", "my", "our", "your", "their", "as",
        "not", "no", "so", "if", "than", "then", "more", "also", "can",
    }


def get_important_keywords(resume_text: str, job_text: str, top_n: int = 10) -> dict:
    """
    Find which keywords in the resume contribute most to matching the job.
    """
    def clean(text):
        text = text.lower()
        text = re.sub(r"[^\w\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    resume_clean = clean(resume_text)
    job_clean    = clean(job_text)

    if not resume_clean or not job_clean:
        return {
            "base_tfidf_score":    0.0,
            "top_resume_keywords": [],
            "top_job_keywords":    [],
            "shared_keywords":     [],
            "keyword_match_count": 0,
        }

    # Fit TF-IDF on both
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=3000)
    try:
        matrix = vectorizer.fit_transform([resume_clean, job_clean])
    except Exception:
        return {
            "base_tfidf_score":    0.0,
            "top_resume_keywords": [],
            "top_job_keywords":    [],
            "shared_keywords":     [],
            "keyword_match_count": 0,
        }

    # ── Fix: cosine_similarity returns 2D array → use [0][0] ──
    base_score = float(cosine_similarity(matrix[0], matrix[1])[0][0])

    vocab      = vectorizer.get_feature_names_out()
    resume_vec = matrix[0].toarray()[0]
    job_vec    = matrix[1].toarray()[0]

    # Shared keywords
    resume_words = set(resume_clean.split())
    job_words    = set(job_clean.split())
    shared       = sorted(list(resume_words & job_words - get_stopwords()))

    # Keywords that appear in BOTH resume and job
    resume_importance = {}
    for i, word in enumerate(vocab):
        if resume_vec[i] > 0 and job_vec[i] > 0:
            importance = float(resume_vec[i]) * float(job_vec[i])
            resume_importance[word] = round(importance, 6)

    # Top job keywords
    job_importance = {}
    for i, word in enumerate(vocab):
        if job_vec[i] > 0:
            job_importance[word] = round(float(job_vec[i]), 6)

    top_resume_keywords = sorted(resume_importance.items(), key=lambda x: x[1], reverse=True)[:top_n]
    top_job_keywords    = sorted(job_importance.items(),    key=lambda x: x[1], reverse=True)[:top_n]

    return {
        "base_tfidf_score":     round(base_score, 4),
        "top_resume_keywords":  top_resume_keywords,
        "top_job_keywords":     top_job_keywords,
        "shared_keywords":      shared[:15],
        "keyword_match_count":  len(resume_importance),
    }


def explain_with_lime(resume: dict, job: dict, tfidf_score: float) -> dict:
    """Generate LIME-style keyword explanation for a job match."""
    resume_text = resume.get("raw_text", "")
    job_text    = " ".join(filter(None, [
        job.get("title", ""),
        job.get("description", ""),
    ]))

    if not job_text.strip():
        return {
            "explanation":       "No job description available for LIME analysis",
            "top_resume_keywords": [],
            "top_job_keywords":    [],
            "shared_keywords":     [],
            "keyword_match_count": 0,
        }

    result   = get_important_keywords(resume_text, job_text, top_n=10)
    top_words = [w for w, s in result["top_resume_keywords"][:5]]
    job_words = [w for w, s in result["top_job_keywords"][:5]]

    result["explanation"] = (
        f"Your resume matches this job mainly through keywords: "
        f"{', '.join(top_words) if top_words else 'N/A'}. "
        f"The job is primarily looking for: "
        f"{', '.join(job_words) if job_words else 'N/A'}."
    )

    return result