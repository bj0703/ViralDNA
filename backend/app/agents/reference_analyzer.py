from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from backend.app.prompts.reference_analyzer import REFERENCE_ANALYZER_SYSTEM_PROMPT
from backend.app.providers.ark_chat import ArkChatProvider


class ReferenceAnalyzerAgent:
    """Analyze a reference video using the fixed prompt and JSON repair steps."""

    def __init__(self, ark_chat_provider: ArkChatProvider) -> None:
        self.ark_chat_provider = ark_chat_provider

    def is_available(self) -> bool:
        return self.ark_chat_provider.config.is_configured

    def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_available():
            raise RuntimeError("ReferenceAnalyzerAgent is not configured.")

        user_prompt = self._build_user_prompt(context)
        response_json = self.ark_chat_provider.chat(
            REFERENCE_ANALYZER_SYSTEM_PROMPT,
            user_prompt,
            max_tokens=1200,
            temperature=0.1,
        )
        content = self.ark_chat_provider.extract_text(response_json)
        parsed, repair_notes = self._parse_and_repair(content)
        validated = self._validate_and_fill(parsed, context)
        validated["_agent_meta"] = {
            "source": "reference-analyzer-agent",
            "repair_notes": repair_notes,
            "raw_model_output": content,
        }
        return validated

    def _build_user_prompt(self, context: Dict[str, Any]) -> str:
        return json.dumps(
            {
                "task": "请基于以下样例视频上下文完成严格 JSON 输出。若上下文中有启发式结果，它们仅作为辅助，不可机械照搬。",
                "video_context": context,
                "constraints": {
                    "must_return_pure_json": True,
                    "must_choose_single_type_label": True,
                    "ignore_watermarks": True,
                    "trim_invalid_outro": True,
                },
            },
            ensure_ascii=False,
        )

    def _parse_and_repair(self, content: str) -> (Dict[str, Any], List[str]):
        repair_notes: List[str] = []
        json_candidate = self._extract_json(content)
        if json_candidate != content:
            repair_notes.append("已从模型输出中提取 JSON 主体。")
        try:
            return json.loads(json_candidate), repair_notes
        except json.JSONDecodeError:
            repaired = self._light_repair(json_candidate)
            if repaired != json_candidate:
                repair_notes.append("已执行轻量 JSON 修复。")
            return json.loads(repaired), repair_notes

    def _extract_json(self, content: str) -> str:
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise RuntimeError("ReferenceAnalyzerAgent did not return JSON content.")
        return content[start : end + 1]

    def _light_repair(self, content: str) -> str:
        repaired = content.replace("```json", "").replace("```", "").strip()
        repaired = repaired.replace("\u201c", '"').replace("\u201d", '"')
        repaired = repaired.replace("\u2018", '"').replace("\u2019", '"')
        repaired = repaired.replace(": null", ": null")
        return repaired

    def _validate_and_fill(self, parsed: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(parsed, dict):
            raise RuntimeError("ReferenceAnalyzerAgent JSON root must be an object.")

        allowed_labels = [
            "旅游转场",
            "vlog旅拍",
            "口播带货",
            "剧情种草",
            "product展示",
            "教程教学",
            "快剪混剪",
            "生活记录",
            "风景短片",
        ]
        basic = parsed.setdefault("video_basic_info", {})
        heuristic = context.get("heuristic", {})
        duration = context.get("duration_seconds", 0.0)
        basic.setdefault("file_total_duration_seconds", duration)
        basic.setdefault(
            "core_content_effective_duration_seconds",
            max(0.0, duration - 2.0),
        )
        basic.setdefault("outro_start_time_seconds", None)
        if basic.get("type_label") not in allowed_labels:
            basic["type_label"] = heuristic.get("fallback_type_label", "生活记录")

        script = parsed.setdefault("script_structure", {})
        script.setdefault("summary", "该视频通过开场吸引、中段展开和结尾收束完成叙事。")
        paragraphs = script.get("paragraphs")
        if not isinstance(paragraphs, list) or not paragraphs:
            script["paragraphs"] = heuristic.get("fallback_paragraphs", [])

        rhythm = parsed.setdefault("rhythm_structure", {})
        rhythm.setdefault("total_effective_shots", max(1, len(script["paragraphs"]) * 3))
        rhythm.setdefault("avg_shot_duration_seconds", round(max(duration / max(rhythm["total_effective_shots"], 1), 0.5), 2))
        rhythm.setdefault("shot_switch_pacing", "中等")
        rhythm.setdefault("highlight_position_seconds", [round(duration * 0.72, 2)] if duration else [0.0])
        rhythm.setdefault("pace_changes_description", "节奏从开场提速，在中段稳定展开，结尾进行收束。")

        packaging = parsed.setdefault("packaging_and_sound", {})
        packaging.setdefault("subtitle_density", "低密度")
        packaging.setdefault("visual_elements", "存在基础字幕和标题强化元素。")
        packaging.setdefault("transitions_feature", "转场较自然，以常规剪切为主。")
        packaging.setdefault("audio_and_sfx", "BGM 与画面节奏基本同步。")
        packaging.setdefault("cover_style", "动态封面")

        migration = parsed.get("migration_suggestion")
        if not isinstance(migration, list) or len(migration) < 2:
            parsed["migration_suggestion"] = [
                "核心要点1：保留开场吸睛结构并快速建立主题。",
                "核心要点2：根据目标受众调整节奏和 CTA 强度。",
            ]
        return parsed
