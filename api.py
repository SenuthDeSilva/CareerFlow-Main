"""
api.py - FastAPI Application
=============================
Root-level API file. Imported directly by main.py.

All Endpoints:
    GET    /                           -> API info
    GET    /api/health                 -> Health check
    GET    /api/model-report           -> ML training report (7 classifiers + Phase 2 tuned SVM)
    POST   /api/resume/upload          -> Upload + parse resume
    GET    /api/resumes                -> All resumes
    GET    /api/resume/{id}            -> Single resume
    DELETE /api/resume/{id}            -> Delete resume
    GET    /api/jobs                   -> All jobs (filter + search)
    GET    /api/jobs/{id}              -> Single job
    GET    /api/recommendations/{id}   -> Top recommendations
    GET    /api/explain/{id}           -> XAI explanations (SHAP + LIME)
    GET    /api/stats                  -> Dashboard statistics
    POST   /api/scrape/{source}        -> Trigger scraper (rooster/topjobs)
    GET    /api/scrape/status          -> Scraping status + timestamps
"""

import os
import sys
import json
import threading
import subprocess
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from database.db_config            import SessionLocal, text as sql_text
from resume_parser.resume_analyzer import analyze_resume
from ml_model.recommender          import recommend_jobs
from xai.xai_engine                import explain_recommendations

# -------------------------------------------------------------
# App Setup
# -------------------------------------------------------------

app = FastAPI(
    title="Job Recommendation System API",
    description="AI-powered job matching with Explainable AI",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# -------------------------------------------------------------
# Root
# -------------------------------------------------------------

@app.get("/")
def root():
    return {
        "message": "Job Recommendation System API",
        "version": "1.0.0",
        "status":  "running",
        "docs":    "/docs",
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.get("/api/model-report")
def get_model_report():
    """Return ML training report (7 classifiers + Phase 2 tuned SVM metrics).
    Normalizes old and new training_report.json formats into a single schema."""
    report_path = os.path.join(BASE_DIR, "saved_models", "training_report.json")
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Training report not found. Run train_role_classifier.py first.")
    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    # Already in new format
    if "evaluation" in report and isinstance(report["evaluation"], dict):
        return report

    # Migrate old format:  {"best_model":..., "test_f1":..., "results":[{model, cv_*},...]}
    results_list = report.get("results", [])
    evaluation = {}
    for entry in results_list:
        name = entry.get("model", "Unknown")
        def _pct(v):
            v = v or 0
            return round(float(v) * 100, 2) if float(v) <= 1.0 else round(float(v), 2)
        evaluation[name] = {
            "accuracy":  _pct(entry.get("cv_accuracy",  0)),
            "precision": _pct(entry.get("cv_precision", 0)),
            "recall":    _pct(entry.get("cv_recall",    0)),
            "f1_score":  _pct(entry.get("cv_f1",        0)),
        }

    best_f1_raw = report.get("test_f1") or report.get("best_f1") or 0
    best_f1 = round(float(best_f1_raw) * 100, 2) if float(best_f1_raw) <= 1.0 else round(float(best_f1_raw), 2)

    # Try to read roles from model pkl
    roles = []
    try:
        import joblib as _jl
        pkl = os.path.join(BASE_DIR, "saved_models", "best_role_model.pkl")
        if os.path.exists(pkl):
            bundle = _jl.load(pkl)
            le = bundle.get("label_encoder")
            roles = bundle.get("roles") or (le.classes_.tolist() if le else [])
    except Exception:
        pass

    return {
        "best_model":    report.get("best_model", "Unknown"),
        "best_f1":       best_f1,
        "best_accuracy": best_f1,
        "n_roles":       len(roles) or report.get("n_roles", 0),
        "total_samples": report.get("total_samples", 0),
        "roles":         roles,
        "evaluation":    evaluation,
        "tuned":         report.get("tuned", None),
    }


# -------------------------------------------------------------
# Resume Endpoints
# -------------------------------------------------------------

@app.post("/api/resume/upload")
async def upload_resume(file: UploadFile = File(...)):
    allowed = [".pdf", ".docx", ".txt"]
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"File type '{ext}' not supported.")

    temp_path = os.path.join(
        UPLOAD_DIR,
        f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    )
    try:
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)

        resume_data = analyze_resume(temp_path, save_db=True)
        if not resume_data:
            raise HTTPException(status_code=500, detail="Failed to parse resume.")

        resume_id = resume_data.get("db_id")
        if not resume_id:
            raise HTTPException(status_code=500, detail="Failed to save resume to DB.")

        recommendations = recommend_jobs(resume_id=resume_id, top_n=20)

        return {
            "success":             True,
            "message":             "Resume uploaded and analyzed successfully.",
            "resume_id":           resume_id,
            "candidate":           resume_data.get("candidate_name") or resume_data.get("email"),
            "email":               resume_data.get("email"),
            "phone":               resume_data.get("phone"),
            "years_experience":    resume_data.get("years_experience", 0),
            "skills_count":        resume_data.get("skills_count", 0),
            "hard_skills":         resume_data.get("hard_skills", []),
            "soft_skills":         resume_data.get("soft_skills", []),
            "predicted_role":      resume_data.get("predicted_role"),
            "role_confidence":     resume_data.get("role_confidence", 0),
            "top_recommendations": len(recommendations),
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print("\n" + "="*60)
        print("[X] UPLOAD ERROR DETAIL:")
        print(traceback.format_exc())
        print("="*60 + "\n")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@app.get("/api/resumes")
def get_all_resumes():
    db = SessionLocal()
    try:
        results = db.execute(sql_text("""
            SELECT id, candidate_name, email, phone,
                   years_experience, skills_count, file_name, uploaded_at
            FROM resumes ORDER BY uploaded_at DESC
        """)).fetchall()
        resumes = []
        for r in results:
            row = dict(r._mapping)
            row["uploaded_at"] = str(row.get("uploaded_at", ""))
            resumes.append(row)
        return {"success": True, "count": len(resumes), "resumes": resumes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/api/resume/{resume_id}")
def get_resume(resume_id: int):
    db = SessionLocal()
    try:
        result = db.execute(
            sql_text("SELECT * FROM resumes WHERE id = :id"), {"id": resume_id}
        ).fetchone()
        if not result:
            raise HTTPException(status_code=404, detail=f"Resume ID {resume_id} not found.")
        row = dict(result._mapping)
        row["hard_skills"]    = json.loads(row.get("hard_skills") or "[]")
        row["soft_skills"]    = json.loads(row.get("soft_skills") or "[]")
        row["all_skills"]     = json.loads(row.get("all_skills")  or "[]")
        row["uploaded_at"]    = str(row.get("uploaded_at", ""))
        row["predicted_role"] = row.get("predicted_role")
        row["role_confidence"]= row.get("role_confidence", 0)
        row.pop("raw_text", None)
        return {"success": True, "resume": row}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.delete("/api/resume/{resume_id}")
def delete_resume(resume_id: int):
    db = SessionLocal()
    try:
        result = db.execute(
            sql_text("SELECT id FROM resumes WHERE id = :id"), {"id": resume_id}
        ).fetchone()
        if not result:
            raise HTTPException(status_code=404, detail=f"Resume ID {resume_id} not found.")
        db.execute(sql_text("DELETE FROM recommendations WHERE resume_id = :id"), {"id": resume_id})
        db.execute(sql_text("DELETE FROM resumes WHERE id = :id"), {"id": resume_id})
        db.commit()
        return {"success": True, "message": f"Resume ID {resume_id} deleted successfully."}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# -------------------------------------------------------------
# Jobs Endpoints
# -------------------------------------------------------------

@app.get("/api/jobs")
def get_jobs(
    source: Optional[str] = Query(None, description="rooster or topjobs"),
    search: Optional[str] = Query(None, description="Search title or company"),
    limit:  int           = Query(50,   description="Results per page"),
    offset: int           = Query(0,    description="Pagination offset"),
):
    db = SessionLocal()
    try:
        query  = "SELECT * FROM jobs WHERE 1=1"
        params = {}
        if source:
            query += " AND source = :source"
            params["source"] = source
        if search:
            query += " AND (LOWER(title) LIKE :search OR LOWER(company) LIKE :search)"
            params["search"] = f"%{search.lower()}%"

        count_q = query.replace("SELECT *", "SELECT COUNT(*)")
        total   = db.execute(sql_text(count_q), params).scalar()

        query += " ORDER BY id DESC LIMIT :limit OFFSET :offset"
        params["limit"]  = limit
        params["offset"] = offset

        results = db.execute(sql_text(query), params).fetchall()
        jobs = []
        for r in results:
            row = dict(r._mapping)
            row["scraped_at"] = str(row.get("scraped_at", ""))
            jobs.append(row)
        return {"success": True, "total": total, "count": len(jobs), "jobs": jobs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/api/jobs/{job_id}")
def get_job(job_id: int):
    db = SessionLocal()
    try:
        result = db.execute(
            sql_text("SELECT * FROM jobs WHERE id = :id"), {"id": job_id}
        ).fetchone()
        if not result:
            raise HTTPException(status_code=404, detail=f"Job ID {job_id} not found.")
        row = dict(result._mapping)
        row["scraped_at"] = str(row.get("scraped_at", ""))
        return {"success": True, "job": row}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# -------------------------------------------------------------
# Recommendations Endpoint
# -------------------------------------------------------------

@app.get("/api/recommendations/{resume_id}")
def get_recommendations(
    resume_id: int,
    top:       int           = Query(20,    description="Number of recommendations"),
    source:    Optional[str] = Query(None,  description="rooster or topjobs"),
    refresh:   bool          = Query(False, description="Re-run ML matching"),
):
    db = SessionLocal()
    try:
        resume = db.execute(
            sql_text("SELECT id, predicted_role, role_confidence FROM resumes WHERE id = :id"),
            {"id": resume_id}
        ).fetchone()
        if not resume:
            raise HTTPException(status_code=404, detail=f"Resume ID {resume_id} not found.")
        resume_row     = dict(resume._mapping)
        predicted_role = resume_row.get("predicted_role")
        role_confidence= resume_row.get("role_confidence", 0)

        if refresh:
            db.close()
            recs = recommend_jobs(resume_id=resume_id, top_n=top, source=source)
            role = recs[0].get("predicted_role") if recs else predicted_role
            conf = recs[0].get("role_confidence", 0) if recs else role_confidence
            return {"success": True, "resume_id": resume_id, "refreshed": True,
                    "predicted_role": role, "role_confidence": conf,
                    "count": len(recs), "recommendations": recs}

        results = db.execute(sql_text("""
            SELECT * FROM recommendations
            WHERE resume_id = :rid ORDER BY rank ASC LIMIT :n
        """), {"rid": resume_id, "n": top}).fetchall()

        if not results:
            db.close()
            recs = recommend_jobs(resume_id=resume_id, top_n=top, source=source)
            return {"success": True, "resume_id": resume_id, "refreshed": True,
                    "count": len(recs), "recommendations": recs}

        recs = []
        for r in results:
            row = dict(r._mapping)
            row["matched_skills"]     = json.loads(row.get("matched_skills") or "[]")
            row["missing_skills"]     = json.loads(row.get("missing_skills") or "[]")
            row["created_at"]         = str(row.get("created_at", ""))
            row["hybrid_score_pct"]   = round((row.get("hybrid_score", 0) * 100), 1)
            row["tfidf_score_pct"]    = round((row.get("tfidf_score",  0) * 100), 1)
            row["skill_score_pct"]    = round((row.get("skill_score",  0) * 100), 1)
            row["word2vec_score_pct"] = round((row.get("word2vec_score", 0) * 100), 1)
            row["ml_score_pct"]       = round((row.get("ml_score", 0) * 100), 1)
            # Normalize: DB stores job_title, frontend expects title
            row["title"]    = row.get("job_title") or row.get("title", "")
            row["job_url"]  = row.get("job_url", "")
            row["location"] = row.get("location", "")
            row["salary"]   = row.get("salary", "")
            recs.append(row)

        return {"success": True, "resume_id": resume_id, "refreshed": False,
                "predicted_role": predicted_role, "role_confidence": role_confidence,
                "count": len(recs), "recommendations": recs}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try: db.close()
        except: pass


# -------------------------------------------------------------
# XAI Endpoint
# -------------------------------------------------------------

@app.get("/api/explain/{resume_id}")
def get_explanations(
    resume_id: int,
    top: int = Query(20, description="Number of jobs to explain"),
):
    try:
        explanations = explain_recommendations(resume_id=resume_id, top_n=top)
        if not explanations:
            raise HTTPException(status_code=404,
                detail="No recommendations found. Run /api/recommendations/{id} first.")
        return {"success": True, "resume_id": resume_id,
                "count": len(explanations), "explanations": explanations}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------
# Stats Endpoint
# -------------------------------------------------------------

@app.get("/api/stats")
def get_stats():
    db = SessionLocal()
    try:
        total_jobs    = db.execute(sql_text("SELECT COUNT(*) FROM jobs")).scalar() or 0
        rooster_jobs  = db.execute(sql_text("SELECT COUNT(*) FROM jobs WHERE source='rooster'")).scalar() or 0
        topjobs_jobs  = db.execute(sql_text("SELECT COUNT(*) FROM jobs WHERE source='topjobs'")).scalar() or 0
        total_resumes = db.execute(sql_text("SELECT COUNT(*) FROM resumes")).scalar() or 0
        try:
            matched = db.execute(
                sql_text("SELECT COUNT(DISTINCT resume_id) FROM recommendations")
            ).scalar() or 0
        except:
            matched = 0
        return {
            "success": True,
            "stats": {
                "total_jobs":      total_jobs,
                "rooster_jobs":    rooster_jobs,
                "topjobs_jobs":    topjobs_jobs,
                "total_resumes":   total_resumes,
                "resumes_matched": matched,
                "last_updated":    datetime.now().isoformat(),
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# -------------------------------------------------------------
# Scraping Endpoints
# -------------------------------------------------------------



# ---------------------------------------------------------------
# Scraping Status + Trigger Endpoints
# ---------------------------------------------------------------

# In-memory scraping status
# ---------------------------------------------------------------
# Scraping Live Log
# ---------------------------------------------------------------

import queue
from fastapi.responses import StreamingResponse

scrape_logs: dict = {
    "rooster": [],
    "topjobs": [],
}

MAX_LOG_LINES = 200


def log_line(source: str, msg: str):
    """Add a timestamped line to the source log buffer."""
    ts   = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    scrape_logs[source].append(line)
    if len(scrape_logs[source]) > MAX_LOG_LINES:
        scrape_logs[source] = scrape_logs[source][-MAX_LOG_LINES:]


@app.get("/api/scrape/logs/{source}")
def get_scrape_logs(source: str):
    """Return all log lines for a source."""
    if source not in ["rooster", "topjobs"]:
        raise HTTPException(status_code=400, detail="Invalid source")
    return {
        "success": True,
        "source":  source,
        "logs":    scrape_logs.get(source, []),
        "running": scraping_status[source]["running"],
    }


@app.delete("/api/scrape/logs/{source}")
def clear_scrape_logs(source: str):
    """Clear log buffer for a source."""
    if source not in ["rooster", "topjobs"]:
        raise HTTPException(status_code=400, detail="Invalid source")
    scrape_logs[source] = []
    return {"success": True, "message": f"{source} logs cleared"}

# ---------------------------------------------------------------
# Scraping Status Store
# ---------------------------------------------------------------

scraping_status = {
    "rooster": {"running": False, "last_run": None, "jobs_before": 0, "jobs_after": 0, "new_jobs": 0, "error": None},
    "topjobs": {"running": False, "last_run": None, "jobs_before": 0, "jobs_after": 0, "new_jobs": 0, "error": None},
}


def get_venv_python() -> str:
    for candidate in [
        os.path.join(BASE_DIR, "venv", "Scripts", "python.exe"),
        os.path.join(BASE_DIR, "venv", "bin", "python"),
        os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe"),
        os.path.join(BASE_DIR, ".venv", "bin", "python"),
    ]:
        if os.path.exists(candidate):
            return candidate
    return sys.executable


def run_scraper_task(source: str, script_path: str):
    db = SessionLocal()
    try:
        before = db.execute(sql_text("SELECT COUNT(*) FROM jobs WHERE source = :s"), {"s": source}).scalar() or 0
        db.close()
        scraping_status[source].update({"running": True, "jobs_before": before, "error": None, "new_jobs": 0})

        python_exe = get_venv_python()
        print(f"\n[START] [{source}] before={before} | python={python_exe}")
        log_line(source, f"Scraper started | Jobs before: {before}")
        log_line(source, f"Python: {python_exe}")

        # Run in script's own directory so relative files (TopJobs.txt) are found
        script_dir = os.path.dirname(script_path)
        proc = subprocess.run(
            [python_exe, script_path],
            capture_output=True, text=True, timeout=360,
            encoding="utf-8", errors="replace",
            cwd=script_dir,
            env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
        )

        if proc.returncode != 0:
            lines = [l.strip() for l in (proc.stderr or "").split("\n") if l.strip()]
            err = next((l[:200] for l in lines if "Error" in l or "Exception" in l), "Scraper failed")
            scraping_status[source]["error"] = err
            log_line(source, f"ERROR: {err}")
        else:
            log_line(source, "Scraper done. Running pipeline...")
            try:
                import glob, csv as csv_mod
                from pipeline.unified_schema import normalize_batch
                from database.db_insert import insert_jobs_batch

                sdir = os.path.join(BASE_DIR, "scraping")
                patterns = {
                    "rooster": [os.path.join(sdir, "rooster_jobs_*.csv"), os.path.join(sdir, "rooster_jobs_*.json")],
                    "topjobs": [os.path.join(sdir, "topjobs_data_*.csv"), os.path.join(sdir, "topjobs_data_*.json")],
                }
                found = None
                for p in patterns.get(source, []):
                    m = sorted(glob.glob(p), reverse=True)
                    if m: found = m[0]; break

                if found:
                    log_line(source, f"Loading: {os.path.basename(found)}")
                    with open(found, "r", encoding="utf-8-sig", errors="replace") as f:
                        raw = [dict(r) for r in csv_mod.DictReader(f)]
                    log_line(source, f"Read {len(raw)} rows")
                    jobs = normalize_batch(raw, source=source)
                    res  = insert_jobs_batch(jobs, source=source)
                    added   = res.get("added",   0) if isinstance(res, dict) else len(jobs)
                    skipped = res.get("skipped", 0) if isinstance(res, dict) else 0
                    log_line(source, f"Pipeline done | +{added} new | {skipped} duplicates")
                else:
                    log_line(source, "WARN: No data file found")
            except Exception as pe:
                scraping_status[source]["error"] = f"Pipeline: {pe}"
                log_line(source, f"Pipeline error: {pe}")

        db2   = SessionLocal()
        after = db2.execute(sql_text("SELECT COUNT(*) FROM jobs WHERE source = :s"), {"s": source}).scalar() or 0
        db2.close()
        new_jobs = max(0, after - before)
        scraping_status[source].update({"jobs_after": after, "new_jobs": new_jobs, "last_run": datetime.now().isoformat()})
        print(f"[DONE] [{source}] {before} -> {after} (+{new_jobs})")
        log_line(source, f"Done | Before: {before} | After: {after} | New: +{new_jobs}")

    except subprocess.TimeoutExpired:
        scraping_status[source]["error"] = "Timeout (6 min)"
        scraping_status[source]["last_run"] = datetime.now().isoformat()
        log_line(source, "TIMEOUT: Scraper exceeded 6 minutes")
    except Exception as e:
        scraping_status[source]["error"] = str(e)
        scraping_status[source]["last_run"] = datetime.now().isoformat()
        log_line(source, f"ERROR: {e}")
    finally:
        scraping_status[source]["running"] = False
        try: db.close()
        except: pass


# status MUST be before {source} to avoid route conflict
@app.get("/api/scrape/status")
def get_scraping_status():
    db = SessionLocal()
    try:
        r_total = db.execute(sql_text("SELECT COUNT(*) FROM jobs WHERE source='rooster'")).scalar() or 0
        t_total = db.execute(sql_text("SELECT COUNT(*) FROM jobs WHERE source='topjobs'")).scalar() or 0
        r_last  = db.execute(sql_text("SELECT scraped_at FROM jobs WHERE source='rooster' ORDER BY scraped_at DESC LIMIT 1")).scalar()
        t_last  = db.execute(sql_text("SELECT scraped_at FROM jobs WHERE source='topjobs' ORDER BY scraped_at DESC LIMIT 1")).scalar()
        return {
            "success": True,
            "rooster": {**scraping_status["rooster"], "total_jobs": r_total, "last_scraped": str(r_last) if r_last else None},
            "topjobs": {**scraping_status["topjobs"], "total_jobs": t_total, "last_scraped": str(t_last) if t_last else None},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.post("/api/scrape/{source}")
def trigger_scraping(source: str):
    if source not in ["rooster", "topjobs"]:
        raise HTTPException(status_code=400, detail="Source must be rooster or topjobs")
    if scraping_status[source]["running"]:
        raise HTTPException(status_code=409, detail=f"{source} is already running")
    scripts = {
        "rooster": os.path.join(BASE_DIR, "scraping", "ScrapingRooster.py"),
        "topjobs": os.path.join(BASE_DIR, "scraping", "ScrapingTOPJobs.py"),
    }
    sp = scripts[source]
    if not os.path.exists(sp):
        raise HTTPException(status_code=404, detail=f"Script not found: {sp}")
    threading.Thread(target=run_scraper_task, args=(source, sp), daemon=True).start()
    return {"success": True, "message": f"{source} scraper started", "source": source, "started_at": datetime.now().isoformat()}

# ================================================================
# Database Management Endpoints
# ================================================================



@app.get("/api/db/overview")
def db_overview():
    """Full database overview — table counts, sizes, timestamps."""
    db = SessionLocal()
    try:
        jobs_total    = db.execute(sql_text("SELECT COUNT(*) FROM jobs")).scalar() or 0
        jobs_rooster  = db.execute(sql_text("SELECT COUNT(*) FROM jobs WHERE source='rooster'")).scalar() or 0
        jobs_topjobs  = db.execute(sql_text("SELECT COUNT(*) FROM jobs WHERE source='topjobs'")).scalar() or 0
        jobs_last     = db.execute(sql_text("SELECT scraped_at FROM jobs ORDER BY scraped_at DESC LIMIT 1")).scalar()

        resumes_total = db.execute(sql_text("SELECT COUNT(*) FROM resumes")).scalar() or 0
        resumes_last  = db.execute(sql_text("SELECT uploaded_at FROM resumes ORDER BY uploaded_at DESC LIMIT 1")).scalar()

        try:
            recs_total = db.execute(sql_text("SELECT COUNT(*) FROM recommendations")).scalar() or 0
            recs_last  = db.execute(sql_text("SELECT created_at FROM recommendations ORDER BY created_at DESC LIMIT 1")).scalar()
        except:
            recs_total = 0
            recs_last  = None

        # DB size estimate
        try:
            db_size = db.execute(sql_text(
                "SELECT pg_size_pretty(pg_database_size(current_database()))"
            )).scalar()
        except:
            db_size = "Unknown"

        return {
            "success": True,
            "overview": {
                "jobs":            { "total": jobs_total, "rooster": jobs_rooster, "topjobs": jobs_topjobs, "last_scraped": str(jobs_last) if jobs_last else None },
                "resumes":         { "total": resumes_total, "last_uploaded": str(resumes_last) if resumes_last else None },
                "recommendations": { "total": recs_total, "last_created": str(recs_last) if recs_last else None },
                "database":        { "size": db_size, "name": "job_recommendation_db" },
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.delete("/api/db/jobs/source/{source}")
def delete_jobs_by_source(source: str):
    """Delete all jobs from a specific source."""
    if source not in ["rooster", "topjobs"]:
        raise HTTPException(status_code=400, detail="Source must be rooster or topjobs")
    db = SessionLocal()
    try:
        count  = db.execute(sql_text("SELECT COUNT(*) FROM jobs WHERE source = :s"), {"s": source}).scalar() or 0
        db.execute(sql_text("DELETE FROM jobs WHERE source = :s"), {"s": source})
        db.commit()
        return {"success": True, "message": f"Deleted {count} {source} jobs", "deleted": count}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.delete("/api/db/jobs/duplicates")
def delete_duplicate_jobs():
    """Delete duplicate jobs keeping the latest entry per job_url."""
    db = SessionLocal()
    try:
        result = db.execute(sql_text("""
            DELETE FROM jobs WHERE id NOT IN (
                SELECT MAX(id) FROM jobs
                WHERE job_url IS NOT NULL AND job_url != ''
                GROUP BY job_url
            ) AND job_url IS NOT NULL AND job_url != ''
        """))
        db.commit()
        deleted = result.rowcount
        return {"success": True, "message": f"Removed {deleted} duplicate jobs", "deleted": deleted}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.delete("/api/db/jobs/all")
def delete_all_jobs():
    """Delete ALL jobs from database."""
    db = SessionLocal()
    try:
        count = db.execute(sql_text("SELECT COUNT(*) FROM jobs")).scalar() or 0
        db.execute(sql_text("DELETE FROM recommendations"))
        db.execute(sql_text("DELETE FROM jobs"))
        db.commit()
        return {"success": True, "message": f"Deleted all {count} jobs and related recommendations", "deleted": count}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.delete("/api/db/resume/{resume_id}")
def db_delete_resume(resume_id: int):
    """Delete a resume and all its recommendations."""
    db = SessionLocal()
    try:
        r = db.execute(sql_text("SELECT id FROM resumes WHERE id = :id"), {"id": resume_id}).fetchone()
        if not r:
            raise HTTPException(status_code=404, detail=f"Resume {resume_id} not found")
        db.execute(sql_text("DELETE FROM recommendations WHERE resume_id = :id"), {"id": resume_id})
        db.execute(sql_text("DELETE FROM resumes WHERE id = :id"), {"id": resume_id})
        db.commit()
        return {"success": True, "message": f"Resume {resume_id} and its recommendations deleted"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.delete("/api/db/resumes/all")
def delete_all_resumes():
    """Delete ALL resumes and recommendations."""
    db = SessionLocal()
    try:
        rc = db.execute(sql_text("SELECT COUNT(*) FROM resumes")).scalar() or 0
        db.execute(sql_text("DELETE FROM recommendations"))
        db.execute(sql_text("DELETE FROM resumes"))
        db.commit()
        return {"success": True, "message": f"Deleted {rc} resumes and all recommendations", "deleted": rc}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.delete("/api/db/recommendations/all")
def delete_all_recommendations():
    """Delete ALL recommendations (keeps resumes and jobs)."""
    db = SessionLocal()
    try:
        count = db.execute(sql_text("SELECT COUNT(*) FROM recommendations")).scalar() or 0
        db.execute(sql_text("DELETE FROM recommendations"))
        db.commit()
        return {"success": True, "message": f"Deleted {count} recommendations", "deleted": count}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.delete("/api/db/recommendations/resume/{resume_id}")
def delete_resume_recommendations(resume_id: int):
    """Delete recommendations for a specific resume."""
    db = SessionLocal()
    try:
        count = db.execute(sql_text("SELECT COUNT(*) FROM recommendations WHERE resume_id = :id"), {"id": resume_id}).scalar() or 0
        db.execute(sql_text("DELETE FROM recommendations WHERE resume_id = :id"), {"id": resume_id})
        db.commit()
        return {"success": True, "message": f"Deleted {count} recommendations for resume {resume_id}", "deleted": count}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.delete("/api/db/reset")
def reset_database():
    """DANGER: Reset entire database — delete all jobs, resumes, recommendations."""
    db = SessionLocal()
    try:
        jobs  = db.execute(sql_text("SELECT COUNT(*) FROM jobs")).scalar() or 0
        res   = db.execute(sql_text("SELECT COUNT(*) FROM resumes")).scalar() or 0
        db.execute(sql_text("DELETE FROM recommendations"))
        db.execute(sql_text("DELETE FROM resumes"))
        db.execute(sql_text("DELETE FROM jobs"))
        db.commit()
        return {
            "success": True,
            "message": f"Database reset complete. Deleted {jobs} jobs and {res} resumes.",
            "deleted": {"jobs": jobs, "resumes": res}
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/api/resumes/export-csv")
def export_resumes_csv():
    """Export resumes as CSV download."""
    import io as _io, csv as _csv
    from fastapi.responses import StreamingResponse as _SR
    db = SessionLocal()
    try:
        rows = db.execute(sql_text(
            "SELECT id, candidate_name, email, phone, years_experience, skills_count, file_name, uploaded_at FROM resumes ORDER BY uploaded_at DESC"
        )).fetchall()
        output = _io.StringIO()
        writer = _csv.writer(output)
        writer.writerow(["id","candidate_name","email","phone","years_experience","skills_count","file_name","uploaded_at"])
        for r in rows:
            writer.writerow(list(r))
        output.seek(0)
        filename = f"resumes_{datetime.now().strftime('%Y%m%d')}.csv"
        return _SR(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ================================================================
# Analytics Endpoints
# ================================================================

@app.get("/api/analytics/skills-demand")
def skills_demand():
    """Top skills demanded across all job descriptions."""
    db = SessionLocal()
    try:
        rows = db.execute(sql_text(
            "SELECT description, title FROM jobs WHERE description IS NOT NULL AND description != ''"
        )).fetchall()

        # Common tech skills to search for
        SKILLS = [
            "python","java","javascript","react","node.js","sql","mysql","postgresql",
            "mongodb","aws","docker","kubernetes","git","github","html","css","typescript",
            "php","c++","c#",".net","spring","flask","django","tensorflow","pytorch",
            "machine learning","deep learning","data science","excel","power bi","tableau",
            "figma","photoshop","illustrator","flutter","android","ios","swift","kotlin",
            "linux","devops","agile","scrum","rest api","graphql","redis","elasticsearch",
            "azure","gcp","selenium","opencv","nlp","spark","hadoop"
        ]

        counts: dict = {s: 0 for s in SKILLS}
        for row in rows:
            text = ((row[0] or "") + " " + (row[1] or "")).lower()
            for skill in SKILLS:
                if skill in text:
                    counts[skill] += 1

        sorted_skills = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        top = [{"skill": k, "count": v, "pct": round(v/max(len(rows),1)*100,1)}
               for k, v in sorted_skills if v > 0][:25]

        return {"success": True, "total_jobs": len(rows), "skills": top}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/api/analytics/job-categories")
def job_categories():
    """Auto-categorize jobs by title keywords."""
    db = SessionLocal()
    try:
        rows = db.execute(sql_text("SELECT title, source FROM jobs")).fetchall()

        CATEGORIES = {
            "Software Engineering": ["software engineer","developer","programmer","backend","frontend","fullstack","full stack","full-stack"],
            "Data & AI":            ["data scientist","machine learning","ai engineer","data analyst","data engineer","deep learning","nlp"],
            "DevOps & Cloud":       ["devops","cloud","infrastructure","sre","platform engineer","kubernetes","docker"],
            "QA & Testing":         ["qa","quality assurance","test","automation engineer","tester"],
            "UI/UX & Design":       ["ui","ux","designer","graphic","figma","creative","illustrator","photoshop"],
            "Mobile":               ["mobile","android","ios","flutter","react native","swift","kotlin"],
            "Management & BA":      ["project manager","business analyst","product manager","scrum master","team lead","tech lead"],
            "IT Support":           ["it support","helpdesk","system admin","network","it technician","it officer"],
            "Cybersecurity":        ["security","cybersecurity","penetration","soc analyst","information security"],
            "Database":             ["dba","database admin","sql developer","data warehouse"],
            "Other":                [],
        }

        cats: dict = {c: {"total": 0, "rooster": 0, "topjobs": 0} for c in CATEGORIES}

        for title, source in rows:
            t = (title or "").lower()
            matched = False
            for cat, keywords in CATEGORIES.items():
                if cat == "Other": continue
                if any(kw in t for kw in keywords):
                    cats[cat]["total"]  += 1
                    cats[cat][source if source in ("rooster","topjobs") else "other"] =                         cats[cat].get(source, 0) + 1
                    matched = True
                    break
            if not matched:
                cats["Other"]["total"] += 1

        result = [{"category": k, **v} for k, v in cats.items() if v["total"] > 0]
        result.sort(key=lambda x: x["total"], reverse=True)
        return {"success": True, "categories": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/api/analytics/companies")
def top_companies():
    """Top hiring companies by job count."""
    db = SessionLocal()
    try:
        rows = db.execute(sql_text("""
            SELECT company, source, COUNT(*) as cnt
            FROM jobs
            WHERE company IS NOT NULL AND company != '' AND company != 'Company Name Withheld'
            GROUP BY company, source
            ORDER BY cnt DESC
            LIMIT 20
        """)).fetchall()
        result = [{"company": r[0], "source": r[1], "count": r[2]} for r in rows]
        return {"success": True, "companies": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/api/analytics/locations")
def job_locations():
    """Job distribution by location."""
    db = SessionLocal()
    try:
        rows = db.execute(sql_text("""
            SELECT location, COUNT(*) as cnt
            FROM jobs
            WHERE location IS NOT NULL AND location != ''
            GROUP BY location
            ORDER BY cnt DESC
            LIMIT 20
        """)).fetchall()
        result = [{"location": r[0], "count": r[1]} for r in rows]
        return {"success": True, "locations": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/api/analytics/timeline")
def scraping_timeline():
    """Jobs scraped over time (by date)."""
    db = SessionLocal()
    try:
        rows = db.execute(sql_text("""
            SELECT DATE(scraped_at) as day, source, COUNT(*) as cnt
            FROM jobs
            WHERE scraped_at IS NOT NULL
            GROUP BY DATE(scraped_at), source
            ORDER BY day DESC
            LIMIT 30
        """)).fetchall()
        result = [{"date": str(r[0]), "source": r[1], "count": r[2]} for r in rows]
        return {"success": True, "timeline": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/api/analytics/xai/evaluation/{resume_id}")
def xai_evaluation(resume_id: int):
    """XAI evaluation metrics: Precision@K, score distribution, counterfactuals."""
    db = SessionLocal()
    try:
        # Get resume skills
        res = db.execute(sql_text("SELECT * FROM resumes WHERE id=:id"), {"id": resume_id}).fetchone()
        if not res:
            raise HTTPException(status_code=404, detail="Resume not found")
        row = dict(res._mapping)
        hard_skills = json.loads(row.get("hard_skills") or "[]")

        # Get recommendations
        recs = db.execute(sql_text("""
            SELECT * FROM recommendations WHERE resume_id=:id ORDER BY rank ASC LIMIT 20
        """), {"id": resume_id}).fetchall()
        if not recs:
            raise HTTPException(status_code=404, detail="No recommendations found")

        recs_list = [dict(r._mapping) for r in recs]

        # Score distribution
        scores = [r.get("hybrid_score", 0) for r in recs_list]
        avg_score    = round(sum(scores) / len(scores) * 100, 1) if scores else 0
        max_score    = round(max(scores) * 100, 1) if scores else 0
        score_spread = round((max(scores) - min(scores)) * 100, 1) if scores else 0

        # Precision@K — jobs with skill_score > 0.3 considered relevant
        def precision_at_k(k):
            top_k   = recs_list[:k]
            relevant = sum(1 for r in top_k if r.get("skill_score", 0) > 0.25)
            return round(relevant / k * 100, 1)

        # NDCG@K
        import math
        def ndcg_at_k(k):
            top_k = recs_list[:k]
            dcg   = sum((r.get("skill_score", 0)) / math.log2(i+2) for i, r in enumerate(top_k))
            idcg  = sum(1.0 / math.log2(i+2) for i in range(min(k, len(top_k))))
            return round(dcg / idcg * 100, 1) if idcg > 0 else 0

        # Counterfactuals — for top 3 jobs, find missing skills that would boost score
        counterfactuals = []
        for rec in recs_list[:3]:
            missing = json.loads(rec.get("missing_skills") or "[]")
            current_skill  = rec.get("skill_score", 0)
            job_id         = rec.get("job_id")

            # Get job total skills
            job = db.execute(sql_text("SELECT * FROM jobs WHERE id=:id"), {"id": job_id}).fetchone()
            if job and missing:
                job_row   = dict(job._mapping)
                # Estimate: each missing skill adds ~1/total_skills to skill_score
                total_job_skills = max(len(missing) + len(json.loads(rec.get("matched_skills") or "[]")), 1)
                boost_per_skill  = 1.0 / total_job_skills
                gain_if_all      = round(min(boost_per_skill * len(missing[:3]), 1.0) * 100, 1)
                new_hybrid       = round(min((rec.get("hybrid_score", 0) + boost_per_skill * min(3, len(missing)) * 0.35), 1.0) * 100, 1)

                counterfactuals.append({
                    "rank":          rec.get("rank"),
                    "job_title":     rec.get("job_title"),
                    "company":       rec.get("company"),
                    "current_score": round(rec.get("hybrid_score", 0) * 100, 1),
                    "current_rank":  rec.get("rank"),
                    "add_skills":    missing[:3],
                    "skill_gain":    f"+{gain_if_all}%",
                    "new_score_est": new_hybrid,
                    "impact":        "High" if gain_if_all > 15 else "Medium" if gain_if_all > 8 else "Low",
                })

        # Bias check — source distribution in top 5 vs top 20
        top5_sources  = [r.get("source","") for r in recs_list[:5]]
        top20_sources = [r.get("source","") for r in recs_list]
        bias_check = {
            "top5":  {"rooster": top5_sources.count("rooster"),  "topjobs": top5_sources.count("topjobs")},
            "top20": {"rooster": top20_sources.count("rooster"), "topjobs": top20_sources.count("topjobs")},
            "balanced": top5_sources.count("rooster") > 0 and top5_sources.count("topjobs") > 0,
        }

        return {
            "success": True,
            "resume_id": resume_id,
            "candidate": row.get("candidate_name") or row.get("email"),
            "skills_count": len(hard_skills),
            "metrics": {
                "avg_match_score":  avg_score,
                "best_match_score": max_score,
                "score_spread":     score_spread,
                "total_recs":       len(recs_list),
                "precision_at_5":   precision_at_k(5),
                "precision_at_10":  precision_at_k(10),
                "ndcg_at_5":        ndcg_at_k(5),
                "ndcg_at_10":       ndcg_at_k(10),
            },
            "counterfactuals": counterfactuals,
            "bias_check": bias_check,
            "score_distribution": [
                {"rank": i+1, "score": round(s*100,1)} for i, s in enumerate(scores)
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ================================================================
# Bookmarks Endpoints
# ================================================================

@app.post("/api/bookmarks/{job_id}")
def add_bookmark(job_id: int):
    """Bookmark a job."""
    db = SessionLocal()
    try:
        # Ensure table exists
        db.execute(sql_text("""
            CREATE TABLE IF NOT EXISTS bookmarks (
                id         SERIAL PRIMARY KEY,
                job_id     INTEGER NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        db.commit()

        job = db.execute(sql_text("SELECT id FROM jobs WHERE id = :id"), {"id": job_id}).fetchone()
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        try:
            db.execute(sql_text(
                "INSERT INTO bookmarks (job_id) VALUES (:jid)"
            ), {"jid": job_id})
            db.commit()
            return {"success": True, "message": "Job bookmarked", "job_id": job_id, "bookmarked": True}
        except Exception:
            db.rollback()
            return {"success": True, "message": "Already bookmarked", "job_id": job_id, "bookmarked": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.delete("/api/bookmarks/{job_id}")
def remove_bookmark(job_id: int):
    """Remove a bookmark."""
    db = SessionLocal()
    try:
        db.execute(sql_text("DELETE FROM bookmarks WHERE job_id = :jid"), {"jid": job_id})
        db.commit()
        return {"success": True, "message": "Bookmark removed", "job_id": job_id, "bookmarked": False}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/api/bookmarks")
def get_bookmarks():
    """Get all bookmarked jobs with full job details."""
    db = SessionLocal()
    try:
        db.execute(sql_text("""
            CREATE TABLE IF NOT EXISTS bookmarks (
                id         SERIAL PRIMARY KEY,
                job_id     INTEGER NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        db.commit()

        rows = db.execute(sql_text("""
            SELECT j.*, b.created_at as bookmarked_at
            FROM bookmarks b
            JOIN jobs j ON j.id = b.job_id
            ORDER BY b.created_at DESC
        """)).fetchall()

        jobs = []
        for r in rows:
            row = dict(r._mapping)
            row["scraped_at"]    = str(row.get("scraped_at", ""))
            row["bookmarked_at"] = str(row.get("bookmarked_at", ""))
            jobs.append(row)
        return {"success": True, "count": len(jobs), "bookmarks": jobs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/api/bookmarks/ids")
def get_bookmark_ids():
    """Get all bookmarked job IDs (for frontend state)."""
    db = SessionLocal()
    try:
        db.execute(sql_text("""
            CREATE TABLE IF NOT EXISTS bookmarks (
                id         SERIAL PRIMARY KEY,
                job_id     INTEGER NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        db.commit()
        rows = db.execute(sql_text("SELECT job_id FROM bookmarks")).fetchall()
        return {"success": True, "ids": [r[0] for r in rows]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.delete("/api/bookmarks")
def clear_all_bookmarks():
    """Clear all bookmarks."""
    db = SessionLocal()
    try:
        count = db.execute(sql_text("SELECT COUNT(*) FROM bookmarks")).scalar() or 0
        db.execute(sql_text("DELETE FROM bookmarks"))
        db.commit()
        return {"success": True, "message": f"Cleared {count} bookmarks"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ================================================================
# Auto-Scrape Scheduler
# ================================================================

import threading as _threading
import time as _time

# Scheduler state
scheduler_state = {
    "enabled":      False,
    "interval_hrs": 24,
    "last_run":     None,
    "next_run":     None,
    "runs_total":   0,
    "thread":       None,
    "stop_event":   None,
}


def _scheduler_loop(stop_event: _threading.Event, interval_hrs: int):
    """Background scheduler loop."""
    import subprocess as _sp

    while not stop_event.is_set():
        now = datetime.now()
        scheduler_state["last_run"]   = now.isoformat()
        scheduler_state["runs_total"] += 1
        next_t = datetime.fromtimestamp(now.timestamp() + interval_hrs * 3600)
        scheduler_state["next_run"] = next_t.isoformat()

        print(f"\n[SCHEDULER] Auto-scrape run #{scheduler_state['runs_total']} at {now.strftime('%H:%M:%S')}")

        for source in ["rooster", "topjobs"]:
            if stop_event.is_set():
                break
            scripts = {
                "rooster": os.path.join(BASE_DIR, "scraping", "ScrapingRooster.py"),
                "topjobs": os.path.join(BASE_DIR, "scraping", "ScrapingTOPJobs.py"),
            }
            sp = scripts[source]
            if not os.path.exists(sp):
                print(f"[SCHEDULER] Script not found: {sp}")
                continue

            # Reuse existing scraper logic
            _threading.Thread(
                target=run_scraper_task,
                args=(source, sp),
                daemon=True
            ).start()

            # Wait for scraper to finish (max 7 min)
            wait_start = _time.time()
            while scraping_status[source]["running"] and _time.time() - wait_start < 420:
                _time.sleep(5)

        print(f"[SCHEDULER] Next run at {next_t.strftime('%Y-%m-%d %H:%M:%S')}")

        # Sleep until next run (check every 30s for stop signal)
        sleep_secs = interval_hrs * 3600
        slept = 0
        while slept < sleep_secs and not stop_event.is_set():
            _time.sleep(30)
            slept += 30


@app.post("/api/scheduler/start")
def start_scheduler(interval_hrs: int = 24):
    """Start the auto-scrape scheduler."""
    if interval_hrs < 1 or interval_hrs > 168:
        raise HTTPException(status_code=400, detail="Interval must be 1–168 hours")

    if scheduler_state["enabled"] and scheduler_state["thread"] and scheduler_state["thread"].is_alive():
        raise HTTPException(status_code=409, detail="Scheduler is already running")

    stop_event = _threading.Event()
    thread = _threading.Thread(
        target=_scheduler_loop,
        args=(stop_event, interval_hrs),
        daemon=True
    )
    thread.start()

    scheduler_state["enabled"]      = True
    scheduler_state["interval_hrs"] = interval_hrs
    scheduler_state["stop_event"]   = stop_event
    scheduler_state["thread"]       = thread
    scheduler_state["next_run"]     = datetime.fromtimestamp(
        datetime.now().timestamp() + interval_hrs * 3600
    ).isoformat()

    return {
        "success":      True,
        "message":      f"Scheduler started — runs every {interval_hrs}h",
        "interval_hrs": interval_hrs,
        "next_run":     scheduler_state["next_run"],
    }


@app.post("/api/scheduler/stop")
def stop_scheduler():
    """Stop the auto-scrape scheduler."""
    if not scheduler_state["enabled"]:
        return {"success": True, "message": "Scheduler was not running"}

    if scheduler_state["stop_event"]:
        scheduler_state["stop_event"].set()

    scheduler_state["enabled"]  = False
    scheduler_state["next_run"] = None

    return {"success": True, "message": "Scheduler stopped"}


@app.get("/api/scheduler/status")
def get_scheduler_status():
    """Get scheduler status."""
    alive = (
        scheduler_state["thread"] is not None and
        scheduler_state["thread"].is_alive()
    )
    return {
        "success":      True,
        "enabled":      scheduler_state["enabled"] and alive,
        "interval_hrs": scheduler_state["interval_hrs"],
        "last_run":     scheduler_state["last_run"],
        "next_run":     scheduler_state["next_run"],
        "runs_total":   scheduler_state["runs_total"],
    }


@app.put("/api/scheduler/interval")
def update_interval(interval_hrs: int = 24):
    """Update scheduler interval (restarts scheduler)."""
    if scheduler_state["enabled"]:
        stop_scheduler()
        import time as t; t.sleep(1)
        return start_scheduler(interval_hrs)
    return {"success": True, "message": "Scheduler not running — start it with new interval"}