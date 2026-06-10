from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("KnowledgeBaseRetrievalService")


class KnowledgeBaseRetrievalService:
    """风格关键词检索知识库剪辑模板服务，替代必须上传参考样例的路径"""

    def __init__(self, kb_root: Optional[str] = None):
        if kb_root:
            self._kb_root = Path(kb_root)
        else:
            # backend/app/services/ 往上跳3层到项目根目录 emo_transfer/
            self._kb_root = Path(__file__).resolve().parents[3] / "knowledge_base"
        self._style_templates_dir = self._kb_root / "style_templates"
        logger.info(f"[KB_RETRIEVAL] 知识库检索服务初始化，模板目录: {self._style_templates_dir}")
        self._style_templates_dir.mkdir(parents=True, exist_ok=True)
        self._templates_cache: List[Dict[str, Any]] | None = None

    def _load_all_templates(self) -> List[Dict[str, Any]]:
        """加载知识库中所有已沉淀的风格模板"""
        if self._templates_cache is not None:
            return self._templates_cache

        all_templates: List[Dict[str, Any]] = []
        for json_file in self._style_templates_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    template = json.load(f)
                    all_templates.append(template)
                    logger.info(f"[KB_RETRIEVAL] 已加载模板: {template.get('style_id')} / {template.get('style_name')}")
            except Exception as e:
                logger.warning(f"[KB_RETRIEVAL] 模板文件读取失败 {json_file.name}: {e}")
        self._templates_cache = all_templates
        logger.info(f"[KB_RETRIEVAL] 全部模板加载完成，总数: {len(all_templates)}")
        return all_templates

    def _flatten_all_strings(self, obj: Any) -> str:
        """递归遍历整个JSON对象，把所有字符串值拼接成一个超长全文本池"""
        parts: list[str] = []
        if isinstance(obj, str):
            parts.append(obj)
        elif isinstance(obj, dict):
            for v in obj.values():
                parts.append(self._flatten_all_strings(v))
        elif isinstance(obj, list):
            for item in obj:
                parts.append(self._flatten_all_strings(item))
        return " ".join(parts)

    def _calculate_match_score(self, user_prompt: str, template: Dict[str, Any]) -> float:
        """全字段全文本匹配：整份模板所有字符串全部参与搜索，不限制任何字段"""
        prompt_lower = user_prompt.lower()
        score = 0.0

        # 把整份JSON模板里所有字符串全部提取出来，做成全量匹配池
        full_text_pool = self._flatten_all_strings(template).lower()
        logger.debug(f"[KB_RETRIEVAL] 全字段文本池总长度: {len(full_text_pool)}")

        # 1. 用户输入里出现任意2字词，只要在全文本池中命中，每命中一个加0.12，上限0.6
        prompt_keywords = self._extract_keywords(prompt_lower)
        hit_count = 0
        for kw in prompt_keywords:
            if kw in full_text_pool:
                hit_count += 1
                logger.debug(f"[KB_RETRIEVAL] 关键词命中全字段池 +0.12: {kw}")
        score += min(hit_count * 0.12, 0.6)

        # 兜底保险逻辑：逐字符遍历用户输入，只要任意连续2个汉字出现在全文本池里，至少给0.3保底分，绝对不可能0分
        if hit_count == 0:
            for i in range(len(prompt_lower) - 1):
                two_chars = prompt_lower[i:i+2]
                if two_chars in full_text_pool:
                    score += 0.3
                    logger.info(f"[KB_RETRIEVAL] 兜底保险命中 +0.3: {two_chars}")
                    break

        # 2. 用户输入整句作为长片段，命中全文本池直接加0.4
        if len(prompt_lower) >= 4 and prompt_lower in full_text_pool:
            score += 0.4
            logger.debug(f"[KB_RETRIEVAL] 长片段全字段完全命中 +0.4")

        logger.info(f"[KB_RETRIEVAL] 最终得分: {score}")
        return min(score, 1.0)

    def _extract_keywords(self, user_prompt: str) -> List[str]:
        """中文全2字词生成：从用户输入自然语言里生成所有可能的连续2字组合，不会漏任何可能的关键词"""
        import re
        cleaned = re.sub(r'[^\w\u4e00-\u9fff]', '', user_prompt).lower()
        bigrams = []
        for i in range(len(cleaned) - 1):
            bigram = cleaned[i:i+2]
            bigrams.append(bigram)
        logger.debug(f"[KB_RETRIEVAL] 生成全部2字词: {bigrams}")
        return bigrams

    def retrieve_best_matching_template(self, user_prompt: str) -> Dict[str, Any]:
        """主入口：根据用户输入的风格关键词，返回最匹配的现成剪辑模板"""
        logger.info(f"[KB_RETRIEVAL] 开始检索，用户输入: {user_prompt}")
        all_templates = self._load_all_templates()

        if len(all_templates) == 0:
            logger.warning("[KB_RETRIEVAL] 知识库为空，没有任何可复用模板")
            return {
                "success": False,
                "matched": False,
                "match_score": 0.0,
                "style_id": None,
                "template": None,
                "reason": "知识库为空，请先上传样例视频沉淀模板"
            }

        scored_templates: List[Tuple[float, Dict[str, Any]]] = []
        for template in all_templates:
            score = self._calculate_match_score(user_prompt, template)
            scored_templates.append((score, template))

        # 按得分降序排序
        scored_templates.sort(key=lambda x: x[0], reverse=True)
        best_score, best_template = scored_templates[0]

        logger.info(f"[KB_RETRIEVAL] 最高匹配得分: {best_score}, style_id={best_template.get('style_id')}")

        # 得分阈值 >=0.3 判定为匹配成功
        if best_score >= 0.3:
            return {
                "success": True,
                "matched": True,
                "match_score": best_score,
                "style_id": best_template.get("style_id"),
                "template": best_template,
                "top3_candidates": [
                    {
                        "style_id": t[1].get("style_id"),
                        "style_name": t[1].get("style_name"),
                        "score": t[0]
                    } for t in scored_templates[:3]
                ]
            }
        else:
            return {
                "success": True,
                "matched": False,
                "match_score": best_score,
                "style_id": best_template.get("style_id"),
                "template": best_template,
                "top3_candidates": [
                    {
                        "style_id": t[1].get("style_id"),
                        "style_name": t[1].get("style_name"),
                        "score": t[0]
                    } for t in scored_templates[:3]
                ],
                "reason": "匹配得分低于阈值0.3，建议上传参考样例视频生成新模板"
            }

    def _normalize_fallback_strategy_to_migration_list(self, fallback_strategy: Any) -> List[str]:
        """将知识库 fallback_strategy（dict列表或任意格式）统一转换为字符串列表格式的 migration_suggestion"""
        result: List[str] = []
        if not fallback_strategy:
            return result

        items: List[Any] = []
        if isinstance(fallback_strategy, list):
            items = fallback_strategy
        elif isinstance(fallback_strategy, dict):
            items = [fallback_strategy]
        else:
            items = [fallback_strategy]

        for item in items:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                prob = str(item.get("problem", "")).strip()
                sol = str(item.get("solution", "")).strip()
                if prob and sol:
                    result.append(f"{prob} -> {sol}")
                elif prob:
                    result.append(prob)
                elif sol:
                    result.append(sol)
                else:
                    try:
                        result.append(str(item))
                    except Exception:
                        pass
            else:
                try:
                    result.append(str(item))
                except Exception:
                    pass

        return result

    def convert_style_template_to_reference_analysis(self, style_template: Dict[str, Any]) -> Dict[str, Any]:
        """将知识库 style template 反向转换成 ReferenceAnalyzer Agent 输出格式，全流程直接复用"""
        logger.info(f"[KB_RETRIEVAL] 转换style_template为reference_analysis格式, style_id={style_template.get('style_id')}")

        duration_range = style_template.get("target_duration_range", [15, 20])
        avg_duration = (duration_range[0] + duration_range[1]) / 2 if len(duration_range) >= 2 else 17.0

        type_label_val = style_template.get("type_label", "其他")
        fallback_strategy = style_template.get("fallback_strategy", [])
        normalized_migration = self._normalize_fallback_strategy_to_migration_list(fallback_strategy)

        return {
            "schema_version": "1.0",
            "template_id": style_template.get("style_id", "kb_template_001"),
            "type_label": type_label_val,
            "source": "knowledge_base_retrieval",
            "summary": style_template.get("core_formula", "知识库检索到的经典剪辑公式"),
            "migration_suggestion": normalized_migration,
            "video_basic_info": {
                "file_total_duration_seconds": avg_duration,
                "core_content_effective_duration_seconds": avg_duration,
                "outro_start_time_seconds": None,
                "type_label": type_label_val
            },
            "script_structure": {
                "summary": style_template.get("core_formula", "知识库检索到的经典剪辑公式"),
                "paragraphs": []
            },
            "structural_slots": style_template.get("structural_slots", []),
            "rhythm_curve": [],
            "rhythm_structure": style_template.get("rhythm_structure", {}),
            "caption_style_template": style_template.get("caption_style_template", {}),
            "transition_style_template": style_template.get("transition_style_template", {}),
            "packaging_style_template": style_template.get("packaging_style_template", {}),
            "packaging_and_sound": {},
            "transition_events": [],
            "shot_segments": [],
            "transfer_rules": style_template.get("transfer_rules", {}),
            "confidence": 0.75,
            "is_kb_template": True
        }
