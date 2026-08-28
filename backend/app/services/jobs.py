import uuid
import time
from enum import Enum
from typing import Dict, Any, Optional

class JobStatus(Enum):
    QUEUED = "queued"
    VALIDATING = "validating"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    SCRIPTING = "scripting"
    AUDIO = "audio"
    VISUALS = "visuals"
    SCENE_RENDER = "scene_render"
    FINAL_RENDER = "final_render"
    UPLOAD = "upload"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"

class JobState:
    def __init__(self, user_id: str, job_type: str, metadata: Dict[str, Any] = None):
        self.job_id = str(uuid.uuid4())
        self.user_id = user_id
        self.job_type = job_type
        self.status = JobStatus.QUEUED
        self.metadata = metadata or {}
        self.created_at = time.time()
        self.updated_at = time.time()
        self.error: Optional[str] = None
        self.result: Optional[Any] = None

    def update_status(self, status: JobStatus, error: str = None, result: Any = None):
        self.status = status
        self.updated_at = time.time()
        if error:
            self.error = error
        if result:
            self.result = result

    def to_dict(self):
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error": self.error,
            "result": self.result,
            "metadata": self.metadata
        }

# For now, use an in-memory dictionary. In production, this maps to a Redis Hash or PostgreSQL 'generation_jobs' table.
_jobs_db: Dict[str, JobState] = {}

def create_job(user_id: str, job_type: str, metadata: Dict[str, Any] = None) -> JobState:
    job = JobState(user_id, job_type, metadata)
    _jobs_db[job.job_id] = job
    return job

def get_job(job_id: str) -> Optional[JobState]:
    return _jobs_db.get(job_id)

def update_job(job_id: str, status: JobStatus, error: str = None, result: Any = None):
    job = get_job(job_id)
    if job:
        job.update_status(status, error, result)
        # In production: sync to DB/Redis here
        return job
    return None
