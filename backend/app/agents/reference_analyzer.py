from __future__ import annotations

import ast
import json
import re
from typing import TYPE_CHECKING, Any, Dict, List

from backend.app.agents.base_agent import BaseAgent
from backend.app.core.multi_variant import ensure_reference_variant_contract
from backend.app.prompts.reference_analyzer import REFERENCE_ANALYZER_SYSTEM_PROMPT
from backend.app.providers.ark_chat import ArkChatProvider

if TYPE_CHECKING:
    from backend.app.core.shared_memory import SessionSharedMemory


class ReferenceAnalyzerAgent(BaseAgent):
    """Analyze a reference video using the fixed prompt and JSON repair steps."""

    read_keys = ["inputs.uploaded_videos"]
    write_keys = ["reference_analysis"]

    def __init__(self, ark_chat_provider: ArkChatProvider):
        super().__init__()
        self.ark_chat_provider = ark_chat_provider

    def is_available(self) -> bool:
        return self.ark_chat_provider.config.is_configured

    def analyze(self, shared_memory: SessionSharedMemory) -> Dict[str, Any]:
        import logging
        from backend.app.services.knowledge_base_retrieval_service import KnowledgeBaseRetrievalService

        logger = logging.getLogger("ReferenceAnalyzerAgent")
        uploaded_videos = shared_memory.get_nested("inputs.uploaded_videos")
        selected_reference_video_id = shared_memory.get_nested("inputs.selected_reference_video_id")
        reference_videos = [v for v in uploaded_videos if v.get("is_reference", False)]
        self.emit_phase("think", "读取参考视频", f"检测到 {len(reference_videos)} 条参考视频，准备确定本次解析目标。")

        if not reference_videos:
            logger.info("[RefAnalyzer_KB] 无参考样例视频，自动触发知识库检索模式")
            self.emit_phase("think", "检索知识库", "未检测到上传的参考样例视频，从知识库检索匹配的成熟剪辑模板。")
            user_input_prompt = shared_memory.get_nested("inputs.user_prompt") or ""
            logger.info(f"[RefAnalyzer_KB] 用户输入关键词: {user_input_prompt}")

            kb_service = KnowledgeBaseRetrievalService()
            retrieval_result = kb_service.retrieve_best_matching_template(str(user_input_prompt))
            logger.info(f"[RefAnalyzer_KB] 检索结果: matched={retrieval_result['matched']}, score={retrieval_result['match_score']}")
            shared_memory.append_event("knowledge_base_retrieval_done", "ReferenceAnalyzerAgent", retrieval_result)

            if retrieval_result["matched"] and retrieval_result["template"]:
                self.emit_phase("observation", "命中知识库模板", f"命中模板 {retrieval_result['style_id']}，通过LLM统一输出格式。")

                if not self.is_available():
                    logger.warning("[RefAnalyzer_KB] LLM未配置，直接使用知识库模板原始格式（可能导致后续Agent兼容问题）")
                    converted_analysis = kb_service.convert_style_template_to_reference_analysis(retrieval_result["template"])
                    converted_analysis["_agent_meta"] = {
                        "source": "knowledge_base_retrieval",
                        "input_modality": "style_keyword",
                        "style_id": retrieval_result["style_id"],
                        "match_score": retrieval_result["match_score"],
                    }
                    converted_analysis = ensure_reference_variant_contract(converted_analysis)
                    return converted_analysis

                self.emit_phase("action", "模板格式统一", "将知识库模板内容作为上下文，通过REFERENCE_ANALYZER_SYSTEM_PROMPT过一遍LLM，确保输出格式与正常解析完全一致。")

                kb_template = retrieval_result["template"]
                kb_user_prompt = self._build_knowledge_base_user_prompt(kb_template, str(user_input_prompt))

                try:
                    response_json = self.ark_chat_provider.chat(
                        REFERENCE_ANALYZER_SYSTEM_PROMPT,
                        kb_user_prompt,
                        temperature=0.1,
                        on_delta=self.emit_stream_delta,
                    )
                    content = self.ark_chat_provider.extract_text(response_json)
                    finish_reason = self.ark_chat_provider.extract_finish_reason(response_json)
                    self.emit_phase("observation", "整理LLM结果", "LLM文本已返回，开始提取JSON主体并补齐缺省字段。")

                    parsed, repair_notes = self._parse_and_repair(content)
                    kb_style_name = kb_template.get('style_name') or kb_template.get('type_label', '知识库模板')
                    context_for_fill = {
                        "filename": f"knowledge_base_{kb_template.get('style_id', 'kb_template')}",
                        "storage_path": "",
                        "content_type": "text/json",
                        "file_size_bytes": 0,
                        "notes": f"基于知识库模板 {kb_style_name}",
                    }
                    validated = self._validate_and_fill(parsed, context_for_fill)
                    validated = ensure_reference_variant_contract(validated)
                    validated["_agent_meta"] = {
                        "source": "knowledge_base_retrieval",
                        "input_modality": "style_keyword",
                        "style_id": retrieval_result["style_id"],
                        "match_score": retrieval_result["match_score"],
                        "repair_notes": repair_notes,
                        "raw_model_output": content,
                        "finish_reason": finish_reason,
                    }
                    logger.info(f"[RefAnalyzer_KB] 知识库模板经LLM统一格式完成，style_id={retrieval_result['style_id']}")
                    return validated
                except Exception as exc:
                    import traceback
                    logger.warning(f"[RefAnalyzer_KB] LLM统一格式失败，降级使用原始模板格式: {exc}")
                    print(f"[ERROR] RefAnalyzer_KB LLM调用失败 traceback: {traceback.format_exc()}")
                    converted_analysis = kb_service.convert_style_template_to_reference_analysis(retrieval_result["template"])
                    converted_analysis["_agent_meta"] = {
                        "source": "knowledge_base_retrieval_fallback",
                        "input_modality": "style_keyword",
                        "style_id": retrieval_result["style_id"],
                        "match_score": retrieval_result["match_score"],
                        "fallback_reason": str(exc),
                    }
                    converted_analysis = ensure_reference_variant_contract(converted_analysis)
                    return converted_analysis
            else:
                logger.warning("[RefAnalyzer_KB] 知识库检索未命中，返回标准跳过标记")
                return {
                    "_skip_reason": "no_reference_video_found_no_kb_match",
                    "warning": "未找到参考样例视频，且知识库无匹配模板"
                }

        primary_ref = next(
            (
                video for video in reference_videos
                if video.get("saved_filename") == selected_reference_video_id
            ),
            reference_videos[0],
        )
        context = {
            "filename": primary_ref.get("original_filename"),
            "storage_path": primary_ref.get("storage_path"),
            "content_type": primary_ref.get("content_type"),
            "file_size_bytes": primary_ref.get("file_size_bytes", 0),
            "notes": primary_ref.get("notes"),
        }
        self.emit_phase("plan", "锁定解析对象", f"优先解析选中的参考视频：{context.get('filename') or 'unknown'}。")

        if not self.is_available():
            raise RuntimeError("ReferenceAnalyzerAgent未配置，无法执行参考视频解析。")

        video_path = context.get("storage_path")
        if not isinstance(video_path, str) or not video_path:
            raise RuntimeError("ReferenceAnalyzerAgent requires a local video path.")

        user_prompt = self._build_user_prompt(context)
        self.emit_phase("action", "发起模型分析", "将视频上下文与结构化约束发送给模型，开始流式生成。")
        response_json = self.ark_chat_provider.analyze_video(
            REFERENCE_ANALYZER_SYSTEM_PROMPT,
            user_prompt,
            video_path=video_path,
            content_type=context.get("content_type"),
            temperature=0.1,
            on_delta=self.emit_stream_delta,
        )
        content = self.ark_chat_provider.extract_text(response_json)
        finish_reason = self.ark_chat_provider.extract_finish_reason(response_json)
        self.emit_phase("observation", "整理模型结果", "模型文本已返回，开始提取 JSON 主体并补齐缺省字段。")
        try:
            print("[DEBUG] Step 1: 开始调用 _parse_and_repair...")
            parsed, repair_notes = self._parse_and_repair(content)
            print(f"[DEBUG] Step 1 完成! parsed keys = {list(parsed.keys())}, repair_notes = {repair_notes}")
            
            print("[DEBUG] Step 2: 开始调用 _validate_and_fill...")
            validated = self._validate_and_fill(parsed, context)
            print(f"[DEBUG] Step 2 完成! validated confidence = {validated.get('confidence')}")
            
            print("[DEBUG] Step 3: 开始调用 ensure_reference_variant_contract...")
            validated = ensure_reference_variant_contract(validated)
            print("[DEBUG] Step 3 完成! 包装 agent_meta...")
            
            validated["_agent_meta"] = {
                "source": "reference-analyzer-agent",
                "input_modality": "video",
                "repair_notes": repair_notes,
                "raw_model_output": content,
                "finish_reason": finish_reason,
            }
            print("[DEBUG] 全部步骤执行成功，返回结果!")
            return validated
        except Exception as exc:
            import traceback
            print(f"[ERROR] ReferenceAnalyzerAgent 执行出错! traceback: {traceback.format_exc()}")
            raise RuntimeError(
                "ReferenceAnalyzerAgent解析失败，已取消自动降级。"
                f" finish_reason={finish_reason!r};"
                f" error={str(exc)};"
                f" raw_model_output={content}"
            ) from exc

    def _build_user_prompt(self, context: Dict[str, Any]) -> str:
        return json.dumps(
            {
                "task": "请基于以下样例视频上下文完成严格 JSON 输出。若上下文中有提示，它们仅作为辅助，不可机械照搬。",
                "analysis_instruction": context.get("notes"),
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

    def _build_knowledge_base_user_prompt(self, kb_template: Dict[str, Any], user_input: str) -> str:
        """将知识库模板内容格式化为文本上下文，作为LLM纯文本分析输入，确保输出格式与正常解析参考视频完全一致。"""
        type_label = kb_template.get("type_label", kb_template.get("style_name", "其他"))
        core_formula = kb_template.get("core_formula", "")
        structural_slots = kb_template.get("structural_slots", [])
        rhythm_structure = kb_template.get("rhythm_structure", {})
        caption_style = kb_template.get("caption_style_template", {})
        transition_style = kb_template.get("transition_style_template", {})
        packaging_style = kb_template.get("packaging_style_template", {})
        transfer_rules = kb_template.get("transfer_rules", {})
        fallback_strategy = kb_template.get("fallback_strategy", [])

        slots_text_parts = []
        for idx, slot in enumerate(structural_slots):
            if not isinstance(slot, dict):
                continue
            slot_role = slot.get("role", slot.get("slot_role", f"slot_{idx + 1}"))
            slot_duration = slot.get("duration", "")
            slot_info = [f"第{idx + 1}段[role={slot_role}]"]
            if slot_duration:
                slot_info.append(f"建议时长: {slot_duration}秒")
            if slot.get("creative_function"):
                slot_info.append(f"创意功能: {slot['creative_function']}")
            if slot.get("information_function"):
                slot_info.append(f"信息功能: {slot['information_function']}")
            if slot.get("required_visual_type"):
                vt = slot["required_visual_type"]
                if isinstance(vt, list):
                    slot_info.append(f"视觉类型: {', '.join([str(v) for v in vt])}")
                else:
                    slot_info.append(f"视觉类型: {vt}")
            if slot.get("required_motion"):
                slot_info.append(f"镜头运动: {slot['required_motion']}")
            if slot.get("shot_size"):
                slot_info.append(f"景别: {slot['shot_size']}")
            caption_req = slot.get("caption_requirement")
            if isinstance(caption_req, dict) and caption_req.get("need_caption"):
                caption_parts = []
                if caption_req.get("style"):
                    caption_parts.append(f"字幕样式: {caption_req['style']}")
                if caption_req.get("position"):
                    caption_parts.append(f"字幕位置: {caption_req['position']}")
                if caption_req.get("semantic_role"):
                    caption_parts.append(f"语义角色: {caption_req['semantic_role']}")
                if caption_parts:
                    slot_info.append(" | ".join(caption_parts))
            audio_sync = slot.get("audio_sync")
            if isinstance(audio_sync, dict):
                audio_parts = []
                if audio_sync.get("beat_position"):
                    audio_parts.append(f"卡点位置: {audio_sync['beat_position']}")
                if audio_sync.get("sfx"):
                    audio_parts.append(f"音效: {audio_sync['sfx']}")
                if audio_parts:
                    slot_info.append(" | ".join(audio_parts))
            if slot.get("transition_out"):
                slot_info.append(f"转场: {slot['transition_out']}")
            if slot.get("importance"):
                slot_info.append(f"重要性: {slot['importance']}")
            if slot.get("copy_risk"):
                slot_info.append(f"迁移提示: {slot['copy_risk']}")
            slots_text_parts.append("；".join(slot_info))

        migration_parts = []
        for item in fallback_strategy:
            if isinstance(item, dict):
                prob = item.get("problem", "")
                sol = item.get("solution", "")
                if prob and sol:
                    migration_parts.append(f"{prob} -> {sol}")
                elif prob:
                    migration_parts.append(prob)
                elif sol:
                    migration_parts.append(sol)
            elif isinstance(item, str):
                migration_parts.append(item)

        rhythm_parts = []
        if isinstance(rhythm_structure, dict):
            if rhythm_structure.get("overall_pace"):
                rhythm_parts.append(f"整体节奏: {rhythm_structure['overall_pace']}")
            if rhythm_structure.get("avg_shot_duration_seconds"):
                rhythm_parts.append(f"平均镜头时长: {rhythm_structure['avg_shot_duration_seconds']}秒")
            if rhythm_structure.get("shot_switch_pacing"):
                rhythm_parts.append(f"切换频率: {rhythm_structure['shot_switch_pacing']}")
            if rhythm_structure.get("highlight_position_ratio"):
                rhythm_parts.append(f"高光位置: {rhythm_structure['highlight_position_ratio']}")
            if rhythm_structure.get("pace_changes_description"):
                rhythm_parts.append(f"节奏变化: {rhythm_structure['pace_changes_description']}")

        caption_parts = []
        if isinstance(caption_style, dict):
            for k, v in caption_style.items():
                caption_parts.append(f"{k}={v}")

        transition_parts = []
        if isinstance(transition_style, dict):
            main_types = transition_style.get("main_transition_types", [])
            if isinstance(main_types, list) and main_types:
                transition_parts.append(f"主转场: {', '.join([str(t) for t in main_types])}")
            if transition_style.get("usage_rule"):
                transition_parts.append(f"使用规则: {transition_style['usage_rule']}")
            fb_types = transition_style.get("fallback_transition_types", [])
            if isinstance(fb_types, list) and fb_types:
                transition_parts.append(f"兜底转场: {', '.join([str(t) for t in fb_types])}")

        packaging_parts = []
        if isinstance(packaging_style, dict):
            stickers = packaging_style.get("stickers", [])
            if isinstance(stickers, list) and stickers:
                packaging_parts.append(f"贴纸: {', '.join([str(s) for s in stickers])}")
            if packaging_style.get("cover_style"):
                packaging_parts.append(f"封面: {packaging_style['cover_style']}")
            if packaging_style.get("color_tone"):
                packaging_parts.append(f"色调: {packaging_style['color_tone']}")
            if packaging_style.get("visual_elements"):
                packaging_parts.append(f"视觉元素: {packaging_style['visual_elements']}")

        transfer_parts = []
        if isinstance(transfer_rules, dict):
            for key in ("must_keep", "can_adapt", "must_not_copy"):
                val = transfer_rules.get(key, [])
                if isinstance(val, list) and val:
                    transfer_parts.append(f"{key}: {'; '.join([str(v) for v in val])}")
                elif isinstance(val, str) and val:
                    transfer_parts.append(f"{key}: {val}")

        context_summary_lines = [
            f"用户输入的风格关键词: {user_input}" if user_input else "",
            f"知识库模板标识: style_id={kb_template.get('style_id', 'unknown')}",
            f"模板类型: {type_label}",
            f"核心剪辑公式: {core_formula}" if core_formula else "",
            "",
            "======== 结构槽位 (structural_slots) ========",
        ]
        if slots_text_parts:
            for idx, slot_text in enumerate(slots_text_parts):
                context_summary_lines.append(f"[slot {idx + 1}] {slot_text}")
        else:
            context_summary_lines.append("（模板中无详细slot定义，需要你根据核心公式补全）")

        if rhythm_parts:
            context_summary_lines.extend(["", "======== 节奏结构 (rhythm_structure) ========", *rhythm_parts])
        if caption_parts:
            context_summary_lines.extend(["", "======== 字幕风格 (caption_style_template) ========", *caption_parts])
        if transition_parts:
            context_summary_lines.extend(["", "======== 转场风格 (transition_style_template) ========", *transition_parts])
        if packaging_parts:
            context_summary_lines.extend(["", "======== 包装风格 (packaging_style_template) ========", *packaging_parts])
        if transfer_parts:
            context_summary_lines.extend(["", "======== 迁移规则 (transfer_rules) ========", *transfer_parts])
        if migration_parts:
            context_summary_lines.extend(["", "======== 迁移/兜底建议 (migration_suggestion) ========", *migration_parts])

        context_summary_lines.extend([
            "",
            "======== 重要约束 ========",
            "1. 任务：将上述知识库模板内容重新整理为符合 REFERENCE_ANALYZER_SYSTEM_PROMPT 定义的标准输出JSON格式",
            "2. 你需要像分析真实视频一样，重新组织所有字段（structural_slots、rhythm_curve、transition_events、shot_segments、migration_suggestion等）",
            "3. migration_suggestion 必须是字符串数组格式：['核心要点1的一句话描述', '核心要点2的一句话描述', ...]",
            "4. structural_slots 每个slot必须完整包含：slot_id、role、start_time、end_time、duration、creative_function、information_function、required_visual_type（字符串数组）、required_motion、shot_size、caption_requirement（含need_caption/style/position/semantic_role）、audio_sync（含beat_position/sfx）、transition_out、importance、copy_risk",
            "5. rhythm_curve 必须是数组格式：[{'time_range': [开始秒, 结束秒], 'pace': 'fast/medium/slow', 'avg_shot_duration': 数字, 'purpose': '该节奏段的功能描述'}]",
            "6. shot_segments 必须是数组格式，每个segment需包含：shot_id、start_time、end_time、summary、pace、transition_in、transition_out",
            "7. transition_events 必须是数组格式，每个event需包含：event_id、at_time、transition_type、from_shot_id、to_shot_id、from_summary、to_summary、strength、purpose",
            "8. transfer_rules 必须是字典格式：{'must_keep': [...], 'can_adapt': [...], 'must_not_copy': [...]}",
            "9. 所有时间字段必须是数字（秒），不能是字符串",
            "10. type_label 必须严格从以下列表中选一个：旅游转场、vlog旅拍、口播带货、剧情种草、product展示、教程教学、快剪混剪、生活记录、风景短片、其他",
            "11. 严格输出纯JSON，不要包含任何Markdown标记或解释文字",
        ])

        context_summary = "\n".join([line for line in context_summary_lines if line != ""])

        return json.dumps(
            {
                "task": "你现在不是在分析视频文件，而是在整理一份成熟的剪辑模板。请将下面的模板内容重新组织为符合标准输出格式的JSON，确保所有字段格式与正常解析参考视频时完全一致。",
                "analysis_instruction": f"用户输入关键词：{user_input}；模板类型：{type_label}",
                "knowledge_base_template_summary": context_summary,
                "constraints": {
                    "must_return_pure_json": True,
                    "must_choose_single_type_label": True,
                    "migration_suggestion_must_be_string_list": True,
                    "all_time_fields_must_be_numbers": True,
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
        # 自动修复所有被LLM错误加上引号的数字字符串，比如 "outro_start_time_seconds": "18.0" → "outro_start_time_seconds": 18.0
        # 用正则替换所有 ": \"数字.数字\"" 格式为 ": 数字.数字"
        repaired = re.sub(r':\s*"(\d+\.\d+)"', r': \1', repaired)
        # 同时替换整数情况 ": \"18\"" → ": 18"
        repaired = re.sub(r':\s*"(\d+)"', r': \1', repaired)
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
        duration_est = max(6.0, min(90.0, context.get("file_size_bytes", 0) / 1_000_000 * 4.5))
        basic.setdefault("file_total_duration_seconds", duration_est)
        basic.setdefault("core_content_effective_duration_seconds", max(0.0, duration_est - 2.0))
        basic.setdefault("outro_start_time_seconds", None)
        if basic.get("type_label") not in allowed_labels:
            basic["type_label"] = "生活记录"

        script = parsed.setdefault("script_structure", {})
        paragraphs = script.get("paragraphs")
        if not isinstance(paragraphs, list) or not paragraphs:
            script["paragraphs"] = [
                {"type": "hook", "content_summary": "开头快速建立主题，吸引注意力。", "start_time": 0.0, "end_time": duration_est * 0.18},
                {"type": "develop", "content_summary": "中段展开核心内容。", "start_time": duration_est * 0.18, "end_time": duration_est * 0.8},
                {"type": "cta", "content_summary": "结尾引导行动。", "start_time": duration_est * 0.8, "end_time": duration_est},
            ]
        if not isinstance(script.get("summary"), str):
            script["summary"] = context.get("notes", "自动生成样例脚本结构")

        rhythm_curve = parsed.get("rhythm_curve")
        if not isinstance(rhythm_curve, list):
            rhythm_curve = []
            parsed["rhythm_curve"] = rhythm_curve

        transition_style_template = parsed.get("transition_style_template", {})
        transition_events = self._normalize_transition_events(
            parsed.get("transition_events"),
            parsed.get("shot_segments"),
            duration_est,
            transition_style_template,
        )
        parsed["transition_events"] = transition_events
        parsed["shot_segments"] = self._normalize_shot_segments(
            parsed.get("shot_segments"),
            transition_events,
            duration_est,
            transition_style_template,
        )
        parsed["transition_style_template"] = self._normalize_transition_style_template(
            transition_style_template,
            transition_events,
        )

        # 新字段：优先生成按卡点/转场边界切分的 structural_slots，而不是粗粒度段落一对一
        existing_slots = parsed.get("structural_slots")
        if not isinstance(existing_slots, list) or len(existing_slots) < max(2, len(script["paragraphs"])):
            if transition_events:
                parsed["structural_slots"] = self._build_structural_slots_from_transition_events(
                    parsed["shot_segments"],
                    transition_events,
                    script["paragraphs"],
                    duration_est,
                )
            else:
                parsed["structural_slots"] = self._build_structural_slots_from_timeline_signals(
                    script["paragraphs"],
                    rhythm_curve,
                    duration_est,
                    transition_style_template,
                )
        else:
            parsed["structural_slots"] = self._normalize_structural_slots(
                existing_slots,
                script["paragraphs"],
                duration_est,
            )

        # 新字段：rhythm_curve 容错填充
        if "rhythm_curve" not in parsed or not isinstance(parsed.get("rhythm_curve"), list):
            parsed["rhythm_curve"] = [{"time_range": [0.0, duration_est], "pace": "medium", "avg_shot_duration": 1.5, "purpose": "正常节奏推进"}]

        # 新字段：caption_style_template 容错填充
        if "caption_style_template" not in parsed or not isinstance(parsed.get("caption_style_template"), dict):
            parsed["caption_style_template"] = {"subtitle_density": "中等", "font_style": "常规", "keyword_highlight": False, "animation": "fade_in"}

        # 新字段：transition_style_template 容错填充
        if "transition_style_template" not in parsed or not isinstance(parsed.get("transition_style_template"), dict):
            parsed["transition_style_template"] = {"main_transition_types": ["cut"], "usage_rule": "信息转折处使用切镜"}

        # 新字段：packaging_style_template 容错填充
        if "packaging_style_template" not in parsed or not isinstance(parsed.get("packaging_style_template"), dict):
            parsed["packaging_style_template"] = {"stickers": [], "cover_style": "普通截图"}

        # 新字段：transfer_rules 容错填充
        if "transfer_rules" not in parsed or not isinstance(parsed.get("transfer_rules"), dict):
            parsed["transfer_rules"] = {
                "must_keep": ["核心三段式结构"],
                "can_adapt": ["具体素材内容"],
                "must_not_copy": ["水印、原作者Logo"]
            }

        rhythm = parsed.setdefault("rhythm_structure", {})
        rhythm.setdefault("total_effective_shots", max(1, len(script["paragraphs"]) * 3))
        rhythm.setdefault("avg_shot_duration_seconds", round(max(duration_est / max(rhythm["total_effective_shots"], 1), 0.5), 2))
        rhythm.setdefault("shot_switch_pacing", "中节奏")
        rhythm.setdefault("highlight_position_seconds", [round(duration_est * 0.72, 2)] if duration_est else [0.0])
        rhythm.setdefault("pace_changes_description", "")

        packaging = parsed.setdefault("packaging_and_sound", {})
        packaging.setdefault("subtitle_density", "")
        packaging.setdefault("visual_elements", "")
        packaging.setdefault("transitions_feature", "")
        packaging.setdefault("audio_and_sfx", "")

        migration = parsed.get("migration_suggestion")
        if not isinstance(migration, list) or len(migration) < 2:
            parsed["migration_suggestion"] = []

        parsed.setdefault("schema_version", "1.0")
        parsed.setdefault("template_id", "ref_001")
        parsed.setdefault("confidence", 0.7)
        parsed.setdefault("risk_notes", [])

        return parsed

    def _normalize_transition_events(
        self,
        raw_events: Any,
        raw_shot_segments: Any,
        duration_est: float,
        transition_style_template: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        default_transition = "cut"
        transition_types = transition_style_template.get("main_transition_types", ["cut"]) if isinstance(transition_style_template, dict) else ["cut"]
        if isinstance(transition_types, list) and transition_types:
            default_transition = str(transition_types[0] or "cut")

        normalized: List[Dict[str, Any]] = []
        if isinstance(raw_events, list):
            for idx, event in enumerate(raw_events):
                if not isinstance(event, dict):
                    continue
                at_time = float(event.get("at_time", event.get("time", event.get("time_seconds", 0.0))))
                transition_type = self._normalize_transition_type(event.get("transition_type") or event.get("type") or default_transition)
                normalized.append({
                    "event_id": str(event.get("event_id") or f"transition_{str(idx + 1).zfill(2)}"),
                    "at_time": round(max(0.0, min(duration_est, at_time)), 2),
                    "transition_type": transition_type,
                    "from_shot_id": str(event.get("from_shot_id") or event.get("from_id") or f"shot_{str(idx + 1).zfill(2)}"),
                    "to_shot_id": str(event.get("to_shot_id") or event.get("to_id") or f"shot_{str(idx + 2).zfill(2)}"),
                    "from_summary": str(event.get("from_summary") or event.get("from_content") or ""),
                    "to_summary": str(event.get("to_summary") or event.get("to_content") or ""),
                    "strength": str(event.get("strength") or "medium"),
                    "purpose": str(event.get("purpose") or "推动镜头切换"),
                })

        if normalized:
            return sorted(normalized, key=lambda item: float(item["at_time"]))

        if isinstance(raw_shot_segments, list) and len(raw_shot_segments) >= 2:
            derived: List[Dict[str, Any]] = []
            sorted_shots = []
            for idx, shot in enumerate(raw_shot_segments):
                if not isinstance(shot, dict):
                    continue
                sorted_shots.append({
                    "shot_id": str(shot.get("shot_id") or f"shot_{str(idx + 1).zfill(2)}"),
                    "start_time": float(shot.get("start_time", 0.0)),
                    "end_time": float(shot.get("end_time", min(duration_est, float(shot.get('start_time', 0.0)) + 1.0))),
                    "summary": str(shot.get("summary") or shot.get("content_summary") or ""),
                    "transition_out": self._normalize_transition_type(shot.get("transition_out") or default_transition),
                })
            sorted_shots.sort(key=lambda item: item["start_time"])
            for idx in range(len(sorted_shots) - 1):
                current_shot = sorted_shots[idx]
                next_shot = sorted_shots[idx + 1]
                derived.append({
                    "event_id": f"transition_{str(idx + 1).zfill(2)}",
                    "at_time": round(max(0.0, min(duration_est, current_shot["end_time"])), 2),
                    "transition_type": self._normalize_transition_type(current_shot["transition_out"]),
                    "from_shot_id": current_shot["shot_id"],
                    "to_shot_id": next_shot["shot_id"],
                    "from_summary": current_shot["summary"],
                    "to_summary": next_shot["summary"],
                    "strength": "medium",
                    "purpose": "根据镜头边界推断转场",
                })
            return derived

        return []

    def _normalize_shot_segments(
        self,
        raw_shot_segments: Any,
        transition_events: List[Dict[str, Any]],
        duration_est: float,
        transition_style_template: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        default_transition = "cut"
        transition_types = transition_style_template.get("main_transition_types", ["cut"]) if isinstance(transition_style_template, dict) else ["cut"]
        if isinstance(transition_types, list) and transition_types:
            default_transition = str(transition_types[0] or "cut")

        normalized: List[Dict[str, Any]] = []
        if isinstance(raw_shot_segments, list):
            for idx, shot in enumerate(raw_shot_segments):
                if not isinstance(shot, dict):
                    continue
                start_time = float(shot.get("start_time", 0.0))
                end_time = float(shot.get("end_time", min(duration_est, start_time + 1.0)))
                if end_time <= start_time:
                    end_time = min(duration_est, start_time + 1.0)
                normalized.append({
                    "shot_id": str(shot.get("shot_id") or f"shot_{str(idx + 1).zfill(2)}"),
                    "start_time": round(max(0.0, min(duration_est, start_time)), 2),
                    "end_time": round(max(0.0, min(duration_est, end_time)), 2),
                    "summary": str(shot.get("summary") or shot.get("content_summary") or ""),
                    "pace": str(shot.get("pace") or "medium"),
                    "transition_in": self._normalize_transition_type(shot.get("transition_in") or "cut"),
                    "transition_out": self._normalize_transition_type(shot.get("transition_out") or default_transition),
                })
        if normalized:
            return sorted(normalized, key=lambda item: float(item["start_time"]))

        boundaries = [0.0]
        for event in transition_events:
            boundaries.append(float(event.get("at_time", 0.0)))
        boundaries.append(duration_est)
        boundaries = sorted({round(max(0.0, min(duration_est, point)), 2) for point in boundaries})

        inferred: List[Dict[str, Any]] = []
        for idx in range(len(boundaries) - 1):
            start_time = boundaries[idx]
            end_time = boundaries[idx + 1]
            if end_time <= start_time:
                continue
            in_transition = "cut" if idx == 0 else self._normalize_transition_type(transition_events[idx - 1].get("transition_type", default_transition))
            out_transition = default_transition
            if idx < len(transition_events):
                out_transition = self._normalize_transition_type(transition_events[idx].get("transition_type", default_transition))
            inferred.append({
                "shot_id": f"shot_{str(idx + 1).zfill(2)}",
                "start_time": round(start_time, 2),
                "end_time": round(end_time, 2),
                "summary": transition_events[idx - 1].get("to_summary", "") if idx > 0 else transition_events[0].get("from_summary", "") if transition_events else "",
                "pace": "fast",
                "transition_in": in_transition,
                "transition_out": out_transition,
            })
        return inferred

    def _build_structural_slots_from_transition_events(
        self,
        shot_segments: List[Dict[str, Any]],
        transition_events: List[Dict[str, Any]],
        paragraphs: List[Dict[str, Any]],
        duration_est: float,
    ) -> List[Dict[str, Any]]:
        transition_by_from = {
            str(event.get("from_shot_id")): event
            for event in transition_events
            if isinstance(event, dict)
        }
        total = max(len(shot_segments), 1)
        normalized_slots: List[Dict[str, Any]] = []
        role_counters: Dict[str, int] = {}

        for idx, shot in enumerate(sorted(shot_segments, key=lambda item: float(item.get("start_time", 0.0)))):
            start_time = float(shot.get("start_time", 0.0))
            end_time = float(shot.get("end_time", min(duration_est, start_time + 1.0)))
            if end_time <= start_time:
                continue
            summary = str(shot.get("summary") or self._find_paragraph_summary(paragraphs, start_time, end_time))
            role = self._role_from_shot_index(idx, total, summary)
            role_counters[role] = role_counters.get(role, 0) + 1
            transition_event = transition_by_from.get(str(shot.get("shot_id")), {})
            pace = str(shot.get("pace", "medium"))
            transition_out = self._normalize_transition_type(shot.get("transition_out") or transition_event.get("transition_type") or "cut")
            importance = self._importance_from_role(role, idx, total)
            normalized_slots.append({
                "slot_id": f"{role}_{str(role_counters[role]).zfill(2)}",
                "role": role,
                "start_time": round(start_time, 2),
                "end_time": round(end_time, 2),
                "duration": round(end_time - start_time, 2),
                "creative_function": str(transition_event.get("purpose") or f"承接{role}镜头功能"),
                "information_function": summary,
                "required_visual_type": self._visual_types_from_role(role),
                "required_motion": self._motion_from_pace(pace),
                "shot_size": self._shot_size_from_role(role),
                "caption_requirement": {
                    "need_caption": role in {"hook", "climax", "cta"},
                    "style": "重点字幕" if role in {"hook", "climax"} else "normal",
                    "position": "bottom_center",
                    "semantic_role": "转场卡点/情绪推进",
                },
                "audio_sync": {
                    "beat_position": self._beat_position_for_segment(idx, total, pace),
                    "sfx": "impact" if transition_out not in {"cut", "none"} else "none",
                },
                "transition_out": transition_out,
                "importance": importance,
                "copy_risk": "迁移镜头切换节奏与转场方法，不复制具体人物和台词",
            })
        return normalized_slots

    def _normalize_transition_style_template(
        self,
        template: Any,
        transition_events: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        normalized = template if isinstance(template, dict) else {}
        raw_types = normalized.get("main_transition_types", [])
        main_types: List[str] = []
        if isinstance(raw_types, list):
            for item in raw_types:
                transition_type = self._normalize_transition_type(item)
                if transition_type not in main_types:
                    main_types.append(transition_type)
        for event in transition_events:
            transition_type = self._normalize_transition_type(event.get("transition_type", "cut"))
            if transition_type not in main_types:
                main_types.append(transition_type)
        if not main_types:
            main_types = ["cut"]
        normalized["main_transition_types"] = main_types
        normalized["usage_rule"] = str(normalized.get("usage_rule") or "在节奏重拍、情绪切换或镜头承接处使用明确转场类型。")
        return normalized

    def _normalize_transition_type(self, raw_value: Any) -> str:
        value = str(raw_value or "cut").strip().lower()
        alias_map = {
            "硬切": "cut",
            "切镜": "cut",
            "直接切": "cut",
            "普通切": "cut",
            "叠化": "dissolve",
            "淡入淡出": "dissolve",
            "黑闪": "flash_black",
            "闪黑": "flash_black",
            "黑场闪切": "flash_black",
            "模糊": "blur",
            "模糊转场": "blur",
            "高斯模糊": "blur",
            "甩镜": "whip_pan",
            "甩鞭": "whip_pan",
            "whippan": "whip_pan",
            "下拉": "pull_down",
            "下拉转场": "pull_down",
            "上拉": "pull_up",
            "上拉转场": "pull_up",
            "左移": "slide_left",
            "右移": "slide_right",
            "左滑": "slide_left",
            "右滑": "slide_right",
            "横移": "slide_left",
            "变焦切": "zoom_cut",
            "推拉切": "zoom_cut",
            "遮罩": "mask_reveal",
            "遮罩揭示": "mask_reveal",
            "叠加": "overlay",
            "覆盖": "overlay",
            "旋转": "camera_spin",
            "转圈": "camera_spin",
        }
        canonical = alias_map.get(value, value)
        allowed = {
            "cut",
            "flash_black",
            "blur",
            "whip_pan",
            "pull_down",
            "pull_up",
            "slide_left",
            "slide_right",
            "zoom_cut",
            "dissolve",
            "overlay",
            "mask_reveal",
            "camera_spin",
        }
        return canonical if canonical in allowed else "cut"

    def _role_from_shot_index(self, idx: int, total: int, summary: str) -> str:
        if idx == 0:
            return "hook"
        if idx == total - 1:
            return "cta"
        if idx >= max(1, total - 2):
            return "climax"
        if "转场" in summary or "切换" in summary:
            return "context_build"
        return "develop"

    def _build_structural_slots_from_timeline_signals(
        self,
        paragraphs: List[Dict[str, Any]],
        rhythm_curve: List[Dict[str, Any]],
        duration_est: float,
        transition_style_template: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        slot_ranges: List[Dict[str, Any]] = []
        transition_types = transition_style_template.get("main_transition_types", ["cut"])
        default_transition = transition_types[0] if isinstance(transition_types, list) and transition_types else "cut"

        for idx, para in enumerate(paragraphs):
            para_start = float(para.get("start_time", 0.0))
            para_end = float(para.get("end_time", max(para_start + 1.0, duration_est)))
            para_type = str(para.get("type", "develop"))
            para_summary = str(para.get("content_summary", ""))
            matched_rhythm_segments = self._collect_rhythm_segments_for_range(rhythm_curve, para_start, para_end)

            if matched_rhythm_segments:
                for segment in matched_rhythm_segments:
                    seg_start = max(para_start, float(segment["start"]))
                    seg_end = min(para_end, float(segment["end"]))
                    if seg_end <= seg_start:
                        continue
                    pace = str(segment.get("pace", "medium"))
                    purpose = str(segment.get("purpose", para_summary))
                    slot_ranges.append({
                        "role": self._resolve_slot_role(para_type, idx, len(paragraphs), pace),
                        "start_time": round(seg_start, 2),
                        "end_time": round(seg_end, 2),
                        "information_function": para_summary or purpose,
                        "creative_function": purpose or f"承接{para_type}节奏推进",
                        "required_motion": self._motion_from_pace(pace),
                        "shot_size": self._shot_size_from_role(para_type),
                        "importance": self._importance_from_role(para_type, idx, len(paragraphs)),
                        "audio_sync": {
                            "beat_position": self._beat_position_for_segment(idx, len(matched_rhythm_segments), pace),
                            "sfx": "impact" if pace == "fast" else "none",
                        },
                        "transition_out": default_transition,
                    })
            else:
                slot_ranges.append({
                    "role": self._resolve_slot_role(para_type, idx, len(paragraphs), "medium"),
                    "start_time": round(para_start, 2),
                    "end_time": round(para_end, 2),
                    "information_function": para_summary,
                    "creative_function": f"承接{para_type}段落推进",
                    "required_motion": self._motion_from_pace("medium"),
                    "shot_size": self._shot_size_from_role(para_type),
                    "importance": self._importance_from_role(para_type, idx, len(paragraphs)),
                    "audio_sync": {"beat_position": "transition_downbeat", "sfx": "none"},
                    "transition_out": default_transition,
                })

        normalized_slots: List[Dict[str, Any]] = []
        role_counters: Dict[str, int] = {}
        for slot in sorted(slot_ranges, key=lambda item: float(item["start_time"])):
            role = str(slot["role"])
            role_counters[role] = role_counters.get(role, 0) + 1
            start_time = float(slot["start_time"])
            end_time = float(slot["end_time"])
            normalized_slots.append({
                "slot_id": f"{role}_{str(role_counters[role]).zfill(2)}",
                "role": role,
                "start_time": start_time,
                "end_time": end_time,
                "duration": round(max(0.0, end_time - start_time), 2),
                "creative_function": slot["creative_function"],
                "information_function": slot["information_function"],
                "required_visual_type": self._visual_types_from_role(role),
                "required_motion": slot["required_motion"],
                "shot_size": slot["shot_size"],
                "caption_requirement": {
                    "need_caption": role in {"hook", "climax", "cta"},
                    "style": "重点字幕" if role in {"hook", "climax"} else "normal",
                    "position": "bottom_center",
                    "semantic_role": "卡点字幕/情绪推进",
                },
                "audio_sync": slot["audio_sync"],
                "transition_out": slot["transition_out"],
                "importance": slot["importance"],
                "copy_risk": "迁移BGM卡点和转场组织方式，不复制原视频具体人物与台词",
            })
        return normalized_slots

    def _normalize_structural_slots(
        self,
        slots: List[Dict[str, Any]],
        paragraphs: List[Dict[str, Any]],
        duration_est: float,
    ) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for idx, slot in enumerate(slots):
            if not isinstance(slot, dict):
                continue
            role = str(slot.get("role") or slot.get("type") or "develop")
            start_time = float(slot.get("start_time", 0.0))
            end_time = float(slot.get("end_time", min(duration_est, start_time + 1.5)))
            if end_time <= start_time:
                end_time = min(duration_est, start_time + 1.5)
            normalized.append({
                "slot_id": str(slot.get("slot_id") or f"{role}_{str(idx + 1).zfill(2)}"),
                "role": role,
                "start_time": round(start_time, 2),
                "end_time": round(end_time, 2),
                "duration": round(end_time - start_time, 2),
                "creative_function": str(slot.get("creative_function") or f"承接{role}镜头功能"),
                "information_function": str(slot.get("information_function") or self._find_paragraph_summary(paragraphs, start_time, end_time)),
                "required_visual_type": slot.get("required_visual_type") or self._visual_types_from_role(role),
                "required_motion": str(slot.get("required_motion") or "normal"),
                "shot_size": str(slot.get("shot_size") or self._shot_size_from_role(role)),
                "caption_requirement": slot.get("caption_requirement") or {"need_caption": False, "style": "normal", "position": "center", "semantic_role": "信息补充"},
                "audio_sync": slot.get("audio_sync") or {"beat_position": "transition_downbeat", "sfx": "none"},
                "transition_out": str(slot.get("transition_out") or "cut"),
                "importance": str(slot.get("importance") or "medium"),
                "copy_risk": str(slot.get("copy_risk") or "迁移结构而非复制具体内容"),
            })
        return normalized

    def _collect_rhythm_segments_for_range(self, rhythm_curve: List[Dict[str, Any]], start: float, end: float) -> List[Dict[str, Any]]:
        matched: List[Dict[str, Any]] = []
        for segment in rhythm_curve:
            if not isinstance(segment, dict):
                continue
            time_range = segment.get("time_range")
            if not isinstance(time_range, list) or len(time_range) < 2:
                continue
            seg_start = float(time_range[0])
            seg_end = float(time_range[1])
            if seg_end <= start or seg_start >= end:
                continue
            matched.append({
                "start": seg_start,
                "end": seg_end,
                "pace": segment.get("pace", "medium"),
                "purpose": segment.get("purpose", ""),
            })
        return matched

    def _resolve_slot_role(self, para_type: str, idx: int, total: int, pace: str) -> str:
        if idx == 0:
            return "hook"
        if idx == total - 1:
            return "cta" if para_type == "cta" else "climax"
        if pace == "fast":
            return "context_build"
        if pace == "slow":
            return "emotion_climax"
        return para_type or "develop"

    def _motion_from_pace(self, pace: str) -> str:
        if pace == "fast":
            return "快切 / 强转场 / 节拍推进"
        if pace == "slow":
            return "停留 / 慢推 / 情绪释放"
        return "常规推进 / 轻转场"

    def _shot_size_from_role(self, role: str) -> str:
        if role in {"hook", "cta"}:
            return "close_up"
        if role in {"climax", "emotion_climax"}:
            return "medium_close"
        return "medium"

    def _importance_from_role(self, role: str, idx: int, total: int) -> str:
        if idx == 0 or idx == total - 1 or role in {"hook", "climax", "emotion_climax", "cta"}:
            return "high"
        return "medium"

    def _beat_position_for_segment(self, idx: int, total: int, pace: str) -> str:
        if idx == 0:
            return "first_strong_beat"
        if idx == total - 1:
            return "transition_downbeat"
        if pace == "fast":
            return "bar_change"
        if pace == "slow":
            return "phrase_release"
        return "any"

    def _visual_types_from_role(self, role: str) -> List[str]:
        if role == "hook":
            return ["结果展示", "高识别主体", "转场起始镜头"]
        if role in {"climax", "emotion_climax"}:
            return ["情绪高潮画面", "关系推进镜头", "长停留主体镜头"]
        if role == "cta":
            return ["收束镜头", "落点画面", "结尾情绪镜头"]
        return ["过渡画面", "承接镜头", "情节推进镜头"]

    def _find_paragraph_summary(self, paragraphs: List[Dict[str, Any]], start_time: float, end_time: float) -> str:
        for para in paragraphs:
            para_start = float(para.get("start_time", 0.0))
            para_end = float(para.get("end_time", 0.0))
            if start_time >= para_start and end_time <= para_end + 0.01:
                return str(para.get("content_summary", ""))
        return ""

    def _parse_and_repair(self, content: str) -> (Dict[str, Any], List[str]):
        repair_notes: List[str] = []
        json_candidate = self._extract_json(content)
        if json_candidate != content:
            repair_notes.append("extracted_json_object")

        candidates: List[tuple[str, str]] = [("raw_json_candidate", json_candidate)]

        light_repaired = self._light_repair(json_candidate)
        if light_repaired != json_candidate:
            repair_notes.append("light_json_repair")
            candidates.append(("light_repair", light_repaired))

        common_repaired = self._repair_common_json_issues(light_repaired)
        if common_repaired != light_repaired:
            repair_notes.append("common_json_repair")
            candidates.append(("common_json_repair", common_repaired))

        for strategy_name, candidate in candidates:
            try:
                parsed = json.loads(candidate)
                if strategy_name != "raw_json_candidate":
                    repair_notes.append(f"parse_strategy={strategy_name}")
                return parsed, repair_notes
            except json.JSONDecodeError:
                continue

        python_literal_candidate = self._repair_to_python_literal(common_repaired)
        try:
            parsed = ast.literal_eval(python_literal_candidate)
        except (SyntaxError, ValueError) as exc:
            raise RuntimeError(f"ReferenceAnalyzerAgent could not parse model JSON: {str(exc)}") from exc

        if not isinstance(parsed, dict):
            raise RuntimeError("ReferenceAnalyzerAgent repaired result is not a JSON object.")

        repair_notes.append("parse_strategy=python_literal_eval")
        return parsed, repair_notes

    def _light_repair(self, content: str) -> str:
        repaired = content.replace("```json", "").replace("```", "").strip()
        repaired = repaired.replace("\u201c", '"').replace("\u201d", '"')
        repaired = repaired.replace("\u2018", '"').replace("\u2019", '"')
        repaired = repaired.replace("\ufeff", "")
        repaired = repaired.replace("\r\n", "\n").replace("\r", "\n")
        # 自动修复LLM经常犯的低级错误：把数字用双引号包裹起来，比如 "outro_start_time_seconds": "18.0"
        # 把所有 "数字" 这样的字符串替换成纯数字
        repaired = re.sub(r'"(-?\d+\.\d+)"', r'\1', repaired)
        repaired = re.sub(r'"(-?\d+)"', r'\1', repaired)
        return repaired

    def _escape_literal_quotes_inside_strings(self, content: str) -> str:
        """状态机自动转义JSON字符串内部的裸双引号。
        对每一对完整的属性键值对（"key": ...），值字符串内部的所有未转义引号自动加反斜杠转义。
        专门解决LLM输出的中文台词里带裸引号导致JSON崩溃的问题。
        """
        result: list[str] = []
        pos = 0
        n = len(content)
        while pos < n:
            # 查找下一个键名开始位置：匹配 "key": 模式
            key_start = content.find('"', pos)
            if key_start == -1:
                result.append(content[pos:])
                break
            # 把键名之前的所有内容原样写入
            result.append(content[pos:key_start+1])
            pos = key_start + 1
            # 遍历键名直到遇到结束引号
            while pos < n and content[pos] != '"':
                result.append(content[pos])
                pos += 1
            # 键名结束引号
            result.append('"')
            pos += 1
            # 跳过所有空白和冒号
            while pos < n and content[pos] in ' \t\n\r:':
                result.append(content[pos])
                pos += 1
            # 如果接下来是字符串值，进入转义模式
            if pos < n and content[pos] == '"':
                result.append('"')
                pos += 1
                # 在值字符串内部，转义所有裸双引号
                escaped = False
                while pos < n:
                    c = content[pos]
                    if escaped:
                        result.append(c)
                        escaped = False
                        pos += 1
                    elif c == '\\':
                        result.append(c)
                        escaped = True
                        pos += 1
                    elif c == '"':
                        # 检查这个引号后面是不是合法的JSON结束符（逗号 / ] / } / 空白后接它们）
                        # 如果不是，说明它是字符串内部的裸引号，需要转义
                        lookahead = pos + 1
                        while lookahead < n and content[lookahead] in ' \t\n\r':
                            lookahead += 1
                        if lookahead < n and content[lookahead] in ',}]':
                            # 正常的值结束引号，直接退出
                            result.append('"')
                            pos += 1
                            break
                        else:
                            # 裸双引号，转义它
                            result.append('\\"')
                            pos += 1
                    else:
                        result.append(c)
                        pos += 1
            else:
                # 非字符串值，原样跳过
                continue
        return "".join(result)

    def _repair_common_json_issues(self, content: str) -> str:
        repaired = content
        repaired = repaired.replace("，", ",").replace("：", ":")
        repaired = re.sub(r",(\s*[}\]])", r"\1", repaired)
        repaired = re.sub(r"([}\]])\s*([{\[])", r"\1, \2", repaired)
        repaired = re.sub(r'("\s*)\n(\s*")', r'\1, \2', repaired)
        repaired = self._escape_literal_quotes_inside_strings(repaired)
        repaired = self._close_unbalanced_brackets(repaired)
        return repaired

    def _repair_to_python_literal(self, content: str) -> str:
        repaired = content
        repaired = re.sub(r"\btrue\b", "True", repaired)
        repaired = re.sub(r"\bfalse\b", "False", repaired)
        repaired = re.sub(r"\bnull\b", "None", repaired)
        return repaired

    def _close_unbalanced_brackets(self, content: str) -> str:
        stack: List[str] = []
        in_string = False
        escaped = False
        for char in content:
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue

            if char == '"':
                in_string = True
            elif char == "{":
                stack.append("}")
            elif char == "[":
                stack.append("]")
            elif char in {"}", "]"} and stack and stack[-1] == char:
                stack.pop()

        if not stack:
            return content
        return content + "".join(reversed(stack))
