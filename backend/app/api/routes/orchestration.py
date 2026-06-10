from __future__ import annotations
import asyncio
import json
import os
import uuid
from pathlib import Path
from typing import List, Optional, Any, Dict
from pydantic import BaseModel
from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile, Body, Query, HTTPException
from fastapi.responses import StreamingResponse, FileResponse

from backend.app.agents.orchestrator import WorkflowOrchestrator
from backend.app.core.shared_memory import UploadedVideo
from backend.app.core.shared_memory_redis import get_or_create_shared_memory_redis
from backend.app.dependencies import DynamicIntentPlanner
import backend.app.services.timeline_editor as timeline_editor_service


class ReSubmitRequest(BaseModel):
    new_user_prompt: str
    force_run_agent_names: Optional[List[str]] = []
    added_assets: Optional[List[str]] = []
    selected_reference_video_id: Optional[str] = None
    requested_variant_id: Optional[str] = None


class ReRenderRequest(BaseModel):
    requested_variant_id: Optional[str] = None


UPLOAD_ROOT = Path("backend/data/orchestration_uploads")
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/api/orchestration", tags=["orchestration"])


@router.post("/jobs/draft")
async def create_draft_job():
    """Create an empty orchestration job container before the first prompt is submitted."""
    job_id = str(uuid.uuid4())
    memory = get_or_create_shared_memory_redis(job_id)
    memory.append_event("resource_updated", "", {
        "uploaded_videos": [],
        "selected_reference_video_id": None,
        "draft": True,
    })
    return {
        "job_id": job_id,
        "draft": True,
        "uploaded_video_count": 0,
    }


@router.post("/jobs")
async def create_job(
    background_tasks: BackgroundTasks,
    intent: str = Form("帮我迁移一个样例"),
    files: Optional[List[UploadFile]] = File(None),
    is_reference_flags: str = Form(""),
    client_video_ids: str = Form(""),
    selected_reference_client_id: Optional[str] = Form(None),
):
    """
    创建多Agent编排任务
    - intent: 用户自然语言输入
    - files: 上传的视频文件数组
    - is_reference_flags: 逗号分隔的布尔字符串，顺序对应files数组，如 "true,false,false"
    """
    job_id = str(uuid.uuid4())
    memory = get_or_create_shared_memory_redis(job_id)

    memory.set_input_user_prompt(intent)

    flags = []
    if is_reference_flags:
        for part in is_reference_flags.split(","):
            flags.append(part.strip().lower() == "true")

    client_ids = [part.strip() for part in client_video_ids.split(",") if part.strip()]
    selected_reference_video_id: Optional[str] = None

    for idx, file in enumerate(files or []):
        flag = flags[idx] if idx < len(flags) else False
        client_id = client_ids[idx] if idx < len(client_ids) else None
        safe_name = (file.filename or "sample.bin").replace("\\", "_").replace("/", "_")
        saved_filename = f"{uuid.uuid4()}_{safe_name}"
        storage_path = UPLOAD_ROOT / saved_filename
        with storage_path.open("wb") as buffer:
            await file.read()
            file.file.seek(0)
            import shutil
            shutil.copyfileobj(file.file, buffer)

        video = UploadedVideo(
            original_filename=safe_name,
            saved_filename=saved_filename,
            storage_path=str(storage_path),
            content_type=file.content_type,
            file_size_bytes=os.path.getsize(str(storage_path)),
            is_reference=flag,
        )
        memory.append_uploaded_video(video)
        if selected_reference_client_id and client_id == selected_reference_client_id:
            selected_reference_video_id = saved_filename

    uploaded_videos = memory.to_dict()["inputs"]["uploaded_videos"]
    if selected_reference_video_id is None:
        first_reference = next((v for v in uploaded_videos if v.get("is_reference", False)), None)
        selected_reference_video_id = first_reference.get("saved_filename") if first_reference else None
    memory.set_selected_reference_video_id(selected_reference_video_id)
    ref_count = sum(1 for v in uploaded_videos if v.get("is_reference", False))
    if ref_count > 1:
        memory.append_event("step_warning", "system", {
            "reason": "multiple_reference_videos",
            "detail": f"用户上传了{ref_count}个标记为is_reference=True的视频，优先使用当前选中的样例视频"
        })

    plan_names = DynamicIntentPlanner.plan(intent, memory)
    orchestrator = WorkflowOrchestrator(job_id)
    orchestrator.build_plan(plan_names)

    def _run_sync():
        import asyncio
        asyncio.run(orchestrator.run())
    background_tasks.add_task(_run_sync)

    return {"job_id": job_id, "plan_agents": plan_names, "uploaded_video_count": len(uploaded_videos)}


@router.post("/jobs/{job_id}/re-submit")
async def re_submit_job(
    background_tasks: BackgroundTasks,
    job_id: str,
    req: ReSubmitRequest
):
    """
    二次提交新需求，基于已有Job状态增量执行，快速生成下一版视频
    - 自动打当前状态快照
    - LLM增量意图规划，选出需要重新执行的Agent子集
    - 增量模式运行，自动跳过已有缓存结果的Agent
    """
    mem = get_or_create_shared_memory_redis(job_id)

    new_version = mem.snapshot()
    mem.set_input_user_prompt(req.new_user_prompt)
    mem.set_selected_reference_video_id(req.selected_reference_video_id)
    mem.set_requested_variant_id(req.requested_variant_id)
    plan_names = DynamicIntentPlanner.plan(req.new_user_prompt, mem)

    orchestrator = WorkflowOrchestrator(
        job_id,
        incremental_mode=True,
        force_run_agent_names=req.force_run_agent_names or []
    )
    orchestrator.build_plan(plan_names)

    def _run_sync():
        import asyncio
        asyncio.run(orchestrator.run())
    background_tasks.add_task(_run_sync)

    return {
        "job_id": job_id,
        "new_version": new_version,
        "plan_agents": plan_names,
        "incremental_enabled": True,
        "added_asset_count": len(req.added_assets or [])
    }


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    orchestrator = WorkflowOrchestrator(job_id)
    return orchestrator.get_status()


@router.get("/jobs/{job_id}/trace")
async def get_job_trace(job_id: str):
    mem = get_or_create_shared_memory_redis(job_id)
    data = mem.to_dict()
    return {
        "session_id": job_id,
        "version": data.get("version", 1),
        "version_history_count": len(data.get("version_history", [])),
        "event_log": data.get("event_log", [])
    }


@router.get("/jobs/{job_id}/timeline")
async def get_full_timeline_endpoint(job_id: str):
    mem = get_or_create_shared_memory_redis(job_id)
    return timeline_editor_service.get_full_timeline(mem)


@router.patch("/jobs/{job_id}/timeline/segments/{segment_id}")
async def update_segment_endpoint(
    job_id: str,
    segment_id: str,
    patch_data: Dict[str, Any] = Body(...)
):
    mem = get_or_create_shared_memory_redis(job_id)
    return timeline_editor_service.update_segment(mem, segment_id, patch_data)


@router.post("/jobs/{job_id}/timeline/segments")
async def insert_new_segment_endpoint(
    job_id: str,
    track_id: str,
    insert_position: int,
    segment_data: Dict[str, Any] = Body(...)
):
    mem = get_or_create_shared_memory_redis(job_id)
    return timeline_editor_service.insert_new_segment(mem, track_id, insert_position, segment_data)


@router.delete("/jobs/{job_id}/timeline/segments/{segment_id}")
async def delete_segment_endpoint(job_id: str, segment_id: str):
    mem = get_or_create_shared_memory_redis(job_id)
    return timeline_editor_service.delete_segment(mem, segment_id)


@router.post("/jobs/{job_id}/timeline/reorder")
async def reorder_segments_endpoint(
    job_id: str,
    track_id: str,
    new_order_ids: List[str] = Body(..., embed=True)
):
    mem = get_or_create_shared_memory_redis(job_id)
    return timeline_editor_service.reorder_segments(mem, track_id, new_order_ids)


@router.post("/jobs/{job_id}/timeline/re-render")
async def re_render_endpoint(job_id: str, background_tasks: BackgroundTasks, req: Optional[ReRenderRequest] = Body(default=None)):
    mem = get_or_create_shared_memory_redis(job_id)
    result = timeline_editor_service.re_render(mem, requested_variant_id=req.requested_variant_id if req else None)
    return result


@router.get("/jobs/{job_id}/stream")
async def stream_job_events(
    job_id: str,
    last_event_id: int = Query(0, description="从该下标后开始续传事件，默认从0开始")
):
    """
    SSE Server-Sent Events 实时事件流接口
    - 完全统一读写来源，所有事件只走Redis版共享内存
    - 支持断点续传：携带 last_event_id 重连不会丢事件
    """
    async def event_generator():
        current_offset = last_event_id
        yield ": heartbeat\n\n"
        while True:
            store = get_or_create_shared_memory_redis(job_id)
            new_events = store.get_new_events_since(current_offset)
            if new_events:
                for evt in new_events:
                    yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
                current_offset += len(new_events)
            await asyncio.sleep(1.5)
            yield ": heartbeat\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Transfer-Encoding": "chunked",
            "Access-Control-Expose-Headers": "*"
        }
    )


@router.post("/jobs/{job_id}/upload-video")
async def upload_single_video(
    job_id: str,
    file: UploadFile = File(...),
    is_reference: str = Form("false"),
):
    """
    单文件追加上传接口
    - 任务创建完成后，可继续往已有job追加上传参考视频或素材视频
    - 前端 SampleVideoSection / MaterialVideoSection 直接调用此接口
    """
    mem = get_or_create_shared_memory_redis(job_id)

    flag = is_reference.strip().lower() == "true"
    safe_name = (file.filename or "video.bin").replace("\\", "_").replace("/", "_")
    saved_filename = f"{uuid.uuid4()}_{safe_name}"
    storage_path = UPLOAD_ROOT / saved_filename
    with storage_path.open("wb") as buffer:
        await file.read()
        file.file.seek(0)
        import shutil
        shutil.copyfileobj(file.file, buffer)

    video = UploadedVideo(
        original_filename=safe_name,
        saved_filename=saved_filename,
        storage_path=str(storage_path),
        content_type=file.content_type,
        file_size_bytes=os.path.getsize(str(storage_path)),
        is_reference=flag,
    )
    mem.append_uploaded_video(video)
    if flag and not mem.get_nested("inputs.selected_reference_video_id"):
        mem.set_selected_reference_video_id(video.saved_filename)
    mem.append_event("resource_updated", "", {
        "uploaded_videos": mem.to_dict()["inputs"]["uploaded_videos"],
        "selected_reference_video_id": mem.get_nested("inputs.selected_reference_video_id"),
    })

    return {
        "id": video.saved_filename,
        "filename": video.original_filename,
        "url": f"/api/orchestration/uploads/{video.saved_filename}",
        "is_reference": video.is_reference,
        "duration": 0,
        "createdAt": int(video.file_size_bytes),
    }


@router.delete("/jobs/{job_id}/videos/{video_id}")
async def delete_uploaded_video(job_id: str, video_id: str):
    mem = get_or_create_shared_memory_redis(job_id)
    removed_video = mem.remove_uploaded_video(video_id)
    if removed_video is None:
        raise HTTPException(status_code=404, detail="video not found")

    removed_path = removed_video.get("storage_path")
    if isinstance(removed_path, str) and removed_path:
        path = Path(removed_path)
        try:
            if path.exists() and path.is_file():
                path.unlink()
        except OSError:
            pass

    selected_reference_video_id = mem.get_nested("inputs.selected_reference_video_id")
    if selected_reference_video_id == video_id:
        uploaded_videos = mem.to_dict()["inputs"]["uploaded_videos"]
        fallback_reference = next((v for v in uploaded_videos if v.get("is_reference", False)), None)
        mem.set_selected_reference_video_id(
            fallback_reference.get("saved_filename") if fallback_reference else None
        )

    mem.append_event("resource_updated", "", {
        "uploaded_videos": mem.to_dict()["inputs"]["uploaded_videos"],
        "selected_reference_video_id": mem.get_nested("inputs.selected_reference_video_id"),
        "deleted_video_id": video_id,
    })

    return {
        "job_id": job_id,
        "deleted_video_id": video_id,
        "uploaded_video_count": len(mem.to_dict()["inputs"]["uploaded_videos"]),
        "selected_reference_video_id": mem.get_nested("inputs.selected_reference_video_id"),
    }


@router.get("/uploads/{filename}")
async def get_uploaded_orchestration_file(filename: str):
    safe_name = Path(filename).name
    path = (UPLOAD_ROOT / safe_name).resolve()
    upload_root = UPLOAD_ROOT.resolve()
    if upload_root not in path.parents and path != upload_root:
        raise HTTPException(status_code=400, detail="invalid upload path")
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(path=path, filename=safe_name)


class GenerateCapCutDraftRequest(BaseModel):
    requested_variant_id: Optional[str] = "structure"


@router.post("/jobs/{job_id}/generate-capcut-draft")
async def generate_capcut_draft_endpoint(
    job_id: str,
    background_tasks: BackgroundTasks,
    req: Optional[GenerateCapCutDraftRequest] = Body(default=None),
):
    """
    异步生成剪映草稿接口
    必须在 EditPlannerAgent 时间线规划完成后调用，后台异步任务生成完整可导入的剪映草稿文件夹。
    通过 SSE 事件流实时通知前端生成进度。
    """
    mem = get_or_create_shared_memory_redis(job_id)
    edit_timeline = mem.get("edit_timeline")

    if not edit_timeline or "timeline" not in edit_timeline and not edit_timeline.get("variants"):
        raise HTTPException(
            status_code=400,
            detail="edit_timeline 尚未就绪，请等待 EditPlannerAgent 时间线规划完成后再调用"
        )

    target_variant_id = req.requested_variant_id if req else "structure"

    mem.append_event("capcut_draft_start", "", {
        "job_id": job_id,
        "requested_variant_id": target_variant_id,
        "phase": "started",
    })

    def _background_generate():
        import logging
        import traceback
        bg_logger = logging.getLogger("CapCutDraftBackgroundTask")
        bg_logger.info(f"[CAPCUT_BG_TASK] 后台剪映草稿生成任务启动, job_id={job_id}, variant_id={target_variant_id}")
        try:
            bg_logger.info("[CAPCUT_BG_TASK] 开始导入 CapCutDraftGeneratorService")
            from backend.app.services.capcut_draft_generator import CapCutDraftGeneratorService
            bg_logger.info("[CAPCUT_BG_TASK] CapCutDraftGeneratorService 导入成功，开始实例化")
            generator = CapCutDraftGeneratorService()
            bg_logger.info("[CAPCUT_BG_TASK] generator 实例化完成")
            
            bg_logger.info("[CAPCUT_BG_TASK] 从 shared_memory 读取 edit_timeline")
            edit_timeline_data = mem.get("edit_timeline")
            bg_logger.info(f"[CAPCUT_BG_TASK] edit_timeline 读取成功, 类型={type(edit_timeline_data)}, 存在? {edit_timeline_data is not None}")
            
            output_root_path = str(Path(__file__).resolve().parents[4] / "data" / "capcut_drafts")
            bg_logger.info(f"[CAPCUT_BG_TASK] 输出根目录: {output_root_path}")
            
            result = generator.generate_draft_from_timeline(
                edit_timeline=edit_timeline_data,
                variant_id=target_variant_id,
                output_root=output_root_path
            )
            bg_logger.info(f"[CAPCUT_BG_TASK] generate_draft_from_timeline 返回结果, success={result.get('success')}")

            mem.set("capcut_draft_meta", result, "CapCutDraftGeneratorService")
            bg_logger.info("[CAPCUT_BG_TASK] capcut_draft_meta 已写入 shared_memory")

            if result.get("success"):
                mem.append_event("capcut_draft_complete", "", result)
                bg_logger.info("[CAPCUT_BG_TASK] capcut_draft_complete 事件已推送，生成全部完成")
            else:
                mem.append_event("capcut_draft_fail", "", {
                    "error": result.get("error", "剪映草稿生成失败"),
                })
                bg_logger.error(f"[CAPCUT_BG_TASK] capcut_draft_fail 事件推送，业务失败: {result.get('error')}")
        except Exception as e:
            full_traceback = traceback.format_exc()
            bg_logger.error(f"[CAPCUT_BG_TASK] 后台任务发生未捕获异常! 完整异常栈:\n{full_traceback}")
            mem.append_event("capcut_draft_fail", "", {
                "error": str(e),
                "traceback": full_traceback,
            })

    background_tasks.add_task(_background_generate)

    return {
        "job_id": job_id,
        "status": "accepted",
        "requested_variant_id": target_variant_id,
        "message": "剪映草稿生成后台异步任务已启动，可通过 SSE 事件流查看生成进度。"
    }


@router.get("/jobs/{job_id}/capcut-draft-meta")
async def get_capcut_draft_meta(job_id: str):
    mem = get_or_create_shared_memory_redis(job_id)
    meta = mem.get("capcut_draft_meta")
    if not meta:
        raise HTTPException(status_code=404, detail="capcut_draft_meta 尚未生成或不存在")
    return meta


@router.post("/jobs/{job_id}/save-to-knowledge-base")
async def save_to_kb_endpoint(job_id: str):
    """
    一键沉淀参考样例分析结果到知识库
    全流程跑完后，样例视频结果区域点击此按钮，从共享记忆读取reference_analysis直接写入知识库style_templates
    """
    mem = get_or_create_shared_memory_redis(job_id)
    reference_analysis = mem.get("reference_analysis")

    if not reference_analysis:
        raise HTTPException(
            status_code=400,
            detail="reference_analysis 不存在，请等待 ReferenceAnalyzerAgent 视频结构拆解完成后再操作"
        )

    from backend.app.services.knowledge_base_service import KnowledgeBaseService
    kb_service = KnowledgeBaseService()
    result = kb_service.save_reference_analysis_to_kb(reference_analysis)

    mem.append_event("knowledge_base_saved", "", result)
    return result


@router.get("/jobs/{job_id}/outputs/{filename}")
async def get_rendered_output_file(job_id: str, filename: str):
    safe_name = Path(filename).name
    # Keep output lookup aligned with FinalVideoRendererAgent, which writes to repo_root/data/outputs.
    output_root = (Path(__file__).resolve().parents[4] / "data" / "outputs" / job_id).resolve()
    path = (output_root / safe_name).resolve()
    if output_root not in path.parents and path != output_root:
        raise HTTPException(status_code=400, detail="invalid output path")
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(path=path, filename=safe_name)
