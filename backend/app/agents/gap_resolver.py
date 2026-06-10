from __future__ import annotations

from copy import deepcopy
import json
from typing import TYPE_CHECKING, Any, Dict, List

from backend.app.agents.base_agent import BaseAgent
from backend.app.core.multi_variant import (
    ensure_resolved_gap_variant_contract,
    ensure_slot_match_variant_contract,
    get_variant_catalog,
    get_variant_payload,
)
from backend.app.prompts.gap_resolver import GAP_RESOLVER_PROMPT
from backend.app.providers.ark_chat import ArkChatProvider

if TYPE_CHECKING:
    from backend.app.core.shared_memory import SessionSharedMemory


STRATEGY_PRIORITY_ORDER = [
    "reuse",
    "static_graphic",
    "text_card",
    "brand_asset",
    "structure_reorder",
    "ai_generate",
    "ask_user"
]


class GapResolverAgent(BaseAgent):
    """缺口补齐专家，按7级优先级策略解决所有素材缺口"""

    read_keys = ["slot_matches", "asset_index"]
    write_keys = ["resolved_gaps"]

    def __init__(self, ark_chat_provider: ArkChatProvider):
        super().__init__()
        self.ark_chat_provider = ark_chat_provider

    def is_available(self) -> bool:
        return self.ark_chat_provider.config.is_configured

    def analyze(self, shared_memory: SessionSharedMemory) -> Dict[str, Any]:
        slot_matches = shared_memory.get("slot_matches")
        asset_index = shared_memory.get("asset_index") or {"assets": []}
        self.emit_phase("think", "检查缺口", "准备读取插槽匹配结果并识别仍未填充的位置。")

        if not slot_matches:
            return ensure_resolved_gap_variant_contract({
                "_skip_reason": "missing_dependency",
                "warning": "缺少slot_matches，跳过GapResolverAgent",
                "resolved_gaps": [],
                "still_unresolved": [],
                "confidence": 0.0
            })

        if not self.is_available():
            raise RuntimeError("GapResolverAgent: Ark LLM 未配置，无法执行缺口补齐。")

        normalized_slot_matches = ensure_slot_match_variant_contract(slot_matches)
        variant_payloads: Dict[str, Dict[str, Any]] = {}
        total_unfilled = 0
        
        for variant_spec in get_variant_catalog(normalized_slot_matches):
            if variant_spec["variant_id"] != "structure":
                variant_payloads[variant_spec["variant_id"]] = {
                    "variant_id": variant_spec["variant_id"],
                    "label": variant_spec["label"],
                    "_lazy": True,
                    "_note": "该变体缺口补全尚未执行，调用 resolve_gaps(variant_id) 后才会实际计算",
                    "resolved_gaps": [],
                    "still_unresolved": [],
                    "confidence": 0.0,
                    "ready": False,
                }
                continue
                
            variant_slot_matches = get_variant_payload(normalized_slot_matches, variant_spec["variant_id"])
            unfilled_slots = variant_slot_matches.get("unfilled_slots", [])
            if not unfilled_slots:
                unfilled_slots = variant_slot_matches.get("gaps", [])
            total_unfilled += len(unfilled_slots) if isinstance(unfilled_slots, list) else 0

            if not unfilled_slots:
                variant_payloads[variant_spec["variant_id"]] = {
                    "resolved_gaps": [],
                    "still_unresolved": [],
                    "confidence": 1.0,
                    "variant_id": variant_spec["variant_id"],
                    "label": variant_spec["label"],
                }
                continue

            self.emit_phase(
                "plan",
                "选择补口策略",
                f"{variant_spec['label']} 当前共有 {len(unfilled_slots)} 个缺口，按优先级尝试复用、图卡、重排等策略。",
            )
            compact_assets = self._compact_assets_for_gap_resolve(asset_index.get("assets", []))
            user_prompt = json.dumps({
                "task": "基于以下unfilled_slots缺口列表和精简素材库，按7级优先级策略为每个缺口生成可执行补齐方案。",
                "variant_id": variant_spec["variant_id"],
                "variant_label": variant_spec["label"],
                "unfilled_slots": unfilled_slots,
                "all_assets": compact_assets,
                "strategy_priority": STRATEGY_PRIORITY_ORDER,
                "constraints": {
                    "must_pick_lowest_possible_strategy": True,
                    "no_empty_params": True,
                    "output_must_be_executable": True
                }
            }, ensure_ascii=False)

            self.emit_phase("action", "生成补口方案", f"为 {variant_spec['label']} 生成可执行补口建议。")
            response_json = self.ark_chat_provider.chat(
                GAP_RESOLVER_PROMPT,
                user_prompt,
                temperature=0.1,
                on_delta=self.emit_stream_delta,
            )
            content = self.ark_chat_provider.extract_text(response_json)
            self.emit_phase("observation", "整理补口结果", f"{variant_spec['label']} 模型返回完成，开始规范化输出。")
            parsed = self._parse_and_repair(content)
            validated = self._validate_and_fill(parsed, unfilled_slots)
            validated["variant_id"] = variant_spec["variant_id"]
            validated["label"] = variant_spec["label"]
            variant_payloads[variant_spec["variant_id"]] = validated

        result = ensure_resolved_gap_variant_contract({
            "schema_version": "2.0",
            "default_variant_id": "structure",
            "variants": variant_payloads,
        })
        result["_agent_meta"] = {
            "source": "gap-resolver-agent",
            "resolved_count": len(result.get("resolved_gaps", [])),
            "variant_count": len(variant_payloads),
            "unfilled_count": total_unfilled,
        }
        return result

    def _compact_assets_for_gap_resolve(self, assets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
                })
            compact_assets.append({
                "asset_id": asset.get("asset_id"),
                "material_id": asset.get("material_id"),
                "duration": asset.get("duration"),
                "content_type": asset.get("content_type"),
                "tags": asset.get("tags"),
                "segments": compact_segments,
            })
        return compact_assets

    def _robust_json_parse(self, raw_content: str) -> Dict[str, Any]:
        """工业级鲁棒JSON解析器，处理LLM生成的各种异常格式"""
        import re
        import logging

        logger = logging.getLogger("GapResolverAgent")
        logger.info(f"[JSON_PARSE] 原始内容长度: {len(raw_content)}")

        step1 = raw_content
        # 移除markdown代码块标记
        step1 = re.sub(r'```(json)?', '', step1, flags=re.IGNORECASE).strip()
        logger.info(f"[JSON_PARSE_STEP1] 移除代码块标记后长度: {len(step1)}")

        step2 = step1
        # 替换全角引号
        step2 = step2.replace("\u201c", '"').replace("\u201d", '"')
        step2 = step2.replace("\u2018", '"').replace("\u2019", '"')
        logger.info(f"[JSON_PARSE_STEP2] 全角引号替换完成")

        step3 = step2
        # 移除单行注释 // 或 #
        step3 = re.sub(r'//.*?$', '', step3, flags=re.MULTILINE)
        step3 = re.sub(r'#.*?$', '', step3, flags=re.MULTILINE)
        logger.info(f"[JSON_PARSE_STEP3] 注释剥离完成")

        step4 = step3
        # 查找JSON边界
        start = step4.find("{")
        end = step4.rfind("}")
        if start == -1 or end == -1 or end <= start:
            logger.error(f"[JSON_PARSE_ERROR] 无法找到有效的JSON边界, start={start}, end={end}")
            raise ValueError("no valid JSON boundary found")
        step4 = step4[start:end + 1]
        logger.info(f"[JSON_PARSE_STEP4] 提取JSON子串, 范围 [{start}:{end+1}], 内容片段前200: {step4[:200]}")

        step5 = step4
        # 处理尾随逗号: 对象和数组中最后一个元素后面多余的逗号
        step5 = re.sub(r',\s*([}\]])', r'\1', step5)
        logger.info(f"[JSON_PARSE_STEP5] 尾随逗号清理完成")

        step6 = step5
        # 转义控制字符：换行符在字符串内部未转义的场景
        def escape_control_chars(match):
            s = match.group(0)
            s = s.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
            return s
        # 对引号内的内容进行转义修正
        step6 = re.sub(r'"[^"\\]*(\\.[^"\\]*)*"', escape_control_chars, step6)
        logger.info(f"[JSON_PARSE_STEP6] 控制字符转义完成")

        # 尝试直接解析
        try:
            result = json.loads(step6)
            logger.info(f"[JSON_PARSE_SUCCESS] 直接解析成功")
            return result
        except json.JSONDecodeError as e:
            logger.warning(f"[JSON_PARSE_ERROR] 首次解析失败 at pos {e.pos}: {e.msg}")

            # 回退策略：从错误位置截断，逐级向后寻找有效的闭合括号
            error_pos = e.pos
            for truncate_offset in [0, 10, 50, 200, 500]:
                candidate_end = error_pos + truncate_offset
                if candidate_end >= len(step6):
                    candidate_end = len(step6) - 1
                candidate = step6[:candidate_end]
                candidate += "}"
                try:
                    result = json.loads(candidate)
                    logger.info(f"[JSON_PARSE_SUCCESS] 回退截断策略成功, 截断位置: {candidate_end}")
                    return result
                except json.JSONDecodeError:
                    continue
            raise

    def _parse_and_repair(self, content: str) -> Dict[str, Any]:
        """带详细日志和3次重试的JSON解析入口"""
        import time
        import logging
        logger = logging.getLogger("GapResolverAgent")
        logger.info(f"[GAP_PARSE_START] 开始解析LLM返回内容, 总长度: {len(content)}")
        if len(content) < 500:
            logger.info(f"[GAP_PARSE_RAW] 原始内容: {content}")
        else:
            logger.info(f"[GAP_PARSE_RAW_PREVIEW] 前500字符: {content[:500]}")

        last_exception: Exception | None = None
        # 三次重试机制，每次使用不同的清洗策略
        strategies = [
            "robust_full",
            "strict_clean",
            "greedy_extract"
        ]

        for attempt in range(1, 4):
            strategy = strategies[attempt - 1]
            logger.info(f"[GAP_PARSE_RETRY] 第 {attempt}/3 次尝试, 使用策略: {strategy}")
            time.sleep(0.05)

            try:
                if strategy == "robust_full":
                    result = self._robust_json_parse(content)
                elif strategy == "strict_clean":
                    import re
                    # 极端严格清洗：仅保留纯JSON，删除所有非结构文本
                    cleaned = re.sub(r'[^a-zA-Z0-9\{\}\[\]":,._\-\s\u4e00-\u9fff]', '', content)
                    result = json.loads(cleaned)
                elif strategy == "greedy_extract":
                    import re
                    # 贪婪提取：递归查找最大可解析的JSON对象
                    max_len = 0
                    best_json = None
                    for match in re.finditer(r'\{.*\}', content, re.DOTALL):
                        try:
                            candidate = json.loads(match.group(0))
                            if len(match.group(0)) > max_len:
                                max_len = len(match.group(0))
                                best_json = candidate
                        except:
                            pass
                    if best_json is None:
                        raise ValueError("greedy extract no valid json found")
                    result = best_json

                logger.info(f"[GAP_PARSE_SUCCESS] 第 {attempt} 次尝试解析完全成功")
                return result

            except Exception as e:
                last_exception = e
                logger.warning(f"[GAP_PARSE_FAIL] 第 {attempt} 次尝试失败: {type(e).__name__}: {str(e)}")

        logger.error(f"[GAP_PARSE_FINAL_FAIL] 全部3次重试全部失败，最终异常: {last_exception}")
        raise RuntimeError(f"GapResolverAgent JSON解析全部重试失败: {str(last_exception)}") from last_exception

    def _validate_and_fill(self, parsed: Dict[str, Any], original_unfilled: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not isinstance(parsed, dict):
            parsed = {}

        parsed.setdefault("schema_version", "1.0")
        parsed.setdefault("resolved_gaps", [])
        parsed.setdefault("still_unresolved", [])
        parsed.setdefault("confidence", 0.7)

        for gap in parsed.get("resolved_gaps", []):
            gap.setdefault("slot", gap.get("slot_id", "unknown"))
            gap.setdefault("strategy", gap.get("chosen_strategy", "reuse"))
            gap.setdefault("params", gap.get("resolution", {}).get("edit_params", {}))
            strat = gap.get("chosen_strategy", gap.get("strategy"))
            if "strategy_priority_level" not in gap and strat in STRATEGY_PRIORITY_ORDER:
                gap["strategy_priority_level"] = STRATEGY_PRIORITY_ORDER.index(strat) + 1

        resolved_ids = {g.get("slot_id", g.get("slot")) for g in parsed.get("resolved_gaps", [])}
        for g in original_unfilled:
            sid = g.get("slot_id", g.get("slot", "unknown"))
            if sid not in resolved_ids and not any(s.get("slot_id", s.get("slot")) == sid for s in parsed.get("still_unresolved", [])):
                parsed["still_unresolved"].append({
                    "slot_id": sid,
                    "need": g.get("need", "未处理缺口"),
                    "reason": "自动兜底未处理"
                })

        return parsed
