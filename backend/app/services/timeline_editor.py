"""
Timeline Editor 中间层服务
提供原子操作API，封装所有对时间线的安全编辑操作
供后续前端剪辑UI直接调用
"""
from __future__ import annotations
import copy
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List

from backend.app.core.multi_variant import (
    ensure_edit_timeline_variant_contract,
    ensure_final_video_multi_output,
    get_default_variant_id,
    get_variant_payload,
)

if TYPE_CHECKING:
    from backend.app.core.shared_memory import SessionSharedMemory


def _load_edit_timeline(mem: "SessionSharedMemory") -> Dict[str, Any]:
    raw = mem.get("edit_timeline")
    return ensure_edit_timeline_variant_contract(raw) if raw else {}


def _sync_default_variant(edit_timeline: Dict[str, Any], default_payload: Dict[str, Any]) -> Dict[str, Any]:
    normalized = ensure_edit_timeline_variant_contract(edit_timeline)
    default_variant_id = get_default_variant_id(normalized)
    normalized["variants"][default_variant_id] = copy.deepcopy(default_payload)
    normalized = ensure_edit_timeline_variant_contract(normalized)
    return normalized


def get_full_timeline(mem: "SessionSharedMemory") -> Dict[str, Any]:
    """获取完整带tracks结构的时间线，前端直接渲染"""
    edit_timeline = _load_edit_timeline(mem)
    if not edit_timeline:
        return {
            "success": False,
            "error": "edit_timeline not found"
        }
    return {
        "success": True,
        "data": edit_timeline
    }


def update_segment(
    mem: "SessionSharedMemory",
    segment_id: str,
    patch_data: Dict[str, Any]
) -> Dict[str, Any]:
    """更新单个片段属性，拖拽移动、调整时长、修改source_in/source_out等"""
    edit_timeline = _load_edit_timeline(mem)
    if not edit_timeline or "timeline" not in edit_timeline:
        return {"success": False, "error": "edit_timeline not found"}

    # 同时更新扁平timeline和tracks中的对应片段
    updated_count = 0
    for seg in edit_timeline["timeline"]:
        if seg.get("clip_id") == segment_id:
            seg.update(patch_data)
            updated_count += 1

    if "tracks" in edit_timeline:
        for track in edit_timeline["tracks"]:
            for seg in track.get("segments", []):
                if seg.get("clip_id") == segment_id:
                    seg.update(patch_data)
                    updated_count += 1

    mem.append_event("timeline_updated", "TimelineEditorService", {
        "action": "update_segment",
        "segment_id": segment_id,
        "patch_keys": list(patch_data.keys()),
        "updated_count": updated_count
    })

    mem.set("edit_timeline", _sync_default_variant(edit_timeline, edit_timeline), "TimelineEditorService")
    return {"success": True, "updated_count": updated_count}


def insert_new_segment(
    mem: "SessionSharedMemory",
    track_id: str,
    insert_position: int,
    segment_data: Dict[str, Any]
) -> Dict[str, Any]:
    """从素材库拖入新片段到指定轨道的指定位置"""
    edit_timeline = _load_edit_timeline(mem)
    if not edit_timeline:
        return {"success": False, "error": "edit_timeline not found"}

    new_seg_id = segment_data.get("clip_id", f"seg_new_{insert_position}")
    segment_data.setdefault("clip_id", new_seg_id)

    # 找到对应track，插入新片段
    target_track_found = False
    for track in edit_timeline.get("tracks", []):
        if track.get("track_id") == track_id:
            segs = track.get("segments", [])
            segs.insert(insert_position, segment_data)
            track["segments"] = segs
            target_track_found = True
            break

    if not target_track_found:
        return {"success": False, "error": f"track not found: {track_id}"}

    # 同时同步更新扁平timeline数组
    edit_timeline["timeline"].insert(insert_position, segment_data)

    mem.append_event("timeline_updated", "TimelineEditorService", {
        "action": "insert_new_segment",
        "track_id": track_id,
        "new_segment_id": new_seg_id
    })

    mem.set("edit_timeline", _sync_default_variant(edit_timeline, edit_timeline), "TimelineEditorService")
    return {"success": True, "new_segment_id": new_seg_id}


def delete_segment(
    mem: "SessionSharedMemory",
    segment_id: str
) -> Dict[str, Any]:
    """删除指定片段"""
    edit_timeline = _load_edit_timeline(mem)
    if not edit_timeline or "timeline" not in edit_timeline:
        return {"success": False, "error": "edit_timeline not found"}

    # 从扁平timeline中删除
    original_len = len(edit_timeline["timeline"])
    edit_timeline["timeline"] = [
        s for s in edit_timeline["timeline"]
        if s.get("clip_id") != segment_id
    ]

    # 从所有tracks中删除
    for track in edit_timeline.get("tracks", []):
        track["segments"] = [
            s for s in track.get("segments", [])
            if s.get("clip_id") != segment_id
        ]

    deleted_count = original_len - len(edit_timeline["timeline"])

    mem.append_event("timeline_updated", "TimelineEditorService", {
        "action": "delete_segment",
        "segment_id": segment_id,
        "deleted_count": deleted_count
    })

    mem.set("edit_timeline", _sync_default_variant(edit_timeline, edit_timeline), "TimelineEditorService")
    return {"success": True, "deleted_count": deleted_count}


def reorder_segments(
    mem: "SessionSharedMemory",
    track_id: str,
    new_order_ids: List[str]
) -> Dict[str, Any]:
    """拖拽重新排序片段"""
    edit_timeline = _load_edit_timeline(mem)
    if not edit_timeline:
        return {"success": False, "error": "edit_timeline not found"}

    target_track = None
    for track in edit_timeline.get("tracks", []):
        if track.get("track_id") == track_id:
            target_track = track
            break

    if not target_track:
        return {"success": False, "error": f"track not found: {track_id}"}

    old_segs = target_track.get("segments", [])
    seg_map = {s.get("clip_id"): s for s in old_segs}
    new_segs = []
    for sid in new_order_ids:
        if sid in seg_map:
            new_segs.append(seg_map[sid])

    target_track["segments"] = new_segs

    # 同步更新扁平timeline
    edit_timeline["timeline"] = new_segs

    mem.append_event("timeline_updated", "TimelineEditorService", {
        "action": "reorder_segments",
        "track_id": track_id,
        "new_order_ids": new_order_ids
    })

    mem.set("edit_timeline", _sync_default_variant(edit_timeline, edit_timeline), "TimelineEditorService")
    return {"success": True, "reordered_count": len(new_segs)}


def re_render(mem: "SessionSharedMemory", requested_variant_id: str | None = None) -> Dict[str, Any]:
    """触发FFmpeg重新渲染出片，返回渲染结果"""
    from backend.app.agents.final_video_renderer import FinalVideoRendererAgent

    if hasattr(mem, "set_requested_variant_id"):
        mem.set_requested_variant_id(requested_variant_id)

    agent = FinalVideoRendererAgent()
    result = agent.analyze(mem)

    mem.append_event("timeline_re_rendered", "TimelineEditorService", {
        "action": "re_render",
        "requested_variant_id": requested_variant_id,
        "result": result
    })

    normalized_result = ensure_final_video_multi_output(result)
    mem.set("final_video_meta", normalized_result, "TimelineEditorService")
    return normalized_result
