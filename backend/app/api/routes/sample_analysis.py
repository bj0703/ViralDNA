from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse

from backend.app.core.errors import api_error
from backend.app.dependencies import intent_routing_service, sample_analysis_service
from backend.app.models.sample_analysis import CreateJobPayload, SampleUpload
from backend.app.renderers.sample_analysis import render_job_html
from backend.app.schemas.sample_analysis import (
    CreateSampleAnalysisResponse,
    IntentRequest,
    IntentResponse,
    JobResultResponse,
    JobViewModelResponse,
)

router = APIRouter(prefix="/sample-analysis", tags=["sample-analysis"])

UPLOAD_ROOT = Path("backend/data/uploads")


def _parse_notes(notes_json: Optional[str]) -> Dict[str, str]:
    if not notes_json:
        return {}
    try:
        parsed = json.loads(notes_json)
    except json.JSONDecodeError as exc:
        raise api_error(400, "INVALID_NOTES_JSON", f"notes_json 不是合法 JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise api_error(400, "INVALID_NOTES_MAPPING", "notes_json 必须是文件名到说明文本的对象映射。")
    return {str(key): str(value) for key, value in parsed.items()}


@router.post("/jobs", response_model=CreateSampleAnalysisResponse)
async def create_job(
    files: List[UploadFile] = File(...),
    session_name: Optional[str] = Form(default=None),
    notes_json: Optional[str] = Form(default=None),
) -> CreateSampleAnalysisResponse:
    notes_by_name = _parse_notes(notes_json)
    job_folder = UPLOAD_ROOT / str(uuid4())
    job_folder.mkdir(parents=True, exist_ok=True)

    uploads: List[SampleUpload] = []
    for file in files:
        original_filename = file.filename or "sample.bin"
        safe_name = original_filename.replace("\\", "_").replace("/", "_")
        saved_filename = f"{uuid4()}_{safe_name}"
        storage_path = job_folder / saved_filename
        with storage_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        uploads.append(
            SampleUpload(
                original_filename=original_filename,
                saved_filename=saved_filename,
                storage_path=str(storage_path),
                content_type=file.content_type,
                notes=notes_by_name.get(original_filename),
            )
        )

    job = sample_analysis_service.create_job(
        CreateJobPayload(
            session_name=session_name,
            uploads=uploads,
        )
    )
    return CreateSampleAnalysisResponse(
        job_id=job.job_id,
        session_id=job.session_id,
        status=job.status,
        sample_count=len(job.sample_results),
    )


@router.get("/jobs/{job_id}", response_model=JobResultResponse)
def get_job(job_id: str) -> JobResultResponse:
    job = sample_analysis_service.get_job(job_id)
    if job is None:
        raise api_error(404, "JOB_NOT_FOUND", "未找到对应分析任务。")
    return JobResultResponse(**job.to_dict())


@router.get("/jobs/{job_id}/result")
def get_job_result(job_id: str) -> dict:
    job = sample_analysis_service.get_job(job_id)
    if job is None:
        raise api_error(404, "JOB_NOT_FOUND", "未找到对应分析任务。")
    return job.to_dict()


@router.get("/jobs/{job_id}/view-model", response_model=JobViewModelResponse)
def get_job_view_model(job_id: str) -> JobViewModelResponse:
    view_model = sample_analysis_service.get_view_model(job_id)
    if view_model is None:
        raise api_error(404, "JOB_NOT_FOUND", "未找到对应分析任务。")
    return JobViewModelResponse(**view_model)


@router.get("/jobs/{job_id}/view", response_class=HTMLResponse)
def get_job_view(job_id: str) -> HTMLResponse:
    job = sample_analysis_service.get_job(job_id)
    if job is None:
        raise api_error(404, "JOB_NOT_FOUND", "未找到对应分析任务。")
    return HTMLResponse(render_job_html(job))


@router.get("/uploads/{job_id}/{filename}")
def get_uploaded_file(job_id: str, filename: str) -> FileResponse:
    job = sample_analysis_service.get_job(job_id)
    if job is None:
        raise api_error(404, "JOB_NOT_FOUND", "未找到对应分析任务。")

    for sample in job.sample_results:
        if sample.metadata.filename == filename:
            path = sample.metadata.storage_path
            if not os.path.exists(path):
                raise api_error(404, "SAMPLE_FILE_NOT_FOUND", "样例文件不存在。")
            return FileResponse(path=path, media_type=sample.metadata.content_type, filename=sample.metadata.original_filename)

    raise api_error(404, "SAMPLE_NOT_FOUND", "未找到对应样例文件。")


@router.post("/intent", response_model=IntentResponse)
def detect_intent(payload: IntentRequest) -> IntentResponse:
    result = intent_routing_service.detect_intent(
        text=payload.text,
        target_video_id=payload.target_video_id,
    )
    return IntentResponse(**result)
