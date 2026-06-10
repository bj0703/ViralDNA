from __future__ import annotations

from copy import deepcopy
import json
from typing import TYPE_CHECKING, Any, Dict, List

from backend.app.agents.base_agent import BaseAgent
from backend.app.core.multi_variant import (
    VARIANT_ORDER,
    ensure_slot_match_variant_contract,
    get_variant_catalog,
)
from backend.app.prompts.slot_matcher import SLOT_MATCHER_PROMPT
from backend.app.providers.ark_chat import ArkChatProvider

if TYPE_CHECKING:
    from backend.app.core.shared_memory import SessionSharedMemory


class SlotMatcherAgent(BaseAgent):
    """素材槽位匹配专家，把素材分配到爆款结构的对应槽位"""

    read_keys = ["reference_analysis", "asset_index"]
    write_keys = ["slot_matches"]

    def __init__(self, ark_chat_provider: ArkChatProvider):
        super().__init__()
        self.ark_chat_provider = ark_chat_provider

    def is_available(self) -> bool:
        return self.ark_chat_provider.config.is_configured

    def analyze(self, shared_memory: SessionSharedMemory) -> Dict[str, Any]:
        reference_analysis = shared_memory.get("reference_analysis")
        asset_index = shared_memory.get("asset_index")
        self.emit_phase("think", "读取上下文", "准备结合参考结构与素材库执行插槽匹配。")

        if not reference_analysis or not asset_index:
            return self._fallback_missing_dependency()

        # 获取结构化 slots
        structural_slots = reference_analysis.get("structural_slots", [])
        if not structural_slots:
            # 容错：从旧的 script_structure paragraphs 生成 slots
            structural_slots = self._generate_slots_from_paragraphs(reference_analysis)

        # 获取完整素材 segments
        assets = asset_index.get("assets", [])
        all_segments_flat = []
        for asset in assets:
            segs = asset.get("segments", [])
            if segs and isinstance(segs, list):
                all_segments_flat.extend(segs)

        if not assets:
            return self._fallback_no_assets(structural_slots, reference_analysis)

        if not self.is_available():
            return self._fallback_llm_unavailable(structural_slots, assets, reference_analysis)

        # 获取逐镜头序列
        shot_segments = reference_analysis.get("shot_segments", []) if isinstance(reference_analysis, dict) else []
        try:
            self.emit_phase(
                "plan",
                "建立匹配目标",
                f"本轮需要匹配 {len(shot_segments)} 个镜头，候选素材 {len(assets)} 条。",
            )
            compact_assets = self._compact_assets_for_matching(assets)
            user_prompt = json.dumps({
                "task": "基于以下完整 shot_segments 逐镜头序列和素材片段库，直接为每一个镜头选择最合适的素材片段，直接生成shot_matches数组。",
                "shot_segments": shot_segments,
                "all_assets_with_segments": compact_assets,
                "constraints": {
                    "must_use_real_ids": True,
                    "no_fabricated_ids": True,
                    "prioritize_shot_centered": True,
                    "forbid_duplicate_material": True
                }
            }, ensure_ascii=False)

            self.emit_phase("action", "发起插槽匹配", "将插槽需求和素材分段列表发送给模型，生成匹配方案。")
            response_json = self.ark_chat_provider.chat(
                SLOT_MATCHER_PROMPT,
                user_prompt,
                temperature=0.1,
                on_delta=self.emit_stream_delta,
            )
            content = self.ark_chat_provider.extract_text(response_json)
            self.emit_phase("observation", "校验匹配结果", "模型文本已返回，开始修复 JSON 并补全未匹配插槽。")
            parsed = self._parse_and_repair(content)
            validated = self._validate_and_fill(parsed, structural_slots, assets)
            validated = self._attach_variant_views(validated, structural_slots, assets, reference_analysis)
            validated["_agent_meta"] = {
                "source": "slot-matcher-agent",
                "matched_count": len(validated.get("slot_assignments", [])),
                "gap_count": len(validated.get("unfilled_slots", [])),
                "low_confidence_count": len(validated.get("low_confidence_slots", []))
            }
            return validated
        except Exception as exc:
            return self._fallback_llm_unavailable(structural_slots, assets, reference_analysis, fallback_reason=str(exc))

    def _parse_and_repair(self, content: str) -> Dict[str, Any]:
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise RuntimeError("SlotMatcherAgent no valid JSON")
        repaired = content[start:end + 1]
        repaired = repaired.replace("```json", "").replace("```", "").strip()
        repaired = repaired.replace("\u201c", '"').replace("\u201d", '"')
        repaired = repaired.replace("\u2018", '"').replace("\u2019", '"')
        return json.loads(repaired)

    def _compact_assets_for_matching(self, assets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        compact_assets: List[Dict[str, Any]] = []
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            compact_segments: List[Dict[str, Any]] = []
            for segment in asset.get("segments", []):
                if not isinstance(segment, dict):
                    continue
                compact_segments.append({
                    "segment_id": segment.get("segment_id"),
                    "start": segment.get("start", segment.get("start_time")),
                    "end": segment.get("end", segment.get("end_time")),
                    "duration": segment.get("duration"),
                    "content_type": segment.get("content_type"),
                    "subjects": segment.get("subjects"),
                    "action": segment.get("action"),
                    "scene": segment.get("scene"),
                    "shot_size": segment.get("shot_size"),
                    "camera_motion": segment.get("camera_motion"),
                    "motion_intensity": segment.get("motion_intensity"),
                    "best_for_roles": segment.get("best_for_roles"),
                    "best_for_slot_types": segment.get("best_for_slot_types"),
                    "can_reuse_by": segment.get("can_reuse_by"),
                    "confidence": segment.get("confidence"),
                })

            compact_assets.append({
                "asset_id": asset.get("asset_id"),
                "material_id": asset.get("material_id"),
                "duration": asset.get("duration"),
                "content_type": asset.get("content_type"),
                "global_description": asset.get("global_description"),
                "suggested_usage": asset.get("suggested_usage"),
                "tags": asset.get("tags"),
                "segments": compact_segments,
            })
        return compact_assets

    def _validate_and_fill(self, parsed: Dict[str, Any], slots: List[Dict[str, Any]], assets: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not isinstance(parsed, dict):
            parsed = {}

        parsed.setdefault("schema_version", "1.0")
        parsed.setdefault("template_id", "ref_001")
        parsed.setdefault("slot_assignments", [])
        parsed.setdefault("shot_matches", [])
        parsed.setdefault("unfilled_slots", [])
        parsed.setdefault("low_confidence_slots", [])
        parsed.setdefault("confidence", 0.7)

        # 向后兼容：生成旧的 matches 字段，slot_id做简单格式兼容
        old_matches = []
        for assign in parsed.get("slot_assignments", []):
            cand = assign.get("selected_candidate", {})
            old_matches.append({
                "slot": assign.get("slot_id", "unknown"),
                "material_id": cand.get("asset_id", "unknown"),
                "reason": assign.get("reason", "智能匹配")
            })
        parsed["matches"] = old_matches

        # 向后兼容：生成旧的 gaps 字段
        old_gaps = []
        for unfilled in parsed.get("unfilled_slots", []):
            old_gaps.append({
                "slot": unfilled.get("slot_id", "unknown"),
                "need": unfilled.get("need", "需要适配素材")
            })
        parsed["gaps"] = old_gaps

        # 补全所有未分配的 slots 到 unfilled_slots
        assigned_slot_ids = {a.get("slot_id") for a in parsed.get("slot_assignments", [])}
        for slot in slots:
            sid = slot.get("slot_id")
            if sid and sid not in assigned_slot_ids and not any(u.get("slot_id") == sid for u in parsed.get("unfilled_slots", [])):
                parsed["unfilled_slots"].append({
                    "slot_id": sid,
                    "need": f"适配 {slot.get('role', 'develop')} 场景素材",
                    "missing_reason": "未在素材库中找到明确匹配片段",
                    "suggested_gap_strategies": ["reuse", "text_card", "structure_reorder"]
                })

        return parsed

    def _attach_variant_views(
        self,
        llm_raw_result: Dict[str, Any],
        slots: List[Dict[str, Any]],
        assets: List[Dict[str, Any]],
        reference_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        # 建立asset查找表，自动补全全路径
        asset_lookup: Dict[str, Dict[str, Any]] = {}
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            for key in (asset.get("asset_id"), asset.get("material_id")):
                if isinstance(key, str) and key:
                    asset_lookup[key] = asset

        # 100%直接使用LLM返回的shot_matches，只补全asset_full_path
        shot_matches_from_llm = llm_raw_result.get("shot_matches", [])
        for shot_match in shot_matches_from_llm:
            if isinstance(shot_match, dict):
                asset_id = str(shot_match.get("matched_asset_id", ""))
                asset_obj = asset_lookup.get(asset_id, {})
                shot_match["asset_full_path"] = asset_obj.get("_debug_full_path", "")

        # 基线版直接用LLM输出，没有任何派生
        structure_payload = deepcopy(llm_raw_result)
        structure_payload["shot_matches"] = shot_matches_from_llm
        structure_payload["variant_focus"] = "structure"
        structure_payload["variant_label"] = "结构优先版"

        variant_payloads: Dict[str, Dict[str, Any]] = {
            "structure": structure_payload
        }
        
        # 其他3个变体懒加载占位
        variants_from_llm = llm_raw_result.get("variants", {})
        for variant_id in ["beat", "transition", "rhythm"]:
            if variant_id in variants_from_llm:
                variant_payloads[variant_id] = variants_from_llm[variant_id]
                variant_payloads[variant_id]["_lazy"] = True
                variant_payloads[variant_id]["_note"] = "变体尚未生成timeline，调用生成接口后自动执行"
                variant_payloads[variant_id]["ready"] = False
        
        return ensure_slot_match_variant_contract(
            {
                "schema_version": "2.0",
                "template_id": llm_raw_result.get("template_id", "ref_001"),
                "default_variant_id": "structure",
                "variants": variant_payloads,
            },
            reference_analysis=reference_analysis,
        )

    def _derive_variant_payload(
        self,
        base_payload: Dict[str, Any],
        slots: List[Dict[str, Any]],
        assets: List[Dict[str, Any]],
        variant_id: str,
        label: str,
    ) -> Dict[str, Any]:
        payload = deepcopy(base_payload)
        asset_offset = VARIANT_ORDER.index(variant_id) if variant_id in VARIANT_ORDER else 0
        slot_lookup = {
            str(slot.get("slot_id")): slot
            for slot in slots
            if isinstance(slot, dict) and slot.get("slot_id") is not None
        }

        updated_assignments: List[Dict[str, Any]] = []
        for assignment in payload.get("slot_assignments", []):
            if not isinstance(assignment, dict):
                continue
            updated = deepcopy(assignment)
            slot_id = str(updated.get("slot_id", ""))
            slot_meta = slot_lookup.get(slot_id, {})
            updated["reason"] = self._build_variant_reason(variant_id, label, updated.get("reason", ""), slot_meta)
            updated["score_breakdown"] = self._variant_score_breakdown(
                variant_id,
                updated.get("score_breakdown", {}),
            )
            updated["match_score"] = round(self._variant_match_score(variant_id, updated.get("match_score", 0.7)), 2)
            updated["adaptation_plan"] = self._variant_adaptation_plan(
                variant_id,
                updated.get("adaptation_plan", {}),
                slot_meta,
            )

            selected_candidate = updated.get("selected_candidate")
            if isinstance(selected_candidate, dict):
                updated["selected_candidate"] = self._remap_candidate_for_variant(selected_candidate, assets, asset_offset)
            updated_assignments.append(updated)

        payload["slot_assignments"] = updated_assignments
        payload["matches"] = [
            {
                "slot": assign.get("slot_id", "unknown"),
                "material_id": assign.get("selected_candidate", {}).get("asset_id", "unknown"),
                "reason": assign.get("reason", "智能匹配"),
            }
            for assign in updated_assignments
        ]
        payload["confidence"] = round(self._variant_match_score(variant_id, payload.get("confidence", 0.7)), 2)
        return payload

    def _build_variant_reason(
        self,
        variant_id: str,
        label: str,
        existing_reason: Any,
        slot_meta: Dict[str, Any],
    ) -> str:
        base_reason = str(existing_reason or "智能匹配")
        if variant_id == "beat":
            return f"{label}：优先对齐 {slot_meta.get('audio_sync', {}).get('beat_position', '节拍落点')}，{base_reason}"
        if variant_id == "transition":
            return f"{label}：优先保持 {slot_meta.get('transition_out', 'cut')} 转场连续性，{base_reason}"
        if variant_id == "rhythm":
            return f"{label}：优先匹配节奏推进与镜头密度，{base_reason}"
        return f"{label}：优先保持结构角色与信息功能，{base_reason}"

    def _variant_score_breakdown(self, variant_id: str, score_breakdown: Any) -> Dict[str, Any]:
        breakdown = deepcopy(score_breakdown) if isinstance(score_breakdown, dict) else {}
        if variant_id == "beat":
            breakdown["beat_fit"] = 0.88
            breakdown["duration_fit"] = max(float(breakdown.get("duration_fit", 0.7)), 0.82)
            breakdown["motion_fit"] = max(float(breakdown.get("motion_fit", 0.7)), 0.8)
        elif variant_id == "transition":
            breakdown["transition_fit"] = 0.86
            breakdown["style_fit"] = max(float(breakdown.get("style_fit", 0.7)), 0.84)
        elif variant_id == "rhythm":
            breakdown["pace_fit"] = 0.87
            breakdown["density_fit"] = 0.83
        else:
            breakdown["semantic_fit"] = max(float(breakdown.get("semantic_fit", 0.7)), 0.84)
            breakdown["visual_fit"] = max(float(breakdown.get("visual_fit", 0.7)), 0.8)
        return breakdown

    def _variant_match_score(self, variant_id: str, score: Any) -> float:
        base_score = float(score) if isinstance(score, (int, float)) else 0.7
        if variant_id == "structure":
            return min(0.95, base_score + 0.06)
        if variant_id == "beat":
            return min(0.93, base_score + 0.04)
        if variant_id == "transition":
            return min(0.91, base_score + 0.02)
        if variant_id == "rhythm":
            return min(0.92, base_score + 0.03)
        return base_score

    def _variant_adaptation_plan(self, variant_id: str, adaptation_plan: Any, slot_meta: Dict[str, Any]) -> Dict[str, Any]:
        plan = deepcopy(adaptation_plan) if isinstance(adaptation_plan, dict) else {}
        plan.setdefault("crop", "16:9_pad")
        plan.setdefault("speed", 1.0)
        plan.setdefault("motion", "none")
        if variant_id == "beat":
            plan["speed"] = 1.08
            plan["motion"] = "beat_push"
        elif variant_id == "transition":
            plan["motion"] = f"transition_{slot_meta.get('transition_out', 'cut')}"
        elif variant_id == "rhythm":
            plan["speed"] = 0.96 if slot_meta.get("importance") == "high" else 1.03
            plan["motion"] = "rhythm_follow"
        return plan

    def _remap_candidate_for_variant(
        self,
        selected_candidate: Dict[str, Any],
        assets: List[Dict[str, Any]],
        offset: int,
    ) -> Dict[str, Any]:
        candidate = deepcopy(selected_candidate)
        if offset <= 0 or len(assets) <= 1:
            return candidate

        current_asset_id = str(candidate.get("asset_id", ""))
        asset_ids = [str(asset.get("material_id", asset.get("asset_id", ""))) for asset in assets]
        if current_asset_id not in asset_ids:
            return candidate

        target_asset = assets[(asset_ids.index(current_asset_id) + offset) % len(assets)]
        target_asset_id = target_asset.get("material_id", target_asset.get("asset_id", current_asset_id))
        target_segments = target_asset.get("segments", [])
        target_segment = target_segments[0] if target_segments else {}
        candidate["asset_id"] = target_asset_id
        if isinstance(target_segment, dict):
            candidate["segment_id"] = target_segment.get("segment_id", candidate.get("segment_id", "seg_01"))
            candidate["source_in"] = target_segment.get("start_time", candidate.get("source_in", 0.0))
            candidate["source_out"] = target_segment.get("end_time", candidate.get("source_out", 2.0))
        return candidate

    def _generate_slots_from_paragraphs(self, reference_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        paragraphs = reference_analysis.get("script_structure", {}).get("paragraphs", [])
        slots = []
        for idx, para in enumerate(paragraphs):
            slot_type = para.get("type", "develop")
            slots.append({
                "slot_id": f"{slot_type}_{str(idx + 1).zfill(2)}",
                "role": slot_type,
                "start_time": float(para.get("start_time", 0.0)),
                "end_time": float(para.get("end_time", 3.0)),
                "duration": float(para.get("end_time", 3.0)) - float(para.get("start_time", 0.0)),
                "creative_function": f"承担{slot_type}创作功能",
                "required_visual_type": ["通用画面"],
                "required_motion": "normal",
                "shot_size": "medium"
            })
        return slots

    def _fallback_missing_dependency(self) -> Dict[str, Any]:
        return ensure_slot_match_variant_contract({
            "_skip_reason": "missing_dependency",
            "warning": "缺少reference_analysis或asset_index，跳过SlotMatcherAgent",
            "slot_assignments": [],
            "unfilled_slots": [],
            "low_confidence_slots": [],
            "matches": [],
            "gaps": [],
            "confidence": 0.0
        })

    def _fallback_no_assets(self, slots: List[Dict[str, Any]], reference_analysis: Dict[str, Any]) -> Dict[str, Any]:
        gaps = []
        for s in slots:
            gaps.append({
                "slot_id": s.get("slot_id", "unknown"),
                "need": "无可用素材，全部为缺口",
                "missing_reason": "素材列表为空",
                "suggested_gap_strategies": ["text_card", "structure_reorder", "ask_user"]
            })
        old_gaps = [{"slot": g["slot_id"], "need": g["need"]} for g in gaps]
        return ensure_slot_match_variant_contract({
            "schema_version": "1.0",
            "template_id": "ref_001",
            "slot_assignments": [],
            "unfilled_slots": gaps,
            "low_confidence_slots": [],
            "matches": [],
            "gaps": old_gaps,
            "confidence": 0.0,
            "_warning": "素材列表为空，所有槽位均为缺口"
        }, reference_analysis=reference_analysis)

    def _fallback_llm_unavailable(
        self,
        slots: List[Dict[str, Any]],
        assets: List[Dict[str, Any]],
        reference_analysis: Dict[str, Any],
        fallback_reason: str = "",
    ) -> Dict[str, Any]:
        variant_payloads: Dict[str, Dict[str, Any]] = {}
        for variant_spec in get_variant_catalog(reference_analysis):
            offset = VARIANT_ORDER.index(variant_spec["variant_id"])
            assignments = []
            unfilled = []
            for idx, s in enumerate(slots):
                target_asset = assets[(idx + offset) % len(assets)] if assets else None
                if target_asset:
                    target_segments = target_asset.get("segments", [])
                    seg = target_segments[0] if target_segments else None
                    assignment = {
                        "slot_id": s.get("slot_id"),
                        "slot_role": s.get("role", "develop"),
                        "required_duration": s.get("duration", 2.0),
                        "selected_candidate": {
                            "asset_id": target_asset.get("material_id", "unknown.mp4"),
                            "segment_id": seg.get("segment_id", "seg_01") if seg else "seg_01",
                            "source_in": seg.get("start_time", 0.0) if isinstance(seg, dict) else 0.0,
                            "source_out": seg.get("end_time", min(2.0, target_asset.get("duration", 3.0))) if isinstance(seg, dict) else min(2.0, target_asset.get("duration", 3.0)),
                        },
                        "match_score": 0.65,
                        "score_breakdown": {"semantic_fit": 0.7, "visual_fit": 0.7, "duration_fit": 0.6, "motion_fit": 0.6, "style_fit": 0.6},
                        "adaptation_plan": {"crop": "16:9_pad", "speed": 1.0, "motion": "none"},
                        "reason": "LLM不可用，使用降级自动分配",
                        "confidence": 0.6,
                    }
                    assignments.append(assignment)
                else:
                    unfilled.append({
                        "slot_id": s.get("slot_id"),
                        "need": f"适配{s.get('role', 'develop')}场景素材",
                        "missing_reason": "无可用素材",
                        "suggested_gap_strategies": ["reuse", "text_card"]
                    })
            base_payload = {
                "schema_version": "1.0",
                "template_id": "ref_001",
                "slot_assignments": assignments,
                "unfilled_slots": unfilled,
                "low_confidence_slots": [],
                "matches": [{"slot": a["slot_id"], "material_id": a["selected_candidate"]["asset_id"], "reason": a["reason"]} for a in assignments],
                "gaps": [{"slot": u["slot_id"], "need": u["need"]} for u in unfilled],
                "confidence": 0.5,
                "_fallback": True,
                "_warning": "LLM不可用，使用降级自动分配"
            }
            variant_payloads[variant_spec["variant_id"]] = self._derive_variant_payload(
                base_payload,
                slots,
                assets,
                variant_spec["variant_id"],
                variant_spec["label"],
            )
        return ensure_slot_match_variant_contract({
            "schema_version": "2.0",
            "template_id": "ref_001",
            "default_variant_id": "structure",
            "variants": variant_payloads,
            "_fallback": True,
            "_warning": "LLM不可用，使用降级自动分配",
            "_fallback_reason": fallback_reason,
        }, reference_analysis=reference_analysis)
