from __future__ import annotations

import json
import asyncio
import mimetypes
import shutil
import subprocess
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from backend.app.agents.base_agent import BaseAgent
from backend.app.prompts.asset_indexer import ASSET_INDEXER_SYSTEM_PROMPT
from backend.app.providers.ark_chat import ArkChatProvider

if TYPE_CHECKING:
    from backend.app.core.shared_memory import SessionSharedMemory


class AssetIndexerAgent(BaseAgent):
    """批量分析所有素材视频，打标签、标记可用片段"""

    read_keys = ["inputs.uploaded_videos"]
    write_keys = ["asset_index"]

    def __init__(self, ark_chat_provider: ArkChatProvider):
        super().__init__()
        self.ark_chat_provider = ark_chat_provider

    def is_available(self) -> bool:
        return self.ark_chat_provider.config.is_configured

    def analyze(self, shared_memory: SessionSharedMemory) -> Dict[str, Any]:
        """保持公共接口为同步，内部用 asyncio.run 运行异步并发逻辑"""
        return asyncio.run(self._async_analyze(shared_memory))

    async def _async_analyze(self, shared_memory: SessionSharedMemory) -> Dict[str, Any]:
        uploaded_videos = shared_memory.get_nested("inputs.uploaded_videos")
        asset_videos = [v for v in uploaded_videos if not v.get("is_reference", False)]
        reference_analysis = shared_memory.get("reference_analysis")
        self.emit_phase("think", "盘点素材池", f"检测到 {len(asset_videos)} 条待分析素材，准备建立资产索引。")

        # 前置备份：先把所有已存在的source_type == "aigc_generated"生成素材备份出来
        existing_assets = (shared_memory.get("asset_index") or {}).get("assets", [])
        backup_aigc_generated = [a for a in existing_assets if a.get("source_type") == "aigc_generated"]
        if backup_aigc_generated:
            print(f"[INFO] AssetIndexerAgent 备份已有生成素材: count={len(backup_aigc_generated)}")

        if not asset_videos:
            return {
                "_skip_reason": "no_asset_video_found",
                "warning": "未找到标记为is_reference=False的素材视频，跳过AssetIndexerAgent",
                "assets": []
            }

        use_streaming = self._stream_callback is not None
        semaphore = asyncio.Semaphore(1 if use_streaming else 3)
        self.emit_phase(
            "plan",
            "确定执行策略",
            f"{'流式模式下按单条素材顺序分析' if use_streaming else '并发分析素材以提高吞吐'}。",
        )

        async def _analyze_one(asset: Dict[str, Any]):
            async with semaphore:
                try:
                    self.emit_phase("action", "开始分析素材", f"当前素材：{asset.get('original_filename', 'unknown.mp4')}。")
                    if use_streaming:
                        self.emit_stream_delta(f"\n\n[{asset.get('original_filename', 'unknown.mp4')}]\n")
                    result = await asyncio.to_thread(
                        self._analyze_single_asset, asset, reference_analysis
                    )
                    shared_memory.append_to_array("asset_index", "assets", result, "AssetIndexerAgent")
                    self.emit_phase(
                        "observation",
                        "写入素材索引",
                        f"已完成 {asset.get('original_filename', 'unknown.mp4')} 的结构化索引。",
                    )
                    shared_memory.append_event("step_write", "AssetIndexerAgent", {"file": asset.get("original_filename")})
                    return result
                except Exception as e:
                    shared_memory.append_event("step_warning", "AssetIndexerAgent", {
                        "file": asset.get("original_filename"),
                        "error": str(e)
                    })
                    return None

        tasks = [_analyze_one(asset) for asset in asset_videos]
        all_results = await asyncio.gather(*tasks)
        valid_results = [r for r in all_results if r is not None]

        # 后置合并：把之前备份的生成素材合并回结果数组，绝对不覆盖生成素材
        final_assets = valid_results + backup_aigc_generated
        if backup_aigc_generated:
            print(f"[INFO] AssetIndexerAgent 合并生成素材完成, 总数: {len(final_assets)}")

        return {
            "assets": final_assets,
            "_agent_meta": {
                "source": "asset-indexer-agent",
                "count": len(valid_results),
                "aigc_generated_preserved_count": len(backup_aigc_generated)
            }
        }

    def _analyze_single_asset(self, asset: Dict[str, Any], reference_analysis: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        filename = asset.get("original_filename", "unknown.mp4")
        full_storage_path = asset.get("storage_path", "")
        file_size = asset.get("file_size_bytes", 0)
        content_type = asset.get("content_type") or mimetypes.guess_type(filename)[0]
        duration_seconds, duration_is_estimated = self._probe_duration(full_storage_path, file_size)

        if not self.is_available():
            return self._build_fallback_asset_result(
                filename,
                duration_seconds,
                full_storage_path,
                duration_is_estimated=duration_is_estimated,
                fallback_reason="ark_not_configured",
            )

        try:
            user_prompt_dict = {
                "filename": filename,
                "duration_seconds": duration_seconds,
                "content_type": content_type,
            }

            # 注入参考样例上下文前缀
            if reference_analysis:
                context_parts = []
                if reference_analysis.get("type_label"):
                    context_parts.append(f"参考主题: {reference_analysis['type_label']}")
                if reference_analysis.get("summary"):
                    context_parts.append(f"参考摘要: {reference_analysis['summary']}")
                if reference_analysis.get("migration_suggestion"):
                    mig = reference_analysis["migration_suggestion"]
                    if isinstance(mig, list):
                        normalized_strings: List[str] = []
                        for item in mig:
                            if isinstance(item, str):
                                normalized_strings.append(item)
                            elif isinstance(item, dict):
                                prob = str(item.get("problem", ""))
                                sol = str(item.get("solution", ""))
                                if prob and sol:
                                    normalized_strings.append(f"{prob} -> {sol}")
                                elif prob:
                                    normalized_strings.append(prob)
                                elif sol:
                                    normalized_strings.append(sol)
                                else:
                                    normalized_strings.append(str(item))
                            else:
                                normalized_strings.append(str(item))
                        context_parts.append(f"迁移建议: {'; '.join(normalized_strings)}")
                    elif isinstance(mig, dict):
                        prob = str(mig.get("problem", ""))
                        sol = str(mig.get("solution", ""))
                        if prob and sol:
                            context_parts.append(f"迁移建议: {prob} -> {sol}")
                        elif prob:
                            context_parts.append(f"迁移建议: {prob}")
                        elif sol:
                            context_parts.append(f"迁移建议: {sol}")
                        else:
                            context_parts.append(f"迁移建议: {str(mig)}")
                    else:
                        context_parts.append(f"迁移建议: {mig}")
                if context_parts:
                    user_prompt_dict["reference_context"] = "\n".join(context_parts)

            user_prompt = json.dumps(user_prompt_dict, ensure_ascii=False)
            response_json = self.ark_chat_provider.analyze_video(
                ASSET_INDEXER_SYSTEM_PROMPT,
                user_prompt,
                video_path=full_storage_path,
                content_type=content_type,
                temperature=0.1,
                on_delta=self.emit_stream_delta,
            )
            content = self.ark_chat_provider.extract_text(response_json)
            parsed, repair_notes = self._parse_and_repair(content)
            if not self._has_core_analysis_fields(parsed):
                return self._build_fallback_asset_result(
                    filename,
                    duration_seconds,
                    full_storage_path,
                    duration_is_estimated=duration_is_estimated,
                    fallback_reason="model_output_missing_core_fields",
                )
            return self._validate_and_fill(
                parsed,
                filename,
                duration_seconds,
                full_storage_path,
                duration_is_estimated=duration_is_estimated,
                repair_notes=repair_notes,
            )
        except Exception as exc:
            return self._build_fallback_asset_result(
                filename,
                duration_seconds,
                full_storage_path,
                duration_is_estimated=duration_is_estimated,
                fallback_reason=str(exc),
            )

    def _probe_duration(self, storage_path: str, file_size: int) -> tuple[float, bool]:
        ffprobe_path = shutil.which("ffprobe")
        if ffprobe_path and storage_path:
            try:
                result = subprocess.run(
                    [
                        ffprobe_path,
                        "-v",
                        "quiet",
                        "-print_format",
                        "json",
                        "-show_format",
                        storage_path,
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="ignore",
                )
                data = json.loads(result.stdout)
                duration = float(data.get("format", {}).get("duration", 0.0))
                if duration > 0:
                    return round(duration, 2), False
            except (subprocess.SubprocessError, ValueError, json.JSONDecodeError):
                pass

        estimated = max(6.0, min(90.0, round(file_size / 1_000_000 * 4.5, 2)))
        return estimated, True

    def _parse_and_repair(self, content: str) -> tuple[Dict[str, Any], List[str]]:
        repair_notes: List[str] = []
        json_candidate = self._extract_json(content)
        if json_candidate != content:
            repair_notes.append("extracted_json_body")
        try:
            return json.loads(json_candidate), repair_notes
        except json.JSONDecodeError:
            repaired = self._light_repair(json_candidate)
            if repaired != json_candidate:
                repair_notes.append("light_json_repair")
            return json.loads(repaired), repair_notes

    def _extract_json(self, content: str) -> str:
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise RuntimeError("AssetIndexerAgent did not return JSON content.")
        return content[start:end + 1]

    def _light_repair(self, content: str) -> str:
        repaired = content.replace("```json", "").replace("```", "").strip()
        repaired = repaired.replace("\u201c", '"').replace("\u201d", '"')
        repaired = repaired.replace("\u2018", '"').replace("\u2019", '"')
        return repaired

    def _has_core_analysis_fields(self, parsed: Dict[str, Any]) -> bool:
        if not isinstance(parsed, dict):
            return False
        return any(
            parsed.get(key)
            for key in ("segments", "global_description", "visual_description", "content_type", "tags")
        )

    def _validate_and_fill(
        self,
        parsed: Dict[str, Any],
        filename: str,
        duration: float,
        full_storage_path: str = "",
        *,
        duration_is_estimated: bool = False,
        repair_notes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        if not isinstance(parsed, dict):
            parsed = {}

        # 保留原有旧字段向后兼容
        parsed.setdefault("material_id", filename)
        parsed.setdefault("content_type", "其他")
        parsed.setdefault("tags", ["未分类素材"])
        parsed.setdefault("suggested_usage", ["general"])
        parsed.setdefault("visual_description", f"素材文件 {filename}")
        parsed.setdefault("confidence", 0.6)
        parsed.setdefault("usable_segments", [
            {"start": 0.0, "end": duration, "quality": 0.8, "best_for": ["general"]}
        ])

        # 新字段容错填充
        parsed.setdefault("schema_version", "1.0")
        parsed.setdefault("asset_id", filename)
        parsed.setdefault("media_type", "video")
        parsed["duration"] = duration
        parsed.setdefault("global_description", parsed.get("visual_description", ""))
        parsed.setdefault("asset_level_risks", [])
        parsed["_duration_is_estimated"] = duration_is_estimated
        parsed["_analysis_mode"] = "model_video_analysis"
        parsed["_analysis_repair_notes"] = list(repair_notes or [])

        # 注入完整存储路径，供下游EditPlanner直接使用
        parsed.setdefault("_debug_full_path", full_storage_path)

        # segments数组容错填充
        if "segments" not in parsed or not isinstance(parsed.get("segments"), list) or len(parsed.get("segments", [])) == 0:
            parsed["segments"] = []
            for idx in range(min(3, int(duration / 2.0))):
                seg_start = idx * (duration / 3.0)
                seg_end = min((idx + 1) * (duration / 3.0), duration)
                parsed["segments"].append({
                    "segment_id": f"{filename.split('.')[0]}_s{str(idx + 1).zfill(2)}",
                    "start": round(seg_start, 2),
                    "end": round(seg_end, 2),
                    "duration": round(seg_end - seg_start, 2),
                    "content_type": "通用画面",
                    "subjects": ["未知主体"],
                    "action": "正常动作",
                    "scene": "通用场景",
                    "shot_size": "medium",
                    "camera_motion": "static",
                    "motion_intensity": 0.3,
                    "visual_quality": 0.8,
                    "lighting_quality": 0.8,
                    "subject_clarity": 0.8,
                    "orientation_fit": "9:16_safe",
                    "audio_available": False,
                    "best_for_roles": ["develop"],
                    "best_for_slot_types": ["通用画面"],
                    "can_reuse_by": ["crop", "speed_up", "zoom_in", "freeze_frame"],
                    "risks": [],
                    "confidence": 0.7
                })
        else:
            normalized_segments: List[Dict[str, Any]] = []
            for idx, segment in enumerate(parsed["segments"]):
                if not isinstance(segment, dict):
                    continue
                seg_start = max(0.0, min(duration, float(segment.get("start", 0.0))))
                seg_end = max(seg_start, min(duration, float(segment.get("end", duration))))
                segment["segment_id"] = str(segment.get("segment_id") or f"{filename.split('.')[0]}_s{str(idx + 1).zfill(2)}")
                segment["start"] = round(seg_start, 2)
                segment["end"] = round(seg_end, 2)
                segment["duration"] = round(max(0.0, seg_end - seg_start), 2)
                normalized_segments.append(segment)
            parsed["segments"] = normalized_segments

        if isinstance(parsed.get("usable_segments"), list):
            normalized_usable_segments: List[Dict[str, Any]] = []
            for item in parsed["usable_segments"]:
                if not isinstance(item, dict):
                    continue
                start = max(0.0, min(duration, float(item.get("start", 0.0))))
                end = max(start, min(duration, float(item.get("end", duration))))
                item["start"] = round(start, 2)
                item["end"] = round(end, 2)
                normalized_usable_segments.append(item)
            parsed["usable_segments"] = normalized_usable_segments

        return parsed

    def _build_fallback_asset_result(
        self,
        filename: str,
        duration: float,
        full_storage_path: str = "",
        *,
        duration_is_estimated: bool = False,
        fallback_reason: str = "",
    ) -> Dict[str, Any]:
        fallback = {
            "material_id": filename,
            "_debug_full_path": full_storage_path,
            "content_type": "其他",
            "tags": ["未分类素材"],
            "suggested_usage": ["general"],
            "visual_description": f"素材文件 {filename}，时长约 {round(duration,1)} 秒",
            "confidence": 0.5,
            "usable_segments": [
                {"start": 0.0, "end": duration, "quality": 0.8, "best_for": ["general"]}
            ],
            "schema_version": "1.0",
            "asset_id": filename,
            "media_type": "video",
            "duration": duration,
            "global_description": f"素材文件 {filename}，时长约 {round(duration,1)} 秒",
            "segments": [],
            "asset_level_risks": ["使用fallback结果"],
            "_fallback": True,
            "_duration_is_estimated": duration_is_estimated,
            "_analysis_mode": "fallback",
        }
        if fallback_reason:
            fallback["asset_level_risks"].append(f"fallback_reason: {fallback_reason}")
        for idx in range(min(3, int(duration / 2.0))):
            seg_start = idx * (duration / 3.0)
            seg_end = min((idx + 1) * (duration / 3.0), duration)
            fallback["segments"].append({
                "segment_id": f"{filename.split('.')[0]}_s{str(idx + 1).zfill(2)}",
                "start": round(seg_start, 2),
                "end": round(seg_end, 2),
                "duration": round(seg_end - seg_start, 2),
                "content_type": "通用画面",
                "subjects": ["未知主体"],
                "action": "正常动作",
                "scene": "通用场景",
                "shot_size": "medium",
                "camera_motion": "static",
                "motion_intensity": 0.3,
                "visual_quality": 0.8,
                "lighting_quality": 0.8,
                "subject_clarity": 0.8,
                "orientation_fit": "9:16_safe",
                "audio_available": False,
                "best_for_roles": ["develop"],
                "best_for_slot_types": ["通用画面"],
                "can_reuse_by": ["crop", "speed_up", "zoom_in", "freeze_frame"],
                "risks": [],
                "confidence": 0.6
            })
        return fallback
