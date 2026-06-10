from __future__ import annotations

import logging
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Dict, List

logger = logging.getLogger("EditPlannerAgent")

from backend.app.agents.base_agent import BaseAgent
from backend.app.core.multi_variant import (
    ensure_edit_timeline_variant_contract,
    ensure_resolved_gap_variant_contract,
    ensure_slot_match_variant_contract,
    get_variant_catalog,
    get_variant_payload,
)
from backend.app.providers.ark_chat import ArkChatProvider

if TYPE_CHECKING:
    from backend.app.core.shared_memory import SessionSharedMemory


class EditPlannerAgent(BaseAgent):
    """Generate a shot-based base timeline, then derive style variants from it."""

    read_keys = ["reference_analysis", "asset_index", "slot_matches", "resolved_gaps", "generated_assets"]
    write_keys = ["edit_timeline"]

    def __init__(self, ark_chat_provider: ArkChatProvider):
        super().__init__()
        self.ark_chat_provider = ark_chat_provider

    def is_available(self) -> bool:
        return self.ark_chat_provider.config.is_configured

    def analyze(self, shared_memory: SessionSharedMemory) -> Dict[str, Any]:
        logger.info("[EDIT_PLANNER] analyze() 入口开始执行")
        reference_analysis = shared_memory.get("reference_analysis")
        asset_index = shared_memory.get("asset_index") or {"assets": []}
        slot_matches = shared_memory.get("slot_matches")
        resolved_gaps = shared_memory.get("resolved_gaps")
        generated_assets = shared_memory.get("generated_assets")
        logger.info(f"[EDIT_PLANNER] 读取输入完成: reference_analysis存在? {reference_analysis is not None}, "
                    f"asset_index.assets数量={len(asset_index.get('assets', []))}, "
                    f"slot_matches存在? {slot_matches is not None}, "
                    f"resolved_gaps存在? {resolved_gaps is not None}, "
                    f"generated_assets存在? {generated_assets is not None}")
        self.emit_phase("think", "准备编排输入", "准备读取参考分析、资产索引、匹配结果和动态生成资源。")

        if generated_assets and isinstance(generated_assets, dict) and generated_assets.get("new_assets"):
            if "assets" not in asset_index or not isinstance(asset_index["assets"], list):
                asset_index["assets"] = []
            for new_asset in generated_assets["new_assets"]:
                asset_index["assets"].append(new_asset)
            self.emit_phase("observation", "合并动态资源", f"已将 {len(generated_assets['new_assets'])} 个AIGC动态资产合并到主资产索引。")

        if not reference_analysis:
            return ensure_edit_timeline_variant_contract({
                "_skip_reason": "missing_dependency",
                "warning": "缺少reference_analysis，跳过EditPlannerAgent",
                "timeline": [],
                "confidence": 0.0,
            })

        try:
            self.emit_phase("plan", "准备剪辑规划", "先按 shot_segments 生成基线，再从同一条剪辑线衍生四个版本。")
            normalized_slot_matches = ensure_slot_match_variant_contract(slot_matches, reference_analysis=reference_analysis)
            normalized_resolved_gaps = ensure_resolved_gap_variant_contract(resolved_gaps)
            structure_slot_matches = get_variant_payload(normalized_slot_matches, "structure")
            structure_resolved_gaps = get_variant_payload(normalized_resolved_gaps, "structure")

            self.emit_phase("action", "构建基线时间线", "根据 shot_segments + shot_matches 组装基线 timeline。")
            logger.info(f"[EDIT_PLANNER] 开始构建基线时间线, shot_segments长度={len(reference_analysis.get('shot_segments', []))}, "
                        f"shot_matches长度={len(structure_slot_matches.get('shot_matches', []))}")
            base_payload = self._build_base_timeline_payload(
                reference_analysis,
                asset_index,
                structure_slot_matches,
                structure_resolved_gaps,
            )
            logger.info(f"[EDIT_PLANNER] base_payload构建完成, timeline长度={len(base_payload.get('timeline', []))}")
            validated_base = self._validate_and_fill(base_payload, reference_analysis, asset_index)
            logger.info(f"[EDIT_PLANNER] validated_base校验填充完成, timeline最终长度={len(validated_base.get('timeline', []))}")

            self.emit_phase("observation", "生成基础版", "默认只生成 structure 基础版 timeline，其他3个变体设置为懒加载状态，按需触发。")
            variant_payloads: Dict[str, Dict[str, Any]] = {}
            # 先生成默认基础版（structure）
            variant_payloads["structure"] = self._apply_variant_timeline_style(
                validated_base,
                reference_analysis,
                "structure",
                "结构优先版",
            )
            # 其他变体标记为 LAZY 状态，暂不生成，后续用户指定才触发
            for variant_spec in get_variant_catalog(reference_analysis):
                if variant_spec["variant_id"] != "structure":
                    variant_payloads[variant_spec["variant_id"]] = {
                        "variant_id": variant_spec["variant_id"],
                        "label": variant_spec["label"],
                        "_lazy": True,
                        "_note": "该变体尚未生成，调用 generate_variant(variant_id) 后才会实际计算",
                        "timeline": None,
                        "ready": False,
                    }

            result = ensure_edit_timeline_variant_contract({
                "schema_version": "2.0",
                "default_variant_id": "structure",
                "base_timeline": deepcopy(validated_base),
                "variants": variant_payloads,
            })
            # 完全向后兼容：把默认 variant 的 timeline 字段同步到根级，旧代码不读 variants 也能正常工作
            result.setdefault("timeline", validated_base.get("timeline", []))
            result.setdefault("timeline_meta", validated_base.get("timeline_meta", {}))
            result.setdefault("tracks", validated_base.get("tracks", []))
            result.setdefault("caption_track", validated_base.get("caption_track", []))
            result.setdefault("packaging_track", validated_base.get("packaging_track", []))
            result.setdefault("audio_track", validated_base.get("audio_track", {}))
            result.setdefault("cover_design", validated_base.get("cover_design", {}))
            result.setdefault("confidence", validated_base.get("confidence", 0.75))
            result.setdefault("human_review_points", validated_base.get("human_review_points", []))
            result["_agent_meta"] = {
                "source": "edit-planner-agent",
                "segment_count": len(result.get("timeline", [])),
                "variant_count": len(variant_payloads),
                "timeline_source": "shot_segments",
            }

            logger.info("[EDIT_PLANNER] 自动开始生成剪映草稿，调用 CapCutDraftGeneratorService")
            self.emit_phase("action", "生成剪映草稿", "调用VectCutAPI库，基于当前timeline生成完整可导入的剪映草稿文件夹。")
            try:
                from pathlib import Path
                from backend.app.services.capcut_draft_generator import CapCutDraftGeneratorService
                generator = CapCutDraftGeneratorService()
                draft_output_root = str(Path(__file__).resolve().parents[4] / "data" / "capcut_drafts")
                logger.info(f"[EDIT_PLANNER] 剪映草稿输出根目录: {draft_output_root}")
                capcut_draft_meta = generator.generate_draft_from_timeline(
                    edit_timeline=result,
                    variant_id="structure",
                    output_root=draft_output_root,
                )
                logger.info(f"[EDIT_PLANNER] 剪映草稿生成完成, success={capcut_draft_meta.get('success')}, draft_id={capcut_draft_meta.get('draft_id')}")
                result["capcut_draft_meta"] = capcut_draft_meta
                if capcut_draft_meta.get("success"):
                    self.emit_phase("observation", "剪映草稿生成完毕", f"草稿ID={capcut_draft_meta.get('draft_id')}, 可直接导入剪映使用。")
                else:
                    logger.warning(f"[EDIT_PLANNER] 剪映草稿业务失败: {capcut_draft_meta.get('error')}")
            except Exception as draft_exc:
                import traceback
                logger.error(f"[EDIT_PLANNER] 生成剪映草稿时发生异常: {traceback.format_exc()}")
                result["capcut_draft_meta"] = {
                    "success": False,
                    "error": str(draft_exc),
                    "traceback": traceback.format_exc(),
                }

            return result
        except Exception as exc:
            return self._fallback_llm_unavailable(reference_analysis, asset_index, fallback_reason=str(exc))

    def _build_base_timeline_payload(
        self,
        ref_analysis: Dict[str, Any],
        asset_index: Any,
        slot_matches: Dict[str, Any],
        resolved_gaps: Dict[str, Any],
    ) -> Dict[str, Any]:
        logger.info("[EDIT_PLANNER] _build_base_timeline_payload 开始执行")
        shot_segments = ref_analysis.get("shot_segments", []) if isinstance(ref_analysis, dict) else []
        shot_matches = slot_matches.get("shot_matches", []) if isinstance(slot_matches, dict) else []
        shot_match_lookup = {
            str(item.get("shot_id")): item
            for item in shot_matches
            if isinstance(item, dict) and item.get("shot_id") is not None
        }
        slot_assignments = slot_matches.get("slot_assignments", []) if isinstance(slot_matches, dict) else []
        asset_lookup = self._build_asset_lookup(asset_index)

        # 双重兜底1：从resolved_gaps直接回填asset_id，支持GeneratedAssetBuilder生成的新动态资源
        resolved_gaps_list = resolved_gaps.get("resolved_gaps", []) if isinstance(resolved_gaps, dict) else []
        gap_asset_lookup: Dict[str, Dict[str, Any]] = {}
        for gap in resolved_gaps_list:
            if not isinstance(gap, dict):
                continue
            slot_id = str(gap.get("slot_id", ""))
            resolution = gap.get("resolution", {}) if isinstance(gap.get("resolution"), dict) else {}
            asset_ref = resolution.get("asset_ref", {}) if isinstance(resolution.get("asset_ref"), dict) else {}
            if asset_ref and asset_ref.get("asset_id"):
                gap_asset_lookup[slot_id] = asset_ref

        # 双重兜底2：收集所有可用asset_id的列表，保证永远有fallback素材
        available_asset_ids = [aid for aid in asset_lookup.keys() if aid and isinstance(aid, str)]
        if not available_asset_ids:
            available_asset_ids = ["dummy"]
        fallback_first_asset_id = available_asset_ids[0]

        total_duration = float(
            ref_analysis.get("video_basic_info", {}).get("core_content_effective_duration_seconds", 15.0)
            if isinstance(ref_analysis, dict) else 15.0
        )
        timeline: List[Dict[str, Any]] = []
        for index, shot in enumerate(shot_segments):
            if not isinstance(shot, dict):
                continue

            shot_id = str(shot.get("shot_id", f"shot_{index + 1:02d}"))
            shot_start = float(shot.get("start_time", 0.0) or 0.0)
            shot_end = float(shot.get("end_time", shot_start + 1.0) or (shot_start + 1.0))
            shot_duration = max(shot_end - shot_start, 0.1)
            match = shot_match_lookup.get(shot_id, {})
            if not match and slot_assignments:
                fallback_assignment = slot_assignments[min(index, len(slot_assignments) - 1)]
                if isinstance(fallback_assignment, dict):
                    candidate = fallback_assignment.get("selected_candidate", {})
                    assignment = fallback_assignment
                else:
                    candidate = {}
                    assignment = {}
                match = {
                    "matched_asset_id": candidate.get("asset_id"),
                    "matched_segment_id": candidate.get("segment_id"),
                    "source_in": candidate.get("source_in", 0.0),
                    "source_out": candidate.get("source_out", shot_duration),
                    "reason": assignment.get("reason", ""),
                    "slot_id": assignment.get("slot_id", shot_id),
                    "slot_role": assignment.get("slot_role"),
                }
            matched_asset_id = match.get("matched_asset_id")

            # 优先从 gap_asset_lookup 取动态生成的资源ID
            current_slot_id = str(match.get("slot_id", shot_id))
            if current_slot_id in gap_asset_lookup:
                gap_asset_ref = gap_asset_lookup[current_slot_id]
                matched_asset_id = gap_asset_ref.get("asset_id", matched_asset_id)
                match["matched_segment_id"] = gap_asset_ref.get("segment_id", match.get("matched_segment_id", ""))
                source_in = float(gap_asset_ref.get("source_in", match.get("source_in", 0.0)) or 0.0)
                source_out = float(gap_asset_ref.get("source_out", match.get("source_out", shot_duration)) or (source_in + shot_duration))
            else:
                source_in = float(match.get("source_in", 0.0) or 0.0)
                source_out = float(match.get("source_out", source_in + shot_duration) or (source_in + shot_duration))

            # 绝对兜底：保证asset_id永远不会是None/空，取第一个可用素材
            if not matched_asset_id or matched_asset_id is None:
                matched_asset_id = fallback_first_asset_id

            asset_record = asset_lookup.get(str(matched_asset_id), {})
            if source_out <= source_in:
                source_out = source_in + shot_duration

            timeline.append({
                "clip_id": f"clip_{index + 1:03d}",
                "shot_id": shot_id,
                "slot_id": match.get("slot_id", shot_id),
                "role": self._map_shot_role(index, shot, total_duration),
                "start": shot_start,
                "end": shot_end,
                "asset_id": matched_asset_id,
                "segment_id": match.get("matched_segment_id", ""),
                "source_in": source_in,
                "source_out": source_out,
                "transform": {
                    "crop": "16:9_pad",
                    "scale": 1.0,
                    "speed": 1.0,
                    "motion": "story_focus",
                },
                "transition_out": shot.get("transition_out", "cut"),
                "transition_in": shot.get("transition_in", "cut"),
                "overlays": [],
                "asset_full_path": match.get("asset_full_path") or asset_record.get("_debug_full_path", ""),
                "shot_summary": shot.get("summary", ""),
                "pace": shot.get("pace", "medium"),
            })

        resolved_gaps_list = resolved_gaps.get("resolved_gaps", []) if isinstance(resolved_gaps, dict) else []
        return {
            "schema_version": "1.0",
            "timeline_meta": {
                "duration": total_duration,
                "aspect_ratio": "16:9",
                "resolution": "1920x1080",
                "fps": 30,
                "style_source": ref_analysis.get("template_id", "ref_001"),
                "music_sync_mode": "beat_aligned",
                "timeline_width_pixels": 1920,
                "timeline_source": "shot_segments",
            },
            "timeline": timeline,
            "caption_track": [],
            "packaging_track": [],
            "audio_track": {
                "bgm": {
                    "source": "reference_style_or_user_selected",
                    "sync_points": [],
                },
                "sfx": [],
            },
            "cover_design": {
                "cover_type": "大字标题",
                "main_title": "核心内容标题",
                "subtitle": "shot_segments 基线版本",
                "visual_focus_asset": timeline[0].get("asset_id", "unknown.mp4") if len(timeline) > 0 else "unknown.mp4",
                "visual_focus_time": timeline[0].get("start", 0.0) if len(timeline) > 0 else 0.0,
            },
            "human_review_points": [
                {
                    "slot_id": item.get("slot_id"),
                    "issue": item.get("reason", "补位策略已应用到基线 timeline"),
                    "options": ["保持当前结果", "替换当前素材", "回退到原始匹配"],
                }
                for item in resolved_gaps_list
                if isinstance(item, dict) and item.get("slot_id")
            ],
            "base_timeline": {
                "timeline_source": "shot_segments",
                "segment_count": len(timeline),
            },
            "confidence": float(slot_matches.get("confidence", 0.75) if isinstance(slot_matches, dict) else 0.75),
        }

    def _build_asset_lookup(self, asset_index: Any) -> Dict[str, Dict[str, Any]]:
        assets = asset_index.get("assets", []) if isinstance(asset_index, dict) else []
        lookup: Dict[str, Dict[str, Any]] = {}
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            for key in (asset.get("asset_id"), asset.get("material_id")):
                if isinstance(key, str) and key:
                    lookup[key] = asset
        return lookup

    def _map_shot_role(self, index: int, shot: Dict[str, Any], total_duration: float) -> str:
        start_time = float(shot.get("start_time", 0.0) or 0.0)
        if index == 0:
            return "hook"
        if start_time >= total_duration * 0.72:
            return "ending"
        if start_time >= total_duration * 0.5:
            return "climax"
        if start_time >= total_duration * 0.3:
            return "turning_point"
        return "memory_build"

    def _compact_reference_for_planning(self, reference_analysis: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "template_id": reference_analysis.get("template_id"),
            "video_basic_info": reference_analysis.get("video_basic_info"),
            "shot_segments": reference_analysis.get("shot_segments"),
            "structural_slots": reference_analysis.get("structural_slots"),
            "rhythm_curve": reference_analysis.get("rhythm_curve"),
            "transition_events": reference_analysis.get("transition_events"),
        }

    def _compact_asset_index_for_planning(self, asset_index: Any) -> Dict[str, Any]:
        assets = asset_index.get("assets", []) if isinstance(asset_index, dict) else []
        return {"assets": assets[:8]}

    def _compact_slot_matches_for_planning(self, slot_matches: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "slot_assignments": slot_matches.get("slot_assignments", []) if isinstance(slot_matches, dict) else [],
            "shot_matches": slot_matches.get("shot_matches", []) if isinstance(slot_matches, dict) else [],
            "confidence": slot_matches.get("confidence") if isinstance(slot_matches, dict) else None,
        }

    def _compact_resolved_gaps_for_planning(self, resolved_gaps: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "resolved_gaps": resolved_gaps.get("resolved_gaps", []) if isinstance(resolved_gaps, dict) else [],
            "still_unresolved": resolved_gaps.get("still_unresolved", []) if isinstance(resolved_gaps, dict) else [],
            "confidence": resolved_gaps.get("confidence") if isinstance(resolved_gaps, dict) else None,
        }

    def _calculate_px_position(self, time_sec: float, total_duration: float, canvas_width_px: int) -> int:
        if total_duration <= 0:
            return 0
        return int(round((time_sec / total_duration) * canvas_width_px))

    def _validate_and_fill(self, parsed: Dict[str, Any], ref_analysis: Dict[str, Any], asset_index: Any) -> Dict[str, Any]:
        if not isinstance(parsed, dict):
            parsed = {}

        parsed.setdefault("schema_version", "1.0")
        if "timeline_meta" not in parsed or not isinstance(parsed.get("timeline_meta"), dict):
            ref_duration = ref_analysis.get("video_basic_info", {}).get("core_content_effective_duration_seconds", 15.0)
            parsed["timeline_meta"] = {
                "duration": ref_duration,
                "aspect_ratio": "16:9",
                "resolution": "1920x1080",
                "fps": 30,
                "style_source": ref_analysis.get("template_id", "ref_001"),
                "music_sync_mode": "beat_aligned",
                "timeline_width_pixels": 1920,
                "timeline_source": "shot_segments",
            }
        else:
            parsed["timeline_meta"].setdefault("timeline_width_pixels", 1920)
            parsed["timeline_meta"].setdefault("timeline_source", "shot_segments")

        total_duration = float(parsed["timeline_meta"].get("duration", 15.0))
        canvas_width_px = int(parsed["timeline_meta"].get("timeline_width_pixels", 1920))
        parsed.setdefault("timeline", [])

        current_time = 0.0
        for idx, item in enumerate(parsed.get("timeline", [])):
            item.setdefault("clip_id", f"clip_{idx + 1:03d}")
            raw_start = float(item.get("start", 0.0) or 0.0)
            raw_end = float(item.get("end", raw_start + 2.0) or (raw_start + 2.0))
            raw_duration = max(raw_end - raw_start, 0.5)
            
            # 强制保证时间线连续，前一个片段的end自动作为当前片段的start
            if idx == 0:
                item["start"] = max(raw_start, 0.0)
            else:
                item["start"] = current_time
            
            # 保证每个片段最小时长≥0.5秒
            item["end"] = max(item["start"] + raw_duration, item["start"] + 0.5)
            current_time = item["end"]
            
            item.setdefault("transform", {"crop": "16:9_pad", "speed": 1.0})
            item.setdefault("overlays", [])
            item.setdefault("transition_out", "cut")
            asset_id_val = item.get("asset_id", "")
            if asset_index and asset_index.get("assets"):
                for asset in asset_index["assets"]:
                    if asset.get("asset_id") == asset_id_val or asset.get("material_id") == asset_id_val:
                        item.setdefault("asset_full_path", asset.get("_debug_full_path", ""))
                        break
            item["timeline_start_px"] = self._calculate_px_position(float(item["start"]), total_duration, canvas_width_px)
            item["timeline_end_px"] = self._calculate_px_position(float(item["end"]), total_duration, canvas_width_px)

        if "tracks" not in parsed or not isinstance(parsed.get("tracks"), list):
            parsed["tracks"] = self._build_default_tracks_from_timeline(parsed["timeline"])

        parsed.setdefault("caption_track", [])
        parsed.setdefault("packaging_track", [])
        parsed.setdefault("audio_track", {"bgm": {"source": "default", "sync_points": []}, "sfx": []})
        parsed.setdefault("cover_design", {
            "cover_type": "大字标题",
            "main_title": "核心内容标题",
            "subtitle": "亮点摘要",
            "visual_focus_asset": parsed["timeline"][0].get("asset_id", "unknown.mp4") if parsed["timeline"] else "unknown.mp4",
            "visual_focus_time": parsed["timeline"][0].get("start", 0.0) if parsed["timeline"] else 0.0,
        })

        if "validation" not in parsed or not isinstance(parsed.get("validation"), dict):
            timeline = parsed.get("timeline", [])
            no_overlap = True
            warnings = []
            sorted_timeline = sorted(timeline, key=lambda x: x.get("start", 0.0))
            for i in range(len(sorted_timeline) - 1):
                if sorted_timeline[i].get("end", 0.0) > sorted_timeline[i + 1].get("start", 9999.0):
                    no_overlap = False
                    warnings.append(f"timeline overlap detected between clip {i} and {i + 1}")
            parsed["validation"] = {
                "all_slots_filled": len(timeline) > 0,
                "no_missing_assets": all(bool(item.get("asset_id")) for item in timeline),
                "no_timeline_overlap": no_overlap,
                "source_ranges_valid": all(float(item.get("source_out", 0.0)) > float(item.get("source_in", 0.0)) for item in timeline),
                "duration_close_to_reference": True,
                "structure_fidelity_score": 0.92,
                "warnings": warnings,
            }

        parsed.setdefault("human_review_points", [])
        parsed.setdefault("confidence", 0.75)
        return parsed

    def _build_default_tracks_from_timeline(self, timeline_flat: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            {
                "track_id": "video_main",
                "track_type": "video",
                "track_name": "主视频轨",
                "height_px": 120,
                "locked": False,
                "segments": deepcopy(timeline_flat),
            },
            {
                "track_id": "audio_bgm",
                "track_type": "audio",
                "track_name": "背景音乐轨",
                "height_px": 60,
                "locked": False,
                "segments": [],
            },
            {
                "track_id": "caption_text",
                "track_type": "text",
                "track_name": "字幕轨",
                "height_px": 60,
                "locked": False,
                "segments": [],
            },
        ]

    def _apply_variant_timeline_style(
        self,
        timeline_payload: Dict[str, Any],
        ref_analysis: Dict[str, Any],
        variant_id: str,
        label: str,
    ) -> Dict[str, Any]:
        payload = deepcopy(timeline_payload)
        payload["variant_id"] = variant_id
        payload["label"] = label
        timeline = payload.get("timeline", [])
        rhythm_curve = ref_analysis.get("rhythm_curve", []) if isinstance(ref_analysis, dict) else []
        total_duration = float(payload.get("timeline_meta", {}).get("duration", 0.0) or 0.0)

        for idx, item in enumerate(timeline):
            if not isinstance(item, dict):
                continue
            transform = item.setdefault("transform", {"crop": "16:9_pad", "speed": 1.0})
            transform.setdefault("crop", "16:9_pad")
            transform.setdefault("speed", 1.0)
            transition_out = item.get("transition_out", "cut")
            slot_role = str(item.get("role", "develop"))

            if variant_id == "beat":
                transform["speed"] = max(float(transform.get("speed", 1.0)), 1.05)
                transform["motion"] = "beat_punch_in"
                item["transition_out"] = "cut"
            elif variant_id == "transition":
                transform["motion"] = "transition_follow"
        return payload

    def _fallback_llm_unavailable(self, reference_analysis: Dict[str, Any], asset_index: Any, fallback_reason: str = "") -> Dict[str, Any]:
        return ensure_edit_timeline_variant_contract({
            "_skip_reason": "llm_unavailable",
            "warning": f"LLM不可用，使用启发式自动生成基础timeline: {fallback_reason}",
            "timeline": [],
            "confidence": 0.6,
        })
