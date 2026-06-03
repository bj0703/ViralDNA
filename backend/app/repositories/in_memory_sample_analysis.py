from __future__ import annotations

from typing import Dict, Optional

from backend.app.models.sample_analysis import SessionJob, utc_now_iso


class InMemorySampleAnalysisRepository:
    """A lightweight repository for local development and demos."""

    def __init__(self) -> None:
        self._jobs: Dict[str, SessionJob] = {}

    def save(self, job: SessionJob) -> SessionJob:
        job.updated_at = utc_now_iso()
        self._jobs[job.job_id] = job
        return job

    def get(self, job_id: str) -> Optional[SessionJob]:
        return self._jobs.get(job_id)
