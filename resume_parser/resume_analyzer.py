"""
resume_analyzer.py
==================
Main entry point for Phase 3 — Resume Parser.
Combines parser + preprocessor + skill_extractor,
then saves results to both PostgreSQL and JSON.

Usage:
    python resume_analyzer.py --file path/to/resume.pdf
    python resume_analyzer.py --file path/to/resume.docx
    python resume_analyzer.py --file path/to/resume.txt
    python resume_analyzer.py --file resume.pdf --no-db    # JSON only
"""

import os
import sys
import json
import argparse
import uuid
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from resume_parser.parser          import extract_text
from resume_parser.preprocessor    import preprocess
from resume_parser.skill_extractor import extract_skills

# ── Output config ─────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR  = os.path.join(BASE_DIR, "resume_parser", "output")


def save_to_json(resume_data: dict) -> str:
    """Save extracted resume data to a JSON file."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    filename  = f"resume_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath  = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(resume_data, f, indent=2, ensure_ascii=False)

    print(f"✓  Saved to JSON : {filepath}")
    return filepath


def save_to_db(resume_data: dict):
    """Save extracted resume data to PostgreSQL. Returns inserted row ID or None."""
    try:
        from database.db_config import SessionLocal, engine, text

        # Create resumes table if not exists
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS resumes (
            id              SERIAL PRIMARY KEY,
            resume_uuid     VARCHAR(36)  UNIQUE NOT NULL,
            candidate_name  VARCHAR(255),
            email           VARCHAR(255),
            phone           VARCHAR(100),
            years_experience INTEGER     DEFAULT 0,
            hard_skills     TEXT,
            soft_skills     TEXT,
            all_skills      TEXT,
            skills_count    INTEGER      DEFAULT 0,
            raw_text        TEXT,
            file_name       VARCHAR(255),
            predicted_role  VARCHAR(100),
            role_confidence FLOAT        DEFAULT 0,
            uploaded_at     TIMESTAMP    DEFAULT NOW()
        )
        """
        with engine.connect() as conn:
            conn.execute(text(create_table_sql))
            # Add predicted_role columns to existing tables (migration)
            for col, definition in [
                ("predicted_role",  "VARCHAR(100)"),
                ("role_confidence", "FLOAT DEFAULT 0"),
            ]:
                try:
                    conn.execute(text(
                        f"ALTER TABLE resumes ADD COLUMN IF NOT EXISTS {col} {definition}"
                    ))
                except Exception:
                    pass
            conn.commit()

        # Predict career role if model is available
        predicted_role  = None
        role_confidence = 0.0
        try:
            from ml_model.role_predictor import predict_role, is_model_available
            if is_model_available():
                role_result     = predict_role(resume_data.get("raw_text", ""), top_n=3)
                predicted_role  = role_result["predicted_role"]
                role_confidence = role_result["confidence"]
                print(f"✓  Predicted Role  : {predicted_role} ({role_confidence}%)")
        except Exception as re:
            print(f"⚠  Role prediction skipped: {re}")

        resume_data["predicted_role"]  = predicted_role
        resume_data["role_confidence"] = role_confidence

        # Insert resume data
        db = SessionLocal()
        try:
            # Use RETURNING id to get inserted row id
            insert_sql = text("""
                INSERT INTO resumes (
                    resume_uuid, candidate_name, email, phone,
                    years_experience, hard_skills, soft_skills,
                    all_skills, skills_count, raw_text, file_name,
                    predicted_role, role_confidence
                ) VALUES (
                    :resume_uuid, :candidate_name, :email, :phone,
                    :years_experience, :hard_skills, :soft_skills,
                    :all_skills, :skills_count, :raw_text, :file_name,
                    :predicted_role, :role_confidence
                )
                ON CONFLICT (resume_uuid) DO UPDATE SET
                    candidate_name   = EXCLUDED.candidate_name,
                    skills_count     = EXCLUDED.skills_count,
                    hard_skills      = EXCLUDED.hard_skills,
                    soft_skills      = EXCLUDED.soft_skills,
                    all_skills       = EXCLUDED.all_skills,
                    years_experience = EXCLUDED.years_experience,
                    predicted_role   = EXCLUDED.predicted_role,
                    role_confidence  = EXCLUDED.role_confidence
                RETURNING id
            """)

            result = db.execute(insert_sql, {
                "resume_uuid":      resume_data["resume_uuid"],
                "candidate_name":   resume_data["name"],
                "email":            resume_data["email"],
                "phone":            resume_data["phone"],
                "years_experience": resume_data["years_experience"],
                "hard_skills":      json.dumps(resume_data["hard_skills"]),
                "soft_skills":      json.dumps(resume_data["soft_skills"]),
                "all_skills":       json.dumps(resume_data["all_skills"]),
                "skills_count":     resume_data["skills_count"],
                "raw_text":         resume_data["raw_text"][:10000],
                "file_name":        resume_data["file_name"],
                "predicted_role":   predicted_role,
                "role_confidence":  role_confidence,
            })
            db.commit()

            row = result.fetchone()
            inserted_id = row[0] if row else None
            print(f"✓  Saved to PostgreSQL (resumes table) — ID: {inserted_id}")
            return inserted_id

        finally:
            db.close()

    except Exception as e:
        print(f"⚠  DB save failed: {e}")
        import traceback; traceback.print_exc()
        return None


def analyze_resume(filepath: str, save_db: bool = True) -> dict:
    """
    Full resume analysis pipeline:
    1. Extract text (PDF / DOCX / TXT)
    2. Preprocess & clean
    3. Extract skills (keyword + spaCy NER)
    4. Save to JSON + PostgreSQL

    Args:
        filepath (str) : Path to resume file
        save_db  (bool): Whether to save to PostgreSQL

    Returns:
        dict: Complete resume analysis result
    """
    print("\n" + "="*55)
    print("📄  Resume Analysis Pipeline — Phase 3")
    print("="*55)

    # ── Step 1: Extract raw text ──────────────────────────────
    raw_text = extract_text(filepath)
    if not raw_text:
        print("✗  Could not extract text from resume.")
        return {}

    # ── Step 2: Preprocess ────────────────────────────────────
    processed = preprocess(raw_text)

    # ── Step 3: Extract skills ────────────────────────────────
    skills = extract_skills(
        text=processed["raw_text"],
        sections=processed["sections"]
    )

    # ── Step 4: Build final result ────────────────────────────
    resume_data = {
        "resume_uuid":      str(uuid.uuid4()),
        "file_name":        os.path.basename(filepath),
        "file_path":        filepath,
        "analyzed_at":      datetime.now().isoformat(),

        # Candidate Info
        "name":             processed["name"],
        "candidate_name":   processed["name"],
        "email":            processed["email"],
        "phone":            processed["phone"],
        "years_experience": processed["years_experience"],

        # Skills
        "hard_skills":      skills["hard_skills"],
        "soft_skills":      skills["soft_skills"],
        "all_skills":       skills["all_skills"],
        "skills_count":     skills["skills_count"],

        # Text
        "raw_text":         processed["raw_text"],
        "sections":         processed["sections"],
    }

    # ── Step 5: Save results ──────────────────────────────────
    print("\n💾  Saving results...")

    # Always save to JSON
    json_path = save_to_json(resume_data)

    # Save to DB if requested — capture returned ID
    if save_db:
        db_id = save_to_db(resume_data)
        resume_data["db_id"] = db_id  # api.py uses this
    else:
        resume_data["db_id"] = None

    # ── Final Summary ─────────────────────────────────────────
    print(f"\n{'='*55}")
    print(f"✅  Resume Analysis Complete!")
    print(f"{'='*55}")
    print(f"   Candidate     : {resume_data['name'] or 'Unknown'}")
    print(f"   Email         : {resume_data['email'] or 'Not found'}")
    print(f"   Experience    : {resume_data['years_experience']} years")
    print(f"   Skills Found  : {resume_data['skills_count']}")
    print(f"   Hard Skills   : {len(resume_data['hard_skills'])}")
    print(f"   Soft Skills   : {len(resume_data['soft_skills'])}")
    print(f"   Predicted Role: {resume_data.get('predicted_role') or 'Not available'}")
    print(f"   JSON Output   : {json_path}")
    print(f"{'='*55}\n")

    return resume_data


# ── CLI Entry Point ───────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Resume Parser — Phase 3"
    )
    parser.add_argument(
        "--file", type=str, required=True,
        help="Path to resume file (PDF / DOCX / TXT)"
    )
    parser.add_argument(
        "--no-db", action="store_true",
        help="Skip PostgreSQL save (JSON only)"
    )
    args = parser.parse_args()

    result = analyze_resume(
        filepath=args.file,
        save_db=not args.no_db
    )

    if result:
        print("Hard Skills:", result["hard_skills"])
        print("Soft Skills:", result["soft_skills"])