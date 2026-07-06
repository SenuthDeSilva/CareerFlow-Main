"""
db_config.py
============
PostgreSQL database connection configuration.
Reads credentials from .env file using python-dotenv.

Setup:
    1. Fill in your .env file with PostgreSQL credentials
    2. Run: pip install psycopg2-binary python-dotenv sqlalchemy
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

# ── Load .env file ────────────────────────────────────────────
load_dotenv()

# ── Database credentials from .env ───────────────────────────
DB_HOST     = os.getenv("DB_HOST",     "localhost")
DB_PORT     = os.getenv("DB_PORT",     "5432")
DB_NAME     = os.getenv("DB_NAME",     "job_recommendation_db")
DB_USER     = os.getenv("DB_USER",     "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")

# ── SQLAlchemy connection URL ─────────────────────────────────
DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ── SQLAlchemy Engine ─────────────────────────────────────────
engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    echo=False,
)

# ── Session Factory ───────────────────────────────────────────
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ── Base class for ORM models ─────────────────────────────────
Base = declarative_base()


def get_db():
    """Dependency for getting a DB session (used in FastAPI Phase 6)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_connection() -> bool:
    """Test the database connection."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✓  PostgreSQL connection successful!")
        print(f"   Host     : {DB_HOST}:{DB_PORT}")
        print(f"   Database : {DB_NAME}")
        print(f"   User     : {DB_USER}")
        return True
    except Exception as e:
        print(f"✗  PostgreSQL connection failed: {e}")
        print(f"\n   Check your .env file:")
        print(f"   DB_HOST={DB_HOST}")
        print(f"   DB_PORT={DB_PORT}")
        print(f"   DB_NAME={DB_NAME}")
        print(f"   DB_USER={DB_USER}")
        return False


def init_db():
    """
    Create all tables directly using SQLAlchemy.
    Run this once to initialize the database.
    """
    statements = [
        # ── Jobs table ────────────────────────────────────────
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id              SERIAL PRIMARY KEY,
            job_uuid        VARCHAR(36)  UNIQUE NOT NULL,
            title           VARCHAR(255) NOT NULL,
            company         VARCHAR(255),
            description     TEXT,
            location        VARCHAR(255),
            salary          VARCHAR(100),
            job_type        VARCHAR(50),
            posted_date     VARCHAR(50),
            closing_date    VARCHAR(50),
            job_url         TEXT         UNIQUE,
            source          VARCHAR(50)  NOT NULL,
            scraped_at      TIMESTAMP    DEFAULT NOW()
        )
        """,
        # ── Scrape logs table ─────────────────────────────────
        """
        CREATE TABLE IF NOT EXISTS scrape_logs (
            id              SERIAL PRIMARY KEY,
            source          VARCHAR(50)  NOT NULL,
            started_at      TIMESTAMP    DEFAULT NOW(),
            finished_at     TIMESTAMP,
            jobs_added      INTEGER      DEFAULT 0,
            jobs_skipped    INTEGER      DEFAULT 0,
            status          VARCHAR(20)  DEFAULT 'running',
            error_message   TEXT
        )
        """,
        # ── Indexes ───────────────────────────────────────────
        "CREATE INDEX IF NOT EXISTS idx_jobs_source     ON jobs(source)",
        "CREATE INDEX IF NOT EXISTS idx_jobs_title      ON jobs(title)",
        "CREATE INDEX IF NOT EXISTS idx_jobs_location   ON jobs(location)",
        "CREATE INDEX IF NOT EXISTS idx_jobs_scraped_at ON jobs(scraped_at)",
    ]

    try:
        with engine.connect() as conn:
            for stmt in statements:
                conn.execute(text(stmt))
            conn.commit()

        print("✓  Database tables initialized successfully!")
        return True

    except Exception as e:
        print(f"✗  Error initializing database: {e}")
        return False


# ── Run directly to test connection ──────────────────────────
if __name__ == "__main__":
    print("Testing database connection...")
    if test_connection():
        print("\nInitializing tables...")
        init_db()