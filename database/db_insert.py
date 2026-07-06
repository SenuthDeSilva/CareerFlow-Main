"""
db_insert.py
============
Handles all database insert operations for the Job Recommendation System.

Features:
    - Insert single or batch jobs into PostgreSQL
    - Deduplication by job_url (skips existing jobs)
    - Scrape log tracking (start / finish / error)
    - Bulk upsert support
    - Summary statistics after every batch insert

Usage:
    from database.db_insert import insert_jobs_batch

    jobs = [...]  # normalized unified schema dicts
    insert_jobs_batch(jobs)
"""

from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.postgresql import insert as pg_insert

from database.db_config import SessionLocal, engine
from database.models    import Job, ScrapeLog


# ─────────────────────────────────────────────────────────────
# Scrape Log Helpers
# ─────────────────────────────────────────────────────────────

def start_scrape_log(source: str) -> int:
    """
    Create a new scrape log entry with status 'running'.

    Args:
        source (str): 'rooster' or 'topjobs'

    Returns:
        int: The log entry ID (use to update later)
    """
    db = SessionLocal()
    try:
        log = ScrapeLog(source=source, status="running")
        db.add(log)
        db.commit()
        db.refresh(log)
        print(f"✓  Scrape log started  [id={log.id}  source={source}]")
        return log.id
    except Exception as e:
        db.rollback()
        print(f"⚠  Could not create scrape log: {e}")
        return -1
    finally:
        db.close()


def finish_scrape_log(log_id: int, added: int, skipped: int, status: str = "success", error: str = None):
    """
    Update a scrape log entry with final results.

    Args:
        log_id  (int): The log entry ID from start_scrape_log()
        added   (int): Number of new jobs inserted
        skipped (int): Number of duplicate jobs skipped
        status  (str): 'success' or 'failed'
        error   (str): Error message if failed
    """
    if log_id < 0:
        return

    db = SessionLocal()
    try:
        log = db.query(ScrapeLog).filter(ScrapeLog.id == log_id).first()
        if log:
            log.finished_at   = datetime.now()
            log.jobs_added    = added
            log.jobs_skipped  = skipped
            log.status        = status
            log.error_message = error
            db.commit()
            print(f"✓  Scrape log updated  [id={log_id}  status={status}  added={added}  skipped={skipped}]")
    except Exception as e:
        db.rollback()
        print(f"⚠  Could not update scrape log: {e}")
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────
# Job Insert Functions
# ─────────────────────────────────────────────────────────────

def insert_single_job(job: dict) -> bool:
    """
    Insert a single normalized job into the database.
    Skips if job_url already exists (deduplication).

    Args:
        job (dict): Unified schema job dict

    Returns:
        bool: True if inserted, False if duplicate or error
    """
    db = SessionLocal()
    try:
        new_job = Job(
            job_uuid     = job.get("id", ""),
            title        = job.get("title", ""),
            company      = job.get("company", ""),
            description  = job.get("description", ""),
            location     = job.get("location", ""),
            salary       = job.get("salary", ""),
            job_type     = job.get("job_type", ""),
            posted_date  = job.get("posted_date", ""),
            closing_date = job.get("closing_date", ""),
            job_url      = job.get("job_url", "") or None,
            source       = job.get("source", ""),
            scraped_at   = datetime.now(),
        )
        db.add(new_job)
        db.commit()
        return True

    except IntegrityError:
        db.rollback()
        return False   # Duplicate job_url — silently skip

    except Exception as e:
        db.rollback()
        print(f"✗  Error inserting job '{job.get('title')}': {e}")
        return False

    finally:
        db.close()


def insert_jobs_batch(jobs: list, source: str = "unknown") -> dict:
    """
    Insert a batch of normalized jobs into PostgreSQL.
    Uses individual inserts with IntegrityError catching for deduplication.

    Args:
        jobs   (list): List of unified schema job dicts
        source (str) : Source name for logging

    Returns:
        dict: { added, skipped, total, errors }
    """
    if not jobs:
        print("⚠  No jobs to insert.")
        return {"added": 0, "skipped": 0, "total": 0, "errors": 0}

    # Start scrape log
    log_id  = start_scrape_log(source)

    added   = 0
    skipped = 0
    errors  = 0
    total   = len(jobs)

    print(f"\n{'='*55}")
    print(f"📥  Inserting {total} jobs into PostgreSQL  [{source}]")
    print(f"{'='*55}")

    for i, job in enumerate(jobs, 1):
        result = insert_single_job(job)
        if result:
            added += 1
        else:
            skipped += 1

        # Progress indicator every 50 jobs
        if i % 50 == 0 or i == total:
            print(f"    Progress: {i}/{total}  |  Added: {added}  |  Skipped: {skipped}")

    # Print final summary
    print(f"\n{'='*55}")
    print(f"✅  Batch insert complete!")
    print(f"    ➕  New jobs added  : {added}")
    print(f"    ⏭   Duplicates skipped : {skipped}")
    print(f"    ⚠   Errors         : {errors}")
    print(f"    📊  Total processed : {total}")
    print(f"{'='*55}\n")

    # Update scrape log
    status = "success" if errors == 0 else "failed"
    finish_scrape_log(log_id, added, skipped, status)

    return {
        "added":   added,
        "skipped": skipped,
        "total":   total,
        "errors":  errors
    }


def insert_jobs_upsert(jobs: list) -> dict:
    """
    Insert jobs using PostgreSQL UPSERT (INSERT ... ON CONFLICT DO NOTHING).
    Faster than individual inserts for large batches.

    Args:
        jobs (list): List of unified schema job dicts

    Returns:
        dict: { inserted, total }
    """
    if not jobs:
        return {"inserted": 0, "total": 0}

    db = SessionLocal()
    try:
        records = [
            {
                "job_uuid":     job.get("id", ""),
                "title":        job.get("title", ""),
                "company":      job.get("company", ""),
                "description":  job.get("description", ""),
                "location":     job.get("location", ""),
                "salary":       job.get("salary", ""),
                "job_type":     job.get("job_type", ""),
                "posted_date":  job.get("posted_date", ""),
                "closing_date": job.get("closing_date", ""),
                "job_url":      job.get("job_url", "") or None,
                "source":       job.get("source", ""),
                "scraped_at":   datetime.now(),
            }
            for job in jobs
        ]

        stmt = pg_insert(Job).values(records)
        stmt = stmt.on_conflict_do_nothing(index_elements=["job_url"])

        result = db.execute(stmt)
        db.commit()

        inserted = result.rowcount
        skipped  = len(jobs) - inserted

        print(f"✅  UPSERT complete: {inserted} inserted, {skipped} skipped")
        return {"inserted": inserted, "total": len(jobs)}

    except Exception as e:
        db.rollback()
        print(f"✗  UPSERT error: {e}")
        return {"inserted": 0, "total": len(jobs)}

    finally:
        db.close()


# ─────────────────────────────────────────────────────────────
# Query Helpers
# ─────────────────────────────────────────────────────────────

def get_all_jobs() -> list:
    """Fetch all jobs from the database as list of dicts."""
    db = SessionLocal()
    try:
        jobs = db.query(Job).order_by(Job.scraped_at.desc()).all()
        return [j.to_dict() for j in jobs]
    except Exception as e:
        print(f"✗  Error fetching jobs: {e}")
        return []
    finally:
        db.close()


def get_jobs_by_source(source: str) -> list:
    """Fetch jobs filtered by source ('rooster' or 'topjobs')."""
    db = SessionLocal()
    try:
        jobs = db.query(Job).filter(Job.source == source).all()
        return [j.to_dict() for j in jobs]
    except Exception as e:
        print(f"✗  Error fetching jobs by source: {e}")
        return []
    finally:
        db.close()


def search_jobs(keyword: str) -> list:
    """Search jobs by keyword in title, company, or description."""
    db = SessionLocal()
    try:
        kw = f"%{keyword.lower()}%"
        jobs = db.query(Job).filter(
            Job.title.ilike(kw) |
            Job.company.ilike(kw) |
            Job.description.ilike(kw)
        ).all()
        return [j.to_dict() for j in jobs]
    except Exception as e:
        print(f"✗  Error searching jobs: {e}")
        return []
    finally:
        db.close()


def get_db_summary() -> dict:
    """Return a summary of database contents."""
    db = SessionLocal()
    try:
        total    = db.query(Job).count()
        rooster  = db.query(Job).filter(Job.source == "rooster").count()
        topjobs  = db.query(Job).filter(Job.source == "topjobs").count()
        latest   = db.query(Job).order_by(Job.scraped_at.desc()).first()

        summary = {
            "total_jobs":    total,
            "rooster_jobs":  rooster,
            "topjobs_jobs":  topjobs,
            "last_scraped":  str(latest.scraped_at) if latest else "N/A",
        }

        print(f"\n{'='*55}")
        print(f"📊  Database Summary")
        print(f"{'='*55}")
        print(f"    Total Jobs   : {total}")
        print(f"    Rooster      : {rooster}")
        print(f"    TopJobs      : {topjobs}")
        print(f"    Last Scraped : {summary['last_scraped']}")
        print(f"{'='*55}\n")

        return summary

    except Exception as e:
        print(f"✗  Error getting summary: {e}")
        return {}
    finally:
        db.close()