from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

from backend.app.agents.base_agent import BaseAgent

if TYPE_CHECKING:
    from backend.app.core.shared_memory import SessionSharedMemory


class GeneratedAssetBuilderAgent(BaseAgent):
    """Execute generation of AIGC assets that GapResolver planned.
    Fills the gap between gap_resolver and edit_planner, ensures all dynamic resources are actually generated before timeline building.
    """

    read_keys = ["resolved_gaps", "asset_index"]
    write_keys = ["generated_assets"]

    def __init__(self, generated_asset_factory=None):
        super().__init__()
        self.generated_asset_factory = generated_asset_factory

    def is_available(self) -> bool:
        return self.generated_asset_factory is not None

    def _choose_vision_supplement_mode(self, slot: Dict[str, Any], asset_status: Dict[str, Any]) -> str:
        """根据 slot 属性自动选择最合适的 VisualSupplement 生成模式"""
        slot_role = str(slot.get("role", ""))
        required_visual_type = slot.get("required_visual_type", []) if isinstance(slot.get("required_visual_type"), list) else []

        if slot_role == "hook" and asset_status.get("no_strong_hook", False):
            return "missing_hook"
        if asset_status.get("has_image_only", False):
            return "image_motion"
        if slot.get("transition_out") in ["blur", "zoom_cut", "whip_pan"] and asset_status.get("transition_not_smooth", False):
            return "transition_clip"
        if any("产品" in str(vt) or "商品" in str(vt) for vt in required_visual_type):
            return "product_motion"
        return "slot_fill"

    def analyze(self, shared_memory: SessionSharedMemory) -> Dict[str, Any]:
        resolved_gaps = shared_memory.get("resolved_gaps") or {}
        asset_index = shared_memory.get("asset_index") or {"assets": []}
        reference_analysis = shared_memory.get("reference_analysis") or {}
        gaps_list: List[Dict[str, Any]] = resolved_gaps.get("resolved_gaps", []) if isinstance(resolved_gaps, dict) else []

        style_context = {}
        if isinstance(reference_analysis, dict):
            vid_basic = reference_analysis.get("video_basic_info", {}) if isinstance(reference_analysis.get("video_basic_info"), dict) else {}
            style_context["style_name"] = vid_basic.get("type_label", "general_film")

        self.emit_phase("think", "准备动态资源生成", f"扫描 {len(gaps_list)} 个规划的gap，识别需要生成的动态资源。")

        new_assets_added: List[Dict[str, Any]] = []
        skip_count = 0
        generated_count = 0
        failed_count = 0

        for gap in gaps_list:
            if not isinstance(gap, dict):
                continue
            resolution = gap.get("resolution", {}) if isinstance(gap.get("resolution"), dict) else {}
            chosen_strategy = str(gap.get("chosen_strategy", ""))
            new_slot_type = str(resolution.get("new_slot_type", ""))
            asset_ref = resolution.get("asset_ref", {}) if isinstance(resolution.get("asset_ref"), dict) else {}

            if asset_ref and isinstance(asset_ref, dict) and asset_ref.get("asset_id"):
                skip_count += 1
                continue

            if new_slot_type == "text_card":
                self.emit_phase("action", "生成文字卡片资源", f"生成slot={gap.get('slot', 'unknown')} 的文字卡片。")
                edit_params = resolution.get("edit_params", {}) if isinstance(resolution.get("edit_params"), dict) else {}
                overlay_text = str(edit_params.get("overlay_text", "点击关注"))
                duration_seconds = float(edit_params.get("duration", 2.0))
                try:
                    if self.is_available():
                        result = self.generated_asset_factory.generate_text_card(
                            shared_memory=shared_memory,
                            text_content=overlay_text,
                            duration_seconds=max(1.0, min(duration_seconds, 5.0))
                        )
                        new_asset_id = result.get("asset_id")
                        resolution["asset_ref"] = {
                            "asset_id": new_asset_id,
                            "segment_id": "gen_auto_text_card",
                            "source_in": 0.0,
                            "source_out": max(1.0, min(duration_seconds, 5.0))
                        }
                        new_assets_added.append(result)
                        generated_count += 1
                    else:
                        self.emit_phase("observation", "跳过资源生成", "GeneratedAssetFactory 未配置，文字卡片资源生成降级跳过。")
                        failed_count += 1
                except Exception as e:
                    self.emit_phase("observation", "生成资源失败", f"text_card 生成失败: {str(e)[:80]}，跳过该资源。")
                    failed_count += 1
                continue

            if chosen_strategy == "ai_generate":
                self.emit_phase("action", "启动AI视频生成", f"slot={gap.get('slot', 'unknown')} 需要补充缺失素材。")
                gap_slot = {
                    "role": gap.get("slot", "general"),
                    "duration": 2.5,
                    "required_visual_type": gap.get("required_visual_type", []),
                    "required_motion": gap.get("required_motion", ["natural"]),
                    "transition_out": gap.get("transition_out", "dissolve"),
                    "creative_function": gap.get("creative_function", ""),
                    "information_function": gap.get("information_function", ""),
                    "shot_size": gap.get("shot_size", ["medium"]),
                }
                mode = self._choose_vision_supplement_mode(gap_slot, {})

                prompt_text = f"""生成一段符合以下要求的短视频片段:
视觉需求: {','.join(gap_slot.get('required_visual_type', []))}
运动方式: {','.join(gap_slot.get('required_motion', []))}
时长: 2.5秒
画幅: 9:16
不要水印、不要乱码文字、不要无关Logo。
风格: {style_context.get('style_name', 'realistic_film')}
"""
                try:
                    if self.is_available():
                        result = self.generated_asset_factory.generate_ai_video_by_prompt(
                            shared_memory=shared_memory,
                            mode=mode,
                            prompt_text=prompt_text,
                            slot_role=str(gap.get("slot", "general")),
                            duration_seconds=2.5,
                            style_name=style_context.get("style_name", "film"),
                        )
                        if result.get("status") in ["success", "degraded_no_api_key"] or result.get("asset_id"):
                            new_asset_id = result.get("asset_id")
                            resolution["asset_ref"] = {
                                "asset_id": new_asset_id,
                                "segment_id": "gen_ai_supplement",
                                "source_in": 0.0,
                                "source_out": 2.5,
                            }
                            new_assets_added.append(result)
                            generated_count += 1
                        else:
                            failed_count += 1
                    else:
                        self.emit_phase("observation", "AI生成降级", "Factory 未配置，跳过AI视频生成。")
                        failed_count += 1
                except Exception as e:
                    self.emit_phase("observation", "AI视频生成异常", f"ai_generate 失败: {str(e)[:80]}")
                    failed_count += 1
                continue

            skip_count += 1

        if "assets" not in asset_index or not isinstance(asset_index["assets"], list):
            asset_index["assets"] = []
        for new_asset in new_assets_added:
            asset_id_val = new_asset.get("asset_id")
            already_exists = any(a.get("asset_id") == asset_id_val for a in asset_index["assets"])
            if not already_exists:
                asset_index["assets"].append(new_asset)

        self.emit_phase("observation", "资源生成完成", f"跳过={skip_count}, 成功生成={generated_count}, 失败={failed_count}。总计资产数={len(asset_index['assets'])}。")

        return {
            "schema_version": "1.0",
            "generated_assets_count": generated_count,
            "skipped_count": skip_count,
            "failed_count": failed_count,
            "new_assets": new_assets_added,
            "asset_index_updated": True,
        }
