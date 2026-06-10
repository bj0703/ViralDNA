from __future__ import annotations

import json
import logging
import time
import re
from pathlib import Path
from typing import Any, Dict, Optional, List

logger = logging.getLogger("KnowledgeBaseService")


class KnowledgeBaseService:
    """将 ReferenceAnalyzer 输出结果自动沉淀到知识库 style_templates 目录"""

    def __init__(self, kb_root: Optional[str] = None):
        if kb_root:
            self._kb_root = Path(kb_root)
        else:
            # backend/app/services/ 往上跳3层到项目根目录 emo_transfer/
            self._kb_root = Path(__file__).resolve().parents[3] / "knowledge_base"
        self._style_templates_dir = self._kb_root / "style_templates"
        logger.info(f"[KB_INIT] 知识库根目录: {self._kb_root}, 样式模板目录: {self._style_templates_dir}")
        self._style_templates_dir.mkdir(parents=True, exist_ok=True)

    def _generate_style_id(self, type_label: str) -> str:
        """根据type_label生成唯一的style_id，格式：style_<英文标识>_<三位序号>"""
        type_slug = re.sub(r'[^\w\u4e00-\u9fff]', '_', type_label.strip().lower())
        type_slug_en = {
            "旅游转场": "travel_transition",
            "vlog旅拍": "vlog_travel",
            "口播带货": "talking_product",
            "剧情种草": "story_seeding",
            "product展示": "product_showcase",
            "教程教学": "tutorial",
            "快剪混剪": "fast_montage",
            "生活记录": "daily_record",
            "风景短片": "landscape_short",
            "其他": "general"
        }.get(type_label, type_slug)

        existing_ids: List[int] = []
        for f in self._style_templates_dir.glob(f"{type_slug_en}_*.json"):
            match = re.search(r'_(\d{3})\.json$', f.name)
            if match:
                existing_ids.append(int(match.group(1)))

        next_seq = 1
        if existing_ids:
            next_seq = max(existing_ids) + 1
        return f"style_{type_slug_en}_{next_seq:03d}"

    def _normalize_reference_analysis_to_style_template(
        self,
        reference_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """将ReferenceAnalyzer输出结果归一化为标准StyleTemplate格式"""
        logger.info("[KB_NORMALIZE] 开始归一化 reference_analysis 到标准 style template")

        video_basic_info = reference_analysis.get("video_basic_info", {}) if isinstance(reference_analysis, dict) else {}
        type_label = str(video_basic_info.get("type_label", "其他"))

        rhythm_structure = reference_analysis.get("rhythm_structure", {}) if isinstance(reference_analysis, dict) else {}
        structural_slots = reference_analysis.get("structural_slots", []) if isinstance(reference_analysis, list) or isinstance(reference_analysis, dict) else []
        if not isinstance(structural_slots, list):
            structural_slots = []

        video_duration = float(video_basic_info.get("core_content_effective_duration_seconds", 15.0))

        style_id = self._generate_style_id(type_label)
        total_slot_duration = sum([float(s.get("duration", 0)) for s in structural_slots]) or video_duration

        transfer_rules = reference_analysis.get("transfer_rules", {}) if isinstance(reference_analysis, dict) else {}
        migration_suggestion = reference_analysis.get("migration_suggestion", []) if isinstance(reference_analysis, list) else []
        fallback_strategy = []
        for idx, sugg in enumerate(migration_suggestion):
            fallback_strategy.append({
                "problem": f"动态 fallback 策略 #{idx+1}",
                "solution": str(sugg)
            })

        embedding_text_parts = [
            f"style_name={type_label}",
            f"总时长={video_duration}秒",
            f"slot数量={len(structural_slots)}",
        ]
        for slot in structural_slots:
            if isinstance(slot, dict):
                embedding_text_parts.append(f"{slot.get('role', 'slot')}: {slot.get('creative_function', '')}")

        final_template = {
            "style_id": style_id,
            "style_name": type_label,
            "type_label": type_label,
            "aliases": [f"{type_label} 参考样例模板", f"auto_import_{int(time.time())}"],
            "target_duration_range": [int(max(video_duration - 3, 5)), int(video_duration + 5)],
            "aspect_ratio": "9:16",
            "core_formula": reference_analysis.get("script_structure", {}).get("summary", f"{len(structural_slots)}个slot剪辑公式"),
            "suitable_materials": [],
            "unsuitable_materials": [],
            "rhythm_structure": {
                "overall_pace": str(rhythm_structure.get("shot_switch_pacing", "中等节奏")),
                "avg_shot_duration_seconds": float(rhythm_structure.get("avg_shot_duration_seconds", 1.5)),
                "shot_switch_pacing": str(rhythm_structure.get("shot_switch_pacing", "每2秒切换一次镜头")),
                "highlight_position_ratio": [float(p) / video_duration for p in rhythm_structure.get("highlight_position_seconds", [0.2 * video_duration, 0.7 * video_duration])],
                "pace_changes_description": str(rhythm_structure.get("pace_changes_description", "无特殊节奏变化说明"))
            },
            "structural_slots": structural_slots,
            "caption_style_template": reference_analysis.get("caption_style_template", {
                "subtitle_density": "中等密度",
                "font_style": "常规无衬线",
                "keyword_highlight": True,
                "animation": "pop_in"
            }),
            "transition_style_template": reference_analysis.get("transition_style_template", {
                "main_transition_types": ["cut", "dissolve"],
                "usage_rule": "在信息转折或节奏重拍处使用转场",
                "fallback_transition_types": ["cut"]
            }),
            "packaging_style_template": reference_analysis.get("packaging_style_template", {
                "stickers": [],
                "cover_style": "大字标题 + 主体特写",
                "color_tone": "原生自然色调"
            }),
            "transfer_rules": {
                "must_keep": transfer_rules.get("must_keep", []),
                "can_adapt": transfer_rules.get("can_adapt", []),
                "must_not_copy": transfer_rules.get("must_not_copy", [])
            },
            "fallback_strategy": fallback_strategy,
            "embedding_text": " | ".join(embedding_text_parts)
        }

        logger.info(f"[KB_NORMALIZE] 归一化完成, style_id={style_id}, slot_count={len(structural_slots)}")
        return final_template

    def _check_duplicate(self, normalized_template: Dict[str, Any]) -> Optional[Path]:
        """检查知识库中是否已存在高度相似的重复模板，避免重复写入"""
        current_slots_count = len(normalized_template.get("structural_slots", []))
        current_type = normalized_template.get("type_label", "")

        for existing_file in self._style_templates_dir.glob("*.json"):
            try:
                with open(existing_file, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                if (
                    existing.get("type_label") == current_type
                    and abs(len(existing.get("structural_slots", [])) - current_slots_count) <= 1
                ):
                    logger.warning(f"[KB_DUPLICATE] 发现相似重复模板: {existing_file.name}")
                    return existing_file
            except Exception:
                continue
        return None

    def save_reference_analysis_to_kb(
        self,
        reference_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """主入口：将参考样例分析结果沉淀到知识库"""
        logger.info("[KB_SAVE] 开始执行参考样例沉淀流程")
        normalized = self._normalize_reference_analysis_to_style_template(reference_analysis)
        duplicate_file = self._check_duplicate(normalized)

        target_filename = f"{normalized['style_id']}.json"
        target_path = self._style_templates_dir / target_filename

        if duplicate_file:
            logger.info(f"[KB_SAVE] 覆盖相似重复模板 -> {duplicate_file.name}")
            target_path = duplicate_file

        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(normalized, f, ensure_ascii=False, indent=2)

        logger.info(f"[KB_SAVE] 沉淀成功，文件写入路径: {target_path}")
        return {
            "success": True,
            "style_id": normalized["style_id"],
            "target_file": str(target_path),
            "type_label": normalized["type_label"],
            "slot_count": len(normalized.get("structural_slots", [])),
            "is_duplicate_overwritten": duplicate_file is not None
        }
