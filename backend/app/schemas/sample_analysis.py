from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CreateSampleAnalysisResponse(BaseModel):
    job_id: str
    session_id: str
    status: str
    sample_count: int


class CapabilityResponse(BaseModel):
    capabilities: List[str]
    providers: List[str]
    strategies: List[str]


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "sample-analysis-backend"


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class JobResultResponse(BaseModel):
    job_id: str
    session_id: str
    session_name: Optional[str]
    status: str
    created_at: str
    updated_at: str
    completed_at: Optional[str]
    sample_results: List[Dict[str, Any]]
    debug: Dict[str, Any] = Field(default_factory=dict)


class ViewModelVideoResponse(BaseModel):
    sample_id: str
    video: Dict[str, Any]
    timeline: List[Dict[str, Any]]
    panels: Dict[str, Any]


class JobViewModelResponse(BaseModel):
    job_id: str
    session_id: str
    session_name: Optional[str]
    status: str
    video_count: int
    videos: List[ViewModelVideoResponse]


class IntentRequest(BaseModel):
    text: str
    target_video_id: Optional[str] = None


class IntentResponse(BaseModel):
    intent: str
    analysis_scope: str
    target_video_id: Optional[str]
    fallback_behavior: str
    confidence: float
    source: str
    raw_model_output: Optional[str] = None
    reason: Optional[str] = None
