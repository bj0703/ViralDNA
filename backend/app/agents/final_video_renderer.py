from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Dict

from backend.app.agents.base_agent import BaseAgent
from backend.app.core.multi_variant import (
    VARIANT_DEFAULTS,
    ensure_edit_timeline_variant_contract,
    ensure_final_video_multi_output,
    get_variant_payload,
)
from backend.app.renderers.ffmpeg_timeline import render_timeline_to_video

if TYPE_CHECKING:
    from pathlib import Path
    from backend.app.core.shared_memory import SessionSharedMemory


class FinalVideoRendererAgent(BaseAgent):
    """从 edit_timeline 全自动 FFmpeg 渲染最终视频，零GUI，零外部依赖
    画面完全来自素材剪辑，音频完全复刻参考样例的原声，完美复刻爆款节奏
    """

    read_keys = ["edit_timeline", "inputs.uploaded_videos"]
    write_keys = ["final_video_meta"]

    def analyze(self, shared_memory: SessionSharedMemory) -> Dict[str, Any]:
        edit_timeline = shared_memory.get("edit_timeline")
        uploaded_videos = shared_memory.get_nested("inputs.uploaded_videos") or []
        requested_variant_id = shared_memory.get_nested("inputs.requested_variant_id")

        if not edit_timeline or "timeline" not in edit_timeline or not edit_timeline["timeline"]:
            return ensure_final_video_multi_output({
                "_skip_reason": "no_valid_timeline",
                "warning": "edit_timeline 为空，跳过视频渲染",
                "output_path": None,
                "success": False,
            })

        normalized_edit_timeline = ensure_edit_timeline_variant_contract(edit_timeline)

        # 素材视频源池：包含两部分 - 1. 上传的is_reference=False素材 2. asset_index中所有生成素材
        source_paths = [
            v.get("storage_path", "")
            for v in uploaded_videos
            if v.get("storage_path", "") and not v.get("is_reference", False)
        ]
        # 从asset_index中额外收集所有素材的storage_path，包含生成的aigc素材
        asset_index = shared_memory.get("asset_index")
        if asset_index and asset_index.get("assets"):
            for asset in asset_index["assets"]:
                path_candidate = asset.get("storage_path", "") or asset.get("_debug_full_path", "")
                if path_candidate and path_candidate not in source_paths:
                    source_paths.append(path_candidate)

        # 单独取出参考样例视频路径，专门用于音频混流
        ref_audio_source_path = None
        ref_videos = [v for v in uploaded_videos if v.get("is_reference", False)]
        if ref_videos:
            ref_audio_source_path = ref_videos[0].get("storage_path", "")

        from pathlib import Path
        output_base_dir = Path(__file__).resolve().parents[3] / "data" / "outputs"
        job_id = shared_memory.session_id
        output_dir = output_base_dir / job_id
        output_dir.mkdir(parents=True, exist_ok=True)
        version = shared_memory.version
        rendered_at = int(time.time() * 1000)
        outputs = []
        variant_ids = list(normalized_edit_timeline.get("variants", {}).keys())
        if isinstance(requested_variant_id, str) and requested_variant_id in normalized_edit_timeline.get("variants", {}):
            variant_ids = [requested_variant_id]

        for variant_id in variant_ids:
            variant_timeline = get_variant_payload(normalized_edit_timeline, variant_id)
            timeline_segments = variant_timeline.get("timeline", [])
            if not timeline_segments:
                outputs.append({
                    "variant_id": variant_id,
                    "label": VARIANT_DEFAULTS.get(variant_id, {}).get("label", variant_id),
                    "output_path": None,
                    "success": False,
                    "warning": "timeline 为空，跳过该版本渲染",
                    "rendered_at": rendered_at,
                })
                continue

            output_mp4_path = str(output_dir / f"final_rendered_v{version}_{variant_id}.mp4")
            result = render_timeline_to_video(
                timeline=timeline_segments,
                source_video_paths=source_paths,
                output_path=output_mp4_path,
                reference_audio_path=ref_audio_source_path
            )

            output_item = dict(result)
            output_path = output_item.get("output_path")
            if output_path:
                output_filename = Path(str(output_path)).name
                output_item.setdefault("output_filename", output_filename)
                output_item.setdefault("output_url", f"/api/orchestration/jobs/{job_id}/outputs/{output_filename}")
            output_item["variant_id"] = variant_id
            output_item.setdefault("label", VARIANT_DEFAULTS.get(variant_id, {}).get("label", variant_id))
            output_item.setdefault("rendered_at", rendered_at)
            outputs.append(output_item)

        result = ensure_final_video_multi_output({
            "default_variant_id": requested_variant_id if isinstance(requested_variant_id, str) and requested_variant_id in variant_ids else normalized_edit_timeline.get("default_variant_id", "structure"),
            "outputs": outputs,
            "rendered_at": rendered_at,
        })
        result["_debug_asset_count"] = len(source_paths)
        result["_debug_asset_list"] = [Path(p).name for p in source_paths]
        result["_debug_ref_audio_source"] = Path(ref_audio_source_path).name if ref_audio_source_path else None
        result["_debug_requested_variant_id"] = requested_variant_id
        return result
