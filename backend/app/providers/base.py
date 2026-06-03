from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.app.models.sample_analysis import SampleUpload


@dataclass
class ProviderSection:
    label: str
    summary: str
    start_seconds: float
    end_seconds: float
    confidence: float
    status: str = "available"


@dataclass
class ProviderPaceSegment:
    label: str
    start_seconds: float
    end_seconds: float
    pace: str
    shot_density_estimate: float
    confidence: float


@dataclass
class ProviderAnalysis:
    duration_seconds: float
    duration_is_estimated: bool
    transcript_overview: Optional[str]
    hook: ProviderSection
    middle_segments: List[ProviderSection]
    ending: ProviderSection
    pace_segments: List[ProviderPaceSegment]
    overall_pace: str
    shot_density_estimate: float
    highlight_position_seconds: Optional[float]
    highlight_position_status: str
    confidence: Dict[str, float]
    availability: Dict[str, str]
    warnings: List[str] = field(default_factory=list)
    raw_outputs: Dict[str, Any] = field(default_factory=dict)


class VideoAnalysisProvider:
    """Interface for sample video understanding providers."""

    def analyze(self, upload: SampleUpload) -> ProviderAnalysis:
        raise NotImplementedError
