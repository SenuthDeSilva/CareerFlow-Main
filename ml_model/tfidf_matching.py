"""
tfidf_matching.py
=================
TF-IDF + Cosine Similarity based Job Matching.
Converts resume text and job descriptions to TF-IDF vectors,
then computes cosine similarity to rank jobs.

Install:
    pip install scikit-learn numpy pandas
"""

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def build_tfidf_matcher(job_texts: list):
    """
    Build and fit a TF-IDF vectorizer on all job descriptions.

    Args:
        job_texts (list): List of job description strings

    Returns:
        tuple: (vectorizer, job_matrix)
    """
    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),     # unigrams + bigrams
        max_features=5000,
        min_df=1,
    )
    job_matrix = vectorizer.fit_transform(job_texts)
    return vectorizer, job_matrix


def compute_tfidf_scores(resume_text: str, vectorizer, job_matrix) -> np.ndarray:
    """
    Compute cosine similarity between resume and all jobs.

    Args:
        resume_text (str) : Resume full text
        vectorizer        : Fitted TF-IDF vectorizer
        job_matrix        : TF-IDF matrix of all jobs

    Returns:
        np.ndarray: Similarity scores for each job (0.0 - 1.0)
    """
    resume_vec = vectorizer.transform([resume_text])
    scores     = cosine_similarity(resume_vec, job_matrix).flatten()
    return scores