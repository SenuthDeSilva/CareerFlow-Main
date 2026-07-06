-- ============================================================
-- Job Recommendation System — PostgreSQL Schema
-- Phase 2: Database Setup
-- ============================================================

-- Create database (run this separately as superuser if needed)
-- CREATE DATABASE job_recommendation_db;

-- ── Jobs Table ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS jobs (
    id              SERIAL PRIMARY KEY,
    job_uuid        VARCHAR(36)     UNIQUE NOT NULL,     -- UUID for deduplication
    title           VARCHAR(255)    NOT NULL,
    company         VARCHAR(255),
    description     TEXT,
    location        VARCHAR(255),
    salary          VARCHAR(100),
    job_type        VARCHAR(50),
    posted_date     VARCHAR(50),
    closing_date    VARCHAR(50),
    job_url         TEXT            UNIQUE,              -- Prevent duplicate jobs
    source          VARCHAR(50)     NOT NULL,            -- 'rooster' | 'topjobs'
    scraped_at      TIMESTAMP       DEFAULT NOW()
);

-- ── Indexes for fast queries ──────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_jobs_source      ON jobs(source);
CREATE INDEX IF NOT EXISTS idx_jobs_title       ON jobs(title);
CREATE INDEX IF NOT EXISTS idx_jobs_location    ON jobs(location);
CREATE INDEX IF NOT EXISTS idx_jobs_scraped_at  ON jobs(scraped_at);

-- ── Scrape Log Table (track every scraping run) ───────────────
CREATE TABLE IF NOT EXISTS scrape_logs (
    id              SERIAL PRIMARY KEY,
    source          VARCHAR(50)     NOT NULL,
    started_at      TIMESTAMP       DEFAULT NOW(),
    finished_at     TIMESTAMP,
    jobs_added      INTEGER         DEFAULT 0,
    jobs_skipped    INTEGER         DEFAULT 0,
    status          VARCHAR(20)     DEFAULT 'running',   -- 'running' | 'success' | 'failed'
    error_message   TEXT
);

-- ============================================================
-- Useful Queries
-- ============================================================

-- View all jobs:
-- SELECT id, title, company, location, source, scraped_at FROM jobs ORDER BY scraped_at DESC;

-- Count jobs per source:
-- SELECT source, COUNT(*) FROM jobs GROUP BY source;

-- Search jobs by keyword:
-- SELECT * FROM jobs WHERE title ILIKE '%python%' OR description ILIKE '%python%';

-- Get latest scrape logs:
-- SELECT * FROM scrape_logs ORDER BY started_at DESC LIMIT 10;