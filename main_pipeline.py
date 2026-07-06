"""
main_pipeline.py — PostgreSQL version
Usage:
    python main_pipeline.py --init-db        # Run FIRST time only
    python main_pipeline.py --process-only   # Process existing scrape files → DB
    python main_pipeline.py --full           # Scrape + Process + Save to DB
    python main_pipeline.py --summary        # DB summary
    python main_pipeline.py --search "python developer"
    python main_pipeline.py --file path.csv --source rooster
"""
import os, sys, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pipeline.unified_schema import normalize_batch
from pipeline.scheduler      import run_full_pipeline, process_and_save_to_db, load_csv_as_jobs, load_json_as_jobs
from database.db_config      import test_connection, init_db
from database.db_insert      import insert_jobs_batch, get_all_jobs, search_jobs, get_db_summary

def load_and_insert_file(filepath, source):
    if not os.path.exists(filepath):
        print(f"✗  File not found: {filepath}"); return
    ext  = os.path.splitext(filepath)[1].lower()
    raw  = load_json_as_jobs(filepath) if ext == ".json" else load_csv_as_jobs(filepath)
    if not raw: print("✗  No jobs found."); return
    insert_jobs_batch(normalize_batch(raw, source), source=source)

def show_sample_jobs(n=5):
    jobs = get_all_jobs()
    if not jobs: print("ℹ  No jobs in database."); return
    print(f"\n{'='*60}\n📋  Sample Jobs ({min(n,len(jobs))} of {len(jobs)} total)\n{'='*60}")
    for i, job in enumerate(jobs[:n], 1):
        desc = job.get("description","")
        print(f"\n[{i}] {job.get('title')} @ {job.get('company')}  [{job.get('source')}]")
        print(f"    Location : {job.get('location')}  |  Salary: {job.get('salary')}")
        print(f"    Desc     : {desc[:100]}..." if len(desc)>100 else f"    Desc     : {desc}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Job Recommendation System — Phase 2 (PostgreSQL)")
    parser.add_argument("--init-db",      action="store_true")
    parser.add_argument("--full",         action="store_true")
    parser.add_argument("--process-only", action="store_true")
    parser.add_argument("--summary",      action="store_true")
    parser.add_argument("--sample",       action="store_true")
    parser.add_argument("--search",       type=str)
    parser.add_argument("--file",         type=str)
    parser.add_argument("--source",       type=str, choices=["rooster","topjobs"])
    args = parser.parse_args()

    print("\n" + "="*60)
    print("  🤖  Job Recommendation System — Phase 2 (PostgreSQL)")
    print("="*60 + "\n")

    if not test_connection():
        print("\n✗  Cannot connect to PostgreSQL.\n   1. Make sure PostgreSQL is running\n   2. Check .env credentials\n   3. Run: createdb job_recommendation_db")
        sys.exit(1)

    if   args.init_db:      init_db()
    elif args.full:         run_full_pipeline()
    elif args.process_only: process_and_save_to_db()
    elif args.file:
        if not args.source: print("✗  Specify --source")
        else: load_and_insert_file(args.file, args.source)
    elif args.summary:      get_db_summary()
    elif args.sample:       show_sample_jobs()
    elif args.search:
        r = search_jobs(args.search)
        print(f"\n🔍  '{args.search}'  →  {len(r)} results\n")
        for i,j in enumerate(r[:10],1): print(f"  [{i}] {j.get('title')} @ {j.get('company')} ({j.get('source')})")
    else:
        parser.print_help()
        print("\n💡  Quick start:\n    python main_pipeline.py --init-db\n    python main_pipeline.py --process-only\n    python main_pipeline.py --summary\n")