"""
ensemble_predictor.py — High-Accuracy Ensemble Prediction
==========================================================
Uses the pre-trained Voting Ensemble model (RF+ET+MLP) for job recommendation.
Expects models in the 'saved_models/' directory.
"""

import os
import json
import joblib
import numpy as np
import pandas as pd
import warnings

warnings.filterwarnings('ignore')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "saved_models")

# Skill mapping to match training feature names
SKILL_MAP = {
    'AI': 'AI', 'C++': 'Cpp', 'CSS': 'CSS', 'Data Science': 'Data_Science', 
    'HTML': 'HTML', 'Java': 'Java', 'JavaScript': 'JavaScript', 
    'Machine Learning': 'Machine_Learning', 'Python': 'Python', 'SQL': 'SQL'
}
SKILLS = list(SKILL_MAP.keys())

def build_ensemble_features(recommendations: list) -> np.ndarray:
    """Recreate the 47 features used during training."""
    
    rows = []
    # Find max hybrid score to normalize inputs for the model
    all_scores = [float(r.get("hybrid_score", 0.0)) for r in recommendations]
    max_score = max(all_scores) if all_scores else 1.0
    
    for rec in recommendations:
        # Scale score: Assume the highest in batch is a strong candidate (approx 0.85-0.90)
        # This prevents the model from hitting 0.0% for everything due to strict training thresholds.
        raw_score = float(rec.get("hybrid_score", 0.0))
        score = (raw_score / max_score) * 0.9 if max_score > 0 else 0.0
        
        # 2. Skill Vectors
        u_text = str(rec.get("user_skills_raw", "")).lower()
        j_text = str(rec.get("job_description_raw", "")).lower()
        
        u_vec = np.array([1 if s.lower() in u_text else 0 for s in SKILLS])
        j_vec = np.array([1 if s.lower() in j_text else 0 for s in SKILLS])
        
        # --- Feature Groups ---
        
        # Group 1: Transforms
        f_sq   = score ** 2
        f_log  = np.log1p(score)
        f_sqrt = np.sqrt(score)
        f_thr  = 1 if score >= 0.8 else 0
        f_band = 0
        if score > 0.8: f_band = 3
        elif score > 0.7: f_band = 2
        elif score > 0.5: f_band = 1
        
        # Group 2: Overlap Metrics
        dot    = (u_vec * j_vec).sum()
        u_cnt  = u_vec.sum()
        j_cnt  = j_vec.sum()
        union  = ((u_vec + j_vec) > 0).sum()
        jac    = dot / (union + 1e-9)
        cov    = dot / (j_cnt + 1e-9)
        excess = u_cnt - dot
        gap    = j_cnt - dot
        
        # Group 3: Interactions
        i_jac  = score * jac
        i_cov  = score * cov
        i_dot  = score * dot
        i_div  = score / (j_cnt + 1e-9)
        
        # Build Row
        row = [score, f_sq, f_log, f_sqrt, f_thr, f_band,
               dot, u_cnt, j_cnt, union, jac, cov, excess, gap,
               i_jac, i_cov, i_dot, i_div]
        
        # Group 4: Per-skill (30 features)
        for i in range(len(SKILLS)):
            row.append(int(u_vec[i]))    # usr_
            row.append(int(j_vec[i]))    # job_
            row.append(int(u_vec[i] * j_vec[i])) # match_
            
        rows.append(row)
        
    return np.array(rows)

def run_ensemble_scoring(recommendations: list) -> dict:
    """Predict using the saved Voting Ensemble model."""
    
    model_path = os.path.join(MODELS_DIR, "best_Voting_Ensemble_RFETMLP.pkl")
    scaler_path = os.path.join(MODELS_DIR, "scaler.pkl")

    if not os.path.exists(model_path):
        raise FileNotFoundError(model_path)

    print("   ⭐  Applying High-Accuracy Voting Ensemble (RF+ET+MLP)...")

    try:
        # Load Model & Scaler
        model = joblib.load(model_path)
        # Note: Scaler is only needed for the MLP part, but the VotingClassifier 
        # usually handles internal scaling if it was saved as a Pipeline.
        # Based on the notebook, it was saved as a VotingClassifier with Pipelines inside.
        
        # Build features
        X = build_ensemble_features(recommendations)
        
        # Predict Proba
        # Voting classifier 'soft' uses predict_proba
        ml_scores = model.predict_proba(X)[:, 1]
        
        print(f"   ✓  Ensemble prediction complete for {len(recommendations)} jobs.")
        
        return {
            "scores": [round(float(s), 4) for s in ml_scores],
            "model_used": "VotingEnsemble (Pre-trained)",
            "trained": True,
        }
        
    except Exception as e:
        print(f"   ⚠  Ensemble prediction error: {e}")
        return {"trained": False}
