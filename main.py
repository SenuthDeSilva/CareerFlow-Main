"""
main.py — Full System Launcher
================================
Single command to start the entire Job Recommendation System.

Usage:
    python main.py                  → Start backend only (React on port 3000)
    python main.py --init-db        → Initialize database only
    python main.py --scrape         → Run scrapers only
    python main.py --process-only   → Process existing scraped files
    python main.py --summary        → Show database summary
    python main.py --search python  → Search jobs in database
    python main.py --backend-only   → Start backend API only
    python main.py --full           → Scrape + Process + Start backend
"""

import os
import sys
import time
import argparse
import subprocess
import threading
import webbrowser
from datetime import datetime

# ── Path setup ──────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# ── Colors for terminal ──────────────────────────────────────────
class C:
    BLUE   = '\033[94m'
    GREEN  = '\033[92m'
    YELLOW = '\033[93m'
    RED    = '\033[91m'
    CYAN   = '\033[96m'
    WHITE  = '\033[97m'
    BOLD   = '\033[1m'
    RESET  = '\033[0m'

def banner():
    print(f"""
{C.BLUE}{C.BOLD}
╔══════════════════════════════════════════════════════════════╗
║           🎯  JOB RECOMMENDATION SYSTEM  v1.0               ║
║              Powered by ML + XAI + FastAPI                  ║
╚══════════════════════════════════════════════════════════════╝
{C.RESET}""")

def log(msg, level="INFO"):
    icons = {
        "INFO":  f"{C.CYAN}ℹ",
        "OK":    f"{C.GREEN}✅",
        "WARN":  f"{C.YELLOW}⚠",
        "ERROR": f"{C.RED}✗",
        "STEP":  f"{C.BLUE}▶",
    }
    icon = icons.get(level, "•")
    ts   = datetime.now().strftime("%H:%M:%S")
    print(f"  {icon}  {C.WHITE}[{ts}]{C.RESET} {msg}")

def separator(title=""):
    if title:
        print(f"\n{C.BLUE}{'─'*20} {C.BOLD}{title}{C.RESET}{C.BLUE} {'─'*20}{C.RESET}\n")
    else:
        print(f"\n{C.BLUE}{'─'*60}{C.RESET}\n")


# ────────────────────────────────────────────────────────────────
# Database
# ────────────────────────────────────────────────────────────────

def init_database():
    separator("Database Initialization")
    try:
        from database.db_config import init_db, test_connection
        log("Testing PostgreSQL connection...")
        if test_connection():
            log("PostgreSQL connected ✓", "OK")
        log("Initializing tables...")
        init_db()
        log("Database tables ready ✓", "OK")
        return True
    except Exception as e:
        log(f"Database error: {e}", "ERROR")
        log("Check your .env file — DB_PASSWORD must be set", "WARN")
        return False


def show_summary():
    separator("Database Summary")
    try:
        from database.db_insert import get_db_summary
        summary = get_db_summary()
        print(f"\n{'='*55}")
        print(f"📊  Database Summary")
        print(f"{'='*55}")
        print(f"    {'Total Jobs':<20} : {C.BOLD}{summary.get('total_jobs', 0)}{C.RESET}")
        print(f"    {'Rooster':<20} : {summary.get('rooster_jobs', 0)}")
        print(f"    {'TopJobs':<20} : {summary.get('topjobs_jobs', 0)}")
        print(f"    {'Last Scraped':<20} : {summary.get('last_scraped', 'Never')}")
        print(f"{'='*55}\n")
        print(f"  {'─'*40}")
        print(f"  {'Total Jobs':<25} {summary.get('total_jobs', 0)}")
        print(f"  {'Rooster Jobs':<25} {summary.get('rooster_jobs', 0)}")
        print(f"  {'TopJobs Jobs':<25} {summary.get('topjobs_jobs', 0)}")
        print(f"  {'Total Resumes':<25} {summary.get('total_resumes', 0)}")
        print(f"  {'Last Scraped':<25} {summary.get('last_scraped', 'Never')}")
        print(f"  {'─'*40}\n")
    except Exception as e:
        log(f"Could not load summary: {e}", "ERROR")


def search_jobs(query):
    separator(f"Search: '{query}'")
    try:
        from database.db_insert import search_jobs as db_search
        results = db_search(query)
        if not results:
            log("No jobs found.", "WARN")
            return
        for i, job in enumerate(results[:10], 1):
            print(f"  [{i}] {C.BOLD}{job.get('title','')}{C.RESET}")
            print(f"       {job.get('company','')} | {job.get('location','')}")
            print(f"       Source: {job.get('source','')} | Salary: {job.get('salary','N/A')}\n")
    except Exception as e:
        log(f"Search error: {e}", "ERROR")


# ────────────────────────────────────────────────────────────────
# Scraping
# ────────────────────────────────────────────────────────────────

def run_scrapers():
    separator("Web Scraping")

    for name, script_name in [("Rooster.jobs", "ScrapingRooster.py"), ("TopJobs.lk", "ScrapingTOPJobs.py")]:
        log(f"Starting {name} scraper...")
        try:
            script = os.path.join(BASE_DIR, "scraping", script_name)
            if os.path.exists(script):
                proc = subprocess.run(
                    [sys.executable, script],
                    capture_output=True, text=True, timeout=300
                )
                if proc.returncode == 0:
                    log(f"{name} scraping complete ✓", "OK")
                else:
                    log(f"{name} scraper error: {proc.stderr[:200]}", "WARN")
            else:
                log(f"{script_name} not found — skipping", "WARN")
        except subprocess.TimeoutExpired:
            log(f"{name} scraper timed out", "WARN")
        except Exception as e:
            log(f"{name} error: {e}", "WARN")


# ────────────────────────────────────────────────────────────────
# Pipeline
# ────────────────────────────────────────────────────────────────

def run_pipeline():
    separator("Data Pipeline")
    try:
        from pipeline.unified_schema import normalize_batch
        from database.db_insert import batch_insert_jobs, get_db_summary

        log("Loading scraped data...")
        all_jobs = []

        file_map = {
            "rooster": [
                os.path.join(BASE_DIR, "scraping", "RoosterJob.txt"),
                os.path.join(BASE_DIR, "scraping", "rooster_jobs.json"),
            ],
            "topjobs": [
                os.path.join(BASE_DIR, "scraping", "TopJobs.txt"),
                os.path.join(BASE_DIR, "scraping", "topjobs_jobs.json"),
            ],
        }

        for source, paths in file_map.items():
            for fpath in paths:
                if os.path.exists(fpath):
                    try:
                        jobs = normalize_batch(fpath, source=source)
                        all_jobs.extend(jobs)
                        log(f"Loaded {len(jobs)} {source} jobs from {os.path.basename(fpath)}", "OK")
                        break
                    except Exception as e:
                        log(f"Could not load {fpath}: {e}", "WARN")

        if not all_jobs:
            log("No job data found to process", "WARN")
            return False

        log(f"Inserting {len(all_jobs)} jobs into database...")
        inserted = batch_insert_jobs(all_jobs)
        log(f"Pipeline complete — {inserted} jobs saved ✓", "OK")

        summary = get_db_summary()
        log(f"Database total: {summary.get('total_jobs', 0)} jobs", "INFO")
        return True

    except Exception as e:
        log(f"Pipeline error: {e}", "ERROR")
        return False


# ────────────────────────────────────────────────────────────────
# Backend Server
# ────────────────────────────────────────────────────────────────

def check_uvicorn():
    try:
        import uvicorn
        return True
    except ImportError:
        return False


def start_backend(port=8000, open_browser=True):
    separator("Starting Backend API")

    if not check_uvicorn():
        log("uvicorn not found. Installing...", "WARN")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "uvicorn", "fastapi", "python-multipart"],
            check=True
        )

    log(f"Starting FastAPI server on port {port}...")
    log(f"API docs     → http://localhost:{port}/docs", "INFO")
    log(f"React App    → http://localhost:3000", "INFO")
    log(f"Press Ctrl+C to stop the server\n", "WARN")

    # Open React app in browser after short delay
    if open_browser:
        def open_browser_delayed():
            time.sleep(2)
            webbrowser.open("http://localhost:3000")
            log("Browser opened → http://localhost:3000 (React App)", "OK")

        t = threading.Thread(target=open_browser_delayed, daemon=True)
        t.start()

    # Start uvicorn
    try:
        import uvicorn
        from api import app
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            reload=False,
            log_level="warning",
        )
    except KeyboardInterrupt:
        print(f"\n{C.YELLOW}  ⚠  Server stopped by user.{C.RESET}\n")
    except Exception as e:
        log(f"Server error: {e}", "ERROR")


# ────────────────────────────────────────────────────────────────
# Main Entry Point
# ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Job Recommendation System — Full Stack Launcher",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
  python main.py                  Start backend API (React on port 3000)
  python main.py --init-db        Initialize database
  python main.py --scrape         Run scrapers only
  python main.py --full           Scrape + process + start server
  python main.py --backend-only   Start API server only
  python main.py --summary        Show database stats
  python main.py --search python  Search jobs
        """
    )
    parser.add_argument("--init-db",      action="store_true", help="Initialize database tables")
    parser.add_argument("--scrape",       action="store_true", help="Run web scrapers")
    parser.add_argument("--process-only", action="store_true", help="Process scraped files into DB")
    parser.add_argument("--full",         action="store_true", help="Scrape + process + start server")
    parser.add_argument("--backend-only", action="store_true", help="Start backend API only")
    parser.add_argument("--summary",      action="store_true", help="Show database summary")
    parser.add_argument("--search",       type=str,            help="Search jobs by keyword")
    parser.add_argument("--port",         type=int, default=8000, help="Backend port (default: 8000)")
    parser.add_argument("--no-browser",   action="store_true", help="Don't open browser automatically")

    args = parser.parse_args()
    banner()

    if args.init_db:
        init_database()
        return

    if args.summary:
        show_summary()
        return

    if args.search:
        search_jobs(args.search)
        return

    if args.scrape:
        if not init_database(): return
        run_scrapers()
        run_pipeline()
        show_summary()
        return

    if args.process_only:
        if not init_database(): return
        run_pipeline()
        show_summary()
        return

    if args.backend_only:
        if not init_database(): return
        start_backend(port=args.port, open_browser=not args.no_browser)
        return

    if args.full:
        if not init_database(): return
        run_scrapers()
        run_pipeline()
        show_summary()
        start_backend(port=args.port, open_browser=not args.no_browser)
        return

    # ── DEFAULT: python main.py ──────────────────────────────────
    separator("System Startup")
    log("Mode: Default — Starting backend API", "STEP")

    if not init_database():
        log("Fix database connection and retry.", "ERROR")
        sys.exit(1)

    show_summary()
    start_backend(port=args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()