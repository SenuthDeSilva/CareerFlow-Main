"""
models.py
=========
SQLAlchemy ORM models for the Job Recommendation System.
Maps Python classes to PostgreSQL tables.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from database.db_config import Base


class Job(Base):
    """
    ORM model for the 'jobs' table.
    Represents a single job listing scraped from any source.
    """
    __tablename__ = "jobs"

    id           = Column(Integer,     primary_key=True, index=True)
    job_uuid     = Column(String(36),  unique=True, nullable=False)
    title        = Column(String(255), nullable=False, index=True)
    company      = Column(String(255))
    description  = Column(Text)
    location     = Column(String(255), index=True)
    salary       = Column(String(100))
    job_type     = Column(String(50))
    posted_date  = Column(String(50))
    closing_date = Column(String(50))
    job_url      = Column(Text,        unique=True)
    source       = Column(String(50),  nullable=False, index=True)
    scraped_at   = Column(DateTime,    server_default=func.now())

    def __repr__(self):
        return f"<Job id={self.id} title='{self.title}' company='{self.company}' source='{self.source}'>"

    def to_dict(self) -> dict:
        """Convert Job ORM object to plain dictionary."""
        return {
            "id":           self.id,
            "job_uuid":     self.job_uuid,
            "title":        self.title,
            "company":      self.company,
            "description":  self.description,
            "location":     self.location,
            "salary":       self.salary,
            "job_type":     self.job_type,
            "posted_date":  self.posted_date,
            "closing_date": self.closing_date,
            "job_url":      self.job_url,
            "source":       self.source,
            "scraped_at":   str(self.scraped_at) if self.scraped_at else None,
        }


class ScrapeLog(Base):
    """
    ORM model for the 'scrape_logs' table.
    Tracks every scraping run for monitoring.
    """
    __tablename__ = "scrape_logs"

    id            = Column(Integer,    primary_key=True, index=True)
    source        = Column(String(50), nullable=False)
    started_at    = Column(DateTime,   server_default=func.now())
    finished_at   = Column(DateTime)
    jobs_added    = Column(Integer,    default=0)
    jobs_skipped  = Column(Integer,    default=0)
    status        = Column(String(20), default="running")  # running | success | failed
    error_message = Column(Text)

    def __repr__(self):
        return f"<ScrapeLog id={self.id} source='{self.source}' status='{self.status}'>"