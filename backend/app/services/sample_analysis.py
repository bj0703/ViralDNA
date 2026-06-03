from __future__ import annotations

import mimetypes
import os
from typing import List

from backend.app.models.sample_analysis import (
    CreateJobPayload,
    SampleAnalysisResult,
    SampleMetadata,
    ScriptSection,
    SessionJob,
    new_job,
    utc_now_iso,
)
from backend.app.providers.base import ProviderAnalysis, ProviderSection, VideoAnalysisProvider
from backend.app.repositories.in_memory_sample_analysis import InMemorySampleAnalysisRepository


class SampleAnalysisService:
    def __init__(
        self,
        repository: InMemorySampleAnalysisRepository,
        provider: VideoAnalysisProvider,
        public_base_url: str = "http://localhost:8000",
    ) -> None:
        self.repository = repository
        self.provider = provider
        self.public_base_url = public_base_url.rstrip("/")

    def create_job(self, payload: CreateJobPayload) -> SessionJob:
        job = new_job(payload.session_name)
        job.status = "processing"
        self.repository.save(job)

        sample_results: List[SampleAnalysisResult] = []
        for upload in payload.uploads:
            provider_result = self.provider.analyze(upload)
            sample_results.append(self._build_sample_result(job, upload, provider_result))

        job.sample_results = sample_results
        job.status = "completed"
        job.completed_at = utc_now_iso()
        job.debug = {
            "sample_count": len(sample_results),
            "session_mode": "multi-video" if len(sample_results) > 1 else "single-video",
        }
        return self.repository.save(job)

    def get_job(self, job_id: str) -> SessionJob | None:
        return self.repository.get(job_id)

    def get_view_model(self, job_id: str) -> dict | None:
        job = self.repository.get(job_id)
        if job is None:
            return None
        return {
            "job_id": job.job_id,
            "session_id": job.session_id,
            "session_name": job.session_name,
            "status": job.status,
            "video_count": len(job.sample_results),
            "videos": [self._sample_view_model(sample) for sample in job.sample_results],
        }

    def _build_sample_result(self, job: SessionJob, upload, provider_result: ProviderAnalysis) -> SampleAnalysisResult:
        metadata = SampleMetadata(
            filename=upload.saved_filename,
            original_filename=upload.original_filename,
            content_type=upload.content_type or mimetypes.guess_type(upload.original_filename)[0],
            file_size_bytes=os.path.getsize(upload.storage_path),
            duration_seconds=provider_result.duration_seconds,
            duration_is_estimated=provider_result.duration_is_estimated,
            preview_url=f"{self.public_base_url}/sample-analysis/uploads/{job.job_id}/{upload.saved_filename}",
            transcript_overview=provider_result.transcript_overview,
            storage_path=upload.storage_path,
        )
        return SampleAnalysisResult(
            sample_id=upload.saved_filename,
            job_id=job.job_id,
            session_id=job.session_id,
            status="completed",
            metadata=metadata,
            script_structure={
                "hook": self._section_to_dict(provider_result.hook),
                "middle_segments": [self._section_to_dict(section) for section in provider_result.middle_segments],
                "ending": self._section_to_dict(provider_result.ending),
            },
            pace_structure={
                "overall_pace": provider_result.overall_pace,
                "shot_density_estimate": provider_result.shot_density_estimate,
                "highlight_position_seconds": provider_result.highlight_position_seconds,
                "highlight_position_status": provider_result.highlight_position_status,
                "segments": [
                    {
                        "label": segment.label,
                        "start_seconds": segment.start_seconds,
                        "end_seconds": segment.end_seconds,
                        "pace": segment.pace,
                        "shot_density_estimate": segment.shot_density_estimate,
                        "confidence": segment.confidence,
                    }
                    for segment in provider_result.pace_segments
                ],
            },
            confidence=provider_result.confidence,
            availability=provider_result.availability,
            raw_outputs=provider_result.raw_outputs,
            warnings=provider_result.warnings,
            timeline_segments=self._build_timeline_segments(provider_result),
        )

    def _section_to_dict(self, section: ProviderSection) -> dict:
        normalized = ScriptSection(
            label=section.label,
            summary=section.summary,
            start_seconds=section.start_seconds,
            end_seconds=section.end_seconds,
            confidence=section.confidence,
            status=section.status,
        )
        return normalized.to_dict()

    def _build_timeline_segments(self, provider_result: ProviderAnalysis) -> List[dict]:
        segments = [
            {
                "segment_id": "hook",
                "segment_type": "script",
                "label": provider_result.hook.label,
                "title": "Hook",
                "summary": provider_result.hook.summary,
                "start_seconds": provider_result.hook.start_seconds,
                "end_seconds": provider_result.hook.end_seconds,
                "confidence": provider_result.hook.confidence,
                "status": provider_result.hook.status,
            }
        ]
        for index, section in enumerate(provider_result.middle_segments, start=1):
            segments.append(
                {
                    "segment_id": f"middle-{index}",
                    "segment_type": "script",
                    "label": section.label,
                    "title": f"中段 {index}",
                    "summary": section.summary,
                    "start_seconds": section.start_seconds,
                    "end_seconds": section.end_seconds,
                    "confidence": section.confidence,
                    "status": section.status,
                }
            )
        segments.append(
            {
                "segment_id": "ending",
                "segment_type": "script",
                "label": provider_result.ending.label,
                "title": "结尾/CTA",
                "summary": provider_result.ending.summary,
                "start_seconds": provider_result.ending.start_seconds,
                "end_seconds": provider_result.ending.end_seconds,
                "confidence": provider_result.ending.confidence,
                "status": provider_result.ending.status,
            }
        )
        for index, segment in enumerate(provider_result.pace_segments, start=1):
            segments.append(
                {
                    "segment_id": f"pace-{index}",
                    "segment_type": "pace",
                    "label": segment.label,
                    "title": f"节奏段 {index}",
                    "summary": f"{segment.label}阶段节奏为{segment.pace}，镜头密度估计为 {segment.shot_density_estimate}。",
                    "start_seconds": segment.start_seconds,
                    "end_seconds": segment.end_seconds,
                    "confidence": segment.confidence,
                    "status": "available",
                }
            )
        return segments

    def _sample_view_model(self, sample: SampleAnalysisResult) -> dict:
        raw_outputs = sample.raw_outputs or {}
        return {
            "sample_id": sample.sample_id,
            "video": {
                "filename": sample.metadata.original_filename,
                "duration_seconds": sample.metadata.duration_seconds,
                "preview_url": sample.metadata.preview_url,
            },
            "timeline": sample.timeline_segments,
            "panels": {
                "overview": {
                    "transcript_overview": sample.metadata.transcript_overview,
                    "warnings": sample.warnings,
                    "availability": sample.availability,
                },
                "script": sample.script_structure,
                "pace": sample.pace_structure,
                "packaging_and_sound": raw_outputs.get("packaging_and_sound"),
                "migration_suggestion": raw_outputs.get("migration_suggestion"),
                "risks": sample.warnings,
            },
        }
