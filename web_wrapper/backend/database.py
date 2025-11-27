import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

DB_PATH = Path(os.getenv("DB_PATH", "jobs.db"))

def init_db():
    """Initialize the database with the jobs table."""
    with sqlite3.connect(DB_PATH, timeout=30.0) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT,
                session_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                config TEXT,
                output_path TEXT
            )
        """)
        conn.commit()

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = dict_factory
    try:
        yield conn
    finally:
        conn.close()

def create_job(job_id: str, filename: str, session_id: str, config: Dict[str, Any], status: str = "queued"):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO jobs (id, filename, status, session_id, config, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (job_id, filename, status, session_id, json.dumps(config), datetime.now())
        )
        conn.commit()

def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        job = cursor.fetchone()
        if job and job['config']:
            job['config'] = json.loads(job['config'])
        return job

def update_job_status(job_id: str, status: str, message: str = "", output_path: str = None):
    with get_db() as conn:
        updates = ["status = ?", "message = ?"]
        params = [status, message]
        
        if status == "completed":
            updates.append("completed_at = ?")
            params.append(datetime.now())
            
        if output_path:
            updates.append("output_path = ?")
            params.append(output_path)
            
        params.append(job_id)
        
        conn.execute(f"UPDATE jobs SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()

def get_jobs_by_session(session_id: str) -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM jobs WHERE session_id = ? ORDER BY created_at DESC", (session_id,))
        jobs = cursor.fetchall()
        for job in jobs:
            if job['config']:
                job['config'] = json.loads(job['config'])
        return jobs

def get_all_jobs() -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC")
        jobs = cursor.fetchall()
        for job in jobs:
            if job['config']:
                job['config'] = json.loads(job['config'])
        return jobs

def delete_job(job_id: str):
    with get_db() as conn:
        conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        conn.commit()

def get_old_completed_jobs(hours: int) -> List[Dict[str, Any]]:
    with get_db() as conn:
        # SQLite datetime function usage depends on how we stored it. 
        # We stored as python datetime object which sqlite adapter converts to string usually.
        # Let's use python to filter to be safe and DB agnostic for now, or use sqlite modifier.
        # 'completed_at' is stored as a string like '2023-10-27 10:00:00.123456'
        
        cursor = conn.execute(
            f"SELECT * FROM jobs WHERE status = 'completed' AND completed_at < datetime('now', '-{hours} hours')"
        )
        return cursor.fetchall()

def delete_all_jobs():
    with get_db() as conn:
        conn.execute("DELETE FROM jobs")
        conn.commit()
