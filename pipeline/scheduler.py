"""
scheduler.py — PostgreSQL version
"""
import os, sys, csv, json, argparse
from datetime import datetime

try:
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.cron import CronTrigger
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.unified_schema import normalize_batch
from database.db_insert import insert_jobs_batch, get_db_summary
from database.db_config import test_connection, init_db

BASE_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRAPING_DIR = os.path.join(BASE_DIR, "scraping")
LOG_DIR      = os.path.join(BASE_DIR, "pipeline", "logs")
SCHEDULE_HOUR, SCHEDULE_MINUTE = 2, 0

def _log(msg):
    os.makedirs(LOG_DIR, exist_ok=True)
    ts  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{ts}]  {msg}"
    print(entry)
    try:
        with open(os.path.join(LOG_DIR, f"scrape_{datetime.now().strftime('%Y%m%d')}.log"), "a") as f:
            f.write(entry + "\n")
    except Exception:
        pass

def load_csv_as_jobs(fp):
    jobs = []
    try:
        with open(fp, "r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f): jobs.append(dict(row))
        print(f"✓  {len(jobs)} jobs from CSV: {os.path.basename(fp)}")
    except Exception as e:
        print(f"✗  CSV load error: {e}")
    return jobs

def load_json_as_jobs(fp):
    try:
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
        jobs = data if isinstance(data, list) else data.get("jobs", [])
        print(f"✓  {len(jobs)} jobs from JSON: {os.path.basename(fp)}")
        return jobs
    except Exception as e:
        print(f"✗  JSON load error: {e}")
        return []

def find_latest_scrape_file(source, ext="json"):
    prefix = {"rooster": "rooster_jobs_", "topjobs": "topjobs_data_"}.get(source, "")
    try:
        files = [os.path.join(SCRAPING_DIR, f) for f in os.listdir(SCRAPING_DIR)
                 if f.startswith(prefix) and f.endswith(f".{ext}")]
        return max(files, key=os.path.getmtime) if files else None
    except Exception:
        return None

def run_scraper(name):
    script_map = {"rooster": "ScrapingRooster.py", "topjobs": "ScrapingTOPJobs.py"}
    txt_map    = {"rooster": "RoosterJob.txt",      "topjobs": "TopJobs.txt"}
    script = os.path.join(SCRAPING_DIR, script_map[name])
    txt    = os.path.join(SCRAPING_DIR, txt_map[name])
    if not os.path.exists(script) or not os.path.exists(txt):
        _log(f"✗  {script_map[name]} or {txt_map[name]} not found")
        return False
    code = os.system(f"python \"{script}\"")
    _log(f"{'✓' if code==0 else '✗'}  {name} scraper {'done' if code==0 else 'failed'}")
    return code == 0

def process_and_save_to_db():
    _log("Processing scraped data → PostgreSQL...")
    all_norm = []
    for source in ["rooster", "topjobs"]:
        fp = find_latest_scrape_file(source, "json") or find_latest_scrape_file(source, "csv")
        if fp:
            _log(f"Found: {os.path.basename(fp)}")
            raw = load_json_as_jobs(fp) if fp.endswith(".json") else load_csv_as_jobs(fp)
            all_norm.extend(normalize_batch(raw, source))
        else:
            _log(f"⚠  No {source} output file found")
    if all_norm:
        result = insert_jobs_batch(all_norm, source="all")
        _log(f"✓  DB: {result['added']} new | {result['skipped']} duplicates")
        get_db_summary()
    else:
        _log("⚠  No jobs to insert")

def run_full_pipeline():
    _log("="*55)
    _log("🚀  Full Scraping Pipeline → PostgreSQL")
    _log("="*55)
    t = datetime.now()
    run_scraper("rooster")
    run_scraper("topjobs")
    process_and_save_to_db()
    _log(f"✅  Done in {(datetime.now()-t).seconds}s")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-now",      action="store_true")
    parser.add_argument("--once",         action="store_true")
    parser.add_argument("--process-only", action="store_true")
    args = parser.parse_args()

    if not test_connection():
        print("✗  Cannot connect to PostgreSQL. Check your .env file.")
        sys.exit(1)
    init_db()

    if args.once:         run_full_pipeline(); sys.exit(0)
    if args.process_only: process_and_save_to_db(); sys.exit(0)
    if not SCHEDULER_AVAILABLE:
        print("✗  Install apscheduler: pip install apscheduler"); sys.exit(1)

    scheduler = BlockingScheduler()
    if args.run_now:
        print("⚡  Running now before schedule..."); run_full_pipeline()
    scheduler.add_job(run_full_pipeline, CronTrigger(hour=SCHEDULE_HOUR, minute=SCHEDULE_MINUTE),
                      id="daily_scrape", misfire_grace_time=3600)
    print(f"\n⏰  Scheduler running — daily at {SCHEDULE_HOUR:02d}:{SCHEDULE_MINUTE:02d}  (Ctrl+C to stop)\n")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n⏹  Stopped.")