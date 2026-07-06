"""
recommender.py — v4 UPGRADED
==============================
Enhanced ML Pipeline:

    Step 1: TF-IDF Cosine Similarity       weight: 0.30
    Step 2: Word2Vec Semantic Similarity   weight: 0.30
    Step 3: Skill Gap Matching             weight: 0.30
    Step 4: Supervised ML (RandomForest)   weight: 0.10
    ─────────────────────────────────────────────────
    Final = TF-IDF×0.30 + W2V×0.30 + Skill×0.30 + ML×0.10

Fallback:
    - gensim not installed → Word2Vec weight → TF-IDF
    - <5 diverse jobs     → ML fallback to hybrid score
"""

import os, sys, json, argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml_model.tfidf_matching       import build_tfidf_matcher, compute_tfidf_scores
from ml_model.skill_gap            import compute_skill_score, extract_job_skills
from ml_model.role_predictor       import predict_role, is_model_available
from database.db_config            import SessionLocal, text as sql_text
from resume_parser.skill_extractor import HARD_SKILLS, SOFT_SKILLS

ALL_SKILLS     = HARD_SKILLS | SOFT_SKILLS
BASE_DIR       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR     = os.path.join(BASE_DIR, "ml_model", "output")
MIN_JOB_SKILLS = 3   # require at least 3 job skills for reliable scoring


# ── DB Helpers ────────────────────────────────────────────────

def get_resume_from_db(resume_id):
    db = SessionLocal()
    try:
        row = db.execute(sql_text("SELECT * FROM resumes WHERE id=:id"), {"id": resume_id}).fetchone()
        if not row: return {}
        r = dict(row._mapping)
        r["hard_skills"] = json.loads(r.get("hard_skills") or "[]")
        r["soft_skills"] = json.loads(r.get("soft_skills") or "[]")
        r["all_skills"]  = json.loads(r.get("all_skills")  or "[]")
        return r
    finally:
        db.close()


def _fix_encoding(text: str) -> str:
    """Replace '?' encoding artifacts used as dash separators in job titles."""
    import re as _re
    if not text:
        return text
    # Pattern: word<space>?<space>word — encoding artifact for em-dash
    return _re.sub(r'(?<=\w) \? (?=\w)', ' – ', text)


def get_jobs_from_db(source=None):
    db = SessionLocal()
    try:
        if source:
            rows = db.execute(sql_text("SELECT * FROM jobs WHERE source=:s ORDER BY id"), {"s": source}).fetchall()
        else:
            rows = db.execute(sql_text("SELECT * FROM jobs ORDER BY id")).fetchall()
        jobs = [dict(r._mapping) for r in rows]

        # Fix encoding artifacts in title and company
        for j in jobs:
            if j.get("title"):
                j["title"] = _fix_encoding(j["title"])
            if j.get("company"):
                j["company"] = _fix_encoding(j["company"])

        # Deduplicate by (title, company) — keep first occurrence (lowest id)
        seen = set()
        unique = []
        for j in jobs:
            key = ((j.get("title") or "").lower().strip(),
                   (j.get("company") or "").lower().strip())
            if key not in seen:
                seen.add(key)
                unique.append(j)

        removed = len(jobs) - len(unique)
        if removed:
            print(f"   ℹ  Removed {removed} duplicate job(s) (same title+company)")
        return unique
    finally:
        db.close()


def save_to_db(resume_id, recs):
    db = SessionLocal()
    try:
        db.execute(sql_text("""
            CREATE TABLE IF NOT EXISTS recommendations (
                id SERIAL PRIMARY KEY, resume_id INTEGER,
                job_id INTEGER, job_title VARCHAR(255), company VARCHAR(255),
                location VARCHAR(255), salary VARCHAR(255), job_url TEXT,
                source VARCHAR(50), hybrid_score FLOAT, tfidf_score FLOAT,
                word2vec_score FLOAT, skill_score FLOAT, ml_score FLOAT,
                matched_skills TEXT, missing_skills TEXT,
                rank INTEGER, created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        for col, t in [("word2vec_score","FLOAT"),("ml_score","FLOAT"),
                       ("location","VARCHAR(255)"),("salary","VARCHAR(255)"),("job_url","TEXT")]:
            try:
                db.execute(sql_text(f"ALTER TABLE recommendations ADD COLUMN IF NOT EXISTS {col} {t}"))
            except: pass

        db.execute(sql_text("DELETE FROM recommendations WHERE resume_id=:r"), {"r": resume_id})
        for rec in recs:
            db.execute(sql_text("""
                INSERT INTO recommendations (
                    resume_id,job_id,job_title,company,location,salary,job_url,source,
                    hybrid_score,tfidf_score,word2vec_score,skill_score,ml_score,
                    matched_skills,missing_skills,rank
                ) VALUES (
                    :resume_id,:job_id,:job_title,:company,:location,:salary,:job_url,:source,
                    :hybrid_score,:tfidf_score,:word2vec_score,:skill_score,:ml_score,
                    :matched_skills,:missing_skills,:rank
                )
            """), {
                "resume_id":      resume_id,
                "job_id":         rec.get("job_id"),
                "job_title":      rec.get("title",""),
                "company":        rec.get("company",""),
                "location":       rec.get("location",""),
                "salary":         rec.get("salary",""),
                "job_url":        rec.get("job_url",""),
                "source":         rec.get("source",""),
                "hybrid_score":   rec.get("hybrid_score",0),
                "tfidf_score":    rec.get("tfidf_score",0),
                "word2vec_score": rec.get("word2vec_score",0),
                "skill_score":    rec.get("skill_score",0),
                "ml_score":       rec.get("ml_score",0),
                "matched_skills": json.dumps(rec.get("matched_skills",[])),
                "missing_skills": json.dumps(rec.get("missing_skills",[])),
                "rank":           rec.get("rank",0),
            })
        db.commit()
        print(f"   ✓  Saved {len(recs)} recommendations to DB")
    except Exception as e:
        db.rollback(); print(f"   ✗  DB error: {e}")
    finally:
        db.close()


def save_to_json(resume_id, recs, name):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    fname = f"recs_resume{resume_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    fpath = os.path.join(OUTPUT_DIR, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump({"resume_id": resume_id, "candidate": name,
                   "pipeline": "TF-IDF + Word2Vec + Skill Gap + Career Role Prediction",
                   "recommendations": recs}, f, indent=2, ensure_ascii=False)
    print(f"   ✓  Saved JSON : {fpath}")
    return fpath


# ── Word2Vec (graceful) ───────────────────────────────────────

def try_word2vec(resume_text, job_texts):
    try:
        import importlib.util, os
        # Always load from same directory as this file — most reliable
        w2v_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "word2vec_matching.py")
        spec = importlib.util.spec_from_file_location("word2vec_matching", w2v_path)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.compute_word2vec_scores(resume_text, job_texts)
    except Exception as e:
        print(f"   ⚠  Word2Vec skipped: {e}")
        return [0.0] * len(job_texts)


# ── Supervised ML (graceful) ──────────────────────────────────

def try_supervised(recs, resume_text=None, job_texts=None):
    """
    Attempt high-accuracy pre-trained Ensemble first.
    Fallback to dynamic RandomForest training if needed.
    """
    # 1. Try Pre-trained High-Accuracy Ensemble (Voting Classifier)
    try:
        from ml_model.ensemble_predictor import run_ensemble_scoring

        if resume_text and job_texts:
            for i, rec in enumerate(recs):
                rec["user_skills_raw"] = resume_text
                rec["job_description_raw"] = job_texts[i] if i < len(job_texts) else ""

        res = run_ensemble_scoring(recs)
        if res.get("trained"):
            return res
    except FileNotFoundError:
        pass  # No pre-trained ensemble — using dynamic RF below
    except Exception as e:
        print(f"   ⚠  Ensemble skip/fail: {e}")

    # 2. Fallback to Dynamic RandomForest training
    try:
        import importlib.util, os
        sup_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "supervised_model.py")
        spec = importlib.util.spec_from_file_location("supervised_model", sup_path)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.run_supervised_scoring(recs)
    except Exception as e:
        print(f"   ⚠  Supervised ML fallback skipped: {e}")
        return {"scores": [r.get("hybrid_score",0) for r in recs],
                "importances": {}, "model_used": "fallback", "trained": False}


# ── Main ──────────────────────────────────────────────────────

def recommend_jobs(resume_id: int, top_n: int = 20, source: str = None) -> list:

    print("\n" + "="*62)
    print("🤖  Job Recommendation Engine — Career Recommendation System")
    print("    Pipeline: TF-IDF → Word2Vec → Skill Gap → Role Predict")
    print("    Runtime : Live Scraped Jobs → Rank → Top 20 → SHAP/LIME")
    print("="*62)

    # Load resume
    resume = get_resume_from_db(resume_id)
    if not resume:
        print(f"✗  Resume ID {resume_id} not found"); return []

    resume_text   = resume.get("raw_text", "")
    resume_skills = resume.get("all_skills", [])
    resume_name   = resume.get("candidate_name") or resume.get("email", "Unknown")
    years_exp     = int(resume.get("years_experience") or 0)
    print(f"\n📄  Candidate : {resume_name}")
    print(f"    Skills    : {len(resume_skills)} detected")
    if years_exp:
        print(f"    Experience: {years_exp} years")

    # Load jobs
    jobs = get_jobs_from_db(source)
    if not jobs:
        print("✗  No jobs in database"); return []
    print(f"\n💼  Jobs loaded: {len(jobs)}")

    job_texts = []
    for job in jobs:
        txt = " ".join(filter(None, [job.get("title",""), job.get("description",""),
                                     job.get("company",""), job.get("location","")]))
        job_texts.append(txt.strip() or "no description")

    # ── Step 1: TF-IDF ───────────────────────────────────────
    print("\n🔢  Step 1/4 — TF-IDF Cosine Similarity...")
    vectorizer, job_matrix = build_tfidf_matcher(job_texts)
    tfidf_scores = compute_tfidf_scores(resume_text, vectorizer, job_matrix)
    print(f"   ✓  Max score: {max(tfidf_scores):.4f}")

    # ── Step 2: Word2Vec ──────────────────────────────────────
    print("\n🧠  Step 2/4 — Word2Vec Semantic Similarity...")
    w2v_scores  = try_word2vec(resume_text, job_texts)
    w2v_active  = any(s > 0 for s in w2v_scores)
    status      = f"Max: {max(w2v_scores):.4f}" if w2v_active else "Inactive — pip install gensim"
    print(f"   {'✓' if w2v_active else '⚠'}  {status}")

    # ── Step 3: Skill Gap ─────────────────────────────────────
    print("\n🎯  Step 3/4 — Skill Gap Analysis...")
    interim = []
    for i, job in enumerate(jobs):
        job_skills   = extract_job_skills(job, ALL_SKILLS)
        skill_result = compute_skill_score(resume_skills, job_skills)

        ts = float(tfidf_scores[i])
        ws = float(w2v_scores[i])
        ss = skill_result["skill_score"]

        # Dynamic weights based on how many skills the job listing has
        n_skills = len(job_skills)
        if n_skills == 0:
            # No skills detected in job listing → rely purely on TF-IDF + W2V
            ss = 0.0
            base = (ts * 0.70 + ws * 0.30) if w2v_active else ts
            hybrid = base * 0.85
        elif n_skills <= 2:
            # Very few skills — keep skill signal but weight TF-IDF heavily
            if w2v_active:
                hybrid = ts * 0.45 + ws * 0.15 + ss * 0.30
            else:
                hybrid = ts * 0.65 + ss * 0.30
        elif n_skills <= 4:
            # Few skills → lean on TF-IDF, moderate skill weight
            if w2v_active:
                hybrid = ts * 0.40 + ws * 0.20 + ss * 0.30
            else:
                hybrid = ts * 0.65 + ss * 0.30
        elif w2v_active:
            # Normal — balanced TF-IDF + W2V + Skill
            hybrid = ts * 0.35 + ws * 0.20 + ss * 0.40
        else:
            hybrid = ts * 0.55 + ss * 0.40

        # Experience-level mismatch penalty
        # Experienced candidates (3+ yrs) are poor fits for intern/trainee roles
        if years_exp >= 3:
            title_lower = job.get("title", "").lower()
            if any(kw in title_lower for kw in ["intern", "trainee", "fresher"]):
                hybrid *= 0.55   # 45% penalty — intern roles for 3+ yr candidates
            elif any(kw in title_lower for kw in ["junior", "entry level", "entry-level"]):
                hybrid *= 0.80   # 20% penalty — junior roles for senior candidates

        interim.append({
            "job_id":           job.get("id"),
            "title":            job.get("title",""),
            "company":          job.get("company",""),
            "location":         job.get("location",""),
            "salary":           job.get("salary",""),
            "job_type":         job.get("job_type",""),
            "job_url":          job.get("job_url",""),
            "source":           job.get("source",""),
            "tfidf_score":      round(ts, 4),
            "word2vec_score":   round(ws, 4),
            "skill_score":      round(ss, 4),
            "hybrid_score":     round(hybrid, 4),
            "tfidf_score_pct":  round(ts * 100, 1),
            "word2vec_score_pct": round(ws * 100, 1),
            "skill_score_pct":  skill_result["skill_score_pct"],
            "job_skills_count": len(job_skills),
            "job_skills":       job_skills,
            "matched_skills":   skill_result["matched_skills"],
            "missing_skills":   skill_result["missing_skills"],
        })
    print(f"   ✓  {len(interim)} jobs scored")

    # ── Step 3.5: Career Role Prediction ─────────────────────
    print("\n🎓  Step 3.5/4 — Career Role Prediction...")
    predicted_role = None
    role_confidence = 0.0
    role_top_predictions = []

    if is_model_available():
        try:
            role_result      = predict_role(resume_text, top_n=3)
            predicted_role   = role_result["predicted_role"]
            role_confidence  = role_result["confidence"]
            role_top_predictions = role_result.get("top_predictions", [])
            print(f"   ✓  Predicted Role : {predicted_role} ({role_confidence}%)")
            print(f"   ✓  Model Used     : {role_result['model_used']}")

            # Apply small role-match boost to hybrid_score — all 16 doc roles
            _ROLE_KW = {
                "Software Engineer":     ["software engineer", "software developer", ".net", "java developer", "c# developer", "c++ developer", "golang", "engineer"],
                "Backend Developer":     ["backend", "back end", "back-end", "node", "django", "laravel", "spring", "php developer", "asp.net", "magento"],
                "Frontend Developer":    ["frontend", "front end", "front-end", "react", "angular", "vue", "ui developer", "web developer"],
                "Full Stack Developer":  ["full stack", "fullstack", "full-stack"],
                "Mobile Developer":      ["android", "ios", "mobile", "flutter", "react native", "kotlin", "swift"],
                "Data Analyst":          ["data analyst", "business intelligence", "bi analyst", "analytics", "power bi"],
                "Data Engineer":         ["data engineer", "etl", "spark", "pipeline", "airflow", "kafka"],
                "AI/ML Engineer":        ["machine learning", "deep learning", "artificial intelligence", "ai engineer", "data scientist", "nlp", "computer vision"],
                "DevOps Engineer":       ["devops", "devsecops", "site reliability", "sre", "ci/cd", "jenkins", "kubernetes", "docker engineer"],
                "Cloud Engineer":        ["cloud", "aws", "azure", "gcp", "solution architect", "infrastructure", "platform engineer"],
                "QA Engineer":           ["qa", "quality assurance", "test engineer", "automation engineer", "tester", "sdet"],
                "Business Analyst":      ["business analyst", "product manager", "scrum master", "project manager", "it manager"],
                "UI/UX Designer":        ["ui/ux", "ux designer", "ui designer", "web designer", "graphic designer", "product designer"],
                "Security Engineer":     ["security", "cybersecurity", "penetration", "ethical hack", "soc analyst", "devsecops"],
                "System Administrator":  ["system admin", "sysadmin", "network admin", "network engineer", "system engineer", "it engineer", "infrastructure"],
                "IT Support":            ["it support", "helpdesk", "help desk", "technical support", "desktop support"],
            }
            role_keywords = _ROLE_KW.get(predicted_role, [])
            if not role_keywords:
                import re as _re
                role_keywords = [w for w in _re.split(r'[\s/\-]+', predicted_role.lower()) if len(w) > 3]
            for rec in interim:
                job_title_lower = rec.get("title", "").lower()
                if any(kw in job_title_lower for kw in role_keywords):
                    rec["hybrid_score"] = round(
                        min(rec["hybrid_score"] + 0.05, 1.0), 4
                    )
                    rec["role_match"] = True
                else:
                    rec["role_match"] = False
        except Exception as e:
            print(f"   ⚠  Role prediction skipped: {e}")
    else:
        print("   ⚠  No trained model found — skipping role prediction")
        print("       Run: python ml_model/train_role_classifier.py")

    # ── Step 4: Supervised ML ─────────────────────────────────
    print("\n🤖  Step 4/4 — Supervised ML (High Accuracy Ensemble)...")
    ml_result  = try_supervised(interim, resume_text, job_texts)
    ml_scores  = ml_result["scores"]
    ml_trained = ml_result["trained"]
    print(f"   {'✓' if ml_trained else '⚠'}  Model: {ml_result['model_used']}")

    if ml_trained and ml_result.get("importances"):
        top3 = sorted(ml_result["importances"].items(), key=lambda x: x[1], reverse=True)[:3]
        print(f"   🔑  Top features: " + " | ".join(f"{k}={v}" for k,v in top3))

    final = []
    for i, rec in enumerate(interim):
        ml_s  = float(ml_scores[i]) if i < len(ml_scores) else 0.0

        # hybrid_score is the primary signal (TF-IDF + W2V + Skill).
        # ML probability adds a 20% supporting boost — using ML as 100%
        # replacement causes inflation because RF labels are derived from
        # the same features it trains on (circular), giving every top-30%
        # job a flat 100% score regardless of true relevance.
        if ml_trained:
            score = rec["hybrid_score"] * 0.80 + ml_s * 0.20
        else:
            score = rec["hybrid_score"]

        final.append({
            **rec,
            "ml_score":         round(ml_s, 4),
            "ml_score_pct":     round(ml_s * 100, 1),
            "hybrid_score":     round(score, 4),
            "hybrid_score_pct": round(score * 100, 1),
        })

    # Sort all by score
    final.sort(key=lambda x: (x["hybrid_score"], x["tfidf_score"]), reverse=True)

    # ── Balanced 50/50 split: top 5 rooster + top 5 topjobs ──
    per_source = top_n // 2  # 10 each for top_n=20

    rooster_pool = [r for r in final if r.get("source") == "rooster"]
    topjobs_pool = [r for r in final if r.get("source") == "topjobs"]

    rooster_top  = rooster_pool[:per_source]
    topjobs_top  = topjobs_pool[:per_source]

    # Combine and fill any gap if one source has fewer jobs
    top = rooster_top + topjobs_top

    if len(top) < top_n:
        used = {id(r) for r in top}
        for r in final:
            if id(r) not in used:
                top.append(r)
                used.add(id(r))
            if len(top) >= top_n:
                break

    # Re-sort by score so best jobs appear first regardless of source
    top.sort(key=lambda x: (x["hybrid_score"], x["tfidf_score"]), reverse=True)
    top = top[:top_n]

    for rank, rec in enumerate(top, 1):
        rec["rank"] = rank

    # Log source distribution
    src_dist = {}
    for r in top:
        s = r.get("source", "?")
        src_dist[s] = src_dist.get(s, 0) + 1
    print(f"   Source split: {src_dist}")


    # Attach predicted role metadata to each recommendation
    for rec in top:
        rec["predicted_role"]        = predicted_role
        rec["role_confidence"]       = role_confidence
        rec["role_top_predictions"]  = role_top_predictions

    # Save
    print(f"\n💾  Saving top {top_n} recommendations...")
    save_to_db(resume_id, top)
    save_to_json(resume_id, top, resume_name)

    # Print summary
    print(f"\n{'='*62}")
    print(f"✅  Top {top_n} Results (10 Rooster + 10 TopJobs) for: {resume_name}")
    print(f"{'='*62}")
    for rec in top:
        m = len(rec["matched_skills"])
        j = rec["job_skills_count"]
        print(f"\n  [{rec['rank']}] {rec['title']} — {rec['company']}")
        print(f"       Final   : {rec['hybrid_score_pct']}%")
        print(f"       TF-IDF  : {rec['tfidf_score_pct']}%  |  "
              f"W2V: {rec['word2vec_score_pct']}%  |  "
              f"Skill: {rec['skill_score_pct']}%  [{m}/{j}]  |  "
              f"ML: {rec['ml_score_pct']}%")

    print(f"\n{'='*62}")
    print(f"  Pipeline: TF-IDF (40%) | Word2Vec (20%) | Skill Gap (30%) | ML Role Boost")
    print(f"{'='*62}\n")

    return top


# ── CLI ───────────────────────────────────────────────────────

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Job Recommender v4")
    p.add_argument("--resume-id", type=int, required=True)
    p.add_argument("--top",       type=int, default=10)
    p.add_argument("--source",    type=str, default=None)
    args = p.parse_args()
    recommend_jobs(resume_id=args.resume_id, top_n=args.top, source=args.source)