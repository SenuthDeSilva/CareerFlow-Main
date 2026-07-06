"""
unified_schema.py
=================
Normalizes scraped data from both Rooster.jobs and TopJobs.lk
into a single unified JSON format.

Unified Fields:
    - id            : Auto-generated unique ID
    - title         : Job title
    - company       : Company name
    - description   : Full job description
    - location      : Job location / town
    - salary        : Salary range (nullable)
    - job_type      : Full-time / Part-time / Contract
    - posted_date   : Date job was posted
    - closing_date  : Application closing date
    - job_url       : Original job listing URL
    - source        : "rooster" | "topjobs"
    - scraped_at    : When record was scraped (ISO timestamp)
"""

import re
import uuid
from datetime import datetime


def normalize_rooster(job: dict) -> dict:
    """
    Normalize a single Rooster.jobs scraped record
    into the unified schema.

    Args:
        job (dict): Raw scraped job dict from ScrapingRooster.py

    Returns:
        dict: Unified job record
    """
    return {
        "id":           str(uuid.uuid4()),
        "title":        _clean(job.get("Job_Title", "")),
        "company":      _clean(job.get("Company", "")),
        "description":  _clean(job.get("Job_Description", "")),
        "location":     _clean(job.get("Location", "")),
        "salary":       _clean(job.get("Salary", "")),
        "job_type":     _clean(job.get("Job_Type", "")),
        "posted_date":  _clean(job.get("Posted_Date", "")),
        "closing_date": "",   # Rooster does not provide closing date
        "job_url":      _clean(job.get("Job_URL", "")),
        "source":       "rooster",
        "scraped_at":   datetime.now().isoformat(),
    }


def normalize_topjobs(job: dict) -> dict:
    """
    Normalize a single TopJobs.lk scraped record
    into the unified schema.

    Args:
        job (dict): Raw scraped job dict from ScrapingTOPJobs.py

    Returns:
        dict: Unified job record
    """
    # Build job_url from Job_Code or Job_Ref_No since TopJobs CSV has no URL
    job_code = _clean(job.get("Job_Code", "")) or _clean(job.get("Job_Ref_No", ""))
    if job_code:
        job_url = f"https://www.topjobs.lk/applicant/JobAdvertisment.jsp?JC={job_code}"
    else:
        # Fallback: build unique url from title + company
        title   = _clean(job.get("Position", "")).replace(" ", "-").lower()
        company = _clean(job.get("Employer", "")).replace(" ", "-").lower()
        job_url = f"https://www.topjobs.lk/job/{title}-{company}-{str(uuid.uuid4())[:8]}"

    return {
        "id":           str(uuid.uuid4()),
        "title":        _clean(job.get("Position", "")),
        "company":      _clean(job.get("Employer", "")),
        "description":  _clean(job.get("Job_Description", "")),
        "location":     _clean(job.get("Town", "")),
        "salary":       "",
        "job_type":     "",
        "posted_date":  _clean(job.get("Opening_Date", "")),
        "closing_date": _clean(job.get("Closing_Date", "")),
        "job_url":      job_url,
        "source":       "topjobs",
        "scraped_at":   datetime.now().isoformat(),
    }


def normalize_batch(jobs: list, source: str) -> list:
    """
    Normalize a list of scraped jobs from a given source.

    Args:
        jobs   (list): List of raw job dicts
        source (str) : "rooster" or "topjobs"

    Returns:
        list: List of unified job dicts
    """
    normalized = []

    for job in jobs:
        try:
            if source == "rooster":
                normalized.append(normalize_rooster(job))
            elif source == "topjobs":
                normalized.append(normalize_topjobs(job))
            else:
                print(f"⚠  Unknown source: {source}")
        except Exception as e:
            print(f"✗  Error normalizing job: {e}")
            continue

    print(f"✓  Normalized {len(normalized)} jobs from '{source}'")
    return normalized


_WIN1252 = {
    '\x80': '€', '\x82': '‚', '\x83': 'ƒ', '\x84': '„', '\x85': '…',
    '\x86': '†', '\x87': '‡', '\x88': 'ˆ', '\x89': '‰', '\x8a': 'Š',
    '\x8b': '‹', '\x8c': 'Œ', '\x8e': 'Ž', '\x91': '‘',
    '\x92': '’', '\x93': '“', '\x94': '”', '\x95': '•',
    '\x96': '–', '\x97': '—', '\x98': '˜', '\x99': '™',
    '\x9a': 'š', '\x9b': '›', '\x9c': 'œ', '\x9e': 'ž', '\x9f': 'Ÿ',
}


def _clean(value: str) -> str:
    """Strip, clean, and repair common encoding artifacts in a string."""
    if not value:
        return ""
    s = str(value).strip()

    # Repair Windows-1252 control-range code points stored in Unicode
    s = s.translate(str.maketrans(_WIN1252))

    # Attempt latin-1 → utf-8 reinterpretation for â€" style artifacts
    try:
        s = s.encode('latin-1').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass

    # Replace Unicode replacement character with em-dash (common separator artifact)
    s = s.replace('�', '–')

    return s