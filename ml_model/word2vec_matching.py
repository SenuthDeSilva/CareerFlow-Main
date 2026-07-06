"""
word2vec_matching.py — v3 IMPROVED
====================================
TF-IDF weighted Word2Vec for meaningful semantic differentiation.

v2 Problem: All jobs scored ~40% (flat) because:
  1. Simple average of word vectors — common words dominate every doc vector
  2. "experience", "skills", "requirements" pull ALL vectors to same direction
  3. Min-max normalization with near-zero spread → everything hits the cap

v3 Fix:
  1. TF-IDF weighted doc vectors — rare/distinctive words (e.g. "docker",
     "kubernetes") get high weight; generic words get low weight
  2. Expanded stopword list filters out noisy job-description boilerplate
  3. Percentile-based (P5–P95) normalization for robust score spread
"""

import re
import math
import numpy as np


STOPWORDS = {
    # Common English
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "this", "that", "it", "we", "you", "he", "she", "they",
    "i", "my", "your", "our", "their", "not", "also", "can", "more",
    "than", "as", "so", "if", "then", "about",
    # Generic job-description boilerplate (appears in nearly every posting)
    "experience", "work", "working", "skills", "skill", "team", "ability",
    "looking", "year", "years", "knowledge", "strong", "good", "minimum",
    "required", "requirement", "requirements", "responsibilities", "role",
    "job", "position", "candidate", "opportunity", "apply", "applications",
    "degree", "qualification", "relevant", "preferred", "plus", "salary",
    "bachelor", "master", "university", "graduate", "fresh", "fresher",
    "full", "time", "part", "excellent", "communication", "interpersonal",
    "must", "well", "high", "detail", "oriented", "motivated", "self",
}


# ── Tokenization ──────────────────────────────────────────────

def tokenize(text: str) -> list:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return [w for w in text.split() if w not in STOPWORDS and len(w) > 2]


# ── IDF computation ───────────────────────────────────────────

def compute_idf(tokenized_docs: list) -> dict:
    """Compute IDF weights across all documents in the corpus."""
    n = len(tokenized_docs)
    df = {}
    for tokens in tokenized_docs:
        for w in set(tokens):
            df[w] = df.get(w, 0) + 1
    # Smoothed IDF: log((N+1)/(df+1)) + 1
    return {w: math.log((n + 1) / (freq + 1)) + 1.0 for w, freq in df.items()}


# ── TF-IDF weighted document vector ──────────────────────────

def get_tfidf_vector(tokens: list, model, idf: dict) -> np.ndarray:
    """
    Weighted average of word vectors using TF-IDF weights.
    Distinctive domain words (docker, kubernetes) dominate;
    generic words (work, team) contribute little.
    """
    if not tokens:
        return np.zeros(model.vector_size)

    tf = {}
    for w in tokens:
        tf[w] = tf.get(w, 0) + 1

    total = len(tokens)
    vecs, weights = [], []

    for w, count in tf.items():
        if w in model.wv:
            tfidf_weight = (count / total) * idf.get(w, 1.0)
            vecs.append(model.wv[w])
            weights.append(tfidf_weight)

    if not vecs:
        return np.zeros(model.vector_size)

    weights = np.array(weights, dtype=float)
    vecs    = np.array(vecs,    dtype=float)
    return np.average(vecs, axis=0, weights=weights)


# ── Cosine similarity ─────────────────────────────────────────

def cosine_sim(v1: np.ndarray, v2: np.ndarray) -> float:
    n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
    if n1 == 0 or n2 == 0:
        return 0.0
    return float(np.dot(v1, v2) / (n1 * n2))


# ── Score normalization ───────────────────────────────────────

def normalize_scores(raw_scores: list, cap: float = 0.40) -> list:
    """
    Percentile-based normalization (P5 floor, P95 ceiling).
    More robust than min-max when there are outliers or flat regions.
    cap=0.40 keeps Word2Vec as a supporting signal (max 40%).
    """
    arr = np.array(raw_scores, dtype=float)

    p5  = np.percentile(arr, 5)
    p95 = np.percentile(arr, 95)

    if p95 - p5 < 1e-6:
        # Truly flat distribution — return uniform low support score
        return [round(cap * 0.25, 4)] * len(raw_scores)

    normalized = np.clip((arr - p5) / (p95 - p5), 0.0, 1.0) * cap
    return [round(float(s), 4) for s in normalized]


# ── Main entry point ──────────────────────────────────────────

def compute_word2vec_scores(resume_text: str, job_texts: list) -> list:
    """
    Compute TF-IDF weighted Word2Vec semantic similarity scores.

    Returns scores in 0.0–0.40 range with genuine differentiation:
      - Relevant tech jobs score near 0.40
      - Irrelevant jobs (Interior Design, Marketing) score near 0.0–0.10
    """
    try:
        from gensim.models import Word2Vec
    except ImportError:
        print("   ⚠  gensim not installed → pip install gensim")
        return [0.0] * len(job_texts)

    if not resume_text.strip() or not job_texts:
        return [0.0] * len(job_texts)

    # Tokenize resume and all jobs
    resume_tokens  = tokenize(resume_text)
    job_token_lists = [tokenize(jt) for jt in job_texts]

    # Build training corpus: resume + non-empty job docs
    corpus = [resume_tokens] + [t for t in job_token_lists if t]
    if len(corpus) < 2:
        return [0.0] * len(job_texts)

    # Train Word2Vec on this corpus
    model = Word2Vec(
        sentences=corpus,
        vector_size=100,
        window=5,
        min_count=1,
        workers=2,
        epochs=15,
        seed=42,
    )

    # Compute IDF weights across the whole corpus
    idf = compute_idf(corpus)

    # Build TF-IDF weighted resume vector
    resume_vec = get_tfidf_vector(resume_tokens, model, idf)

    # Score each job
    raw_scores = []
    for job_tokens in job_token_lists:
        job_vec = get_tfidf_vector(job_tokens, model, idf)
        raw_scores.append(max(0.0, cosine_sim(resume_vec, job_vec)))

    return normalize_scores(raw_scores, cap=0.40)
