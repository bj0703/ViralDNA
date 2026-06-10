from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ScriptSection:
    label: str
    summary: str
    start_seconds: float
    end_seconds: float
    confidence: float
    status: str = "available"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PaceSegment:
    label: str
    start_seconds: float
    end_seconds: float
    pace: str
    shot_density_estimate: float
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SampleMetadata:
    filename: str
    original_filename: str
    content_type: Optional[str]
    file_size_bytes: int
    duration_seconds: float
    duration_is_estimated: bool
    preview_url: Optional[str]
    transcript_overview: Optional[str]
    storage_path: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SampleAnalysisResult:
    sample_id: str
    job_id: str
    session_id: str
    status: str
    metadata: SampleMetadata
    script_structure: Dict[str, Any]
    pace_structure: Dict[str, Any]
    confidence: Dict[str, float]
    availability: Dict[str, str]
    provider_trace: Dict[str, Any]
    raw_outputs: Dict[str, Any]
    warnings: List[str] = field(default_factory=list)
    timeline_segments: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "job_id": self.job_id,
            "session_id": self.session_id,
            "status": self.status,
            "metadata": self.metadata.to_dict(),
            "script_structure": self.script_structure,
            "pace_structure": self.pace_structure,
            "confidence": self.confidence,
            "availability": self.availability,
            "provider_trace": self.provider_trace,
            "raw_outputs": self.raw_outputs,
            "warnings": self.warnings,
            "timeline_segments": self.timeline_segments,
        }


@dataclass
class SessionJob:
    job_id: str
    session_id: str
    session_name: Optional[str]
    status: str
    created_at: str
    updated_at: str
    completed_at: Optional[str]
    sample_results: List[SampleAnalysisResult]
    debug: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "session_id": self.session_id,
            "session_name": self.session_name,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "sample_results": [sample.to_dict() for sample in self.sample_results],
            "debug": self.debug,
        }


@dataclass
class SampleUpload:
    original_filename: str
    saved_filename: str
    storage_path: str
    content_type: Optional[str]
    notes: Optional[str] = None
    analysis_instruction: Optional[str] = None


@dataclass
class CreateJobPayload:
    session_name: Optional[str]
    uploads: List[SampleUpload]


def new_job(session_name: Optional[str]) -> SessionJob:
    now = utc_now_iso()
    return SessionJob(
        job_id=str(uuid4()),
        session_id=str(uuid4()),
        session_name=session_name,
        status="queued",
        created_at=now,
        updated_at=now,
        completed_at=None,
        sample_results=[],
    )
